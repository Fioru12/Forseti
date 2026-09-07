"""
Forseti - Generazione HTML per l'interfaccia web (questionario + report).

Nessuna dipendenza da un motore di templating: le pagine sono generate con
semplici funzioni Python, coerentemente con lo stile del resto della suite
Asgard. Il design è intenzionalmente diverso da quello "SOC/hacker" di
Ragnarök: qui il pubblico è un titolare di PMI o un consulente, non un
analista di sicurezza, quindi la resa è quella di uno strumento
istituzionale/di audit - chiaro, leggibile, senza gergo tecnico non necessario.
"""

import html
from typing import Any, Dict, List

from core.nis2_scope import ALL_SECTORS, ANNEX_I_SECTORS, ANNEX_II_SECTORS, NOT_LISTED

BASE_STYLE = """
<style>
  :root {
    --bg: #f4f6f9; --surface: #ffffff; --border: #dde3ea;
    --text: #1c2733; --text-muted: #5b6b7c;
    --accent: #1d4e8f; --accent-soft: #e8eff8;
    --alta: #b3352f; --alta-bg: #fbe9e8;
    --media: #a1720f; --media-bg: #faf1dc;
    --bassa: #3f7a4f; --bassa-bg: #e9f4ec;
  }
  * { box-sizing: border-box; }
  body {
    background: var(--bg); color: var(--text); margin: 0;
    font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.55;
  }
  .wrap { max-width: 880px; margin: 0 auto; padding: 40px 24px 80px; }
  header.page-head { margin-bottom: 32px; }
  header.page-head h1 { font-size: 1.7rem; margin: 0 0 6px; color: var(--accent); }
  header.page-head p { color: var(--text-muted); margin: 0; max-width: 62ch; }
  .disclaimer {
    background: var(--accent-soft); border: 1px solid #c7d7ec; border-radius: 8px;
    padding: 14px 18px; font-size: 0.85rem; color: #2c455e; margin-bottom: 28px;
  }
  .card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 22px 24px; margin-bottom: 16px;
  }
  .card h2 { font-size: 1.1rem; margin: 0 0 4px; }
  .card .meta { font-size: 0.75rem; text-transform: uppercase; letter-spacing: .04em; color: var(--accent); font-weight: 600; margin-bottom: 6px; }
  .card .desc { font-size: 0.85rem; color: var(--text-muted); margin: 6px 0 14px; }
  .card .question { font-weight: 600; margin-bottom: 10px; }
  .answer-row { display: flex; gap: 10px; flex-wrap: wrap; }
  .answer-row label {
    border: 1px solid var(--border); border-radius: 100px; padding: 7px 16px;
    font-size: 0.85rem; cursor: pointer; background: #fbfcfd;
  }
  .answer-row input { margin-right: 6px; }
  select, input[type=text], input[type=number] {
    border: 1px solid var(--border); border-radius: 8px; padding: 9px 12px;
    font-size: 0.9rem; width: 100%; background: #fff;
  }
  .field { margin-bottom: 16px; }
  .field label.field-label { display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 5px; font-weight: 600; }
  .section-title { font-size: 1.25rem; margin: 36px 0 14px; color: var(--accent); }
  button.primary {
    background: var(--accent); color: #fff; border: none; border-radius: 100px;
    padding: 13px 28px; font-size: 0.95rem; font-weight: 600; cursor: pointer;
  }
  button.primary:hover { background: #163d70; }
  a.secondary-link { color: var(--accent); font-size: 0.85rem; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  th, td { text-align: left; padding: 10px 10px; border-bottom: 1px solid var(--border); font-size: 0.85rem; vertical-align: top; }
  th { color: var(--text-muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }
  .score-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 20px 0 30px; }
  .score-tile { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px; text-align: center; }
  .score-tile .num { font-size: 2rem; font-weight: 700; }
  .score-tile .lbl { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: .04em; margin-top: 4px; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 100px; font-size: 0.72rem; font-weight: 700; }
  .sev-alta { color: var(--alta); background: var(--alta-bg); }
  .sev-media { color: var(--media); background: var(--media-bg); }
  .sev-bassa { color: var(--bassa); background: var(--bassa-bg); }
  .nis2-result { border-radius: 10px; padding: 18px 20px; margin-top: 16px; font-size: 0.9rem; }
  .nis2-yes { background: var(--alta-bg); border: 1px solid #eecac7; }
  .nis2-no { background: var(--bassa-bg); border: 1px solid #cfe6d5; }
  .nis2-maybe { background: var(--media-bg); border: 1px solid #f0dfae; }
</style>
"""


def _esc(value: Any) -> str:
    return html.escape(str(value))


def render_nis2_scope_form(sector_options: str) -> str:
    return f"""
    <div class="card">
      <h2>Sei soggetto a NIS2?</h2>
      <p class="desc">Stima orientativa (non una determinazione legale) in base a settore e dimensione. Compila e premi "Stima applicabilità" — questo non invia ancora il questionario di conformità qui sotto.</p>
      <form method="get" action="/nis2-scope" style="display:flex; gap:12px; flex-wrap:wrap; align-items:flex-end;">
        <div class="field" style="flex:2; min-width:220px;">
          <label class="field-label">Settore di attività</label>
          <select name="sector">{sector_options}</select>
        </div>
        <div class="field" style="flex:1; min-width:120px;">
          <label class="field-label">Dipendenti</label>
          <input type="number" name="employees" min="0" value="10" required>
        </div>
        <div class="field" style="flex:1; min-width:140px;">
          <label class="field-label">Fatturato annuo (mln €)</label>
          <input type="number" name="turnover" min="0" step="0.1" value="2" required>
        </div>
        <div class="field">
          <button class="primary" type="submit">Stima applicabilità</button>
        </div>
      </form>
    </div>
    """


def render_nis2_scope_result(result: Dict[str, Any], sector_label: str) -> str:
    if result["likely_in_scope"] is True:
        css = "nis2-yes"
        headline = f"Probabilmente SEI soggetto a NIS2, come entità {result['entity_type']}."
    elif result["likely_in_scope"] is False:
        css = "nis2-no"
        headline = "Probabilmente NON sei soggetto a NIS2."
    else:
        css = "nis2-maybe"
        headline = "Caso incerto: potresti rientrare per eccezione, verifica con un consulente."

    return f"""
    <div class="nis2-result {css}">
      <b>{_esc(headline)}</b>
      <p style="margin:8px 0 0;">{_esc(result['reasoning'])}</p>
      <p style="margin:12px 0 0; font-size:0.78rem; opacity:.85;">{_esc(result['disclaimer'])}</p>
    </div>
    """


def sector_options_html(selected: str = NOT_LISTED) -> str:
    groups = [("Allegato I - Settori essenziali", ANNEX_I_SECTORS), ("Allegato II - Settori importanti", ANNEX_II_SECTORS)]
    parts = []
    for label, sectors in groups:
        parts.append(f'<optgroup label="{_esc(label)}">')
        for key, sector_label in sectors.items():
            sel = " selected" if key == selected else ""
            parts.append(f'<option value="{_esc(key)}"{sel}>{_esc(sector_label)}</option>')
        parts.append("</optgroup>")
    sel = " selected" if selected == NOT_LISTED else ""
    parts.append(f'<option value="{NOT_LISTED}"{sel}>{_esc(ALL_SECTORS[NOT_LISTED])}</option>')
    return "".join(parts)


def _answer_input(control: Dict[str, Any]) -> str:
    cid = _esc(control["id"])
    if control["answer_type"] == "bool":
        return f"""
        <div class="answer-row">
          <label><input type="radio" name="{cid}" value="1" required> Sì</label>
          <label><input type="radio" name="{cid}" value="0"> No</label>
        </div>
        """
    scale_max = int(control.get("scale_max", 4))
    labels = ["Per niente", "In parte", "Quasi del tutto", "Completamente"]
    options = []
    for i in range(scale_max + 1):
        lbl = labels[min(i, len(labels) - 1)] if scale_max == 4 else str(i)
        options.append(f'<label><input type="radio" name="{cid}" value="{i}" required> {i} - {_esc(lbl)}</label>')
    return f'<div class="answer-row">{"".join(options)}</div>'


def render_questionnaire_page(controls_by_framework: Dict[str, List[Dict[str, Any]]]) -> str:
    sections = []
    for framework, controls in controls_by_framework.items():
        sections.append(f'<h2 class="section-title">{_esc(framework)}</h2>')
        for c in controls:
            sections.append(f"""
            <div class="card">
              <div class="meta">{_esc(c['category'])}</div>
              <h2>{_esc(c['title'])}</h2>
              <p class="desc">{_esc(c['description'].strip())}</p>
              <p class="question">{_esc(c['question'])}</p>
              {_answer_input(c)}
            </div>
            """)

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Forseti - Verifica di Conformità GDPR &amp; NIS2</title>
{BASE_STYLE}
</head>
<body>
<div class="wrap">
  <header class="page-head">
    <h1>Forseti — Verifica di Conformità GDPR &amp; NIS2</h1>
    <p>Rispondi al questionario per ottenere uno score di conformità e un elenco concreto dei punti da sistemare, con priorità e suggerimenti di rimedio.</p>
  </header>
  <div class="disclaimer">
    Questo strumento supporta l'autovalutazione ma <b>non sostituisce una consulenza legale o di compliance specialistica</b>. Lo score è indicativo e basato solo sulle risposte fornite.
  </div>

  {render_nis2_scope_form(sector_options_html())}

  <form method="post" action="/assess">
    <div class="field" style="max-width:340px; margin: 28px 0;">
      <label class="field-label">Nome dell'organizzazione (facoltativo)</label>
      <input type="text" name="company_name" placeholder="La tua azienda">
    </div>
    {"".join(sections)}
    <div style="margin-top:24px;">
      <button class="primary" type="submit">Genera Report di Conformità</button>
    </div>
  </form>
</div>
</body>
</html>"""


def _score_tile(label: str, score) -> str:
    if score is None:
        return f'<div class="score-tile"><div class="num">N/D</div><div class="lbl">{_esc(label)}</div></div>'
    color = "var(--alta)" if score < 50 else ("var(--media)" if score < 80 else "var(--bassa)")
    return f'<div class="score-tile"><div class="num" style="color:{color}">{score}</div><div class="lbl">{_esc(label)}</div></div>'


def render_report_page(result: Dict[str, Any], company_name: str, markdown_download_url: str) -> str:
    scores = result["scores_by_framework"]
    gaps = result["gaps"]

    if gaps:
        rows = []
        for g in gaps:
            sev_class = {"alta": "sev-alta", "media": "sev-media", "bassa": "sev-bassa"}.get(g["severity"], "sev-media")
            rows.append(f"""
            <tr>
              <td><span class="badge {sev_class}">{_esc(g['severity'].upper())}</span></td>
              <td>{_esc(g['framework'])}</td>
              <td>{_esc(g['title'])}</td>
              <td>{g['compliance_pct']}%</td>
              <td>{_esc(g['remediation'].strip())}</td>
            </tr>
            """)
        gaps_html = f"""
        <table>
          <tr><th>Severità</th><th>Framework</th><th>Controllo</th><th>Conformità</th><th>Come rimediare</th></tr>
          {"".join(rows)}
        </table>
        """
    else:
        gaps_html = "<p>Nessun gap rilevato: tutti i controlli risultano pienamente soddisfatti in base alle risposte fornite.</p>"

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Report di Conformità - {_esc(company_name)}</title>
{BASE_STYLE}
</head>
<body>
<div class="wrap">
  <header class="page-head">
    <h1>Report di Conformità — {_esc(company_name)}</h1>
    <p>{result['total_controls']} controlli valutati su GDPR e NIS2.</p>
  </header>

  <div class="score-grid">
    {_score_tile("Score Combinato", result['combined_score'])}
    {_score_tile("GDPR", scores.get('GDPR'))}
    {_score_tile("NIS2", scores.get('NIS2'))}
  </div>

  <h2 class="section-title">Gap di conformità ({len(gaps)})</h2>
  {gaps_html}

  <div style="margin-top:30px; display:flex; gap:20px;">
    <a class="secondary-link" href="/">← Rifai la valutazione</a>
    <a class="secondary-link" href="{_esc(markdown_download_url)}">⬇ Scarica report in Markdown</a>
  </div>
</div>
</body>
</html>"""
