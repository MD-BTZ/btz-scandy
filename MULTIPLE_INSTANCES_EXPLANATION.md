# Mehrere Instances - Erklärung der Verbesserungen

## Problem
Das ursprüngliche Skript zeigte eine Warnung "ALLE DATEN GEHEN VERLOREN!" bei jeder zweiten Installation, auch wenn es sich um eine andere Instance handelte.

## Ursache
Das Skript prüfte nur, ob eine `docker-compose.yml` Datei existiert, ohne zu berücksichtigen, dass es sich um verschiedene Instances handeln könnte.

## Lösung
Das Skript wurde verbessert und prüft jetzt:

### 1. Instance-spezifische Prüfung
```bash
# Alt: Prüfte nur ob docker-compose.yml existiert
if [ -f "docker-compose.yml" ]; then
    # Warnung vor Datenverlust
fi

# Neu: Prüft ob die gleiche Instance bereits existiert
if grep -q "scandy-app-$INSTANCE_NAME" docker-compose.yml; then
    # Warnung nur bei gleicher Instance
else
    # Installation mit anderem Namen wird fortgesetzt
fi
```

### 2. Intelligente Port-Konflikt-Prüfung
- Zeigt an, welcher Prozess den Port blockiert
- Gibt konkrete Lösungsvorschläge
- Erklärt, dass mehrere Instances parallel laufen können

### 3. Instance-Übersicht
- Zeigt an, welche anderen Scandy-Instances bereits laufen
- Erklärt, dass alle Instances parallel betrieben werden können

## Beispiele

### ✅ Korrekte Verwendung für mehrere Instances:

```bash
# Erste Instance (Standard)
./install_unified.sh

# Zweite Instance (andere Ports automatisch)
./install_unified.sh -n verwaltung

# Dritte Instance (andere Ports automatisch)
./install_unified.sh -n produktion
```

### ✅ Keine Warnung mehr bei:
- Verschiedenen Instance-Namen
- Verschiedenen Ports
- Parallel-Betrieb mehrerer Instances

### ⚠️ Warnung nur noch bei:
- Gleichem Instance-Namen
- Gleichen Ports
- Tatsächlichem Datenverlust-Risiko

## Vorteile

1. **Keine falschen Warnungen** mehr bei verschiedenen Instances
2. **Bessere Benutzerführung** mit konkreten Lösungsvorschlägen
3. **Transparenz** über laufende Instances
4. **Sicherheit** bleibt bei tatsächlichen Risiken erhalten

## Migration

Die Verbesserungen sind rückwärtskompatibel:
- Bestehende Installationen funktionieren weiterhin
- Alte Skripte können weiterhin verwendet werden
- Neue Features sind optional 