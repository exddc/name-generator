# Tests for the domain_checker service

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from domain_checker.logic import (
    check_domains,
    check_domain,
    _check_single_domain,
    normalize_domain,
    DomainCheckResult,
)
from domain_checker.main import (
    handle_domain_check,
    handle_domain_recheck,
)


class TestNormalizeDomain:
    """Tests for domain normalization."""
    
    def test_simple_domain(self):
        assert normalize_domain("example.com") == "example.com"
    
    def test_uppercase(self):
        assert normalize_domain("EXAMPLE.COM") == "example.com"
    
    def test_with_spaces(self):
        assert normalize_domain("  example.com  ") == "example.com"
    
    def test_with_url_scheme(self):
        assert normalize_domain("https://example.com") == "example.com"
        assert normalize_domain("http://example.com/path") == "example.com"


class TestCheckSingleDomain:
    """Tests for single domain checking."""
    
    @patch("domain_checker.logic.check_domain")
    def test_successful_check(self, mock_check):
        mock_check.return_value = "free"
        result = _check_single_domain("example.com")
        
        assert result.domain == "example.com"
        assert result.status == "free"
    
    @patch("domain_checker.logic.check_domain")
    def test_check_with_error(self, mock_check):
        mock_check.side_effect = Exception("DNS error")
        result = _check_single_domain("example.com")
        
        assert result.domain == "example.com"
        assert result.status == "invalid"


class TestCheckDomains:
    """Tests for concurrent domain checking."""
    
    @patch("domain_checker.logic._check_single_domain")
    def test_empty_domains(self, mock_check):
        result = check_domains([])
        assert result == []
        mock_check.assert_not_called()
    
    @patch("domain_checker.logic._check_single_domain")
    def test_single_domain_no_threading(self, mock_check):
        """Single domain should skip threading overhead."""
        mock_check.return_value = DomainCheckResult(domain="test.com", status="free")
        result = check_domains(["test.com"])
        
        assert len(result) == 1
        assert result[0].domain == "test.com"
        mock_check.assert_called_once_with("test.com")
    
    @patch("domain_checker.logic._check_single_domain")
    def test_multiple_domains_concurrent(self, mock_check):
        """Multiple domains should be checked concurrently."""
        domains = ["a.com", "b.com", "c.com"]
        mock_check.side_effect = [
            DomainCheckResult(domain=d, status="free") for d in domains
        ]
        
        result = check_domains(domains)
        
        assert len(result) == 3
        assert mock_check.call_count == 3
    
    @patch("domain_checker.logic._check_single_domain")
    def test_handles_partial_failures(self, mock_check):
        """Should handle some domains failing while others succeed."""
        def side_effect(domain):
            if domain == "fail.com":
                raise Exception("Failed")
            return DomainCheckResult(domain=domain, status="free")
        
        mock_check.side_effect = side_effect
        domains = ["ok.com", "fail.com", "also-ok.com"]
        
        result = check_domains(domains)
        
        assert len(result) == 3
        # Results may be in any order due to concurrent execution
        statuses = {r.domain: r.status for r in result}
        assert statuses["ok.com"] == "free"
        assert statuses["fail.com"] == "invalid"
        assert statuses["also-ok.com"] == "free"


class TestHandleDomainCheck:
    """Tests for the RQ job handler."""
    
    @patch("domain_checker.main.check_domains")
    def test_returns_list_of_dicts(self, mock_check):
        mock_check.return_value = [
            DomainCheckResult(domain="test.com", status="free"),
            DomainCheckResult(domain="taken.com", status="registered"),
        ]
        
        result = handle_domain_check(["test.com", "taken.com"])
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"domain": "test.com", "status": "free"}
        assert result[1] == {"domain": "taken.com", "status": "registered"}


class TestHandleDomainRecheck:
    """Tests for the recheck job handler."""
    
    @patch("domain_checker.main.asyncio.run")
    @patch("domain_checker.main.check_domains")
    def test_updates_database(self, mock_check, mock_asyncio_run):
        mock_results = [
            DomainCheckResult(domain="test.com", status="free"),
        ]
        mock_check.return_value = mock_results
        mock_asyncio_run.return_value = None
        
        result = handle_domain_recheck(["test.com"])
        
        # Verify asyncio.run was called (to update database)
        mock_asyncio_run.assert_called_once()
        assert result == [{"domain": "test.com", "status": "free"}]
    
    @patch("domain_checker.main.asyncio.run")
    @patch("domain_checker.main.check_domains")
    def test_handles_database_error_gracefully(self, mock_check, mock_asyncio_run):
        mock_results = [
            DomainCheckResult(domain="test.com", status="free"),
        ]
        mock_check.return_value = mock_results
        mock_asyncio_run.side_effect = Exception("DB connection failed")
        
        # Should not raise, just log the error
        result = handle_domain_recheck(["test.com"])
        
        assert result == [{"domain": "test.com", "status": "free"}]
