"""La mémoire de Gazette : un fichier SQLite dans /data.

L'unité est la personne : une fiche (nom, date de naissance) et UN livret, préparé une fois puis réimprimé
à chaque visite. Les séjours viennent de Home Assistant ; ils retrouvent le livret, ils n'en créent pas.
Le cache des sources (le passé ne change pas) est gardé sans limite de durée."""
from __future__ import annotations

import json
import sqlite3
import threading
import unicodedata
from datetime import date, datetime
from pathlib import Path

ETATS = ("a_preparer", "en_preparation", "a_relire", "approuve")


def maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def cle_nom(nom: str) -> str:
    """Nom comparable : sans accents, sans casse, espaces réduits."""
    s = "".join(c for c in unicodedata.normalize("NFD", nom or "") if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().replace("-", " ").split())


class Base:
    def __init__(self, chemin: Path):
        self._verrou = threading.RLock()
        self._c = sqlite3.connect(chemin, check_same_thread=False)
        self._c.row_factory = sqlite3.Row
        self._c.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS personnes (
                id INTEGER PRIMARY KEY, nom TEXT NOT NULL, prenom TEXT NOT NULL DEFAULT '',
                naissance TEXT NOT NULL DEFAULT '', pays TEXT NOT NULL DEFAULT 'France',
                alias TEXT NOT NULL DEFAULT '[]', cree_le TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS livrets (
                personne_id INTEGER PRIMARY KEY REFERENCES personnes(id) ON DELETE CASCADE,
                etat TEXT NOT NULL DEFAULT 'a_preparer', contenu TEXT NOT NULL DEFAULT '{}',
                propositions TEXT NOT NULL DEFAULT '{}', mot TEXT NOT NULL DEFAULT '',
                accent TEXT NOT NULL DEFAULT '#9E1B1B', prepare_le TEXT NOT NULL DEFAULT '',
                approuve_le TEXT NOT NULL DEFAULT '', erreur TEXT NOT NULL DEFAULT '', modifie_le TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS sejours (
                id INTEGER PRIMARY KEY, chambre TEXT NOT NULL, du TEXT NOT NULL, jusqu_au TEXT NOT NULL,
                recu_le TEXT NOT NULL, UNIQUE (chambre, du));
            CREATE TABLE IF NOT EXISTS invites (
                sejour_id INTEGER NOT NULL REFERENCES sejours(id) ON DELETE CASCADE, nom TEXT NOT NULL,
                personne_id INTEGER, PRIMARY KEY (sejour_id, nom));
            CREATE TABLE IF NOT EXISTS ignores (
                sorte TEXT NOT NULL, cle TEXT NOT NULL, le TEXT NOT NULL, PRIMARY KEY (sorte, cle));
            CREATE TABLE IF NOT EXISTS sources (cle TEXT PRIMARY KEY, lu_le TEXT NOT NULL, contenu TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, le TEXT NOT NULL, geste TEXT NOT NULL,
                personne_id INTEGER, detail TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS reglages (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
        """)
        self._c.execute("PRAGMA foreign_keys=ON")

    def fermer(self) -> None:
        self._c.close()

    # ------------------------------------------------------------ personnes
    def _personne(self, l) -> dict:
        d = dict(l)
        d["alias"] = json.loads(d["alias"] or "[]")
        return d

    def personnes(self) -> list[dict]:
        with self._verrou:
            return [self._personne(l) for l in self._c.execute("SELECT * FROM personnes ORDER BY nom COLLATE NOCASE")]

    def personne(self, pid: int) -> dict | None:
        with self._verrou:
            l = self._c.execute("SELECT * FROM personnes WHERE id = ?", (pid,)).fetchone()
        return self._personne(l) if l else None

    def creer_personne(self, nom: str, prenom: str, naissance: str, pays: str = "France", alias: list[str] | None = None) -> int:
        with self._verrou, self._c:
            cur = self._c.execute("INSERT INTO personnes (nom, prenom, naissance, pays, alias, cree_le) VALUES (?,?,?,?,?,?)",
                                  (nom, prenom, naissance, pays or "France", json.dumps(alias or [], ensure_ascii=False), maintenant()))
            pid = cur.lastrowid
            self._c.execute("INSERT INTO livrets (personne_id, modifie_le) VALUES (?, ?)", (pid, maintenant()))
        self.relier_invites()
        return pid

    def modifier_personne(self, pid: int, **champs) -> None:
        autorises = {k: v for k, v in champs.items() if k in ("nom", "prenom", "naissance", "pays", "alias")}
        if "alias" in autorises:
            autorises["alias"] = json.dumps(autorises["alias"] or [], ensure_ascii=False)
        if not autorises:
            return
        with self._verrou, self._c:
            ancienne = self._c.execute("SELECT naissance FROM personnes WHERE id = ?", (pid,)).fetchone()
            self._c.execute(f"UPDATE personnes SET {', '.join(k + ' = ?' for k in autorises)} WHERE id = ?",
                            (*autorises.values(), pid))
            if ancienne and "naissance" in autorises and autorises["naissance"] != ancienne["naissance"]:
                # Nouvelle date : le livret est à refaire
                self._c.execute("UPDATE livrets SET etat = 'a_preparer', contenu = '{}', propositions = '{}', "
                                "approuve_le = '' WHERE personne_id = ?", (pid,))
        self.relier_invites()

    def supprimer_personne(self, pid: int) -> None:
        with self._verrou, self._c:
            self._c.execute("UPDATE invites SET personne_id = NULL WHERE personne_id = ?", (pid,))
            self._c.execute("DELETE FROM livrets WHERE personne_id = ?", (pid,))
            self._c.execute("DELETE FROM personnes WHERE id = ?", (pid,))

    def trouver(self, nom: str) -> dict | None:
        """La fiche de ce nom (nom complet, prénom seul s'il est unique, ou un alias). Deux fiches possibles : aucune."""
        c = cle_nom(nom)
        if not c:
            return None
        exacts, prenoms = [], []
        for p in self.personnes():
            noms = [p["nom"], *p["alias"]]
            if any(cle_nom(n) == c for n in noms):
                exacts.append(p)
            elif p["prenom"] and cle_nom(p["prenom"]) == c:
                prenoms.append(p)
        if len(exacts) == 1:
            return exacts[0]
        if not exacts and len(prenoms) == 1:
            return prenoms[0]
        return None

    # ------------------------------------------------------------ livrets
    def livret(self, pid: int) -> dict | None:
        with self._verrou:
            l = self._c.execute("SELECT * FROM livrets WHERE personne_id = ?", (pid,)).fetchone()
        if not l:
            return None
        d = dict(l)
        d["contenu"] = json.loads(d["contenu"] or "{}")
        d["propositions"] = json.loads(d["propositions"] or "{}")
        return d

    def maj_livret(self, pid: int, **champs) -> None:
        for k in ("contenu", "propositions"):
            if k in champs:
                champs[k] = json.dumps(champs[k], ensure_ascii=False)
        champs["modifie_le"] = maintenant()
        with self._verrou, self._c:
            self._c.execute(f"UPDATE livrets SET {', '.join(k + ' = ?' for k in champs)} WHERE personne_id = ?",
                            (*champs.values(), pid))

    # ------------------------------------------------------------ séjours (Home Assistant)
    def poser_sejour(self, chambre: str, du: str, jusqu_au: str, noms: list[str]) -> int:
        """Un séjour par chambre et date d'arrivée. Les invités sont remplacés par la liste reçue."""
        with self._verrou, self._c:
            # Un séjour de la même chambre qui chevauche (dates changées dans HA) est remplacé
            self._c.execute("DELETE FROM sejours WHERE chambre = ? AND du != ? AND du <= ? AND jusqu_au >= ?",
                            (chambre, du, jusqu_au, du))
            self._c.execute("INSERT INTO sejours (chambre, du, jusqu_au, recu_le) VALUES (?,?,?,?) "
                            "ON CONFLICT(chambre, du) DO UPDATE SET jusqu_au = excluded.jusqu_au, recu_le = excluded.recu_le",
                            (chambre, du, jusqu_au, maintenant()))
            sid = self._c.execute("SELECT id FROM sejours WHERE chambre = ? AND du = ?", (chambre, du)).fetchone()["id"]
            self._c.execute("DELETE FROM invites WHERE sejour_id = ?", (sid,))
            for n in noms:
                p = self.trouver(n)
                self._c.execute("INSERT OR IGNORE INTO invites VALUES (?,?,?)", (sid, n, p["id"] if p else None))
        return sid

    def retirer_sejours(self, chambre: str) -> None:
        """La chambre est libre : ses séjours à venir ou en cours sont oubliés."""
        with self._verrou, self._c:
            self._c.execute("DELETE FROM sejours WHERE chambre = ? AND jusqu_au >= ?", (chambre, date.today().isoformat()))

    def relier_invites(self) -> None:
        """Après la création ou le renommage d'une fiche : relie les invités restés sans fiche."""
        with self._verrou, self._c:
            for l in self._c.execute("SELECT sejour_id, nom FROM invites WHERE personne_id IS NULL").fetchall():
                p = self.trouver(l["nom"])
                if p:
                    self._c.execute("UPDATE invites SET personne_id = ? WHERE sejour_id = ? AND nom = ?",
                                    (p["id"], l["sejour_id"], l["nom"]))

    def sejours(self, depuis: str | None = None) -> list[dict]:
        depuis = depuis or date.today().isoformat()
        with self._verrou:
            ss = [dict(l) for l in self._c.execute("SELECT * FROM sejours WHERE jusqu_au >= ? ORDER BY du", (depuis,))]
            for s in ss:
                s["invites"] = [dict(l) for l in self._c.execute(
                    "SELECT nom, personne_id FROM invites WHERE sejour_id = ? ORDER BY nom", (s["id"],))]
        return ss

    # ------------------------------------------------------------ « Ignorer » (tuiles d'À traiter)
    def ignorer(self, sorte: str, cle: str) -> None:
        with self._verrou, self._c:
            self._c.execute("INSERT OR REPLACE INTO ignores VALUES (?,?,?)", (sorte, cle, maintenant()))

    def ignores(self, sorte: str) -> set[str]:
        with self._verrou:
            return {l["cle"] for l in self._c.execute("SELECT cle FROM ignores WHERE sorte = ?", (sorte,))}

    # ------------------------------------------------------------ cache des sources
    def source(self, cle: str) -> str | None:
        with self._verrou:
            l = self._c.execute("SELECT contenu FROM sources WHERE cle = ?", (cle,)).fetchone()
        return l["contenu"] if l else None

    def garder_source(self, cle: str, contenu: str) -> None:
        with self._verrou, self._c:
            self._c.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?)", (cle, maintenant(), contenu))

    def oublier_sources(self, prefixe: str) -> int:
        with self._verrou, self._c:
            return self._c.execute("DELETE FROM sources WHERE cle LIKE ?", (prefixe + "%",)).rowcount

    def stats_sources(self) -> dict:
        with self._verrou:
            ls = self._c.execute("SELECT substr(cle, 1, instr(cle, ':') - 1) AS s, count(*) AS n, max(lu_le) AS d "
                                 "FROM sources GROUP BY s").fetchall()
        return {l["s"]: {"pages": l["n"], "derniere": l["d"]} for l in ls}

    # ------------------------------------------------------------ journal et réglages
    def noter(self, geste: str, personne_id: int | None = None, detail: str = "") -> None:
        with self._verrou, self._c:
            self._c.execute("INSERT INTO journal (le, geste, personne_id, detail) VALUES (?,?,?,?)",
                            (maintenant(), geste, personne_id, detail))

    def journal(self, n: int = 50) -> list[dict]:
        with self._verrou:
            return [dict(l) for l in self._c.execute(
                "SELECT j.*, p.nom FROM journal j LEFT JOIN personnes p ON p.id = j.personne_id ORDER BY j.id DESC LIMIT ?", (n,))]

    def reglage(self, cle: str, defaut: str = "") -> str:
        with self._verrou:
            l = self._c.execute("SELECT valeur FROM reglages WHERE cle = ?", (cle,)).fetchone()
        return l["valeur"] if l else defaut

    def poser_reglage(self, cle: str, valeur: str) -> None:
        with self._verrou, self._c:
            self._c.execute("INSERT OR REPLACE INTO reglages VALUES (?,?)", (cle, valeur))
