import json
import socket
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from domain_checker.logic import (
    check_domain,
    check_domains,
    contains_any_keyword,
    normalize_domain,
)
from domain_checker.main import handle_domain_check, handle_single_domain_check


DOMAIN_CONTRACT = json.loads(
    (Path(__file__).parents[3] / "tests/contracts/domain_names.json").read_text()
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Example.COM", "example.com"),
        ("example.com.", "example.com"),
        ("xn--bcher-kva.de", "xn--bcher-kva.de"),
    ],
)
def test_normalize_domain_removes_transport_details(raw, expected):
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize("case", DOMAIN_CONTRACT)
def test_worker_obeys_shared_domain_contract(case):
    if case["normalized"] is None:
        with pytest.raises(ValueError):
            normalize_domain(case["input"])
    else:
        assert normalize_domain(case["input"]) == case["normalized"]


def test_dns_success_is_registered_without_whois():
    with patch("domain_checker.logic.dns_lookup_with_timeout", return_value="203.0.113.1"), patch(
        "domain_checker.logic.subprocess.run"
    ) as whois:
        assert check_domain("example.com") == "registered"
    whois.assert_not_called()


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("No match for EXAMPLE.TEST", "free"),
        ("Domain Name: EXAMPLE.COM\nRegistrar: Example", "registered"),
        ("unexpected registry response", "non conclusive"),
    ],
)
def test_whois_output_is_parsed_conservatively(output, expected):
    with patch(
        "domain_checker.logic.dns_lookup_with_timeout", side_effect=socket.gaierror
    ), patch(
        "domain_checker.logic.subprocess.run",
        return_value=subprocess.CompletedProcess(["whois"], 0, stdout=output, stderr=""),
    ):
        assert check_domain("example.test") == expected


def test_whois_timeout_uses_safe_partial_output():
    timeout = subprocess.TimeoutExpired("whois", 3, output="Status: available")
    with patch(
        "domain_checker.logic.dns_lookup_with_timeout", side_effect=socket.gaierror
    ), patch("domain_checker.logic.subprocess.run", side_effect=timeout):
        assert check_domain("example.test") == "free"


def test_dns_timeout_does_not_start_a_second_slow_lookup():
    with patch(
        "domain_checker.logic.dns_lookup_with_timeout", side_effect=socket.timeout
    ), patch("domain_checker.logic.subprocess.run") as whois:
        assert check_domain("example.test") == "non conclusive"
    whois.assert_not_called()


def test_batch_and_queue_handlers_preserve_one_result_per_input():
    with patch(
        "domain_checker.logic.check_domain",
        side_effect=["free", UnicodeEncodeError("idna", "x", 0, 1, "bad")],
    ):
        results = check_domains(["free.test", "bad.test"])

    assert [result.model_dump() for result in results] == [
        {"domain": "free.test", "status": "free"},
        {"domain": "bad.test", "status": "invalid"},
    ]

    with patch("domain_checker.main.check_domains", return_value=results):
        assert handle_domain_check(["free.test", "bad.test"]) == [
            {"domain": "free.test", "status": "free"},
            {"domain": "bad.test", "status": "invalid"},
        ]


def test_single_handler_reports_worker_metadata_and_failures():
    with patch("domain_checker.main.check_domain", side_effect=ValueError("bad")):
        result = handle_single_domain_check("bad.test", enqueued_at=0)

    assert result["domain"] == "bad.test"
    assert result["status"] == "invalid"
    assert result["worker_id"]
    assert result["processing_time_ms"] >= 0
    assert result["queue_wait_time_ms"] >= 0


def test_keyword_matching_is_case_normalized_by_caller():
    assert contains_any_keyword("status: available", ["status: available"])
    assert not contains_any_keyword("ambiguous", ["status: available"])
