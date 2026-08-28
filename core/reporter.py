"""
Forseti - Generatore di report Markdown per l'assessment di conformità.
"""

import datetime
import os
from typing import Any, Dict


def _score_badge(score: int) -> str:
    if score is None:
        return "N/D"
    if score < 50:
        return "🔴 CRITICO"
    if score < 80:
        return "🟡 DA MIGLIORARE"
    return "🟢 CONFORME"


def _severity_icon(severity: str) -> str:
    return {"alta": "🔴", "media": "🟡", "bassa": "🟢"}.get(severity, "⚪")


class ComplianceReporter:
    """Genera un report Markdown a partire dal risultato di ComplianceAssessor.assess()."""

    def generate_report(self, result: Dict[str, Any], company_name: str = "Azienda") -> str:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        combined = result["combined_score"]
        scores = result["scores_by_framework"]
        gaps = result["gaps"]

        gdpr_score = scores.get("GDPR")
        nis2_score = scores.get("NIS2")

        lines = []
        lines.append("# Forseti - Report di Conformità GDPR/NIS2")
        lines.append("")
        lines.append(f"- **Organizzazione**: `{company_name}`")
        lines.append(f"- **Data valutazione**: `{now}`")
        lines.append(f"- **Score combinato**: `{combined}/100` ({_score_badge(combined)})")
        lines.append(f"- **Controlli valutati**: `{result['total_controls']}`")
        if result.get("unknown_ids"):
            lines.append(
                f"- **Attenzione**: {len(result['unknown_ids'])} id di controllo nel file di risposte "
                f"non riconosciuti e ignorati: `{', '.join(result['unknown_ids'])}`"
            )
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Punteggio per framework")
        lines.append("")
        lines.append("| Framework | Score | Stato |")
        lines.append("|---|---:|:---|")
        lines.append(f"| GDPR | {gdpr_score if gdpr_score is not None else 'N/D'}/100 | {_score_badge(gdpr_score)} |")
        lines.append(f"| NIS2 | {nis2_score if nis2_score is not None else 'N/D'}/100 | {_score_badge(nis2_score)} |")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"## Gap di conformità ({len(gaps)})")
        lines.append("")

        if not gaps:
            lines.append("Nessun gap rilevato: tutti i controlli risultano pienamente soddisfatti.")
        else:
            lines.append("| Severità | Framework | Categoria | Controllo | Conformità | Remediation |")
            lines.append("|:---:|:---:|:---|:---|---:|:---|")
            for g in gaps:
                icon = _severity_icon(g["severity"])
                lines.append(
                    f"| {icon} {g['severity'].upper()} | {g['framework']} | {g['category']} | "
                    f"**{g['title']}** (`{g['id']}`) | {g['compliance_pct']}% | {g['remediation'].strip()} |"
                )

        lines.append("")
        lines.append("---")
        lines.append("*Generato da Forseti - Compliance Checker GDPR/NIS2 - Asgard Suite*")
        lines.append("")

        return "\n".join(lines)

    def write_report(self, result: Dict[str, Any], output_path: str, company_name: str = "Azienda") -> str:
        content = self.generate_report(result, company_name=company_name)
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return output_path
