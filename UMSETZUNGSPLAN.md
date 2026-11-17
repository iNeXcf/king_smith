# Kingsmith Z1 in Home Assistant

## Ziel und Ausgangslage

Stand der Analyse ist der 17. November 2026 auf Commit `7e01359`.
Zielsystem ist Home Assistant 2026.11.2 auf einem Raspberry Pi mit integriertem Bluetooth und mehreren Bluetooth-Proxys in der Wohnung. Die genaue Installationsart und die Proxy-Konfiguration sind noch offen.
Der vom Nutzer bestätigte Bluetooth-Name ist `KS-HD-Z1D`.

Die Integration soll das Z1 über Bluetooth einrichten, das Laufband starten und stoppen, die Geschwindigkeit einstellen und die tatsächlich verfügbaren Messwerte anzeigen. Verbindungsabbrüche, Integrations-Reloads und Home-Assistant-Neustarts gehören zur Abnahme.

Als erste Ausbaustufe sind ein Laufband-Schalter, eine Geschwindigkeitseinstellung in km/h sowie Sensoren für aktuelle Geschwindigkeit, Sitzungsdauer und Distanz vorgesehen. Welche Messwerte dein Gerät liefert, wird am Gerät geprüft. Schritte und Schrittfrequenz hängen vom ermittelten Protokoll und den verfügbaren Daten ab.

## Umsetzungsstand

Der Code für die FTMS-Anbindung von `KS-HD-Z1D`, die Supplement-Freischaltung, zentrale Verbindungsverwaltung, manuelle Einrichtung, deutsche Texte und die korrigierten Entities ist implementiert. Geschwindigkeitsgrenzen stammen aus dem Gerät. Schritte werden über die KingSmith-Erweiterung ausgewertet. Fehlende optionale Messwerte bleiben bis zur ersten passenden Meldung unbekannt.

Die lokalen Tests verwenden Home Assistant 2026.11.2 und simulierten Bluetooth-Transport. Sie prüfen auch das Laden aller zehn Entities, einen Geschwindigkeitsbefehl über den HA-Dienst und das Entladen der Integration. Alle 41 Tests bestehen. Ruff meldet keine Lint-Fehler, Hassfest meldet keine ungültige Integration. Die Migration des alten Konfigurationseintrags und wiederholtes Aufräumen beim Entladen sind ebenfalls getestet.

Die Installation erfolgt über HACS mit diesem Fork. Der Test mit dem echten Z1, dessen Firmware und den vorhandenen Bluetooth-Proxys steht aus. Firmware und GATT-Daten werden bei diesem Test erfasst.

## Vorhandene Architektur

- `manifest.json` beschreibt Bluetooth-Erkennung und Python-Abhängigkeiten.
- `config_flow.py` verarbeitet die Bluetooth-Erkennung und legt einen Konfigurationseintrag an.
- `__init__.py` löst die Bluetooth-Adresse auf und lädt die Plattformen.
- `walking_pad.py` kapselt `ph4-walkingpad` und hält den Gerätezustand.
- `coordinator.py` verteilt Statusmeldungen und erzeugt Sitzungsereignisse.
- `switch.py`, `number.py` und `sensor.py` stellen einen Schalter, eine Geschwindigkeitseinstellung und acht Sensoren bereit.
- `device_trigger.py` soll Sitzungsereignisse für Geräteautomationen bereitstellen.

Die README nennt C2 und A1 Pro als verifizierte Modelle. Die Entwicklungsumgebung verwendet Home Assistant 2023.8.0 und Python 3.11. Die Kompatibilität mit deinem Zielsystem muss geprüft werden. Home Assistant 2026.11.2 verlangt laut Projektmetadaten Python ab 3.14.2. [Home-Assistant-Projektmetadaten](https://raw.githubusercontent.com/home-assistant/core/2026.11.2/pyproject.toml)

## Z1-Protokoll als erste technische Abhängigkeit

Der eingebundene Controller verwendet die klassischen WalkingPad-Characteristics `fe01` und `fe02`. Eine untersuchte unabhängige Implementierung ordnet das Z1 der FTMS-Familie mit Service `1826` zu. Daraus folgt die Arbeitshypothese, dass dein Z1 einen zusätzlichen FTMS-Pfad benötigt. Entscheidend sind die GATT-Services deines konkreten Geräts. [Bisheriger Controller](https://raw.githubusercontent.com/ph4r05/ph4-walkingpad/master/ph4_walkingpad/pad.py), [Z1-Zuordnung in BeltControl](https://github.com/morsela/beltcontrol#will-it-work-with-my-pad)

Mit dem bestätigten Namen `KS-HD-Z1D` lässt sich die Recherche konkretisieren. Sowohl `walkingpad-controller` als auch die Home-Assistant-Integration `mcdax/hass-walkingpad` führen genau dieses Gerät als getestet mit FTMS auf. Die weitere Umsetzung priorisiert deshalb den FTMS-Pfad und prüft die bestehende Bibliothek als Grundlage. Firmware und GATT-Tabelle deines konkreten Geräts sind noch zu erfassen. [Controller-Bibliothek](https://github.com/mcdax/walkingpad-controller), [Vorhandene HA-Integration](https://github.com/mcdax/hass-walkingpad)

Eine weitere Implementierung dokumentiert für `KS-HD-Z1D` mit Firmware V0.0.6 eine Freischaltsequenz über den KingSmith-Supplement-Service vor der FTMS-Kommunikation. Diese Initialisierung wird bei der Bibliotheksprüfung und der Geräteabnahme ausdrücklich berücksichtigt. Der Geschwindigkeitsbereich wird aus dem Gerät gelesen, da die veröffentlichten Geräteberichte unterschiedliche Grenzen nennen. [Z1-Initialisierung](https://github.com/slandau3/z1-walkingpad-mcp#how-it-works-the-protocol)

Die aktuelle `manifest.json` erkennt ausschließlich `KS-BL*`, `KS-ST-*` und `WalkingPad`. Keines dieser Muster passt auf `KS-HD-Z1D`. Damit ist bereits ein konkreter Fehler in der automatischen Erkennung dieses Geräts belegt.

## Befunde im Repository

Die Zeilenangaben beziehen sich auf den analysierten Commit.

| Priorität | Fundstelle | Befund und Auswirkung |
| --- | --- | --- |
| P0 | `walking_pad.py`, Zeilen 43–45 | Jeder Befehl erzeugt einen eigenen `asyncio.Lock`. Gleichzeitige Zugriffe werden dadurch gegenseitig freigegeben. |
| P0 | `walking_pad.py`, Zeilen 134–201 | Das Freigeben von `_status_lock` erfolgt erst nach erfolgreichem Befehlsabschluss. Ein BLE-Fehler kann die Statusverarbeitung dauerhaft sperren. |
| P0 | `entity.py`, Zeilen 13–27 | Alle Plattformen erhalten IDs mit Domain `king_smith`. Erwartet werden die jeweiligen Plattform-Domains. Geschwindigkeitssensor und Geschwindigkeitseinstellung erzeugen zudem denselben vorgeschlagenen Entity-ID-Text. |
| P0 | `walking_pad.py`, Zeilen 22 und 134–140 | Der Controller wird fest auf die bisherige Bibliothek festgelegt. Die Eignung für das konkrete Z1-Protokoll ist ungeprüft. |
| P0 | `manifest.json`, Bluetooth-Matcher | Der bestätigte Name `KS-HD-Z1D` passt auf keines der vorhandenen Namensmuster. Die automatische Erkennung dieses Geräts wird dadurch nicht ausgelöst. |
| P1 | `config_flow.py`, Zeilen 13–49 | `async_step_user` fehlt. Die Einrichtung über „Integration hinzufügen“ hat damit keinen implementierten Einstieg. `self.devices` wird erst durch Bluetooth-Discovery initialisiert. |
| P1 | `config_flow.py`, Zeile 16, und `strings.json` | Die Flow-Version ist `0.1`. Ein ganzzahliges Versionsschema samt Umgang mit alten Einträgen fehlt. Texte für Einrichtungsformulare und Fehler fehlen ebenfalls. |
| P1 | `entity.py`, Zeilen 33–51, und `coordinator.py`, Zeilen 37–41 | Jede Entity pollt das gemeinsame Gerät selbst. Der Coordinator hat keinen zentralen Aktualisierungszyklus. Mehrere Plattformen können sich bei Abfragen und Steuerbefehlen überschneiden. |
| P1 | `switch.py`, Zeilen 71–85, und `__init__.py`, Zeilen 52–59 | Verbindungsaufbau und Trennung hängen am Schalter. Das Deaktivieren dieser Entity beeinflusst die übrigen Plattformen. Beim Unload wird der Coordinator samt Timer nicht explizit heruntergefahren. |
| P1 | `walking_pad.py`, Zeilen 52–59 und 203–223 | Statusmeldungen werden nach Befehlen fünf Sekunden verworfen. Fehlerzustände und unerwartete Disconnects werden unvollständig an Entities weitergegeben. |
| P1 | `walking_pad.py`, Zeilen 150–201, und `switch.py` | Steuerbefehle bei fehlender Verbindung kehren still zurück. Der Schalter setzt seinen Zustand teilweise schon vor dem bestätigten Ergebnis. Dadurch kann Home Assistant einen erfolgreichen Start anzeigen. |
| P1 | `sensor.py`, Klassen `TotalDistanceSensor`, `TotalTimeSensor`, `TotalStepsSensor` | Der Gesamtwert wird wiederhergestellt, der letzte Sitzungsstand beginnt erneut bei null. Eine laufende Sitzung kann nach einem Neustart erneut auf den Gesamtwert addiert werden. |
| P1 | `__init__.py`, Zeile 45, und `coordinator.py`, Zeilen 82–97 | Die Config-Entry-ID wird als Geräte-ID an Ereignisse übergeben. Geräteautomationen erwarten die ID aus der Device Registry. |
| P1 | `device_trigger.py`, Zeilen 56–91 | Die Trigger-Auflistung filtert Entity-Domains auf `king_smith`. Die Anbindung wählt den Ereignistyp nicht anhand des konfigurierten Triggers aus und verlangt ein `type`-Feld, das die gesendeten Ereignisse nicht enthalten. |
| P2 | `number.py`, Zeilen 19–22 und 80–83 | Geschwindigkeitsgrenzen sind fest codiert. Die Umrechnung mit `int(value * 10)` kann durch Gleitkommaabrundung einen zu kleinen Wert senden. |
| P2 | `coordinator.py`, Zeilen 63–99 | Sitzungsende wird allein am Zurücksetzen der Laufzeit erkannt. Ob Stop, Pause und Wiederaufnahme beim Z1 so abgebildet werden, ist offen. |
| P2 | `requirements.txt`, `.devcontainer.json`, CI und README | Entwicklungsbasis, Dokumentation und Fork-Verweise müssen auf das Zielsystem und die geprüften Funktionen abgestimmt werden. Automatisierte Tests fehlen. |

## Durchgeführte Prüfungen

- Alle zehn Python-Dateien lassen sich unter dem lokal verfügbaren Python 3.14.10 syntaktisch parsen.
- `manifest.json`, `strings.json` und `hacs.json` sind gültiges JSON.
- Eine isolierte Prüfung der vorhandenen Methoden bestätigt, dass zwei `_begin_cmd()`-Aufrufe unterschiedliche Locks liefern.
- Ein simulierter BLE-Fehler in `change_speed()` lässt `_status_lock` gesetzt.
- Die vorhandene Gesamtzähler-Methode macht aus einem wiederhergestellten Wert von 1000 und einer darin bereits enthaltenen Sitzung mit 300 Schritten den Wert 1300.
- Der manuelle Einstieg `async_step_user` fehlt im Syntaxbaum.
- Die vorhandenen drei Bluetooth-Namensmuster wurden gegen `KS-HD-Z1D` geprüft. Alle Vergleiche liefern keinen Treffer.

Die isolierten Prüfungen verwenden Ersatzobjekte für externe Abhängigkeiten. Ein vollständiger Home-Assistant-Lauf, Ruff, Hassfest und Tests mit deinem Z1 stehen aus. Lokal fehlen die installierten Projektabhängigkeiten und `pip`.

## Umsetzungsschritte

### 1. Zielumgebung und Gerät erfassen

- [ ] Genaue Installationsart und Bluetooth-Proxy-Typen festhalten.
- [x] Bluetooth-Namen erfassen. Der Nutzer bestätigt `KS-HD-Z1D`.
- [ ] Adresse und Advertisement-Services des Z1 über Home Assistant erfassen.
- [ ] GATT-Services, Characteristics und deren Read-, Write-, Notify- und Indicate-Eigenschaften auslesen. Firmware und Modellinformationen erfassen, soweit verfügbar.
- [ ] Für die Verbindung zur Geräteprüfung die KS-Fit-Verbindung freigeben.
- [ ] Prüfen, welche Proxys aktive GATT-Verbindungen unterstützen und einen freien Verbindungsslot haben.
- [ ] Aus den vorhandenen Services den passenden Protokollpfad bestimmen.

**Abnahme** — Geräteprofil und verwendbarer Verbindungsweg sind dokumentiert. Die angebotenen Messwerte und Steuer-Characteristics sind bekannt.

Home Assistant verwaltet lokale Adapter und Remote-Proxys gemeinsam. Die Integration soll Geräte mit `connectable=True` auflösen und diese Auswahl bei einer Wiederverbindung erneuern. Die aktuelle Dokumentation empfiehlt `bluetooth_adapters` als Abhängigkeit, neue Clients pro Verbindung und Wiederholungen für vorübergehende Verbindungsfehler. [Bluetooth-Dokumentation](https://contributors.home-assistant.io/core/integrations/bluetooth/)

### 2. Entwicklungsbasis auf Home Assistant 2026.11.2 bringen

- [ ] Eine isolierte Entwicklungsumgebung mit passender Python-Version und Home Assistant 2026.11.2 einrichten.
- [ ] Runtime-Abhängigkeiten auf Kompatibilität prüfen und reproduzierbar festlegen.
- [ ] Imports und verwendete Home-Assistant-APIs gegen die Zielversion prüfen.
- [ ] Devcontainer und CI auf dieselbe Python- und Home-Assistant-Basis bringen.
- [ ] Den bestehenden Integrationsaufbau und die Domain `king_smith` weiterverwenden.

**Abnahme** — Die Integration lässt sich in einer frischen Zielumgebung laden. Vorhandene Lint- und Validierungsbefunde sind erfasst und werden mit den betroffenen Änderungen behoben.

### 3. Verbindung, Befehle und Zustandsaktualisierung korrigieren

Betroffene Dateien sind vor allem `walking_pad.py`, `coordinator.py`, `__init__.py`, `entity.py` und `switch.py`.

- [ ] Einen gemeinsamen Lock für Geräteoperationen anlegen. Mehrteilige Start- und Stop-Sequenzen zusammenhängend ausführen.
- [ ] Befehlsabstände protokollgerecht behandeln und Ressourcen mit `finally` auch bei Fehlern und Abbruch freigeben.
- [ ] Verbindung und Lebenszyklus im Config Entry beziehungsweise Coordinator verwalten.
- [ ] Vor dem Anlegen der Entities eine erste erfolgreiche Zustandsabfrage durchführen. Vorübergehende Setup-Fehler über Home Assistants Wiederholungsmechanismus behandeln.
- [ ] Aktualisierungen zentral koordinieren. Je nach Protokoll Statusabfragen oder Notifications verwenden.
- [ ] Unerwartete Disconnects und ausbleibende Statusantworten erkennen, Verfügbarkeit aktualisieren und die Verbindung mit begrenzter Wiederholungsrate neu aufbauen.
- [ ] Fehlgeschlagene Steueraktionen als verständliche Home-Assistant-Fehler weitergeben.
- [ ] Beim Unload Timer, Notifications, Callbacks und Verbindung vollständig aufräumen.

**Abnahme** — Alle Entities nutzen eine gemeinsame Geräteverbindung. Parallel ausgelöste Aktionen bleiben geordnet. Nach einem Fehler sind weitere Befehle und Statusmeldungen möglich. Das Deaktivieren des Schalters unterbricht die Sensoren nicht.

Die zentrale Datenverteilung und der erste Refresh folgen dem dokumentierten Coordinator-Lebenszyklus. [Coordinator-Dokumentation](https://contributors.home-assistant.io/core/integrations/fetching-data/)

### 4. Den bestätigten Z1-Protokollpfad integrieren

- [ ] Falls die GATT-Prüfung klassische `fe00`-Services bestätigt, den vorhandenen Controller mit den korrigierten Verbindungs- und Befehlsabläufen verwenden.
- [ ] `walkingpad-controller` gezielt auf Z1-Initialisierung, HA-2026.11.2-Kompatibilität und lokale sowie Proxy-Verbindungen prüfen. Die Integration `mcdax/hass-walkingpad` als Referenz für deren Verwendung prüfen.
- [ ] Den passenden FTMS-Controller hinter der vorhandenen API einbinden. Statuswerte und Einheiten anpassen, da die Kandidatenbibliothek Geschwindigkeit in km/h und Distanz in Metern bereitstellt.
- [ ] Den KingSmith-Supplement-Service und eine gegebenenfalls erforderliche Freischaltung vor der FTMS-Kommunikation berücksichtigen.
- [ ] Bei FTMS Control-Point-Indications abonnieren, Steuerberechtigung anfordern und Befehlsergebnisse mit Timeout auswerten.
- [ ] FTMS-Messwerte anhand ihrer Flags und jeweiligen Einheiten auswerten. Den angebotenen Geschwindigkeitsbereich berücksichtigen.
- [ ] Falls das Gerät ein abweichendes Herstellerprotokoll zeigt, dessen Initialisierung und Datenformat anhand der Geräteinformationen untersuchen.
- [ ] Einheitliche Zustandswerte für die Entities bereitstellen. Fehlende Messwerte als unbekannt behandeln und die dazugehörigen Entities bedarfsgerecht anlegen.

**Abnahme** — Statuswerte stimmen mit der Anzeige beziehungsweise KS Fit überein. Start, Stop und Geschwindigkeitsänderung werden vom Gerät bestätigt und anschließend im Istzustand sichtbar.

Die untersuchte FTMS-Referenz beschreibt Control Point `2ad9`, Treadmill Data `2acd` und den Geschwindigkeitsbereich `2ad4`. Für KingSmith-Schritte dokumentiert `walkingpad-controller` inzwischen eine Herstellererweiterung über FTMS-Flag-Bit 13. Das bietet einen konkreten Ansatz für Schritte und Schrittfrequenz, dessen Daten auf deinem Gerät geprüft werden. [FTMS-Protokollreferenz](https://raw.githubusercontent.com/morsela/beltcontrol/main/docs/protocols.md), [KingSmith-Erweiterungen](https://github.com/mcdax/walkingpad-controller)

### 5. Einrichtung und Steuer-Entities fertigstellen

- [ ] Einen manuellen Config Flow mit den von Home Assistant gesehenen Geräten und verständlichen Fehlermeldungen ergänzen.
- [ ] Discovery-Matcher für `KS-HD-Z1D` ergänzen und auf verbindbare Geräte abstimmen. Erweiterungen auf weitere Namensmuster anhand belegter Geräteprofile vornehmen.
- [ ] Flow-Version und Umgang mit bestehenden Einträgen prüfen.
- [ ] Entity-IDs durch die jeweilige Plattform und Registry vergeben lassen. Bestehende Unique IDs bei der Migration berücksichtigen.
- [ ] Geschwindigkeit mit korrekter Rundung, Schrittweite und Gerätebereich validieren.
- [ ] Das Verhalten für Geschwindigkeit null anhand des Protokolls eindeutig auf Stop abbilden.
- [ ] Zustände aus Geräteantworten aktualisieren und die pauschale fünfsekündige Statusunterdrückung ersetzen.
- [ ] Deutsche und englische Texte für Einrichtung, Entities und Fehler ergänzen.

**Abnahme** — Das Gerät lässt sich über Discovery und „Integration hinzufügen“ einrichten. Doppelte Einrichtung wird erkannt. Schalter, Geschwindigkeitseinstellung und Sensoren erscheinen unter ihren korrekten Plattformen.

### 6. Statistik und Sitzungsereignisse reparieren

- [ ] Gesamtwerte zusammen mit dem letzten bekannten Sitzungsstand wiederherstellen und Sitzungswechsel nachvollziehbar behandeln.
- [ ] Die Grenzen der Erfassung während einer HA-Ausfallzeit anhand der vom Gerät gelieferten Historie dokumentieren.
- [ ] Start, Stop, mögliche Pause und neue Sitzung anhand des bestätigten Protokolls unterscheiden.
- [ ] Ereignisse mit der tatsächlichen Device-Registry-ID und serialisierbaren Daten senden.
- [ ] Beide Geräte-Trigger genau einmal anbieten und jeweils den zugehörigen Ereignistyp mit passendem Gerätefilter abonnieren.
- [ ] Schrittfrequenz nur bei gültigen Schritt- und Zeitdifferenzen berechnen.

**Abnahme** — Ein HA-Neustart während einer Sitzung zählt bereits erfasste Werte nicht erneut. Start- und Abschlussautomationen reagieren jeweils auf das richtige Gerät und Ereignis.

### 7. Tests, Installation und Abnahme am Gerät

- [ ] Regressionstests für gemeinsame Befehlssperre, Fehlerfreigabe, Gesamtzähler-Restore und Ereignisfilter ergänzen.
- [ ] Config Flow, Duplicate-Erkennung, Setup-Retry, Unload und Wiederverbindung mit simuliertem BLE testen.
- [ ] Bei FTMS die tatsächlich benötigten Paketvarianten, optionale Felder, unvollständige Daten und Control-Point-Antworten testen.
- [ ] Ruff, die automatisierten Tests, Hassfest und HACS-Validierung ausführen.
- [ ] Manuelle Installation und HACS-Custom-Repository-Installation für diesen Fork dokumentieren. README und Manifest-Verweise aktualisieren.
- [ ] Ein Dashboard-Beispiel mit den nach der Einrichtung tatsächlich vergebenen Entity-IDs ergänzen.
- [ ] Start, Stop und mehrere Geschwindigkeiten am Z1 prüfen.
- [ ] Änderungen über die physische Fernbedienung in Home Assistant nachverfolgen.
- [ ] Aus- und Einschalten des Z1, Integrations-Reload und HA-Neustart prüfen.
- [ ] Verbindung über Pi-Bluetooth und mindestens einen geeigneten Proxy prüfen. Ausfall des verwendeten Adapters und anschließende Wiederverbindung über eine erreichbare Quelle testen.
- [ ] Mindestens 30 Minuten laufen lassen und Werte, Verbindungsstabilität sowie Logs prüfen.

**Abnahme** — Die Integrationsdateien sind installierbar, Prüfungen laufen durch und die dokumentierten Funktionen funktionieren auf deinem Home Assistant 2026.11.2 mit deinem Z1.

## Reihenfolge und nächster Meilenstein

Geräteprofil und Entwicklungsumgebung können zuerst erarbeitet werden. Danach folgen die gemeinsame Verbindungslogik und der ermittelte Z1-Protokollpfad, anschließend Einrichtung, Statistik und Hardware-Abnahme.

Der nächste Meilenstein ist eine unter Home Assistant 2026.11.2 ladbare Integration, die `KS-HD-Z1D` erkennt, eine Verbindung über Home Assistants Bluetooth-Infrastruktur aufbaut und einen gültigen Status empfängt. Als Grundlage wird `walkingpad-controller` geprüft. Für die Hardware-Abnahme werden noch Firmware, Advertisement-Informationen und GATT-Services deines konkreten Geräts erfasst.
