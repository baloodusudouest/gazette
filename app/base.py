"""La mémoire de Gazette : un fichier SQLite dans /data.

L'unité est la personne : une fiche (nom, date de naissance) et UN livret, la Gazette de son premier séjour.
0.9 : à partir du deuxième séjour, une édition de La Récidive (journal à scandale) par séjour, table `recidives`.
Les séjours viennent de Home Assistant et restent en mémoire après le départ : ils comptent les visites.
Le cache des sources (le passé ne change pas) est gardé sans limite de durée."""
from __future__ import annotations

import json
import sqlite3
import threading
import unicodedata
from datetime import date, datetime
from pathlib import Path

ETATS = ("a_preparer", "en_preparation", "a_relire", "approuve")
ETATS_RECIDIVE = (*ETATS, "vide")      # « vide » : aucune photo dans la fenêtre, le séjour garde la Gazette


def maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


# 0.24 : `essai_de` d'une fiche d'essai sans vraie fiche (contact de carnet choisi dans Réglages › Simuler)
ESSAI_GAZETTE = -1      # la fiche porte la Gazette d'essai
ESSAI_PORTEUR = -2      # la fiche ne sert qu'à porter une Récidive d'essai


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
            CREATE TABLE IF NOT EXISTS recidives (
                id INTEGER PRIMARY KEY, personne_id INTEGER NOT NULL REFERENCES personnes(id) ON DELETE CASCADE,
                sejour_du TEXT NOT NULL, etat TEXT NOT NULL DEFAULT 'a_preparer', numero INTEGER NOT NULL DEFAULT 2,
                numero_main INTEGER, precedent TEXT NOT NULL DEFAULT '{}', genre TEXT NOT NULL DEFAULT '',
                immich_id TEXT NOT NULL DEFAULT '', accroche TEXT NOT NULL DEFAULT '', photos TEXT NOT NULL DEFAULT '[]',
                trouvees INTEGER NOT NULL DEFAULT 0, manque_scandale INTEGER NOT NULL DEFAULT 0, tag_absent INTEGER NOT NULL DEFAULT 0,
                mot TEXT NOT NULL DEFAULT '', erreur TEXT NOT NULL DEFAULT '', prepare_le TEXT NOT NULL DEFAULT '',
                approuve_le TEXT NOT NULL DEFAULT '', modifie_le TEXT NOT NULL DEFAULT '', UNIQUE (personne_id, sejour_du));
            CREATE TABLE IF NOT EXISTS scandales_publies (
                asset_id TEXT NOT NULL, personne_id INTEGER NOT NULL, le TEXT NOT NULL, PRIMARY KEY (asset_id, personne_id));
            -- 0.23 : pépites de la fiche complète tirées pour chaque demande à l'IA (journal « gazette » : id de la
            -- fiche, « recidive » : id de l'édition ; cible : une, id de photo, rumeurs, courrier, horoscope, droit, mot).
            -- À l'approbation, les pépites des tirages dont un texte a été retenu reçoivent `parue_le` dans carnet.
            CREATE TABLE IF NOT EXISTS tirages (
                id INTEGER PRIMARY KEY, journal TEXT NOT NULL, numero INTEGER NOT NULL, cible TEXT NOT NULL,
                personne TEXT NOT NULL, pepites TEXT NOT NULL DEFAULT '[]', propositions TEXT NOT NULL DEFAULT '[]',
                le TEXT NOT NULL, marque_le TEXT NOT NULL DEFAULT '');
            -- un numéro supprimé emporte ses tirages (un identifiant repris ne doit pas hériter de vieux tirages)
            CREATE TRIGGER IF NOT EXISTS tirages_recidive AFTER DELETE ON recidives BEGIN
                DELETE FROM tirages WHERE journal = 'recidive' AND numero = old.id; END;
            CREATE TRIGGER IF NOT EXISTS tirages_personne AFTER DELETE ON personnes BEGIN
                DELETE FROM tirages WHERE journal = 'gazette' AND numero = old.id; END;
        """)
        # 0.9 : séjours d'avant Gazette notés sur la fiche (nombre et date d'arrivée du dernier)
        colonnes = {l["name"] for l in self._c.execute("PRAGMA table_info(personnes)")}
        if "essai_de" not in colonnes:           # 0.20 : fiche d'essai (Réglages › Simuler) : l'id de la vraie fiche
            self._c.execute("ALTER TABLE personnes ADD COLUMN essai_de INTEGER NOT NULL DEFAULT 0")
        if "sejours_avant" not in colonnes:
            self._c.execute("ALTER TABLE personnes ADD COLUMN sejours_avant INTEGER NOT NULL DEFAULT 0")
        if "dernier_avant" not in colonnes:
            self._c.execute("ALTER TABLE personnes ADD COLUMN dernier_avant TEXT NOT NULL DEFAULT ''")
        # 0.9.1 : gros titre de la une choisi ou écrit, description et propositions de l'IA
        colonnes = {l["name"] for l in self._c.execute("PRAGMA table_info(recidives)")}
        if "essai" not in colonnes:              # 0.20 : édition d'essai (Réglages › Simuler), jamais comptée
            self._c.execute("ALTER TABLE recidives ADD COLUMN essai INTEGER NOT NULL DEFAULT 0")
        if "valides" not in colonnes:            # 0.17 : éléments validés à la relecture
            self._c.execute("ALTER TABLE recidives ADD COLUMN valides TEXT NOT NULL DEFAULT '{}'")
        if "evenement" not in colonnes:          # 0.15 : événement du séjour (pour l'horoscope, gardé pour les suivants)
            self._c.execute("ALTER TABLE recidives ADD COLUMN evenement TEXT NOT NULL DEFAULT ''")
        if "code_barres" not in colonnes:        # 0.11.4 : message du code-barres de la page 4
            self._c.execute("ALTER TABLE recidives ADD COLUMN code_barres TEXT NOT NULL DEFAULT ''")
        if "macaron" not in colonnes:            # 0.9.2 : place du macaron « Exclusif ! » sur la photo de la une
            self._c.execute("ALTER TABLE recidives ADD COLUMN macaron TEXT NOT NULL DEFAULT 'hd'")
        for col in ("titre_une", "description_une", "propositions_une", "rumeurs", "indices_rumeurs", "propositions_rumeurs",
                    "courrier", "propositions_courrier", "horoscope", "propositions_horoscope"):
            if col not in colonnes:
                self._c.execute(f"ALTER TABLE recidives ADD COLUMN {col} TEXT NOT NULL DEFAULT '{'' if col in ('titre_une', 'description_une', 'indices_rumeurs', 'horoscope') else '[]'}'")
        # 0.13 : Gazette classique — photo d'Immich en page 4 (6 au choix) et message du code-barres
        colonnes = {l["name"] for l in self._c.execute("PRAGMA table_info(livrets)")}
        for col, defaut in (("photo", "{}"), ("photos_choix", "[]"), ("code_barres", ""), ("valides", "{}")):
            if col not in colonnes:
                self._c.execute(f"ALTER TABLE livrets ADD COLUMN {col} TEXT NOT NULL DEFAULT '{defaut}'")
        self._c.commit()
        self._c.execute("PRAGMA foreign_keys=ON")

    def fermer(self) -> None:
        self._c.close()

    # ------------------------------------------------------------ personnes
    def _personne(self, l) -> dict:
        d = dict(l)
        d["alias"] = json.loads(d["alias"] or "[]")
        return d

    def personnes(self, essais: bool = False) -> list[dict]:
        """Les fiches ; 0.20 : sans les fiches d'essai (Réglages › Simuler), sauf `essais`."""
        with self._verrou:
            return [self._personne(l) for l in self._c.execute(
                "SELECT * FROM personnes" + ("" if essais else " WHERE essai_de = 0") + " ORDER BY nom COLLATE NOCASE")]

    def creer_essai(self, vraie: dict) -> int:
        """0.20 : une fiche d'essai copiée de la vraie (même date de naissance), pour simuler sa Gazette sans toucher au
        vrai livret ; jamais reliée à un invité de Home Assistant (aucun alias, nom marqué « (essai) »)."""
        pid = self.creer_personne(f"{vraie['nom']} (essai)", vraie.get("prenom", ""), vraie["naissance"], vraie.get("pays", "France"))
        with self._verrou, self._c:
            self._c.execute("UPDATE personnes SET essai_de = ? WHERE id = ?", (vraie["id"], pid))
            self._c.execute("UPDATE invites SET personne_id = NULL WHERE personne_id = ?", (pid,))
        return pid

    def creer_essai_contact(self, nom: str, prenom: str, naissance: str, nom_carnet: str, sorte: int) -> int:
        """0.24 : fiche d'essai pour un contact de carnet qui n'a pas de fiche dans Gazette (Réglages › Simuler).
        `sorte` : ESSAI_GAZETTE (la Gazette d'essai elle-même) ou ESSAI_PORTEUR (porte une Récidive d'essai). Le nom
        de carnet est gardé en autre nom pour retrouver le contact ; une fiche d'essai n'est jamais trouvée par
        `trouver` (ni reliée à un invité de Home Assistant)."""
        with self._verrou, self._c:
            cur = self._c.execute("INSERT INTO personnes (nom, prenom, naissance, pays, alias, cree_le, essai_de) "
                                  "VALUES (?,?,?,?,?,?,?)", (f"{nom} (essai)", prenom, naissance, "France",
                                                             json.dumps([nom_carnet], ensure_ascii=False), maintenant(), sorte))
            pid = cur.lastrowid
            self._c.execute("INSERT INTO livrets (personne_id, modifie_le) VALUES (?, ?)", (pid, maintenant()))
        return pid

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
        autorises = {k: v for k, v in champs.items() if k in ("nom", "prenom", "naissance", "pays", "alias",
                                                              "sejours_avant", "dernier_avant")}
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

    def copie(self, dossier: Path, nom: str, garder: int = 10) -> Path:
        """0.20.6 : copie cohérente de la base (API de sauvegarde de SQLite) ; les plus anciennes au-delà de `garder` partent."""
        dossier.mkdir(parents=True, exist_ok=True)
        cible = dossier / nom
        with self._verrou:
            dest = sqlite3.connect(cible)
            try:
                self._c.backup(dest)
            finally:
                dest.close()
        for vieille in sorted(dossier.glob("gazette-*.db"))[:-garder]:
            vieille.unlink(missing_ok=True)
        return cible

    def supprimer_personne(self, pid: int) -> None:
        with self._verrou, self._c:
            self._c.execute("UPDATE invites SET personne_id = NULL WHERE personne_id = ?", (pid,))
            self._c.execute("DELETE FROM livrets WHERE personne_id = ?", (pid,))
            self._c.execute("DELETE FROM recidives WHERE personne_id = ?", (pid,))
            self._c.execute("DELETE FROM scandales_publies WHERE personne_id = ?", (pid,))
            self._c.execute("DELETE FROM personnes WHERE id = ?", (pid,))

    def trouver(self, nom: str) -> dict | None:
        """La fiche de ce nom (nom complet, prénom seul s'il est unique, ou un alias). Deux fiches possibles : aucune."""
        c = cle_nom(nom)
        if not c:
            return None
        exacts, prenoms = [], []
        for p in self.personnes():              # 0.20 : jamais une fiche d'essai
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
        d["photo"] = json.loads(d.get("photo") or "{}")                # 0.13 : photo de la page 4
        d["photos_choix"] = json.loads(d.get("photos_choix") or "[]")
        d["valides"] = json.loads(d.get("valides") or "{}")            # 0.17 : éléments validés à la relecture
        return d

    def maj_livret(self, pid: int, **champs) -> None:
        for k in ("contenu", "propositions", "photo", "photos_choix", "valides"):
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
            # 0.24 : Home Assistant n'annonce que le prochain séjour de la chambre. Un séjour pas encore commencé qui
            # arrivait AVANT celui-ci n'existe plus (annulé, remplacé par une réservation plus tardive) : il part.
            # Un séjour plus tardif reste (une réservation plus proche a pu s'intercaler).
            # 0.24.1 : le jour d'arrivée compte comme « pas commencé » (HA montre encore le séjour ce jour-là).
            auj = date.today().isoformat()
            self._c.execute("DELETE FROM sejours WHERE chambre = ? AND du < ? AND (du > ? OR (du = ? AND jusqu_au > ?))",
                            (chambre, du, auj, auj, auj))
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
        """La chambre est libre : ses séjours à venir sont oubliés. 0.9 : un séjour commencé reste en mémoire (il
        compte comme une visite pour La Récidive) ; il finit la veille et sort de la liste des séjours à venir."""
        aujourd_hui = date.today()
        auj = aujourd_hui.isoformat()
        with self._verrou, self._c:
            # 0.24.1 : un séjour qui arrive aujourd'hui (et ne finit pas aujourd'hui) est encore « à venir » : annulé
            self._c.execute("DELETE FROM sejours WHERE chambre = ? AND (du > ? OR (du = ? AND jusqu_au > ?))",
                            (chambre, auj, auj, auj))
            self._c.execute("UPDATE sejours SET jusqu_au = ? WHERE chambre = ? AND du <= ? AND jusqu_au >= ?",
                            (date.fromordinal(aujourd_hui.toordinal() - 1).isoformat(), chambre,
                             aujourd_hui.isoformat(), aujourd_hui.isoformat()))

    def sejour(self, sid: int) -> dict | None:
        with self._verrou:
            l = self._c.execute("SELECT * FROM sejours WHERE id = ?", (sid,)).fetchone()
        return dict(l) if l else None

    def supprimer_sejour(self, sid: int) -> None:
        """0.24 : séjour annulé à la main (bouton de Livrets), quand Home Assistant ne l'a pas retiré."""
        with self._verrou, self._c:
            self._c.execute("DELETE FROM sejours WHERE id = ?", (sid,))

    def recidives_orphelines(self) -> list[dict]:
        """0.24 : les numéros de La Récidive d'un séjour pas encore commencé que plus aucun séjour ne porte (séjour
        annulé avant la 0.22.1, qui ne nettoyait pas encore les journaux). Jamais un essai."""
        with self._verrou:
            ls = self._c.execute(
                "SELECT r.* FROM recidives r WHERE r.essai = 0 AND r.sejour_du > ? AND NOT EXISTS ("
                "SELECT 1 FROM sejours s JOIN invites i ON i.sejour_id = s.id "
                "WHERE i.personne_id = r.personne_id AND s.du = r.sejour_du)", (date.today().isoformat(),)).fetchall()
        return [self._recidive(l) for l in ls]

    def sejours_a_venir_de_chambre(self, chambre: str) -> set[tuple[int, str]]:
        """0.22.1 : (personne, date d'arrivée) des séjours pas encore commencés de cette chambre (invités avec fiche)."""
        with self._verrou:
            return {(l["personne_id"], l["du"]) for l in self._c.execute(
                "SELECT i.personne_id, s.du FROM sejours s JOIN invites i ON i.sejour_id = s.id "
                "WHERE s.chambre = ? AND (s.du > ? OR (s.du = ? AND s.jusqu_au > ?)) AND i.personne_id IS NOT NULL",
                (chambre, *[date.today().isoformat()] * 3))}

    def deplacer_recidive(self, pid: int, ancien_du: str, nouveau_du: str) -> None:
        """0.22.1 : le séjour a changé de dates dans Home Assistant : le numéro suit le séjour."""
        with self._verrou, self._c:
            if not self._c.execute("SELECT 1 FROM recidives WHERE personne_id = ? AND sejour_du = ?", (pid, nouveau_du)).fetchone():
                self._c.execute("UPDATE recidives SET sejour_du = ? WHERE personne_id = ? AND sejour_du = ? AND essai = 0",
                                (nouveau_du, pid, ancien_du))

    def supprimer_recidive_du_sejour(self, pid: int, du: str) -> bool:
        """0.22.1 : séjour annulé : son numéro de La Récidive est supprimé, même approuvé (choix de Julien)."""
        with self._verrou, self._c:
            return self._c.execute("DELETE FROM recidives WHERE personne_id = ? AND sejour_du = ? AND essai = 0",
                                   (pid, du)).rowcount > 0

    def remettre_livret(self, pid: int) -> None:
        """0.22.1 : le seul séjour de l'invité est annulé : sa Gazette repart à zéro (la fiche reste)."""
        with self._verrou, self._c:
            self._c.execute("UPDATE livrets SET etat = 'a_preparer', contenu = '{}', propositions = '{}', mot = '', "
                            "prepare_le = '', approuve_le = '', erreur = '', photo = '{}', photos_choix = '[]', "
                            "valides = '{}', code_barres = '', modifie_le = ? WHERE personne_id = ?", (maintenant(), pid))
            self._c.execute("DELETE FROM tirages WHERE journal = 'gazette' AND numero = ?", (pid,))     # 0.23

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

    def sejours_de(self, pid: int) -> list[dict]:
        """0.9 : tous les séjours connus d'une personne (passés compris), par date d'arrivée."""
        with self._verrou:
            return [dict(l) for l in self._c.execute(
                "SELECT DISTINCT s.du, s.jusqu_au, s.chambre FROM sejours s JOIN invites i ON i.sejour_id = s.id "
                "WHERE i.personne_id = ? ORDER BY s.du", (pid,))]

    # ------------------------------------------------------------ La Récidive (0.9)
    def _recidive(self, l) -> dict:
        d = dict(l)
        d["photos"] = json.loads(d["photos"] or "[]")
        d["valides"] = json.loads(d.get("valides") or "{}")               # 0.17 : éléments validés à la relecture
        d["propositions_une"] = json.loads(d.get("propositions_une") or "[]")
        d["rumeurs"] = json.loads(d.get("rumeurs") or "[]")                      # 0.9.7 : rumeurs de la page 3
        d["propositions_rumeurs"] = json.loads(d.get("propositions_rumeurs") or "[]")
        for k in ("courrier", "propositions_courrier", "propositions_horoscope"):      # 0.11 : page 4
            d[k] = json.loads(d.get(k) or "[]")
        # 0.14.1 : chiffres en émoji et émojis laissés par l'IA, retirés aussi de ce qui est déjà gardé
        from .ollama import CORPS, sans_emoji, sans_numero
        d["horoscope"] = sans_numero(d.get("horoscope") or "")
        for k in ("propositions_horoscope", "propositions_rumeurs", "rumeurs", "propositions_une"):
            d[k] = [sans_numero(x) if isinstance(x, str) else x for x in d.get(k) or []]
            if k.startswith("propositions"):           # 0.18.1 : propositions sur le corps écartées, même déjà gardées
                d[k] = [x for x in d[k] if not (isinstance(x, str) and CORPS.search(x))]
        for k in ("courrier", "propositions_courrier"):
            d[k] = [{**x, **{c: sans_emoji(x.get(c) or "") for c in ("lettre", "signe", "reponse")}} if isinstance(x, dict) else x
                    for x in d.get(k) or []]
        d["propositions_courrier"] = [x for x in d["propositions_courrier"]
                                      if not (isinstance(x, dict) and CORPS.search(" ".join(str(v) for v in x.values())))]
        d["precedent"] = json.loads(d["precedent"] or "{}") or None
        d["manque_scandale"], d["tag_absent"] = bool(d["manque_scandale"]), bool(d["tag_absent"])
        return d

    def recidive(self, rid: int) -> dict | None:
        with self._verrou:
            l = self._c.execute("SELECT * FROM recidives WHERE id = ?", (rid,)).fetchone()
        return self._recidive(l) if l else None

    def recidive_de(self, pid: int, du: str) -> dict | None:
        with self._verrou:
            l = self._c.execute("SELECT * FROM recidives WHERE personne_id = ? AND sejour_du = ? AND essai = 0", (pid, du)).fetchone()
        return self._recidive(l) if l else None

    def recidives(self, pid: int | None = None, essais: bool = False) -> list[dict]:
        """0.20 : sans les éditions d'essai, sauf `essais` (alors seulement elles)."""
        filtre = ["essai = 1" if essais else "essai = 0"] + (["personne_id = ?"] if pid else [])
        with self._verrou:
            ls = self._c.execute("SELECT * FROM recidives WHERE " + " AND ".join(filtre) + " ORDER BY sejour_du DESC",
                                 (pid,) if pid else ()).fetchall()
        return [self._recidive(l) for l in ls]

    def creer_essai_recidive(self, pid: int, numero: int) -> int:
        """0.20 : une édition d'essai de La Récidive (date du jour, ou la veille si une vraie occupe déjà ce jour)."""
        from datetime import timedelta
        with self._verrou, self._c:
            for recul in range(60):
                du = (date.today() - timedelta(days=recul)).isoformat()
                if not self._c.execute("SELECT 1 FROM recidives WHERE personne_id = ? AND sejour_du = ?", (pid, du)).fetchone():
                    break
            cur = self._c.execute("INSERT INTO recidives (personne_id, sejour_du, numero, essai, modifie_le) VALUES (?,?,?,1,?)",
                                  (pid, du, numero, maintenant()))
            return cur.lastrowid

    def creer_recidive(self, pid: int, du: str, numero: int) -> int:
        with self._verrou, self._c:
            self._c.execute("INSERT OR IGNORE INTO recidives (personne_id, sejour_du, numero, modifie_le) VALUES (?,?,?,?)",
                            (pid, du, numero, maintenant()))
            return self._c.execute("SELECT id FROM recidives WHERE personne_id = ? AND sejour_du = ?", (pid, du)).fetchone()["id"]

    def maj_recidive(self, rid: int, **champs) -> None:
        for k in ("photos", "precedent", "propositions_une", "rumeurs", "propositions_rumeurs", "courrier",
                  "propositions_courrier", "propositions_horoscope", "valides"):
            if k in champs:
                champs[k] = json.dumps(champs[k] or ({} if k in ("precedent", "valides") else []), ensure_ascii=False)
        for k in ("manque_scandale", "tag_absent"):
            if k in champs:
                champs[k] = int(bool(champs[k]))
        champs["modifie_le"] = maintenant()
        with self._verrou, self._c:
            self._c.execute(f"UPDATE recidives SET {', '.join(k + ' = ?' for k in champs)} WHERE id = ?", (*champs.values(), rid))

    def supprimer_recidive(self, rid: int) -> None:
        with self._verrou, self._c:
            self._c.execute("DELETE FROM recidives WHERE id = ?", (rid,))

    def publies(self, pid: int) -> set[str]:
        """Photos « scandale » de cette personne déjà parues dans une édition approuvée."""
        with self._verrou:
            return {l["asset_id"] for l in self._c.execute("SELECT asset_id FROM scandales_publies WHERE personne_id = ?", (pid,))}

    def publier(self, pid: int, assets: list[str]) -> None:
        with self._verrou, self._c:
            for a in assets:
                self._c.execute("INSERT OR IGNORE INTO scandales_publies VALUES (?,?,?)", (a, pid, maintenant()))

    # ------------------------------------------------------------ 0.23 : tirages de pépites pour l'IA
    TIRAGES_GARDES = 40                 # par numéro et par cible : les plus anciens partent

    def garder_tirage(self, journal: str, numero: int, cible: str, personne: str, pepites: list[str], propositions: list) -> None:
        """Quelles pépites (identifiants de carnet) ont servi à quelles propositions de l'IA."""
        with self._verrou, self._c:
            self._c.execute("INSERT INTO tirages (journal, numero, cible, personne, pepites, propositions, le) VALUES (?,?,?,?,?,?,?)",
                            (journal, numero, str(cible)[:80], personne, json.dumps(list(pepites)),
                             json.dumps(propositions, ensure_ascii=False), maintenant()))
            self._c.execute("DELETE FROM tirages WHERE journal = ? AND numero = ? AND cible = ? AND id NOT IN (SELECT id FROM "
                            "tirages WHERE journal = ? AND numero = ? AND cible = ? ORDER BY id DESC LIMIT ?)",
                            (journal, numero, cible, journal, numero, cible, self.TIRAGES_GARDES))

    def tirages(self, journal: str, numero: int) -> list[dict]:
        with self._verrou:
            ls = self._c.execute("SELECT * FROM tirages WHERE journal = ? AND numero = ? ORDER BY id", (journal, numero)).fetchall()
        return [{**dict(l), "pepites": json.loads(l["pepites"]), "propositions": json.loads(l["propositions"])} for l in ls]

    def tirages_marques(self, ids: list[int]) -> None:
        with self._verrou, self._c:
            for i in ids:
                self._c.execute("UPDATE tirages SET marque_le = ? WHERE id = ?", (maintenant(), i))

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
