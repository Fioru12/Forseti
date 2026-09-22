"""Forseti evidence auto — letture readonly dagli store locali degli altri moduli.

Raccoglie metriche tecniche reali (conteggi, non giudizi) da usare come
`evidence` a corredo del questionario manuale:

  heimdall: alerts totali + IP bloccati (Heimdall/heimdall.db)
  fenrir:   IOC indicizzati (Fenrir/fenrir.db)
  gjallarhorn: notifiche inviate (Gjallarhorn/gjallarhorn.db)

Ogni sorgente fallisce indipendentemente: DB assente o illeggibile ->
sorgente saltata (chiave "error"), mai un crash dell'assessment.
`asgard_root` e' la root della suite (default: due livelli sopra core/).
"""
import datetime
import os
import sqlite3
from typing import Any, Dict


def _count(db_path: str, sql: str) -> int:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    finally:
        conn.close()


def _try(source: str, collected: Dict[str, Any], fn):
    try:
        collected[source] = fn()
    except Exception as exc:
        collected[source] = {"error": f"{type(exc).__name__}: {exc}"}


def collect_evidence(asgard_root: str = None) -> Dict[str, Any]:
    if asgard_root is None:
        asgard_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    collected: Dict[str, Any] = {}

    def _heimdall():
        db = os.path.join(asgard_root, "Heimdall", "heimdall.db")
        return {
            "alerts_total": _count(db, "SELECT COUNT(*) FROM alerts"),
            "blocked_ips": _count(db, "SELECT COUNT(*) FROM blocked_ips"),
        }

    def _fenrir():
        db = os.path.join(asgard_root, "Fenrir", "fenrir.db")
        return {"iocs_total": _count(db, "SELECT COUNT(*) FROM iocs")}

    def _gjallarhorn():
        db = os.path.join(asgard_root, "Gjallarhorn", "gjallarhorn.db")
        return {"notifications_total": _count(db, "SELECT COUNT(*) FROM notification_log")}

    _try("heimdall", collected, _heimdall)
    _try("fenrir", collected, _fenrir)
    _try("gjallarhorn", collected, _gjallarhorn)
    collected["collected_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return collected
