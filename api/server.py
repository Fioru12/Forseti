"""
Forseti - Interfaccia web.

Espone lo stesso motore di scoring usato dalla CLI (core.assessor) dietro
un questionario compilabile in un browser, senza che l'utente debba mai
scrivere o modificare un file YAML a mano. Pensato per un pubblico non
tecnico (titolare di PMI, consulente) - la CLI resta disponibile per usi
scriptabili/CI.
"""

import os
import warnings

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from core.assessor import ComplianceAssessor, ControlLoadError
from core.reporter import ComplianceReporter
from core.nis2_scope import estimate_nis2_applicability, ALL_SECTORS
from core.webapp_html import (
    render_questionnaire_page,
    render_report_page,
    render_nis2_scope_form,
    render_nis2_scope_result,
    sector_options_html,
    BASE_STYLE,
    _esc,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONTROL_FILES = [
    os.path.join(REPO_ROOT, "controls", "gdpr.yaml"),
    os.path.join(REPO_ROOT, "controls", "nis2.yaml"),
]

app = FastAPI(title="Forseti - Compliance Checker GDPR/NIS2")

# Loaded once at startup - a bad controls file should fail fast and loudly
# rather than surface as a confusing 500 on the first request.
try:
    assessor = ComplianceAssessor(DEFAULT_CONTROL_FILES)
except ControlLoadError as exc:
    raise RuntimeError(f"Forseti non può avviarsi: {exc}") from exc

# The last computed report is kept in memory so /report/download can offer
# the Markdown version without re-submitting the form. This is a single-user
# local tool (like the CLI), so a module-level variable is an intentional,
# simple choice - not meant to serve multiple concurrent assessments.
_last_report: dict = {"result": None, "company_name": "Azienda"}


def _controls_by_framework():
    grouped: dict = {}
    for control in assessor.all_controls():
        grouped.setdefault(control["framework"], []).append(control)
    return grouped


@app.get("/", response_class=HTMLResponse)
def questionnaire():
    return render_questionnaire_page(_controls_by_framework())


@app.post("/assess", response_class=HTMLResponse)
async def assess(request: Request):
    # The questionnaire has one dynamically-named field per control (its
    # id, e.g. "GDPR-01"), so we read the raw form body instead of
    # declaring one FastAPI Form(...) parameter per control.
    form = await request.form()
    company_name = (form.get("company_name") or "").strip() or "Azienda"

    # Form values arrive as strings (radio button values "0"/"1"/"2"...).
    # bool("0") is True in Python, so for boolean controls we must convert
    # explicitly instead of handing the raw string to ComplianceAssessor.
    answers = {}
    for control_id, control in assessor.controls.items():
        raw_value = form.get(control_id)
        if raw_value is None or raw_value == "":
            continue
        if control["answer_type"] == "bool":
            answers[control_id] = raw_value == "1"
        else:
            answers[control_id] = raw_value

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = assessor.assess(answers)

    _last_report["result"] = result
    _last_report["company_name"] = company_name

    return render_report_page(result, company_name, markdown_download_url="/report/download")


@app.get("/nis2-scope", response_class=HTMLResponse)
def nis2_scope(sector: str = Query(...), employees: int = Query(...), turnover: float = Query(...)):
    result = estimate_nis2_applicability(sector, employees, turnover)
    sector_label = ALL_SECTORS.get(sector, sector)
    result_html = render_nis2_scope_result(result, sector_label)
    form_html = render_nis2_scope_form(sector_options_html(selected=sector))

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Applicabilità NIS2 - Forseti</title>
{BASE_STYLE}
</head>
<body>
<div class="wrap">
  <header class="page-head">
    <h1>Applicabilità NIS2</h1>
    <p>Stima orientativa per {_esc(sector_label)}, {employees} dipendenti, {turnover} mln € di fatturato.</p>
  </header>
  {result_html}
  <div style="margin-top:24px;">{form_html}</div>
  <div style="margin-top:20px;"><a class="secondary-link" href="/">← Torna al questionario di conformità</a></div>
</div>
</body>
</html>"""


@app.get("/report/download", response_class=PlainTextResponse)
def download_report():
    if _last_report["result"] is None:
        return PlainTextResponse("Nessun report generato in questa sessione. Compila prima il questionario su /.", status_code=404)
    reporter = ComplianceReporter()
    content = reporter.generate_report(_last_report["result"], company_name=_last_report["company_name"])
    return PlainTextResponse(content, media_type="text/markdown")
