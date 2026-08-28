import argparse
import os
import sys
import warnings

import yaml

from core.assessor import ComplianceAssessor, ControlLoadError
from core.reporter import ComplianceReporter
from core.colors import Colors

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_CONTROL_FILES = [
    os.path.join(os.path.dirname(__file__), "controls", "gdpr.yaml"),
    os.path.join(os.path.dirname(__file__), "controls", "nis2.yaml"),
]


def _print_header():
    print(Colors.CYAN + "=" * 65 + Colors.ENDC)
    print(f"{Colors.BOLD} Forseti - Compliance Checker GDPR/NIS2 per PMI{Colors.ENDC}")
    print(Colors.CYAN + "=" * 65 + Colors.ENDC)


def cmd_init(args):
    """Genera un file assessment.yaml vuoto con tutte le domande da compilare."""
    try:
        assessor = ComplianceAssessor(args.controls)
    except ControlLoadError as exc:
        print(f"{Colors.RED}[ERROR]{Colors.ENDC} {exc}")
        sys.exit(1)

    if os.path.exists(args.output) and not args.force:
        print(
            f"{Colors.RED}[ERROR]{Colors.ENDC} Il file '{args.output}' esiste già. "
            f"Usa --force per sovrascriverlo."
        )
        sys.exit(1)

    lines = [
        "# Questionario di autovalutazione Forseti - GDPR/NIS2",
        "# Compila il campo 'answer' per ogni controllo:",
        "#   - per i controlli 'bool' usa true / false",
        "#   - per i controlli 'scale' usa un numero da 0 a scale_max (vedi commento)",
        "",
        "company_name: \"La Mia Azienda Srl\"",
        "",
        "answers:",
    ]

    for control in assessor.all_controls():
        default = "false" if control["answer_type"] == "bool" else "0"
        hint = (
            "true/false"
            if control["answer_type"] == "bool"
            else f"0-{int(control.get('scale_max', 4))}"
        )
        lines.append(f"  # [{control['framework']}] {control['title']} ({hint})")
        lines.append(f"  # {control['question']}")
        lines.append(f"  {control['id']}: {default}")
        lines.append("")

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC} Template generato in: {args.output}")
    print(f"    Controlli inclusi: {len(assessor.controls)}")


def cmd_assess(args):
    """Esegue l'assessment a partire da un file di risposte e genera un report Markdown."""
    _print_header()

    try:
        assessor = ComplianceAssessor(args.controls)
    except ControlLoadError as exc:
        print(f"{Colors.RED}[ERROR]{Colors.ENDC} {exc}")
        sys.exit(1)

    print(f"{Colors.CYAN}[*]{Colors.ENDC} Controlli caricati: {len(assessor.controls)}")

    try:
        with open(args.input, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        print(f"{Colors.RED}[ERROR]{Colors.ENDC} File di input non trovato: {args.input}")
        sys.exit(1)
    except yaml.YAMLError as exc:
        print(f"{Colors.RED}[ERROR]{Colors.ENDC} File di input YAML malformato: {exc}")
        sys.exit(1)

    answers = data.get("answers", {}) if isinstance(data, dict) else {}
    company_name = data.get("company_name", "Azienda") if isinstance(data, dict) else "Azienda"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = assessor.assess(answers)
        for w in caught:
            print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {w.message}")

    print(f"{Colors.CYAN}[*]{Colors.ENDC} Score combinato: {Colors.BOLD}{result['combined_score']}/100{Colors.ENDC}")
    for fw, score in result["scores_by_framework"].items():
        print(f"    - {fw}: {score if score is not None else 'N/D'}/100")
    print(f"    - Gap rilevati: {len(result['gaps'])}")

    reporter = ComplianceReporter()
    path = reporter.write_report(result, args.output, company_name=company_name)
    print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC} Report salvato in: {path}")

    if args.fail_under is not None and result["combined_score"] < args.fail_under:
        print(
            f"{Colors.RED}[FAIL]{Colors.ENDC} Score combinato {result['combined_score']} "
            f"inferiore alla soglia richiesta di {args.fail_under}."
        )
        sys.exit(1)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Forseti: Compliance Checker GDPR/NIS2 per PMI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comando da eseguire")

    assess_parser = subparsers.add_parser("assess", help="Esegue l'assessment e genera il report")
    assess_parser.add_argument("--input", required=True, help="File YAML con le risposte al questionario")
    assess_parser.add_argument("--output", default="report.md", help="Percorso del report Markdown da generare")
    assess_parser.add_argument(
        "--controls",
        nargs="+",
        default=DEFAULT_CONTROL_FILES,
        help="File YAML dei controlli da caricare (default: controls/gdpr.yaml controls/nis2.yaml)",
    )
    assess_parser.add_argument(
        "--fail-under",
        type=int,
        default=None,
        metavar="SCORE",
        help="Esce con status 1 se lo score combinato è inferiore a SCORE (utile in CI/CD)",
    )

    init_parser = subparsers.add_parser("init", help="Genera un template assessment.yaml da compilare")
    init_parser.add_argument("--output", default="assessment.yaml", help="Percorso del template da generare")
    init_parser.add_argument(
        "--controls",
        nargs="+",
        default=DEFAULT_CONTROL_FILES,
        help="File YAML dei controlli da usare per generare il template",
    )
    init_parser.add_argument("--force", action="store_true", help="Sovrascrive il file di output se già esistente")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "assess":
        cmd_assess(args)
    elif args.command == "init":
        cmd_init(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
