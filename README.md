# CalcpadCE

Modulare Linux-Oberfläche für CalcpadCE mit GTK 4, GtkSourceView 5 und WebKitGTK 6.
Der sichtbare Anwendungstitel lautet **CalcpadCE** (`APP_TITLE = "CalcpadCE"`).
Die überflüssige Fassade `calcpad_gui/app.py` wurde entfernt; Root-Starter,
Modulstart und Konsolenstarter verwenden direkt `calcpad_gui.application`.
Einstellungen, App-ID, Version, Funktionen und die bestätigte SVG-Wurzeldarstellung
bleiben unverändert. Der gemeldete erste erfolgreiche Test
ist keine vollständige End-to-End-Freigabe; siehe [Validierung](docs/VALIDATION.md).

## Vollständiges Paket starten

**Nicht nur `app.py` kopieren!** Der Starter braucht das vollständige Paket
`calcpad_gui/` samt `resources/`. Auch `tests/`, `docs/` und `pyproject.toml` gehören
zum Quellpaket. Bisherige Installation, eigene Änderungen und Arbeitsblätter sichern.
Das Archiv zunächst separat in einen noch nicht vorhandenen Prüfpfad entpacken:

```sh
python3 -m zipfile -e calcpad_gui_clean_start.zip bereitstellung
cd bereitstellung/calcpad_gui_clean_start
python3 app.py
```

Eine vorhandene Datei öffnet `python3 app.py beispiel.cpd`; `beispiel.cpd` ist dabei
nur ein Platzhalter für ein eigenes Arbeitsblatt, kein mitgeliefertes Beispiel.
Alternativ: `python3 -m calcpad_gui`.
**Einzige neue Kompatibilitätsänderung:** Historische Importe aus `calcpad_gui.app`
und `python3 -m calcpad_gui.app` wurden absichtlich entfernt. Desktopklassen und
`main` liegen in `calcpad_gui.application`; Konstanten in `calcpad_gui.data`,
weitere Helfer in ihren Fachmodulen (siehe Architektur). Der in `pyproject.toml`
definierte Konsolenstarter `calcpad-gui` setzt eine Paketinstallation voraus;
Quellcode-Start benötigt sie nicht. Eine Installation oder ein Wheel-Build wurde
hier nicht durchgeführt.

## Voraussetzungen und Diagnose

- Python **3.10+** mit PyGObject (`gi`), GTK **4.10+** (`Gtk` 4.0).
- GtkSourceView 5 (`GtkSource` 5), WebKitGTK 6 (`WebKit` 6.0).
- Funktionierende CalcpadCE-CLI; bei einer CLI-DLL die passende .NET-Laufzeit.
- Systembibliotheken aus der Distribution, keine neuen Python-Abhängigkeiten.
  Debian-/Ubuntu-Paketnamen sind beispielsweise `python3-gi`, `gir1.2-gtk-4.0`,
  `gir1.2-gtksource-5`, `gir1.2-webkit-6.0`; verfügbare Versionen vorher prüfen.
  Ein Paketname allein garantiert nicht GTK 4.10. Hier wurden keine Pakete installiert.

```sh
python3 -m calcpad_gui --doctor
```

Auch `python3 app.py --doctor` ist möglich. Die Diagnose braucht **ebenfalls GI**
und führt mit vorhandener CLI einen Rechen-Roundtrip aus. Die CLI-Suche über
`CALCPAD_CLI`, `PATH`, System-DLLs und lokale Builds bleibt bestehen.
„New Window“ versucht zuerst `gtk-launch calcpad-gui`, dann den Python-Modulstart.
Die vorhandene Desktopregistrierung muss auf die richtige Installation zeigen;
für den Modul-Fallback muss das Paket im verwendeten Interpreter auffindbar sein.
Desktopdateien und Benutzerkonfiguration wurden nicht verändert.

## Einstellungen und vorhandene Assets

GLib bestimmt weiterhin `calcpad-gui/settings.json` im Benutzer-Konfigurationspfad
und `gtksourceview-5/language-specs/calcpad.lang` im Benutzer-Datenpfad. Schema,
Schlüssel und Standardwerte bleiben unverändert; keine Migration oder Rücksetzung.
Eine vorhandene Sprachdatei wird nicht überschrieben. Reine Domain-Imports erzeugen
keine Konfiguration.

Vorhandene `calcpadce-logo.svg`/`.png` werden in `assets/` neben dem Paket, im
historischen übergeordneten `assets/` und optional in `calcpad_gui/assets/` gesucht;
innerhalb eines Ordners hat SVG Vorrang. Der Projektordner geht dem historischen
Elternordner vor. Kein Logo wird erzeugt/überschrieben; ohne Logo bleibt der Bereich
leer. Vorhandene Repository-Header, Lizenzdateien, Assets und Metadaten bei der
Integration erhalten; dieses Paket erfindet weder eine Lizenz noch einen Autor.

## Tests und Erweiterungen

Im Projektordner:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t . -v
python3 -m compileall -q app.py calcpad_gui tests
# Optional, wenn Node.js vorhanden ist:
node --check tests/dom_harness.js
```

Die Suite verwendet die Standardbibliothek und ausschließlich testseitige GI-Doubles.
Node.js ist optional: ohne Node werden zehn Geometrie-/Syntax-Tests explizit
übersprungen. Mit Node prüft die Suite auch die **tatsächlich eingebetteten**
JavaScript-Scripte. Arbeitsdateien liegen nur unter `.test-work/` und werden bereinigt.
Die unveränderten Golden-Fixtures bleiben Herkunftsnachweis; nur die Titeländerung
ist ausdrücklich erlaubt und separat getestet. Ergebnisse und Grenzen stehen in
[docs/VALIDATION.md](docs/VALIDATION.md); generierte Testlogs gehören nicht ins Paket.

Reine Transformationen in `calcpad_gui/domain/` ergänzen und ohne GI testen,
Prozessarbeit in `services/` und GTK-Signale in das passende `ui/`-Modul aufnehmen.
`window.py` setzt die Klassen explizit zusammen; keine konkurrierenden Callbacks oder
zweite Initialisierung einführen. `preview/` und `resources/` enthalten die getestete
Darstellung. Interne `root-fix-v3`-IDs und Ressourcen sind bewusst unverändert, keine
Fensterbeschriftung. Änderungen daran erfordern neue Tests und echte WebKit-Prüfung.
Details: [Architektur](docs/ARCHITECTURE.md).

## Ins bestehende Git-Repository integrieren

**Keine Git-Befehle ausgeführt und nichts remote hochgeladen.**
1. ZIP separat entpacken.
2. Den **Inhalt** von `calcpad_gui_clean_start/` in den tatsächlichen Projekt-/Repo-Root
   übernehmen, nicht den Ordner als zusätzliche Ebene. Vorher eigene Änderungen sichern.
3. Die alte Datei `calcpad_gui/app.py` im Ziel ausdrücklich entfernen: bloßes
   Darüberkopieren löscht diese veraltete Datei nicht.
4. Im Repo-Root mit `python3 app.py` oder `python3 -m calcpad_gui` starten.

`.git/`, vorhandene `assets/`, `LICENSE` und sonstige Lizenzdateien/Metadaten
unbedingt erhalten; sie wurden nicht bereitgestellt und sind nicht im ZIP enthalten. README, `.gitignore` und `pyproject.toml` mit vorhandenen Dateien
zusammenführen statt einen Monorepo-Stamm blind zu überschreiben. Unbeteiligte
Dateien, Lizenz und Assets erhalten. Sichere Branch-/Review-/Commit-Schritte und
der bedingte Push stehen in [docs/GIT.md](docs/GIT.md).
