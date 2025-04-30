# Einführung in Scandy

## Was ist Scandy?

Scandy ist eine webbasierte Anwendung zur Verwaltung von Werkzeugen und Verbrauchsmaterialien in Unternehmen. Die Anwendung ermöglicht es, den Bestand zu verwalten, Ausleihvorgänge zu dokumentieren und die Materialentnahme zu protokollieren.

## Grundlegende Konzepte

### 1. Werkzeuge
- Physische Gegenstände, die ausgeliehen werden können
- Jedes Werkzeug hat einen eindeutigen Barcode
- Status-Tracking (verfügbar, ausgeliehen, defekt, etc.)
- Kategorisierung und Standortverwaltung

### 2. Verbrauchsmaterial
- Materialien, die verbraucht werden
- Bestandsverwaltung mit Mindestbestand
- Protokollierung der Entnahme
- Kategorisierung und Lagerort

### 3. Mitarbeiter
- Benutzer der Anwendung
- Zugehörigkeit zu Abteilungen
- Ausleihhistorie
- Zugriffsrechte

### 4. Ausleihen
- Dokumentation von Ausleihvorgängen
- Rückgabeprotokollierung
- Statusverfolgung
- Erinnerungssystem

### 5. Barcode-System
- Eindeutige Identifikation von Werkzeugen
- Schnelle Erfassung durch Scannen
- Vereinfachte Prozesse
- Reduzierung von Fehlern

### 6. Tickets
- System für Meldungen und Probleme
- Statusverfolgung
- Zuweisung an Verantwortliche
- Dokumentation der Lösung

## Vorteile von Scandy

1. **Effizienz**
   - Schnelle Erfassung durch Barcode-Scanning
   - Automatisierte Prozesse
   - Reduzierung von manuellen Eingaben

2. **Transparenz**
   - Klare Übersicht über Bestände
   - Nachvollziehbare Ausleihvorgänge
   - Dokumentierte Materialentnahme

3. **Sicherheit**
   - Benutzerauthentifizierung
   - Rollenbasierte Zugriffsrechte
   - Protokollierung aller Aktionen

4. **Flexibilität**
   - Anpassbare Kategorien
   - Erweiterbare Funktionalität
   - Responsive Design für mobile Nutzung

## Systemanforderungen

### Server
- Python 3.x
- SQLite-Datenbank
- Webserver (z.B. Gunicorn)
- Mindestens 1GB RAM
- 10GB Festplattenspeicher

### Client
- Moderner Webbrowser (Chrome, Firefox, Safari, Edge)
- Internetverbindung
- Optional: Barcode-Scanner

## Lizenzierung

Scandy ist unter der MIT-Lizenz verfügbar. Details finden Sie in der [LICENSE](../LICENSE)-Datei. 