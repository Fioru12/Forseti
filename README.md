<div align="center">

# FORSETI

### **Asgard Cybersecurity Suite — Modulo VIII (Compliance Checker GDPR/NIS2)**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![GDPR](https://img.shields.io/badge/GDPR-Reg._UE_2016%2F679-003399?style=for-the-badge)
![NIS2](https://img.shields.io/badge/NIS2-Dir._UE_2022%2F2555-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)

</div>

> **Perché ho costruito Forseti?**
> Molte PMI devono rispondere di conformità GDPR e, sempre più spesso, NIS2, ma non hanno un modo semplice e ripetibile per capire "a che punto siamo". I checklist Excel si perdono, gli audit esterni costano e spesso il primo passo — un'autovalutazione onesta — non viene mai fatto. Forseti è nato per colmare esattamente questo primo gradino: un questionario strutturato su controlli reali di GDPR e NIS2, uno score oggettivo e un elenco di gap con suggerimenti concreti di rimedio. Niente promesse di "conformità automatica" o funzionalità legali: è uno strumento di autovalutazione tecnica, non un parere legale.

---

## Cosa fa (e cosa NON fa)

Forseti **fa**:

- Carica una base di **25 controlli** di conformità reali e riconoscibili (13 GDPR + 12 NIS2), ciascuno con descrizione normativa, domanda di autovalutazione e suggerimento di rimedio.
- Calcola uno **score 0-100 per framework** (GDPR e NIS2 separati) e uno **score combinato**, a partire dalle risposte di un questionario YAML compilato dall'utente.
- Produce l'elenco dei **gap** (controlli non pienamente soddisfatti), ordinati per severità/peso, con remediation testuale per ciascuno.
- Genera un **report Markdown** leggibile e condivisibile.
- Genera un **template di questionario vuoto** (`init`) con tutte le domande pronte da compilare.

Forseti **non fa** (e non lo dichiara da nessuna parte):

- Non fornisce un parere legale né sostituisce un DPO, un consulente privacy o un audit di conformità formale.
- Non scansiona automaticamente sistemi, reti o documenti aziendali: le risposte al questionario sono fornite manualmente dall'utente.
- Non si collega ad alcuna API esterna né richiede credenziali: è uno strumento CLI locale, offline.

---

## Quick Start

```bash
pip install -r requirements.txt

# 1. Genera un questionario vuoto con tutte le domande da compilare
python main.py init --output assessment.yaml

# 2. Compila assessment.yaml (true/false o 0-4 a seconda del controllo)
#    In alternativa, usa/adatta l'esempio già compilato:
#    assessment.example.yaml

# 3. Esegui l'assessment e genera il report Markdown
python main.py assess --input assessment.example.yaml --output report.md
```

Il comando `assess` stampa a schermo lo score combinato, lo score per framework e il numero di gap rilevati, poi scrive il report completo in `report.md`.

---

## Come sono strutturati i controlli

I controlli vivono in `controls/gdpr.yaml` e `controls/nis2.yaml`. Ogni controllo ha:

| Campo | Significato |
|---|---|
| `id` | Identificativo univoco (es. `GDPR-04`, `NIS2-10`) |
| `category` | Area tematica (es. "Data breach", "Controllo accessi") |
| `framework` | `GDPR` o `NIS2` |
| `title` / `description` | Titolo e riferimento normativo del requisito |
| `question` | Domanda di autovalutazione |
| `answer_type` | `bool` (sì/no) oppure `scale` (0-`scale_max`, livello di maturità) |
| `weight` | Peso del controllo nello score |
| `severity` | `alta` / `media` / `bassa`, usata nel report |
| `remediation` | Suggerimento testuale di rimedio, incluso nel report per ogni gap |

**Controlli GDPR inclusi (13)**: registro dei trattamenti, nomina DPO, base giuridica documentata, procedura data breach 72h, informativa privacy, DPIA, accordi con i responsabili del trattamento (DPA), diritti dell'interessato, cifratura dei dati, retention/cancellazione, privacy by design, formazione, registro delle violazioni.

**Controlli NIS2 inclusi (12)**: analisi dei rischi, piano di gestione incidenti, continuità operativa/DR testato, sicurezza supply chain, politiche di crittografia, MFA su accessi privilegiati/remoti, inventario asset IT, formazione periodica, procedura di vulnerability disclosure, segnalazione incidenti all'autorità (24h/72h), controllo accessi a minimo privilegio, test di sicurezza periodici.

---

## Come funziona lo scoring (`core/assessor.py`)

- Ogni controllo `bool` vale `weight` punti se la risposta è `true`, `0` altrimenti.
- Ogni controllo `scale` vale `weight * (valore / scale_max)` punti (i valori fuori range vengono limitati a `[0, scale_max]`).
- Lo **score per framework** è la somma dei punti ottenuti diviso la somma dei pesi massimi di quel framework, in percentuale.
- Lo **score combinato** è calcolato allo stesso modo sull'insieme di tutti i controlli di entrambi i framework.
- Un controllo con punteggio inferiore al proprio peso massimo genera un **gap**, riportato con percentuale di conformità e remediation.
- Un id di risposta non presente tra i controlli caricati viene **ignorato con un warning**, senza interrompere l'esecuzione.
- Un id di controllo senza risposta nel questionario viene trattato come **non soddisfatto** (0 punti).

---

## Comandi disponibili

```bash
# Genera un template di questionario vuoto
python main.py init --output assessment.yaml [--force] [--controls file1.yaml file2.yaml]

# Esegue l'assessment e genera il report
python main.py assess --input assessment.yaml --output report.md \
    [--controls file1.yaml file2.yaml] [--fail-under 70]
```

`--fail-under` fa uscire il comando con status 1 se lo score combinato è sotto la soglia indicata: utile per far fallire una pipeline CI/CD quando la conformità scende sotto un livello minimo accettato.

---

## Test

```bash
pytest -v
```

I test (`tests/test_forseti.py`) coprono: caricamento dei controlli YAML (reali e di fixture), calcolo dello score con risposte tutte positive/negative/miste, ordinamento dei gap per severità, gestione di id di risposta sconosciuti (warning, non crash), gestione di file di controlli malformati o con campi mancanti, generazione del report Markdown.

---

<div align="center">

**Sviluppato da [Fioru12](https://github.com/Fioru12)** — Parte della Suite Asgard.

</div>
