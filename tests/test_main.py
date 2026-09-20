"""Tests for main.py's CLI wiring - previously 0% covered by any test."""
import argparse
import os
import pytest
import yaml

import main


def test_cmd_init_generates_template(tmp_path):
    out_path = str(tmp_path / "assessment.yaml")
    args = argparse.Namespace(controls=main.DEFAULT_CONTROL_FILES, output=out_path, force=False)
    main.cmd_init(args)
    assert os.path.exists(out_path)
    with open(out_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "answers:" in content


def test_cmd_init_refuses_overwrite_without_force(tmp_path):
    out_path = tmp_path / "assessment.yaml"
    out_path.write_text("existing", encoding="utf-8")
    args = argparse.Namespace(controls=main.DEFAULT_CONTROL_FILES, output=str(out_path), force=False)
    with pytest.raises(SystemExit) as exc:
        main.cmd_init(args)
    assert exc.value.code == 1
    assert out_path.read_text(encoding="utf-8") == "existing"


def test_cmd_assess_runs_end_to_end(tmp_path):
    from core.assessor import ComplianceAssessor
    assessor = ComplianceAssessor(main.DEFAULT_CONTROL_FILES)
    answers = {cid: (False if c["answer_type"] == "bool" else 0) for cid, c in assessor.controls.items()}

    input_path = tmp_path / "answers.yaml"
    input_path.write_text(yaml.dump({"company_name": "Test Srl", "answers": answers}), encoding="utf-8")
    output_path = str(tmp_path / "report.md")

    args = argparse.Namespace(
        controls=main.DEFAULT_CONTROL_FILES, input=str(input_path),
        output=output_path, fail_under=None,
    )
    main.cmd_assess(args)
    assert os.path.exists(output_path)


def test_cmd_assess_fail_under_exits_1_when_score_too_low(tmp_path):
    from core.assessor import ComplianceAssessor
    assessor = ComplianceAssessor(main.DEFAULT_CONTROL_FILES)
    answers = {cid: (False if c["answer_type"] == "bool" else 0) for cid, c in assessor.controls.items()}

    input_path = tmp_path / "answers.yaml"
    input_path.write_text(yaml.dump({"company_name": "Test Srl", "answers": answers}), encoding="utf-8")

    args = argparse.Namespace(
        controls=main.DEFAULT_CONTROL_FILES, input=str(input_path),
        output=str(tmp_path / "report.md"), fail_under=100,
    )
    with pytest.raises(SystemExit) as exc:
        main.cmd_assess(args)
    assert exc.value.code == 1


def test_cmd_assess_missing_input_file_exits_cleanly(tmp_path):
    args = argparse.Namespace(
        controls=main.DEFAULT_CONTROL_FILES, input=str(tmp_path / "does_not_exist.yaml"),
        output=str(tmp_path / "report.md"), fail_under=None,
    )
    with pytest.raises(SystemExit) as exc:
        main.cmd_assess(args)
    assert exc.value.code == 1


def test_main_dispatches_init_subcommand(monkeypatch):
    called = {}
    monkeypatch.setattr(main, "cmd_init", lambda args: called.setdefault("args", args))
    monkeypatch.setattr("sys.argv", ["main.py", "init", "--output", "out.yaml"])
    main.main()
    assert called["args"].output == "out.yaml"


def test_main_dispatches_assess_subcommand(monkeypatch):
    called = {}
    monkeypatch.setattr(main, "cmd_assess", lambda args: called.setdefault("args", args))
    monkeypatch.setattr("sys.argv", ["main.py", "assess", "--input", "in.yaml"])
    main.main()
    assert called["args"].input == "in.yaml"


def test_main_dispatches_serve_subcommand(monkeypatch):
    called = {}
    monkeypatch.setattr(main, "cmd_serve", lambda args: called.setdefault("args", args))
    monkeypatch.setattr("sys.argv", ["main.py", "serve", "--port", "9999"])
    main.main()
    assert called["args"].port == 9999


def test_cmd_serve_calls_uvicorn_run(monkeypatch):
    calls = {}
    monkeypatch.setattr("uvicorn.run", lambda app, host, port, reload: calls.update(locals()))
    args = argparse.Namespace(host="127.0.0.1", port=8091, reload=False)
    main.cmd_serve(args)
    assert calls["app"] == "api.server:app"
    assert calls["port"] == 8091
