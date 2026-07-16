import re
from pathlib import Path

import pytest

from api.models.api_models import MetricsResponse, MetricsSummaryResponse, ModelMetrics


TYPES_FILE = Path(__file__).resolve().parents[2] / "web" / "lib" / "types.ts"


def _typescript_fields(source: str, type_name: str) -> set[str]:
    match = re.search(
        rf"export type {re.escape(type_name)} = \{{(?P<body>.*?)^\}}",
        source,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"Missing TypeScript contract {type_name}"
    return set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*):", match.group("body"), re.MULTILINE))


@pytest.mark.parametrize(
    ("type_name", "backend_model"),
    [
        ("ModelMetrics", ModelMetrics),
        ("MetricsResponse", MetricsResponse),
        ("MetricsSummaryResponse", MetricsSummaryResponse),
    ],
)
def test_frontend_metrics_contract_matches_openapi_model(type_name, backend_model):
    """Fail CI when backend metrics fields drift from the frontend contract."""
    frontend_fields = _typescript_fields(TYPES_FILE.read_text(), type_name)
    assert frontend_fields == set(backend_model.model_fields)
