import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.assessor import ComplianceAssessor
from core.evidence import collect_evidence
from core.reporter import ComplianceReporter
import main as forseti_main


def _make_root(tmp_path):
    for mod, db, sql in (
        ("Heimdall", "heimdall.db", "CREATE TABLE alerts(id INTEGER); CREATE TABLE blocked_ips(id INTEGER);"),
        ("Fenrir", "fenrir.db", "CREATE TABLE iocs(id INTEGER);"),
        ("Gjallarhorn", "gjallarhorn.db", "CREATE TABLE notification_log(id INTEGER);"),
    ):
        d = tmp_path / mod
        d.mkdir(exist_ok=True)
        con = sqlite3.connect(str(d / db))
        con.executescript(sql)
        con.commit()
        con.close()
    con = sqlite3.connect(str(tmp_path / "Heimdall" / "heimdall.db"))
    con.execute("INSERT INTO alerts VALUES (1)")
    con.execute("INSERT INTO blocked_ips VALUES (1)")
    con.commit()
    con.close()
    con = sqlite3.connect(str(tmp_path / "Fenrir" / "fenrir.db"))
    con.execute("INSERT INTO iocs VALUES (1)")
    con.execute("INSERT INTO iocs VALUES (2)")
    con.commit()
    con.close()
    return str(tmp_path)


def test_collect_evidence_counts(tmp_path):
    root = _make_root(tmp_path)
    ev = collect_evidence(root)
    assert ev["heimdall"] == {"alerts_total": 1, "blocked_ips": 1}
    assert ev["fenrir"] == {"iocs_total": 2}
    assert ev["gjallarhorn"] == {"notifications_total": 0}
    assert "collected_at" in ev


def test_collect_evidence_missing_dbs_never_crashes(tmp_path):
    ev = collect_evidence(str(tmp_path))
    assert ev["heimdall"]["error"].startswith("OperationalError")
    assert "collected_at" in ev


def test_assess_carries_evidence_and_report_shows_it(tmp_path):
    assessor = ComplianceAssessor(forseti_main.DEFAULT_CONTROL_FILES)
    ev = {"heimdall": {"alerts_total": 5}, "collected_at": "2026-01-01 00:00:00"}
    result = assessor.assess({}, evidence=ev)
    assert result["evidence"] == ev
    report = ComplianceReporter().generate_report(result, company_name="Test")
    assert "Evidence automatiche" in report
    assert "heimdall" in report
    assert "alerts_total" in report


def test_assess_without_evidence_stays_compatible(tmp_path):
    assessor = ComplianceAssessor(forseti_main.DEFAULT_CONTROL_FILES)
    result = assessor.assess({})
    assert result["evidence"] == {}
    assert "Evidence automatiche" not in ComplianceReporter().generate_report(result)
