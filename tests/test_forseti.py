import os
import warnings

import pytest
import yaml

from core.assessor import ComplianceAssessor, ControlLoadError
from core.reporter import ComplianceReporter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDPR_CONTROLS = os.path.join(REPO_ROOT, "controls", "gdpr.yaml")
NIS2_CONTROLS = os.path.join(REPO_ROOT, "controls", "nis2.yaml")
DORA_CONTROLS = os.path.join(REPO_ROOT, "controls", "dora.yaml")
ISO27001_CONTROLS = os.path.join(REPO_ROOT, "controls", "iso27001.yaml")


# ----------------------------------------------------------------------
# Helpers / fixtures
# ----------------------------------------------------------------------

def _write_yaml(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh)
    return path


@pytest.fixture
def small_controls(tmp_path):
    """Un piccolo set di controlli isolato, per asserzioni di scoring esatte."""
    data = [
        {
            "id": "T-BOOL-1",
            "category": "Test",
            "framework": "GDPR",
            "title": "Controllo booleano 1",
            "description": "desc",
            "question": "domanda?",
            "answer_type": "bool",
            "weight": 10,
            "severity": "alta",
            "remediation": "fai qualcosa",
        },
        {
            "id": "T-BOOL-2",
            "category": "Test",
            "framework": "GDPR",
            "title": "Controllo booleano 2",
            "description": "desc",
            "question": "domanda?",
            "answer_type": "bool",
            "weight": 10,
            "severity": "media",
            "remediation": "fai qualcos'altro",
        },
        {
            "id": "T-SCALE-1",
            "category": "Test",
            "framework": "NIS2",
            "title": "Controllo a scala",
            "description": "desc",
            "question": "domanda?",
            "answer_type": "scale",
            "scale_max": 4,
            "weight": 20,
            "severity": "alta",
            "remediation": "migliora gradualmente",
        },
    ]
    path = tmp_path / "small.yaml"
    return _write_yaml(path, data)


# ----------------------------------------------------------------------
# Caricamento controlli
# ----------------------------------------------------------------------

def test_load_real_gdpr_controls():
    assessor = ComplianceAssessor([GDPR_CONTROLS])
    assert len(assessor.controls) >= 10
    for control in assessor.controls.values():
        assert control["framework"] == "GDPR"
        assert control["weight"] > 0


def test_load_real_nis2_controls():
    assessor = ComplianceAssessor([NIS2_CONTROLS])
    assert len(assessor.controls) >= 10
    for control in assessor.controls.values():
        assert control["framework"] == "NIS2"


def test_load_real_dora_controls():
    assessor = ComplianceAssessor([DORA_CONTROLS])
    assert len(assessor.controls) >= 3
    for control in assessor.controls.values():
        assert control["framework"] == "DORA"


def test_load_real_iso27001_controls():
    assessor = ComplianceAssessor([ISO27001_CONTROLS])
    assert len(assessor.controls) >= 3
    for control in assessor.controls.values():
        assert control["framework"] == "ISO27001"


def test_load_all_frameworks_combined():
    assessor = ComplianceAssessor([GDPR_CONTROLS, NIS2_CONTROLS, DORA_CONTROLS, ISO27001_CONTROLS])
    frameworks = {c["framework"] for c in assessor.controls.values()}
    assert frameworks == {"GDPR", "NIS2", "DORA", "ISO27001"}


def test_load_small_controls_fixture(small_controls):
    assessor = ComplianceAssessor([small_controls])
    assert set(assessor.controls.keys()) == {"T-BOOL-1", "T-BOOL-2", "T-SCALE-1"}


def test_missing_control_file_raises():
    with pytest.raises(ControlLoadError):
        ComplianceAssessor(["does_not_exist.yaml"])


def test_no_control_files_raises():
    with pytest.raises(ControlLoadError):
        ComplianceAssessor([])


def test_malformed_yaml_raises_control_load_error(tmp_path):
    bad_path = tmp_path / "bad.yaml"
    # YAML sintatticamente non valido (indentazione/struttura rotta).
    bad_path.write_text("id: [unbalanced\n  - broken: : :\nkey", encoding="utf-8")
    with pytest.raises(ControlLoadError):
        ComplianceAssessor([str(bad_path)])


def test_control_missing_required_field_raises(tmp_path):
    data = [
        {
            "id": "BAD-1",
            "category": "Test",
            "framework": "GDPR",
            # manca "title", "description", "question", "answer_type", "weight", "severity"
        }
    ]
    path = _write_yaml(tmp_path / "bad_fields.yaml", data)
    with pytest.raises(ControlLoadError):
        ComplianceAssessor([str(path)])


def test_control_invalid_framework_raises(tmp_path):
    data = [
        {
            "id": "BAD-2",
            "category": "Test",
            "framework": "NOTREAL",
            "title": "x",
            "description": "x",
            "question": "x",
            "answer_type": "bool",
            "weight": 5,
            "severity": "bassa",
        }
    ]
    path = _write_yaml(tmp_path / "bad_framework.yaml", data)
    with pytest.raises(ControlLoadError):
        ComplianceAssessor([str(path)])


def test_control_file_not_a_list_raises(tmp_path):
    path = tmp_path / "not_a_list.yaml"
    path.write_text("just_a_string: true\n", encoding="utf-8")
    with pytest.raises(ControlLoadError):
        ComplianceAssessor([str(path)])


# ----------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------

def test_all_positive_answers_score_100(small_controls):
    assessor = ComplianceAssessor([small_controls])
    answers = {"T-BOOL-1": True, "T-BOOL-2": True, "T-SCALE-1": 4}
    result = assessor.assess(answers)
    assert result["combined_score"] == 100
    assert result["scores_by_framework"]["GDPR"] == 100
    assert result["scores_by_framework"]["NIS2"] == 100
    assert result["gaps"] == []


def test_all_negative_answers_score_0(small_controls):
    assessor = ComplianceAssessor([small_controls])
    answers = {"T-BOOL-1": False, "T-BOOL-2": False, "T-SCALE-1": 0}
    result = assessor.assess(answers)
    assert result["combined_score"] == 0
    assert result["scores_by_framework"]["GDPR"] == 0
    assert result["scores_by_framework"]["NIS2"] == 0
    assert len(result["gaps"]) == 3


def test_mixed_answers_score(small_controls):
    assessor = ComplianceAssessor([small_controls])
    # GDPR: T-BOOL-1 (10) ok, T-BOOL-2 (10) no -> 10/20 = 50
    # NIS2: T-SCALE-1 (20) a metà scala (2/4) -> 10/20 = 50
    answers = {"T-BOOL-1": True, "T-BOOL-2": False, "T-SCALE-1": 2}
    result = assessor.assess(answers)
    assert result["scores_by_framework"]["GDPR"] == 50
    assert result["scores_by_framework"]["NIS2"] == 50
    assert result["combined_score"] == 50
    gap_ids = {g["id"] for g in result["gaps"]}
    assert gap_ids == {"T-BOOL-2", "T-SCALE-1"}


def test_missing_answers_treated_as_not_satisfied(small_controls):
    assessor = ComplianceAssessor([small_controls])
    result = assessor.assess({})
    assert result["combined_score"] == 0
    assert len(result["gaps"]) == 3
    for g in result["gaps"]:
        assert g["answered"] is False


def test_gaps_sorted_by_weight_descending(small_controls):
    assessor = ComplianceAssessor([small_controls])
    result = assessor.assess({})
    weights = [g["weight"] for g in result["gaps"]]
    assert weights == sorted(weights, reverse=True)
    assert result["gaps"][0]["id"] == "T-SCALE-1"  # peso 20, il più alto


def test_unknown_control_id_ignored_with_warning(small_controls):
    assessor = ComplianceAssessor([small_controls])
    answers = {
        "T-BOOL-1": True,
        "T-BOOL-2": True,
        "T-SCALE-1": 4,
        "DOES-NOT-EXIST": True,
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = assessor.assess(answers)

    assert result["combined_score"] == 100  # l'id sconosciuto non altera lo score
    assert result["unknown_ids"] == ["DOES-NOT-EXIST"]
    assert len(caught) == 1
    assert "DOES-NOT-EXIST" in str(caught[0].message)


def test_scale_answer_out_of_range_is_clamped(small_controls):
    assessor = ComplianceAssessor([small_controls])
    result = assessor.assess({"T-SCALE-1": 999})
    # clampato al massimo (4) -> punteggio pieno per quel controllo
    scale_gap = [g for g in result["gaps"] if g["id"] == "T-SCALE-1"]
    assert scale_gap == []  # nessun gap: pienamente conforme dopo il clamp


def test_full_real_controls_all_true_and_max_scale():
    assessor = ComplianceAssessor([GDPR_CONTROLS, NIS2_CONTROLS])
    answers = {}
    for cid, control in assessor.controls.items():
        if control["answer_type"] == "bool":
            answers[cid] = True
        else:
            answers[cid] = control["scale_max"]
    result = assessor.assess(answers)
    assert result["combined_score"] == 100
    assert result["scores_by_framework"]["GDPR"] == 100
    assert result["scores_by_framework"]["NIS2"] == 100
    assert result["gaps"] == []


def test_full_real_controls_all_false():
    assessor = ComplianceAssessor([GDPR_CONTROLS, NIS2_CONTROLS])
    answers = {cid: False for cid in assessor.controls}
    result = assessor.assess(answers)
    assert result["combined_score"] == 0
    assert len(result["gaps"]) == len(assessor.controls)


# ----------------------------------------------------------------------
# Report Markdown
# ----------------------------------------------------------------------

def test_report_contains_scores_and_gaps(small_controls, tmp_path):
    assessor = ComplianceAssessor([small_controls])
    result = assessor.assess({"T-BOOL-1": True, "T-BOOL-2": False, "T-SCALE-1": 1})

    reporter = ComplianceReporter()
    output_path = tmp_path / "report.md"
    path = reporter.write_report(result, str(output_path), company_name="ACME Test Srl")

    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    assert "ACME Test Srl" in content
    assert "Forseti" in content
    assert "GDPR" in content
    assert "NIS2" in content
    assert "Controllo booleano 2" in content  # nel gap
    assert "fai qualcos'altro" in content  # remediation del gap
    assert f"{result['combined_score']}/100" in content


def test_report_no_gaps_message(small_controls, tmp_path):
    assessor = ComplianceAssessor([small_controls])
    result = assessor.assess({"T-BOOL-1": True, "T-BOOL-2": True, "T-SCALE-1": 4})

    reporter = ComplianceReporter()
    content = reporter.generate_report(result, company_name="ACME Test Srl")
    assert "Nessun gap rilevato" in content


def test_report_warns_about_unknown_ids_in_content(small_controls, tmp_path):
    assessor = ComplianceAssessor([small_controls])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = assessor.assess({"T-BOOL-1": True, "T-BOOL-2": True, "T-SCALE-1": 4, "GHOST-ID": True})

    reporter = ComplianceReporter()
    content = reporter.generate_report(result)
    assert "GHOST-ID" in content
