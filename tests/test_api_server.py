"""Tests for api/server.py's web questionnaire - previously 0% covered by
any test (only the CLI path through core.assessor/core.reporter directly
was tested)."""
from fastapi.testclient import TestClient

from api.server import app, assessor

client = TestClient(app)


def test_questionnaire_page_loads():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_assess_and_download_report_end_to_end():
    first_control = next(iter(assessor.controls.values()))
    form_data = {
        "company_name": "Test Srl",
        first_control["id"]: "1" if first_control["answer_type"] == "bool" else "2",
    }
    res = client.post("/assess", data=form_data)
    assert res.status_code == 200

    download = client.get("/report/download")
    assert download.status_code == 200
    assert "Test Srl" in download.text


def test_download_report_without_assess_first_returns_404():
    from api import server as server_module
    server_module._last_report["result"] = None
    res = client.get("/report/download")
    assert res.status_code == 404


def test_nis2_scope_endpoint():
    res = client.get("/nis2-scope", params={"sector": "energy", "employees": 50, "turnover": 10})
    assert res.status_code == 200
    assert "Applicabilit" in res.text
