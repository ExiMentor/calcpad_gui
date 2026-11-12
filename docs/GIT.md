# Sicher ins vorhandene Git-Repository übernehmen

Dieses Archiv ist ein Quellpaket, kein Git-Checkout. Es wurde kein Repository
angelegt, kein Commit erstellt, kein Remote geraten und nichts gepusht.
Die folgende Anleitung ist vom Benutzer im **tatsächlichen eigenen Repository**
auszuführen, nicht blind im entpackten Archiv.

## Kurz: Dateien übernehmen und starten

1. `calcpad_gui_clean_start.zip` separat entpacken.
2. Den **Inhalt** des entpackten Ordners `calcpad_gui_clean_start/` in den
   tatsächlichen Projekt-/Repo-Root übernehmen, keine zusätzliche Ordnerebene.
   Eigene Änderungen vorher sichern; README, `.gitignore`, `pyproject.toml` zusammenführen.
3. Im Ziel die alte Datei **`calcpad_gui/app.py` ausdrücklich entfernen**.
   Ein Kopieren/Overlay entfernt veraltete Dateien nicht automatisch.
4. `.git/`, `assets/`, `LICENSE`, andere Lizenzdateien, Header und Metadaten
   erhalten. Das vorhandene Benutzerrepository wurde nicht bereitgestellt;
   diese externen Dateien sind daher nicht im ZIP enthalten.
5. Im Projekt-Root `python3 app.py` oder `python3 -m calcpad_gui` ausführen.

Nur `import calcpad_gui.app` (einschließlich bisheriger Re-Exports) und
`python3 -m calcpad_gui.app` entfallen absichtlich. Implementierungen liegen weiter
in ihren Fachmodulen; Desktopklassen/`main` in `calcpad_gui.application`.
Es wurden **keine Git-Befehle ausgeführt** und nichts remote hochgeladen.
Die folgenden Git-Schritte sind nur optionale manuelle Hinweise.

## 1. Ort, Layout und bestehenden Arbeitsstand prüfen

Vor dem Kopieren im vorgesehenen Repository ausführen:

```sh
pwd
git rev-parse --show-toplevel
git status --short
git branch --show-current
git diff --cached --name-status
git remote -v
```

Prüfen, ob dies wirklich das gewünschte Repository ist, wo dessen Starter und
Python-Paket liegen und worauf die vorhandene Desktopregistrierung zeigt.
**Bei unerwarteten lokalen oder bereits gestagten Änderungen anhalten und diese
bewusst klären/reviewen.** Bereits gestagte fremde Änderungen würden sonst im neuen
Commit landen. Nicht automatisch stashen, zurücksetzen, bereinigen oder erzwingen.
Ein sauberer, bekannter Ausgangsstand ist der sicherste Weg.

Auf der bewusst gewählten Ausgangsbranch eine neue, noch nicht vorhandene Branch
anlegen, zum Beispiel:

```sh
git switch -c prepare-calcpadce-release
```

Erst jetzt den Starter `app.py` **zusammen mit dem vollständigen `calcpad_gui/`
einschließlich `resources/`** und den zugehörigen Tests/Dokumenten in den ermittelten
Projektpfad übernehmen. Keine alte Monolith-Datei zusätzlich einbauen. Vorhandene
README, `.gitignore` und `pyproject.toml` **zusammenführen**; nicht blind über den
Repository-/Monorepo-Stamm kopieren. Bestehende Lizenz, Urheber-/Repository-Header,
Assets, Paketmetadaten und unbeteiligte Dateien erhalten. Keine neue Lizenz oder
Versionsnummer aus dieser Integration ableiten. Desktopregistrierung und persönliche
Einstellungen nicht ungeprüft umstellen oder ersetzen.

## 2. Prüfen und gezielt stagen

Die folgenden Befehle setzen voraus, dass der aktuelle Ordner der tatsächliche
Projektordner mit `app.py`, `calcpad_gui/`, `tests/` und `docs/` ist. Bei einem
Unterprojekt erst dorthin wechseln; Pfade nicht auf eine unbekannte Struktur
übertragen. Die Liste gilt für dieses Paket, nicht für pauschal alle Repo-Dateien.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t . -v
python3 -m compileall -q app.py calcpad_gui tests
# Optional, wenn Node.js vorhanden ist:
node --check tests/dom_harness.js

git diff --check
git status --short
git diff --stat
git diff -- app.py calcpad_gui tests docs README.md .gitignore pyproject.toml
```

Tests und Diff müssen nachvollziehbar sein. Neu hinzugefügte (untracked) Dateien
werden von `git diff` noch nicht gezeigt und deshalb nach dem Stagen mitprüfen.
Die Offline-Suite ersetzt nicht den Desktop-/CLI-/Exporttest auf dem Zielsystem.
Keine ZIPs, Testlogs, Caches, lokalen Einstellungen oder Geheimnisse stagen. Die
angepasste `.gitignore` schützt nicht rückwirkend bereits getrackte Dateien.

Nur die tatsächlich übernommenen und beabsichtigten Projektdateien stagen:

```sh
git add -- app.py calcpad_gui tests docs/ARCHITECTURE.md docs/VALIDATION.md docs/GIT.md README.md .gitignore pyproject.toml
git diff --cached --check
git diff --cached --stat
git diff --cached
git status --short
```

Die vollständige gestagte Ansicht vor dem Commit lesen: keine fremden Dateien,
keine vorhandenen unbeabsichtigt gestagten Änderungen, keine Geheimnisse. Ganze
Verzeichnisse in der Liste nur stagen, wenn ihr Inhalt zuvor geprüft wurde.
Kein `git add .` als Ersatz für diese bewusste Auswahl verwenden.

## 3. Commit und optionaler Push

Erst nach erfolgreichem Review:

```sh
git commit -m "Prepare modular CalcpadCE app for Git integration"
git status --short
```

Der folgende Push ist **optional** und nur korrekt, wenn `git remote -v` tatsächlich
das beabsichtigte eigene Ziel unter dem Namen `origin` zeigt und dessen Zugriff und
Veröffentlichung gewollt sind:

```sh
git push -u origin HEAD
```

Bei einem anderen Remote dessen verifizierten Namen verwenden; bei fehlendem
Remote erst das tatsächliche Ziel klären. Kein geratenes Remote hinzufügen, kein
öffentliches Repository automatisch anlegen, kein Force-Push. Diese Anleitung führt
selbst keine Git-Aktion aus.
