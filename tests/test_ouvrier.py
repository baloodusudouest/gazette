"""0.20.4 : une tâche de préparation qui plante ne tue plus le fil ; les suivantes passent."""
import queue
import threading

from app import main


def test_une_tache_ratee_ne_tue_pas_l_ouvrier(monkeypatch):
    faites, notes, livrets = [], [], []

    class FausseBase:
        def noter(self, *a):
            notes.append(a)

        def maj_livret(self, pid, **k):
            livrets.append((pid, k))

    def preparer(pid):
        if pid == 1:
            raise KeyError("donnée inattendue")
        faites.append(pid)

    monkeypatch.setattr(main, "_preparer", preparer)
    monkeypatch.setitem(main.ETAT, "file", queue.Queue())
    monkeypatch.setitem(main.ETAT, "en_file", {1, 2})
    monkeypatch.setitem(main.ETAT, "base", FausseBase())
    fil = threading.Thread(target=main._ouvrier, daemon=True)
    fil.start()
    for t in (1, 2):
        main.ETAT["file"].put(t)
    main.ETAT["file"].join()
    assert faites == [2]
    assert fil.is_alive()
    assert livrets[0][0] == 1 and livrets[0][1]["etat"] == "a_preparer" and "KeyError" in livrets[0][1]["erreur"]
    assert main.ETAT["en_file"] == set()
    main.ETAT["file"].put(None)
    fil.join(2)
