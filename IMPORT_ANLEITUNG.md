# Excel-Import-Funktion für Scandy

## Übersicht

Die Scandy-Anwendung unterstützt jetzt den Import von Daten aus Excel-Dateien (.xlsx). Die Import-Funktion ist flexibel und erkennt automatisch sowohl deutsche als auch englische Spaltennamen.

## Unterstützte Arbeitsblätter

### 1. Werkzeuge (Sheet: "Werkzeuge")
**Erforderliche Spalten:**
- `Barcode` (oder `barcode`)
- `Name` (oder `name`)

**Optionale Spalten:**
- `Kategorie` (oder `category`, `cat`)
- `Standort` (oder `location`, `loc`)
- `Status` (oder `status`) - Standard: "verfügbar"
- `Beschreibung` (oder `description`, `desc`)

### 2. Mitarbeiter (Sheet: "Mitarbeiter")
**Erforderliche Spalten:**
- `Barcode` (oder `barcode`)
- `Vorname` (oder `firstname`, `vorname`)
- `Nachname` (oder `lastname`, `nachname`)

**Optionale Spalten:**
- `Abteilung` (oder `department`, `dept`)
- `E-Mail` (oder `email`, `e-mail`)

### 3. Verbrauchsmaterial (Sheet: "Verbrauchsmaterial")
**Erforderliche Spalten:**
- `Barcode` (oder `barcode`)
- `Name` (oder `name`)

**Optionale Spalten:**
- `Kategorie` (oder `category`, `cat`)
- `Standort` (oder `location`, `loc`)
- `Menge` (oder `quantity`, `qty`) - Standard: 0
- `Mindestmenge` (oder `min_quantity`, `min_qty`) - Standard: 0
- `Beschreibung` (oder `description`, `desc`)
- `Einheit` (oder `unit`, `Einheiten`) - Standard: "Stück"

### 4. Verlauf (Sheet: "Verlauf") - Optional
**Erforderliche Spalten:**
- `Ausgeliehen am` (oder Spalte mit "ausgeliehen" im Namen)
- `Werkzeug-Barcode` (oder Spalte mit "werkzeug" und "barcode")
- `Mitarbeiter-Barcode` (oder Spalte mit "mitarbeiter" und "barcode")

**Optionale Spalten:**
- `Zurückgegeben am` (oder Spalte mit "zurückgegeben" im Namen)

## Verwendung

### 1. Über die Web-Oberfläche
1. Melden Sie sich als Administrator oder Mitarbeiter an
2. Gehen Sie zu **Admin → System**
3. Scrollen Sie zum Abschnitt **"Daten importieren"**
4. Wählen Sie Ihre Excel-Datei aus
5. Klicken Sie auf **"Importieren"**

### 2. Datei-Format
- **Dateityp:** .xlsx (Excel 2007+)
- **Encoding:** UTF-8
- **Erste Zeile:** Spaltenüberschriften
- **Daten:** Ab Zeile 2

## Beispiel-Excel-Struktur

### Werkzeuge
| Barcode | Name | Kategorie | Standort | Status | Beschreibung |
|---------|------|-----------|----------|--------|--------------|
| 1001 | Akkuschrauber | Elektrowerkzeuge | Werkstatt A | verfügbar | 18V Akkuschrauber |
| 1002 | Hammer | Handwerkzeug | Werkstatt B | verfügbar | 500g Hammer |

### Mitarbeiter
| Barcode | Vorname | Nachname | Abteilung | E-Mail |
|---------|---------|----------|-----------|--------|
| 2001 | Max | Mustermann | Technik | max@firma.de |
| 2002 | Anna | Musterfrau | Verwaltung | anna@firma.de |

### Verbrauchsmaterial
| Barcode | Name | Kategorie | Standort | Menge | Mindestmenge | Beschreibung |
|---------|------|-----------|----------|-------|--------------|--------------|
| 3001 | Schrauben | Verbrauchsgut | Lager A | 1000 | 100 | M4x20 Schrauben |
| 3002 | Masken | Verbrauchsgut | Lager B | 50 | 10 | FFP2 Masken |

## Import-Verhalten

### Duplikat-Behandlung
- **Werkzeuge/Mitarbeiter/Verbrauchsmaterial:** Werden basierend auf dem Barcode aktualisiert (upsert)
- **Verlauf:** Nur neue Einträge werden hinzugefügt (keine Duplikate)

### Datenvalidierung
- Leere Zeilen werden übersprungen
- Fehlende optionale Felder werden mit Standardwerten gefüllt
- Datumsfelder werden automatisch konvertiert
- Zahlen werden automatisch konvertiert

### Fehlerbehandlung
- Fehler in einzelnen Zeilen werden protokolliert
- Der Import wird fortgesetzt, auch wenn einzelne Zeilen fehlschlagen
- Detaillierte Fehlermeldungen werden angezeigt

## Tipps für erfolgreichen Import

1. **Spaltennamen:** Verwenden Sie die exakten Spaltennamen oder Varianten
2. **Barcodes:** Stellen Sie sicher, dass Barcodes eindeutig sind
3. **Datenqualität:** Überprüfen Sie die Daten vor dem Import
4. **Backup:** Erstellen Sie ein Backup vor dem Import großer Datenmengen
5. **Test:** Testen Sie den Import mit einer kleinen Datei zuerst

## Fehlerbehebung

### Häufige Probleme

**"Arbeitsblatt 'Werkzeuge' nicht gefunden"**
- Stellen Sie sicher, dass das Arbeitsblatt "Werkzeuge" heißt
- Prüfen Sie die Groß-/Kleinschreibung

**"Ungültige Spaltenüberschriften"**
- Überprüfen Sie die Spaltennamen in der ersten Zeile
- Stellen Sie sicher, dass erforderliche Spalten vorhanden sind

**"Fehler beim Importieren"**
- Prüfen Sie das Excel-Datei-Format (.xlsx)
- Überprüfen Sie die Datenqualität
- Schauen Sie in die Logs für detaillierte Fehlermeldungen

## Support

Bei Problemen mit dem Import:
1. Überprüfen Sie die Fehlermeldungen in der Web-Oberfläche
2. Prüfen Sie die Logs der Anwendung
3. Testen Sie mit der bereitgestellten Test-Datei (`test_import.xlsx`) 