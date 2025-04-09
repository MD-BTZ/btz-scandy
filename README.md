# Scandy - Werkzeug- und Materialverwaltung

## Demo-Datenbank

Die Datei `app/database/inventory.db` enthält eine SQLite-Datenbank mit Demodaten. Diese dient zu Demonstrations- und Testzwecken und enthält:

- Beispielwerkzeuge
- Beispiel-Verbrauchsmaterialien
- Beispiel-Mitarbeiter
- Beispiel-Abteilungen und Standorte
- Beispiel-Ausleihvorgänge und Materialentnahmen

**Hinweis**: Diese Datenbank enthält nur Testdaten und sollte nicht für den produktiven Einsatz verwendet werden.

## Datenbankschema

Das Schema der Datenbank ist in der Datei `schema.sql` dokumentiert. Es enthält die Struktur aller Tabellen und Indizes.

## Entwicklung

Für die Entwicklung können Sie die Demo-Datenbank als Ausgangspunkt verwenden:

1. Stellen Sie sicher, dass der Ordner `app/database` existiert
2. Die Datenbank `inventory.db` wird automatisch mit dem Repository geladen
3. Für eigene Tests können Sie die Datenbank kopieren und den Pfad in der Konfiguration anpassen 