"""
Forseti - Stima orientativa di applicabilità NIS2 (Direttiva UE 2022/2555).

Questo modulo NON fornisce una determinazione legale vincolante. Le regole
di applicabilità NIS2 hanno numerose eccezioni settoriali (es. unico
fornitore di un servizio essenziale in uno Stato membro, criticità per
ordine pubblico/sicurezza pubblica, entità della pubblica amministrazione
designate) che non sono modellabili in modo affidabile da un semplice
questionario. Il risultato va sempre trattato come un punto di partenza
per una verifica con un consulente legale/compliance, mai come risposta
definitiva.
"""

from typing import Any, Dict

# Elenco semplificato (non esaustivo) dei settori Allegato I (soggetti
# "essenziali") e Allegato II (soggetti "importanti") della Direttiva NIS2.
ANNEX_I_SECTORS = {
    "energia": "Energia (elettricità, gas, petrolio, teleriscaldamento, idrogeno)",
    "trasporti": "Trasporti (aereo, ferroviario, per vie d'acqua, su strada)",
    "bancario": "Settore bancario",
    "infrastrutture_finanziarie": "Infrastrutture dei mercati finanziari",
    "sanita": "Sanità (strutture sanitarie, laboratori, produzione farmaceutica/dispositivi medici critici)",
    "acqua_potabile": "Fornitura e distribuzione di acqua potabile",
    "acque_reflue": "Acque reflue",
    "infrastrutture_digitali": "Infrastrutture digitali (DNS, cloud, data center, CDN, servizi fiduciari, comunicazioni elettroniche pubbliche)",
    "gestione_ict": "Gestione di servizi ICT (B2B)",
    "pubblica_amministrazione": "Pubblica amministrazione",
    "spazio": "Settore spaziale",
}

ANNEX_II_SECTORS = {
    "postale": "Servizi postali e di corriere",
    "gestione_rifiuti": "Gestione dei rifiuti",
    "chimico": "Fabbricazione, produzione e distribuzione di sostanze chimiche",
    "alimentare": "Produzione, trasformazione e distribuzione alimentare",
    "manifatturiero": "Manifatturiero (dispositivi medici, elettronica, macchinari, veicoli, altri mezzi di trasporto)",
    "digitale_provider": "Fornitori digitali (marketplace online, motori di ricerca, piattaforme social)",
    "ricerca": "Organizzazioni di ricerca",
}

NOT_LISTED = "non_elencato"

ALL_SECTORS: Dict[str, str] = {
    **ANNEX_I_SECTORS,
    **ANNEX_II_SECTORS,
    NOT_LISTED: "Nessuno dei precedenti / settore non elencato",
}


def _size_class(employees: int, turnover_millions: float) -> str:
    """Classificazione dimensionale semplificata, coerente con la
    Raccomandazione UE 2003/361 sulle PMI (criterio 'occupati OR fatturato',
    la Direttiva NIS2 usa la stessa soglia base per individuare medie/grandi
    imprese all'art. 2)."""
    if employees >= 250 or turnover_millions > 50:
        return "grande"
    if employees >= 50 or turnover_millions > 10:
        return "media"
    if employees >= 10 or turnover_millions > 2:
        return "piccola"
    return "micro"


def estimate_nis2_applicability(sector: str, employees: int, turnover_millions: float) -> Dict[str, Any]:
    """
    Stima orientativa (non vincolante) se un'organizzazione potrebbe
    rientrare nel perimetro NIS2, in base a settore dichiarato e dimensione.

    Ritorna un dizionario con:
      - likely_in_scope: bool | None (None = incerto, serve verifica manuale)
      - entity_type: "essenziale" | "importante" | None
      - size_class: "micro" | "piccola" | "media" | "grande"
      - reasoning: spiegazione testuale della stima
      - disclaimer: testo di avvertenza da mostrare sempre
    """
    disclaimer = (
        "Questa è una stima orientativa, non una determinazione legale. "
        "La Direttiva NIS2 prevede eccezioni (es. unico fornitore di un "
        "servizio essenziale in Italia, criticità per l'ordine pubblico, "
        "specifiche designazioni della pubblica amministrazione) che questo "
        "strumento non può valutare. Verifica sempre con un consulente "
        "legale o con l'Agenzia per la Cybersicurezza Nazionale (ACN)."
    )

    size = _size_class(employees, turnover_millions)

    if sector == NOT_LISTED or sector not in ALL_SECTORS:
        return {
            "likely_in_scope": False,
            "entity_type": None,
            "size_class": size,
            "reasoning": (
                "Il settore indicato non rientra tra quelli elencati negli "
                "Allegati I e II della Direttiva NIS2. Probabilmente non sei "
                "soggetto, salvo che la tua attività rientri in una delle "
                "eccezioni previste."
            ),
            "disclaimer": disclaimer,
        }

    entity_type = "essenziale" if sector in ANNEX_I_SECTORS else "importante"
    sector_label = ALL_SECTORS[sector]

    if size in ("media", "grande"):
        return {
            "likely_in_scope": True,
            "entity_type": entity_type,
            "size_class": size,
            "reasoning": (
                f"Il settore '{sector_label}' rientra nell'Allegato "
                f"{'I' if entity_type == 'essenziale' else 'II'} della NIS2, e la dimensione "
                f"aziendale dichiarata ({size}, in base a dipendenti/fatturato) supera la soglia "
                f"che tipicamente fa scattare l'obbligo. Probabilmente sei soggetto come entità "
                f"{entity_type}."
            ),
            "disclaimer": disclaimer,
        }

    return {
        "likely_in_scope": None,
        "entity_type": entity_type,
        "size_class": size,
        "reasoning": (
            f"Il settore '{sector_label}' rientra tra quelli NIS2, ma la dimensione dichiarata "
            f"({size}) è sotto la soglia generale (media/grande impresa). Potresti comunque "
            "essere soggetto se rientri in una delle eccezioni previste dalla direttiva "
            "(es. unico fornitore di un servizio critico nel tuo territorio). Da verificare "
            "con un consulente."
        ),
        "disclaimer": disclaimer,
    }
