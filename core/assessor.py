"""
Forseti - Compliance scoring engine.

Carica i controlli di conformità GDPR/NIS2 da file YAML e calcola uno
score di conformità a partire dalle risposte fornite dall'utente in un
questionario di autovalutazione.
"""

import warnings
from typing import Any, Dict, List, Optional

import yaml

REQUIRED_FIELDS = [
    "id",
    "category",
    "framework",
    "title",
    "description",
    "question",
    "answer_type",
    "weight",
    "severity",
]

VALID_ANSWER_TYPES = ("bool", "scale")
VALID_FRAMEWORKS = ("GDPR", "NIS2", "DORA", "ISO27001")


class ControlLoadError(ValueError):
    """Raised when a controls YAML file is missing, malformed or invalid."""


class ComplianceAssessor:
    """
    Carica i controlli di conformità da uno o più file YAML e calcola lo
    score di conformità (0-100) a partire dalle risposte di un'autovalutazione.
    """

    def __init__(self, control_files: List[str]):
        if not control_files:
            raise ControlLoadError("È necessario specificare almeno un file di controlli.")

        self.controls: Dict[str, Dict[str, Any]] = {}
        for path in control_files:
            for control in self._load_control_file(path):
                self.controls[control["id"]] = control

        if not self.controls:
            raise ControlLoadError("Nessun controllo caricato dai file forniti.")

    # ------------------------------------------------------------------
    # Loading & validation
    # ------------------------------------------------------------------

    @staticmethod
    def _load_control_file(path: str) -> List[Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except FileNotFoundError as exc:
            raise ControlLoadError(f"File dei controlli non trovato: {path}") from exc
        except yaml.YAMLError as exc:
            raise ControlLoadError(f"YAML malformato in {path}: {exc}") from exc

        if data is None:
            return []

        if not isinstance(data, list):
            raise ControlLoadError(
                f"Il file {path} deve contenere una lista di controlli, trovato: {type(data).__name__}"
            )

        controls = []
        for i, raw in enumerate(data):
            controls.append(ComplianceAssessor._validate_control(raw, path, i))
        return controls

    @staticmethod
    def _validate_control(raw: Any, path: str, index: int) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            raise ControlLoadError(f"Controllo #{index} in {path} non è un oggetto valido.")

        missing = [f for f in REQUIRED_FIELDS if f not in raw or raw[f] in (None, "")]
        if missing:
            raise ControlLoadError(
                f"Controllo #{index} in {path} (id={raw.get('id', '?')}) manca dei campi "
                f"obbligatori: {', '.join(missing)}"
            )

        if raw["framework"] not in VALID_FRAMEWORKS:
            raise ControlLoadError(
                f"Controllo {raw['id']} in {path} ha framework non valido: {raw['framework']!r} "
                f"(attesi: {VALID_FRAMEWORKS})"
            )

        if raw["answer_type"] not in VALID_ANSWER_TYPES:
            raise ControlLoadError(
                f"Controllo {raw['id']} in {path} ha answer_type non valido: {raw['answer_type']!r} "
                f"(attesi: {VALID_ANSWER_TYPES})"
            )

        try:
            weight = float(raw["weight"])
        except (TypeError, ValueError) as exc:
            raise ControlLoadError(
                f"Controllo {raw['id']} in {path} ha un peso (weight) non numerico: {raw['weight']!r}"
            ) from exc
        if weight <= 0:
            raise ControlLoadError(f"Controllo {raw['id']} in {path} ha un peso (weight) non positivo.")

        control = dict(raw)
        control["weight"] = weight
        if control["answer_type"] == "scale":
            control["scale_max"] = float(control.get("scale_max", 4))
            if control["scale_max"] <= 0:
                raise ControlLoadError(
                    f"Controllo {raw['id']} in {path} ha scale_max non positivo."
                )
        control.setdefault("remediation", "")

        return control

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_control(self, control: Dict[str, Any], answer: Optional[Any]) -> float:
        """Restituisce il punteggio "guadagnato" (0..weight) per un controllo."""
        weight = control["weight"]

        if answer is None:
            return 0.0

        if control["answer_type"] == "bool":
            return weight if bool(answer) else 0.0

        # scale
        scale_max = control["scale_max"]
        try:
            value = float(answer)
        except (TypeError, ValueError):
            return 0.0
        value = max(0.0, min(scale_max, value))
        return weight * (value / scale_max)

    def assess(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcola lo score di conformità a partire dalle risposte fornite.

        answers: dict {control_id: risposta}. Risposte con id sconosciuto
        (non presenti tra i controlli caricati) vengono ignorate con un
        warning, non causano un errore.
        """
        unknown_ids = [cid for cid in answers if cid not in self.controls]
        for cid in unknown_ids:
            warnings.warn(
                f"Forseti: id di controllo sconosciuto nelle risposte, ignorato: '{cid}'",
                stacklevel=2,
            )

        framework_totals = {fw: {"earned": 0.0, "max": 0.0} for fw in VALID_FRAMEWORKS}
        gaps: List[Dict[str, Any]] = []

        for cid, control in self.controls.items():
            answer = answers.get(cid)
            earned = self._score_control(control, answer)
            weight = control["weight"]
            fw = control["framework"]

            framework_totals[fw]["earned"] += earned
            framework_totals[fw]["max"] += weight

            if earned < weight:
                compliance_pct = round((earned / weight) * 100) if weight else 0
                gaps.append(
                    {
                        "id": cid,
                        "framework": fw,
                        "category": control["category"],
                        "title": control["title"],
                        "severity": control["severity"],
                        "weight": weight,
                        "compliance_pct": compliance_pct,
                        "remediation": control["remediation"],
                        "answered": answer is not None,
                    }
                )

        gaps.sort(key=lambda g: (-g["weight"], g["compliance_pct"]))

        scores_by_framework = {}
        total_earned = 0.0
        total_max = 0.0
        for fw, totals in framework_totals.items():
            total_earned += totals["earned"]
            total_max += totals["max"]
            if totals["max"] > 0:
                scores_by_framework[fw] = round((totals["earned"] / totals["max"]) * 100)
            else:
                scores_by_framework[fw] = None

        combined_score = round((total_earned / total_max) * 100) if total_max > 0 else 0

        return {
            "combined_score": combined_score,
            "scores_by_framework": scores_by_framework,
            "gaps": gaps,
            "total_controls": len(self.controls),
            "unknown_ids": unknown_ids,
        }

    def all_controls(self) -> List[Dict[str, Any]]:
        """Restituisce tutti i controlli caricati, ordinati per framework e id."""
        return sorted(self.controls.values(), key=lambda c: (c["framework"], c["id"]))
