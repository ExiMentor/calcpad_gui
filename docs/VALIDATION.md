# Validierung und Nachweisgrenzen

## Aktuelle Bereinigung: clean_start (12.11.2026)

Die überflüssige Datei `calcpad_gui/app.py` wurde entfernt. Root-`app.py`,
`calcpad_gui/__main__.py` und der Konsolenstarter zeigen nun direkt auf
`calcpad_gui.application`. `APP_TITLE = "CalcpadCE"` bleibt erhalten.
**Einzige neue Kompatibilitätsänderung:** `import calcpad_gui.app` (einschließlich
seiner Re-Exports) und `python3 -m calcpad_gui.app` sind absichtlich nicht mehr
verfügbar. Die Helfer selbst bleiben in ihren Fachmodulen erhalten.

Die bisherigen 68 Tests bleiben erhalten; Fassaden-Imports wurden auf das echte
Anwendungsmodul und Konstanten auf `data` umgestellt. Zwei zusätzliche Tests
prüfen das absichtliche Entfernen beider historischen Aufrufe, genau eine Datei
namens `app.py` im Projekt und das neue Konsolenskript-Ziel. Fixtures, Renderer,
root-fix-v3-Ressourcen, Berechnung, Exporte und Settings wurden nicht geändert.

**Aktuell im Quellprojekt: 70 Tests bestanden, 0 Fehler, 0 übersprungen**
(23.590 s, Node vorhanden). Vollständiges `compileall` und `node --check` bestanden.
Auch aus dem frisch entpackten ZIP, vom übergeordneten Arbeitsverzeichnis:
**70 Tests bestanden, 0 Fehler, 0 übersprungen**; erneute Kompilierung und
`node --check` bestanden. Es gibt keine echte GTK-/WebKit-/CLI-Laufzeitvalidierung;
Startprüfungen verwenden ausschließlich testseitige GI-Doubles.

Das neue Archiv heißt `calcpad_gui_clean_start.zip` und enthält 54 Dateien unter
`calcpad_gui_clean_start/`, ausschließlich root-relativ. Nur
`calcpad_gui_clean_start/app.py` trägt den Dateinamen `app.py`.
Originalprojekt und Original-ZIP bleiben unverändert. Kein Git-Befehl, keine
Installation, kein Wheel-Build und kein Remote-Upload wurden ausgeführt.
Vorhandene externe Repository-Assets/Lizenzen wurden nicht bereitgestellt und
müssen bei der Integration erhalten bleiben; die alte Paket-`app.py` muss im
Ziel ausdrücklich gelöscht werden (Overlay-Kopieren genügt nicht).

Die folgenden Abschnitte dokumentieren die historische Refactor-/Titelvalidierung;
ihre 68er-Läufe und das alte Archiv sind **nicht** das aktuelle clean_start-Ergebnis.

## Autoritative Ausgangsfassung

Die vom Benutzer mit „funktioniert“ bestätigte **root-fix-v3**-Fassung ist die
alleinige Code-Baseline: 3013 Zeilen, SHA-256

```text
8e3289027cc18df3db5c3a092207c4f13793fc89ef32ffba1a07b848fe296e23
```

Die ältere Eingabefassung wurde nicht als Codequelle benutzt. Die ursprünglichen
Dateien wurden weder überschrieben noch als versteckter Laufzeit-Monolith in dieses
Projekt kopiert. Die Tests benötigen keine Originaldatei. `tests/fixtures/baseline.json`
enthält ihren Hash, alle ursprünglichen Methodensignaturen/-Deskriptoren und
AST-Digests; `outputs.json` enthält repräsentative eingefrorene Ausgaben bzw.
vollständige HTML-Ausgabehashes. Die Fixtures wurden aus der bestätigten Fassung
gewonnen, nicht erst aus dem Refactor. XML/CSS/Script-Ressourcen sind die tatsächlichen
unveränderten Laufzeitliterale, keine Ersatzimplementierung für die Tests.

## Historische Git-Vorbereitung: damalige einzige Produktionsänderung

Am 12.11.2026 wurde gegenüber dem erstmals vom Benutzer getesteten modularen
Stand ausschließlich diese Zeile im Anwendungscode geändert:

```diff
-APP_TITLE = "CalcpadCE — Wurzel-Fix 3"
+APP_TITLE = "CalcpadCE"
```

Die App-ID `org.community.calcpadce.linuxgui`, Settings/Schema/Pfade, Metadatenversion
und sämtliche Methoden/Ressourcen bleiben unverändert. Insbesondere wurden die
SVG-Wurzelkorrektur, interne Script-IDs, Sentinels, Diagnoseattribute, Dateinamen und
historische Generator-Metadaten nicht umbenannt.

**Die beiden Golden-Fixtures wurden nicht neu erzeugt oder angepasst.** Der alte
APP_TITLE-AST-Digest in `baseline.json` bleibt Herkunftsnachweis. Die explizite
Allowlist `INTENTIONAL_DATA_CHANGES` in `tests/test_invariants.py` erlaubt nur den
exakten alten/neuen Titel. Der Test verlangt genau diese Abweichungsmenge und
vergleicht nach Rückeinsetzen des alten Werts erneut den ursprünglichen Digest;
alle anderen Daten-/Versions-Gate-Digests müssen unverändert passen.

Drei neue Tests prüfen neutralen Titel/App-ID/fehlende temporäre Produktionsbeschriftung,
Titel-Refresh für benannte/unbenannte und saubere/geänderte Dokumente sowie eine
neue Datei. Der bestehende Initialisierungstest prüft zusätzlich den tatsächlich an
den Fensterkonstruktor übergebenen Titel. Dateiname, `[Untitled]` und Dirty-Marker
bleiben bewusst erhalten. Der bestehende Preview-Test erwartet jetzt den neutralen
App-Titel, aber weiterhin die ursprünglichen internen Rendering-Metadaten.

**Benutzerrückmeldung:** „erster Test geht“, allerdings noch mit temporärem Titel.
Das ist ein gemeldeter erster Smoke-Test des modularen Vorstands, kein von uns
beobachteter vollständiger Desktop-/CLI-/Exporttest des finalen Titelstands.

## Ausgeführte Prüfungen

Umgebung: **Python 3.12.16**, **Node.js v24.22.1**. Kein Paket wurde nachinstalliert.
Die folgenden Befehle wurden im finalen Projektordner ausgeführt:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t . -v
python3 -m compileall -q app.py calcpad_gui tests
node --check tests/dom_harness.js
```

Ergebnis des vollständigen Quellcode-Laufs am 12.11.2026:

```text
Ran 68 tests in 26.872s
OK
```

**68 Tests bestanden, 0 Fehler, 0 übersprungen** (65 bestehende plus drei neue Tests).
Alle **40 Python-Quelldateien** wurden geparst/kompiliert, davon 32 im Anwendungspaket.
`node --check` für den DOM-Harness war erfolgreich. Die Suite prüft darüber hinaus
die **tatsächlich aus HTML extrahierten** Wurzel-, Scroll-Restore-,
Zeilennavigations- und dynamischen Scroll-Sync-Scripte per `node --check`.

Auch der finale Testlauf mit leerem `PATH` wurde über `sys.executable` wiederholt:
**68 ausgeführt, 58 bestanden, 10 explizite optionale Node-Tests übersprungen,
0 Fehler.** Das ist ein Abhängigkeitstest der Offline-Suite, kein Test der Anwendung
ohne GI. Frühere modulare Validierung: 65/65 mit Node sowie 55 bestanden und zehn
übersprungen ohne Node; die finalen Resultate ersetzen diese nicht durch neue
Golden-Fixtures. Generierte Testlogs werden nicht im Git-Quellpaket mitgeliefert;
mit den Befehlen oben lässt sich der Lauf reproduzieren.

## Was genau abgedeckt wird

| Nachweis | Methode / Grenze |
|---|---|
| Alle 121 Fenstermethoden vorhanden, keine doppelten oder verdeckten Implementierungen | AST-Inventar plus echte Python-MRO mit ausschließlich testseitigen GI-Doubles |
| 121 unveränderte Signaturen und Deskriptoren | Digest von `ast.arguments`; `classmethod` / `staticmethod` zusätzlich zur Laufzeit geprüft |
| 117 unveränderte Methodenkörper | ursprüngliche vollständige AST-Digests, unabhängig von Verschiebung/Einrückung |
| Ressourcenextraktion in zwei weiteren Methoden | nach Ersatz von Ressourcenaufrufen durch ihre Originalkonstanten identischer ursprünglicher AST-Digest |
| CLI-Adapter | Body-Digest der mechanisch parametrisierten Originalroutine; Lazy-Source-, Escape-, Argument- und Rückgabeverträge separat geprüft |
| Logo-Anpassung | vorhandene SVG-/PNG-Suche, Projekt-/historischer Pfad, kein Überschreiben; Header-Signale und Exportaktionen geprüft |
| App, Daten, Versions-Gate | alle 3 App-Methoden und 7 Top-Level-Funktionen unverändert; nur APP_TITLE explizit erlaubt, sonst Identitäts-/Default-/Symbolkonstanten und GI-/GTK-Gate per AST unverändert |
| Reine Imports / Ressourcen | separater Prozess ohne GI, anderes Arbeitsverzeichnis und isoliertes HOME; keine Konfigurationsdateierzeugung |
| Aktuelle Start-Kompatibilität | `app.py` und `-m calcpad_gui` per `runpy` und GI-Doubles; historisches `-m calcpad_gui.app` absichtlich entfernt und negativ getestet; kein echter Desktopstart |
| Einstellungen | Schema/Defaults, bekannte Schlüssel, JSON-/I/O-Fehler, GLib-Pfade, Roundtrip, Recent-Liste/Favoriten/Optionen mit isolierten Dateien |
| Sprache | Ressourcenbytes, Suchpfad-Ergänzung, vorhandene Sprachdatei nicht überschreiben |
| Reine Textlogik | eingefrorene Unicode-/Mikro-/Widerstands-/Kommentar-/Formatierungsfälle und überschreibbarer rekursiver Klassenaufruf |
| Präzision / Komma | Grenzwerte und fehlerhafte Optionen, HTML-Attribute unverändert, CLI-`#round` erhalten |
| Preview-Literal-Parität | 6 Ressourcenhashes und 48 vollständige HTML-Ausgabehashes aus der Baseline; Scroll-/Navigation-Ausgaben ebenfalls eingefroren |
| v3-Wurzelgeometrie | tatsächliches Script in numerischem DOM-Doppel; siehe unten |
| DOCX | eingefrorene OMML-/Einheiten-/Farben-/Dezimalfälle; ZIP-Dateien/Metadaten und unbeteiligte Parts erhalten; Fehler-Cleanup |
| CLI | Discovery-Reihenfolge, DLL/Binary/Local-Build, Flags/Umgebung, HTML-Body, expliziter/lazy Quelltext, Prozessfehler/Timeout/OSError und Eingabe-Cleanup mit Mocks |
| Dateien / Sicherheit | Rohtext statt normalisiertem CLI-Text speichern, Fehler-/Cancel-/Dirty-/Close-Pfade, Open-Fehler verändern den Puffer nicht |
| Exporte | exklusive Word-Namensreservierung bei parallelen Aufrufen, Fehlerfreigabe, ONLYOFFICE-/Desktop-Fallback mit Mocks, HTML/PDF/DOCX-Pfade und Mainloop-Übergabe |
| Worker / Preview-Bridge | erhaltene Busy-/Closing-Guards, `GLib.idle_add`, Ergebnisdatei-Cleanup, Scroll-/Jump-Titelprotokoll und WebKit-API-Fallbacks |

### Numerisches DOM ist kein Browser

`tests/dom_harness.js` stammt aus den v3-Regressionstests. Die synthetischen
Bruch-/Wurzelmarkups sind **keine erfasste CLI-Ausgabe**. Numerische Rechtecke
modellieren Überläufe, positionierte Brüche sowie hoch-/tiefgestellte Elemente.
Die Prüfungen decken vier Paaranordnungen, unterschiedliche numerische rN/oN-Klassen,
fehlende `.eq`-Vorfahren, verschachtelte Wurzeln und Brüche, n-te Wurzeln, kontinuierliche
Radikal-/Überstrich-Pfade, Idempotenz, unveränderte Texte, innere-vor-äußerer Neuberechnung,
Font-/Viewport-/ResizeObserver-Ereignisse und zusammengefasste Redraws ab.

Bei einem frühen erweiterten Testlauf auf dem gemeinsam genutzten Host liefen drei
synthetische verschachtelte Fälle in das **1000-ms-Limit des Node-vm-Harness**.
Der produktive Algorithmus wurde dafür nicht geändert. Ausschließlich das
Test-Harness-Limit wurde auf 5000 ms erhöht, der Python-Prozessschutz auf 30 s.
Der oben dokumentierte vollständige Lauf bestand danach. Es bleibt ein endliches
Zeitlimit; das ist kein Leistungsnachweis für WebKit.

## Historische Archiv- und Unabhängigkeitsprüfung (git_ready)

`calcpad_gui_git_ready.zip` enthält ausschließlich den relativen Projektordner
`calcpad_gui_git_ready/` mit **55 beabsichtigten Dateien**. Beim Erzeugen und Prüfen
wurden Git-Metadaten, Caches/Bytecode, `.test-work`, lokale Konfiguration/Secrets,
Build-/Wheel-/Egg-Artefakte, weitere Archive und generierte Testlogs ausgeschlossen.
Die sechs XML-/CSS-/HTML-Ressourcen sind im Paketmanifest angegeben. Es gibt keinen
alten Laufzeit-Monolithen, kein Generatorscript und keine absoluten
Arbeitsumgebungspfade in den gelieferten Textdateien.

Das finale ZIP wurde auf eindeutige relative sichere Einträge und CRC geprüft und
frisch in einen separaten Prüfbaum entpackt. Der vollständige Testlauf wurde mit
Arbeitsverzeichnis **außerhalb** des extrahierten Projekts ausgeführt. Die Tests
finden ihr Projekt über `__file__`, nicht über einen ursprünglichen Hostpfad.
Der verwendete Aufruf aus dem übergeordneten Prüfverzeichnis:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s git-ready-archive-check/calcpad_gui_git_ready/tests -t git-ready-archive-check/calcpad_gui_git_ready -v
```

Auch aus dem finalen Archiv: **68 Tests bestanden, 0 Fehler, 0 übersprungen**,
einschließlich GI-freier Imports, testseitiger Einstiegspunktprüfungen und tatsächlicher
eingebetteter JavaScript-Checks. Erneute Kompilierung und `node --check` des entpackten
Harness waren erfolgreich. Der direkte ZIP-Import reiner Module und das Lesen der
Paketressourcen funktionierten ohne GI (ZIP-Pythonpfad inklusive
`/calcpad_gui_git_ready`, entsprechend dem Projekt-Unterordner im ZIP).

Ein Dateivergleich bestätigt: im Produktionspaket wurde nur `APP_TITLE` geändert,
beide Fixtures und alle sechs Ressourcen sind byte-identisch. Ursprüngliches
Projekt, ursprüngliches Archiv und akzeptierter älterer Monolith bleiben unverändert.
Die ZIP-Prüfung ist keine Veröffentlichung/Installation. Kein Wheel-Build, keine
Paketinstallation und keine echte Git-/Remote-Aktion wurde ausgeführt.

## Was noch nicht nachgewiesen ist

**Keine Live-Desktopvalidierung:** GTK, WebKit, Calcpad-CLI, ein Browser und eine
Office-Anwendung standen für einen echten End-to-End-Test nicht zur Verfügung.
GI-Doubles validieren Python-Verträge, nicht GObject-Introspektion, Widget-Rendering,
Fonts oder Fokusverhalten. Ebenso wurden keine echte CLI-HTML-/PDF-/DOCX-Ausgabe,
kein echter ONLYOFFICE-Start und keine vorhandene Desktopregistrierung ausgeführt.

Die Stichproben-/Hash-/AST-Nachweise sind stark für die mechanisch erhaltenen
Verträge, aber **keine Behauptung absoluter Funktionsgleichheit** in jeder möglichen
Desktopumgebung. Nicht alle Such-/Selection-/Completion-Interaktionen sind dynamisch
simuliert; ihre Originalkörper und Callbacknamen werden unverändert geprüft.
Vorhandene Sonderfall-/Thread-/Fehlerverhaltensweisen wurden nicht im Rahmen dieses
Refactors als neue Funktionen repariert. Siehe Besitz-/Threadverträge in
`ARCHITECTURE.md`.

## Manuelle Freigabe auf dem Zielsystem

1. Bestehende Einstellungen laden, Recent-Liste/Favoriten/Optionen prüfen, ohne sie
   zu löschen; danach neu starten und die Persistenz prüfen.
2. Neue Datei, Öffnen, Speichern/Save As und Abbrechen/Verwerfen/Speichern im
   Dirty-/Close-Dialog durchspielen; Rohtext mit µ, Unicode und `||` vergleichen.
3. Formatieren, Completion, Suche/Ersetzen, virtuelle Tastatur und Tastenkürzel,
   Zoom sowie Auto-Refresh mit der bisherigen Fassung vergleichen.
4. `python3 -m calcpad_gui --doctor` mit der realen CLI ausführen und anschließend
   Berechnung/Fehlerfälle in der UI prüfen.
5. Wurzeln über `1/5`, inverse/n-te/verschachtelte Wurzeln und hohe Brüche in
   echtem WebKit prüfen; Theme, Schriftladen, Resize und Scroll-/Zeilensprünge
   vergleichen.
6. HTML/PDF/DOCX und Quick-Word exportieren; OMML-Editierbarkeit, grüne Einheiten,
   Dezimaltrennzeichen, Nichtüberschreiben vorhandener Word-Dateien und Desktopöffnung
   mit der tatsächlichen Office-Anwendung verifizieren.
7. Neues Fenster über die vorhandene Desktopregistrierung und den Modul-Fallback
   auslösen; Starter und vorhandenes Logo in der realen Repositorystruktur prüfen.
