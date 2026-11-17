# King Smith Walking Pad

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![Community Forum][forum-shield]][forum]

[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]


Custom integration to connect Home Assistant with [King Smith Walking Pads][king_smith].

This integration provides a belt switch, speed control in km/h, and session and accumulated sensors for speed, distance, duration, steps, and cadence.

This integration discovers/connects to the device using bluetooth (you may need to configure a bluetooth proxy like an ESP32).

The upstream integration was tested with C2 and A1 Pro devices. This fork adds a Z1 FTMS implementation for `KS-HD-Z1D` and targets Home Assistant 2026.11.2. Validation on the owner’s Z1 and Bluetooth proxies is pending.

In order for the device to be connected to HA, it must not be connected to another device (e.g. the mobile app). If it is already configured via the mobile app, you will have to disconnect it before using it in HA.

## Kingsmith Z1 über HACS einrichten

Dieser Fork unterstützt die Erkennung von `KS-HD-Z1D` und implementiert den FTMS-Verbindungsaufbau einschließlich der dokumentierten KingSmith-Freischaltung. Voraussetzung ist Home Assistant ab 2026.11.2 mit einem lokalen Bluetooth-Adapter oder einem Proxy, der aktive Bluetooth-Verbindungen unterstützt.

1. In HACS das Menü für benutzerdefinierte Repositorys öffnen.
2. `https://github.com/koalexbear/king_smith` mit Typ **Integration** hinzufügen.
3. **King Smith** herunterladen. Bei einer Versionsauswahl den aktuellen Stand von `main` verwenden. Bei bereits installierter Integration zuerst die Repository-Informationen aktualisieren und anschließend „Erneut herunterladen“ wählen.
4. Home Assistant neu starten, das Z1 einschalten und KS Fit vollständig schließen.
5. Unter **Einstellungen → Geräte & Dienste** das erkannte WalkingPad konfigurieren. Alternativ **Integration hinzufügen → King Smith Walking Pad** öffnen und das Gerät auswählen oder seine Bluetooth-MAC-Adresse eintragen.
6. Einen Namen vergeben und die angelegten Entities auf dem Dashboard anzeigen.

Falls bereits eine andere Integration mit Domain `king_smith` installiert ist, erfolgt die Installation über deren bestehenden Eintrag. HACS verwaltet pro Domain einen Komponentenordner.

Der Schalter startet das Laufband mit seiner geräteseitigen Startgeschwindigkeit und beendet beim Ausschalten die Sitzung. Die Geschwindigkeitseinstellung verwendet die vom Gerät gemeldete Schrittweite und Höchstgeschwindigkeit. **0 km/h stoppt das Band.** Positive Werte müssen mindestens der vom Gerät gemeldeten Mindestgeschwindigkeit entsprechen. Das Setzen einer positiven Geschwindigkeit kann ein stehendes Band starten.

Statuswerte folgen den Bluetooth-Meldungen des Geräts. Bis zur ersten Meldung können sie „Unbekannt“ anzeigen. Ein Reload oder eine Wiederverbindung baut die Bluetooth-Verbindung neu auf. Start- und Geschwindigkeitsbefehle werden ausschließlich durch die entsprechenden Benutzeraktionen ausgelöst.

Die Gesamtzähler speichern ihren letzten Sitzungsstand, damit ein Neustart während einer Sitzung bereits erfasste Werte nicht erneut addiert. Beim Upgrade alter Gesamtzähler ohne gespeicherten Sitzungsstand wird die erste aktuelle Meldung als Ausgangswert übernommen. Vollständige Sitzungen während einer HA-Ausfallzeit lassen sich nur erfassen, wenn das Gerät passende Historie bereitstellt. Ein Sitzungswechsel während einer Ausfallzeit kann bei erneut höheren Zählern unentdeckt bleiben.

Für ein Dashboard eine Entities-Karte hinzufügen und den Laufband-Schalter, die Geschwindigkeitseinstellung und die gewünschten Sensoren dieses Geräts auswählen. Home Assistant vergibt die Entity-IDs passend zum gewählten Gerätenamen.

Bei Verbindungsproblemen in Home Assistant die Debug-Protokollierung der Integration einschalten. Für die Protokollanalyse kann zusätzlich der Logger `walkingpad_controller` auf `debug` gesetzt werden. Hilfreich sind die Fehlermeldung beim Einrichten, die Firmware-Version und der verwendete Bluetooth-Adapter beziehungsweise Proxy.

Die Protokollimplementierung verwendet [walkingpad-controller](https://github.com/mcdax/walkingpad-controller). Die Z1-Freischaltsequenz ist im Projekt [z1-walkingpad-mcp](https://github.com/slandau3/z1-walkingpad-mcp#how-it-works-the-protocol) dokumentiert. Beide Projekte stehen unter der MIT-Lizenz.

## Manual installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `king_smith`.
1. Download _all_ the files from the `custom_components/king_smith/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. Click on `Settings` and then `Devices & services`
1. If the treadmill is on and not currently connected to another device, it should show up in the `Discovered` list. Click `configure` and give it a name.

## Configuration is done in the UI

## Verified Supported Models

* C2
* A1 Pro

(if you have a King Smith treadmill and would like to verify support, please reach out)

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[king_smith]: https://github.com/ludeeus/integration_blueprint
[buymecoffee]: https://www.buymeacoffee.com/indiefan
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/koalexbear/king_smith.svg?style=for-the-badge
[commits]: https://github.com/koalexbear/king_smith/commits/main
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/indiefan/king_smith.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/koalexbear/king_smith.svg?style=for-the-badge
[releases]: https://github.com/koalexbear/king_smith/releases
