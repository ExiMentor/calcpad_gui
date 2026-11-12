# Architektur und Wartungsverträge

## Ziel und bewusste Grenzen

Ausgangspunkt ist ausschließlich die bestätigte root-fix-v3-Version (3013 Zeilen).
Das Refactoring trennt Verantwortungen und ermöglicht Tests ohne GI, ohne die
Callback-API oder die Rechen-/Darstellungsalgorithmen neu zu entwerfen. Es wurden
keine zusätzlichen Frameworks, Abhängigkeiten, Hintergrunddienste oder neuen
Benutzeroberflächen eingeführt. Der bewusst mechanisch erhaltene Code behält auch
seinen bisherigen kompakten Stil; eine umfassende Neuformatierung oder fachliche
Korrektur wäre ein eigenständiger, risikoreicherer Schritt.

## Abhängigkeitsrichtung

```text
app.py / calcpad_gui.__main__ / calcpad-gui (Konsolenstarter)
                  |
             application
        bootstrap + config.initialize_paths
                  |
                window
       +----------+----------+
      ui/      domain/     preview/
       |                     |
   services/             resource_loader
       |                     |
   Standardbibliothek    resources/
```

`data`, `config`, `domain`, `services` und `preview` importieren kein GI und keine
UI-Klasse. `bootstrap.py` ist das einzige Versions-Gate. `application.py`
initialisiert die von GLib gelieferten Verzeichnisse, bevor Module mit den
Desktop-Pfadkonstanten importiert werden. `calcpad_gui.__init__` bleibt leichtgewichtig.
Die internen UI-/Fenstermodule sind keine alternativen Startpunkte; dafür dienen
`app.py` und `calcpad_gui.__main__`; der Konsolenstarter zeigt ebenfalls direkt
auf `calcpad_gui.application:main`. Die frühere Fassade `calcpad_gui/app.py` ist
absichtlich entfernt. Historische Importe aus `calcpad_gui.app` und
`python3 -m calcpad_gui.app` entfallen als einzige neue Kompatibilitätsänderung.
Die Implementierungen und Fachmodule bleiben unverändert.

## Feature-zu-Modul-Zuordnung

| Bereich | Modul | Erhaltener Vertrag |
|---|---|---|
| App-ID, Titel, Defaults, Beispiel, griechische Zeichen, Hotkeys | `data.py` | nur der sichtbare App-Titel ist jetzt `CalcpadCE`; sonst gleiche Werte, kein neuer Settings-Schlüssel |
| Persistenz | `config.py` | bekannte Schlüssel laden, bisherige JSON-/I/O-Fehlerbehandlung |
| Sprache | `language.py`, `resources/calcpad.lang` | bestehende Datei erhalten, Suchpfad ergänzen |
| GI / App-Lebenszyklus / Diagnose | `bootstrap.py`, `application.py`, `doctor.py` | gleiche Namespace-/Versionsfehler, Open-/Activate- und Doctor-Abläufe |
| Fensterinitialisierung | `window.py` | dieselbe Setup-Reihenfolge, Signale und Start-Timer |
| Highlighting, Zoom, Editorzeilen, Formatieren, Textzugriff | `ui/editor.py` | dieselben Puffer-/Cursoraktionen und GTK-Controller |
| Completion | `ui/autocomplete.py` | Verzögerung, Symbole oberhalb Cursor, kein Wiederöffnen kompletter Namen |
| Suchen / Ersetzen | `ui/search.py` | Auswahl, Vorwärts-/Rückwärtssuche, Ersetzungsabläufe |
| Header, Layout, Theme, Recent-Menü, Optionen, Shortcuts | `ui/chrome.py` | gleiche Aktionen, Menüs, Optionen und Tastenkürzel |
| Virtuelle Tastatur, Favoriten, Symbolauswahl | `ui/keyboard.py` | gleiche Einfügeaktionen, Bereinigung und Persistenz |
| WebKit-Bridge und Scroll-/Zeilensynchronisierung | `ui/preview.py` | gleiche API-Fallbacks und Title-Protokolle |
| Zahlen-/Dezimalformatierung | `domain/numbers.py` | nur HTML-Textteile bearbeiten; Präzisionsgrenzen erhalten |
| Mikropräfix, Unicode, parallele Widerstände, Zeilenformatierung | `domain/expressions.py` | Editorinhalt unverändert, CLI-Eingabe normalisieren |
| HTML, Wurzel-CSS/JS, anklickbare Zeilen | `preview/html.py`, `resources/` | identische ausgegebene Literale und v3-Wurzelgeometrie |
| Scroll-Restore-Helper | `preview/scroll.py` | historische Importfunktion unverändert |
| CLI-Suche / Aufruf | `services/cli.py` | Aufrufreihenfolge, Flags, Umgebung, Timeout, Eingabedatei-Cleanup |
| Auto-Refresh / Berechnungs-Worker | `ui/calculation.py` | Busy-/Closing-Guards, `GLib.idle_add`, Fehlerpreview |
| Öffnen / Speichern / Dirty-/Close-Dialoge / neues Fenster | `ui/files.py` | Rohtext speichern, keine stillschweigende Verwerfung, Modul-Fallback |
| Standard-/Word-Quick-Export | `ui/exports.py` | HTML/PDF/DOCX, exklusive Namen, Desktopöffnung |
| DOCX/OMML-Nachverarbeitung | `domain/docx.py` | OMML erhalten, Einheiten grün, Dezimaltrennzeichen, ZIP-Teile |
| Logo-Suche | `assets.py` | vorhandene SVG-/PNG-Dateien finden, keine Dateierzeugung |

## Explizite Komposition statt dynamischer Magie

`CalcpadWindow` kombiniert neun fokussierte UI-Verhaltensklassen sowie vier reine
Verhaltensklassen mit `Gtk.ApplicationWindow`. Die Verhaltensklassen sind
zustandslose Methoden-Namensräume; die Daten liegen auf **demselben Fensterobjekt**.
Sie definieren weder `__init__` noch `super()`-Ketten. Nur `CalcpadWindow.__init__`
initialisiert das GTK-Fenster und baut seine gemeinsamen Attribute auf. Es gibt
keine dynamische Methodenkopie, keinen Import mit `*`, kein `exec`/`eval`, keine
Manipulation von `sys.path` und keine Rückimporte zur Fensterklasse.

Diese gezielte Kompatibilitätsschicht lässt sämtliche **121 vorhandenen
Fenstermethoden** unter ihren bisherigen Namen auflösbar. Auch `classmethod` und
`staticmethod` bleiben echte Deskriptoren. Alle Methodensignaturen sind eingefroren;
die Tests prüfen fehlende, doppelte und verdeckte Implementierungen sowie die
Auflösung der über `self` verbundenen Callbacks. Die drei `CalcpadApp`-Methoden
bleiben unverändert.

Gemeinsame Zustandsverträge:

- `settings`, `current_file`, `buffer`, `editor`, `webview`, `status` werden im
  bisherigen Aufbau angelegt. UI-Verhalten erwartet diese Attribute, wie zuvor die
  Methoden der einen Klasse. Separates Instanziieren einzelner UI-Klassen ist kein
  unterstützter Anwendungsstart.
- Pure Zahlen-/HTML-Methoden benötigen ein Objekt mit `settings`; Preview erwartet
  zusätzlich `_format_preview_numbers`. `ExpressionTransforms` erhält die rekursiven
  `cls`-Aufrufe, damit Unterklassen weiterhin überschreiben können. DOCX-Verhalten
  benötigt weder GTK noch Settings; die Trennzeichenoption wird explizit übergeben.
- Neue UI-Callbacks erhalten eindeutige Namen und werden in `window.py` explizit
  zugeordnet. Die Tests des eingefrorenen Inventars bewusst erweitern, statt eine
  Kollision durch die MRO verdecken zu lassen.

## Prozess-, Thread- und Dateibesitz

`services.cli.run_cli` ist synchron und erhält Kommando, Hint, Format, Body-Flag,
eine **lazy** Quelltextfunktion, HTML-Wrapper, Escape-Funktion und optional einen
bereits gelesenen Quelltext. Dadurch bleiben fehlende-CLI-/Dateifehler und die
bisherige GTK-Escapefunktion unverändert, während der Dienst ohne GI testbar wird.
`_run_cli` auf dem Fenster ist der dünne Adapter und bleibt überschreibbar.

Der Dienst besitzt die temporäre Eingabe und löscht sie im bisherigen `finally`.
Bei Erfolg gehört die Ausgabedatei dem Aufrufer: Preview-Finish liest und löscht
sie, Export verschiebt sie. Die bestehenden Fehlerpfade wurden nicht neu gestaltet;
die Tests behaupten insbesondere keine neu hinzugefügte, allumfassende
Absturz-/Leak-Freiheit in zuvor ungeprüften Sonderfällen.

Die vorhandenen Worker und `GLib.idle_add`-Übergänge bleiben erhalten. Quick-Word
liest GTK-Zustand wie bisher vor dem Worker und reserviert den Zielnamen exklusiv
mit `xb`. Abbruch/Fehler entfernt dessen leere Reservierung. Die bestehende Preview-
und Standardexport-Quelltextbeschaffung wurde **nicht** nebenbei threadtechnisch
umgeschrieben; die Tests prüfen die erhaltenen Übergänge, nicht allgemeine
Thread-Sicherheit der gesamten Anwendung. DOCX wird in einer Nachbardatei `.tmp`
verarbeitet und danach wie bisher verschoben; bei Verarbeitungsfehlern bleibt das
Original erhalten und die Staging-Datei wird entfernt.

## Die vier gezielten Methoden-Anpassungen

117 von 121 Fenstermethoden sind AST-identisch verschoben. Nur diese vier benötigen
Adapter-/Ressourcenänderungen:

1. `_wrap_preview`: CSS und das komplette Script-Element als UTF-8-Paketdaten laden;
   deren Bytes bleiben unverändert. Light/Dark, Zahlenformatierung und HTML-Hülle
   werden über 48 eingefrorene vollständige Ausgabehashes geprüft.
2. `_inject_output_line_navigation`: die beiden unveränderten CSS-/Script-Literale
   aus Ressourcen laden. Das wiederholte Einfügen bleibt idempotent.
3. `_run_cli`: Delegation an den GI-freien Dienst. Sein Funktionskörper ist eine
   mechanische Parametrisierung des alten Körpers; eigener AST-Digest und
   Aufruf-/Fehler-/Cleanup-Tests sichern die Extraktion ab.
4. `_build_headerbar`: Logo mit `assets.find_logo()` suchen, da das verschobene
   `__file__` sonst auf ein anderes Verzeichnis zeigte. Alle übrigen Buttons,
   Aktionen und Signale bleiben unverändert. Der Suchvertrag steht im README.

Auch das Anlegen der Konfigurationsverzeichnisse ist vom Import reiner Module an
den Desktop-Einstieg gerückt. Dort werden explizit die ursprünglichen GLib-Pfade
verwendet; auf dieser Plattform erfolgt keine Settings-Migration. Der reine Import
berechnet höchstens XDG-Standardpfade, liest oder schreibt aber keine Benutzerdaten.

## Ressourcen und Paketierung

`importlib.resources` liest XML/CSS/HTML-Literale unabhängig vom aktuellen
Arbeitsverzeichnis; Lesen als Bytes vermeidet Newline-Konvertierung. `lru_cache`
verhindert wiederholte Festplattenzugriffe bei Auto-Refresh. Die Literale werden
bei Paketierung über `pyproject.toml` mitgenommen. Die Wurzelkorrektur bleibt
**root-fix-v3**, einschließlich numeric-pair matching, inverser Layouts, kontinuierlichem
SVG-Pfad, Range-/positionierten Bounds, innerer-vor-äußerer Neuberechnung,
ResizeObserver, Font- und Viewport-Ereignissen. Kein Teil des Algorithmus wurde
funktional neu formuliert.
