# Platzhalter für Bewerbungsvorlagen

Diese Dokumentation beschreibt die verfügbaren Platzhalter, die in den Bewerbungsvorlagen verwendet werden können.

## Persönliche Daten
- `{{firstname}}` - Vorname des Bewerbers
- `{{lastname}}` - Nachname des Bewerbers
- `{{address}}` - Vollständige Adresse
- `{{phone}}` - Telefonnummer
- `{{email}}` - E-Mail-Adresse
- `{{birthdate}}` - Geburtsdatum
- `{{birthplace}}` - Geburtsort

## Bewerbungsdaten
- `{{position}}` - Bezeichnung der ausgeschriebenen Stelle
- `{{company_name}}` - Name des Unternehmens
- `{{application_date}}` - Datum der Bewerbung
- `{{reference_number}}` - Referenznummer der Stellenausschreibung

## Dokumente
- `{{cv}}` - Platzhalter für den Lebenslauf
- `{{certificates}}` - Platzhalter für Zeugnisse
- `{{cover_letter}}` - Platzhalter für das Anschreiben

## Zusätzliche Informationen
- `{{skills}}` - Liste der Fähigkeiten
- `{{experience}}` - Berufserfahrung
- `{{education}}` - Ausbildung
- `{{languages}}` - Sprachkenntnisse
- `{{notes}}` - Zusätzliche Anmerkungen

## Verwendung
Die Platzhalter können in den Vorlagen wie folgt verwendet werden:

```markdown
Sehr geehrte(r) {{firstname}} {{lastname}},

vielen Dank für Ihre Bewerbung als {{position}} bei {{company_name}}.

Mit freundlichen Grüßen
Ihr Team
```

## Hinweise
- Alle Platzhalter müssen in doppelten geschweiften Klammern `{{}}` eingeschlossen sein
- Platzhalter sind case-sensitive (Groß-/Kleinschreibung beachten)
- Nicht verwendete Platzhalter werden automatisch entfernt
- Bei der Erstellung einer neuen Bewerbung werden die Platzhalter durch die entsprechenden Werte ersetzt 