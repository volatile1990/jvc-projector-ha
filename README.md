# JVC Projector Resilient Home Assistant Integration

Custom integration fuer JVC Projektoren in Home Assistant.

Diese Integration basiert auf der Home-Assistant-Core-Integration `jvc_projector`,
laedt den Config Entry aber auch dann, wenn der Projektor beim Home-Assistant-Start
stromlos ist oder waehrend der Bootphase noch keine TCP-Verbindung auf Port `20554`
annimmt.

## Verhalten

- verwendet weiterhin die Domain `jvc_projector`
- ueberschreibt damit die mit Home Assistant gelieferte JVC-Integration
- bestehende Config Entries und Entity IDs koennen weiterverwendet werden
- ein ausgeschalteter oder stromloser Projektor blockiert das Setup nicht
- Entities werden sofort geladen; der erste Refresh laeuft im Hintergrund
- Entities werden bei Kommunikationsfehlern `unavailable`
- sobald der Projektor wieder erreichbar ist, stellt der Coordinator den Zustand
  automatisch beim naechsten Poll wieder her
- das erkannte Modell wird im Config Entry gespeichert, damit spaetere Starts auch
  ohne erreichbaren Projektor mit den richtigen Capabilities funktionieren

## Installation

### HACS Custom Repository

1. Home Assistant oeffnen.
2. HACS oeffnen.
3. Custom repository hinzufuegen.
4. Diese Repository-URL als Kategorie `Integration` eintragen.
5. Integration installieren.
6. Home Assistant neu starten.

### Manuell

Den Ordner kopieren nach:

```text
custom_components/jvc_projector
```

Zielstruktur:

```text
custom_components/
`-- jvc_projector/
    |-- __init__.py
    |-- binary_sensor.py
    |-- config_flow.py
    |-- const.py
    |-- coordinator.py
    |-- entity.py
    |-- icons.json
    |-- manifest.json
    |-- remote.py
    |-- select.py
    |-- sensor.py
    |-- switch.py
    |-- strings.json
    `-- util.py
```

Danach Home Assistant neu starten.

## Hinweis zu bestehenden Installationen

Weil die Domain identisch zu Core ist, sollte Home Assistant nach dem Neustart
eine Warnung fuer eine Custom Integration `jvc_projector` loggen. Das ist
erwartet und zeigt, dass diese Integration statt der Core-Version geladen wurde.
