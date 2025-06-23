#!/usr/bin/env python3
"""
Test-Skript für die Import-Funktion
"""

import pandas as pd
from datetime import datetime

def create_test_excel():
    """Erstellt eine Test-Excel-Datei mit den korrekten Spaltennamen"""
    
    # Werkzeuge Daten
    tools_data = {
        'Barcode': [1001, 1002, 1003],
        'Name': ['Test Werkzeug 1', 'Test Werkzeug 2', 'Test Werkzeug 3'],
        'Kategorie': ['Elektrowerkzeuge', 'Handwerkzeug', 'Messgeräte'],
        'Standort': ['Werkstatt A', 'Werkstatt B', 'Labor'],
        'Status': ['verfügbar', 'verfügbar', 'verfügbar'],
        'Beschreibung': ['Test Beschreibung 1', 'Test Beschreibung 2', 'Test Beschreibung 3']
    }
    
    # Mitarbeiter Daten
    workers_data = {
        'Barcode': [2001, 2002, 2003],
        'Vorname': ['Max', 'Anna', 'Tom'],
        'Nachname': ['Mustermann', 'Musterfrau', 'Test'],
        'Abteilung': ['Technik', 'Verwaltung', 'Labor'],
        'E-Mail': ['max@test.de', 'anna@test.de', 'tom@test.de']
    }
    
    # Verbrauchsmaterial Daten
    consumables_data = {
        'Barcode': [3001, 3002, 3003],
        'Name': ['Test Material 1', 'Test Material 2', 'Test Material 3'],
        'Kategorie': ['Verbrauchsgut', 'Verbrauchsgut', 'Verbrauchsgut'],
        'Standort': ['Lager A', 'Lager B', 'Lager C'],
        'Menge': [100, 50, 75],
        'Mindestmenge': [10, 5, 15],
        'Beschreibung': ['Test Beschreibung 1', 'Test Beschreibung 2', 'Test Beschreibung 3']
    }
    
    # Verlauf Daten
    history_data = {
        'Ausgeliehen am': [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ],
        'Zurückgegeben am': [None, None, None],
        'Werkzeug': ['Test Werkzeug 1', 'Test Werkzeug 2', 'Test Werkzeug 3'],
        'Werkzeug-Barcode': [1001, 1002, 1003],
        'Mitarbeiter': ['Max Mustermann', 'Anna Musterfrau', 'Tom Test'],
        'Mitarbeiter-Barcode': [2001, 2002, 2003],
        'Typ': ['Werkzeug Ausleihe', 'Werkzeug Ausleihe', 'Werkzeug Ausleihe'],
        'Menge': [None, None, None]
    }
    
    # Excel-Datei erstellen
    with pd.ExcelWriter('test_import.xlsx', engine='openpyxl') as writer:
        pd.DataFrame(tools_data).to_excel(writer, sheet_name='Werkzeuge', index=False)
        pd.DataFrame(workers_data).to_excel(writer, sheet_name='Mitarbeiter', index=False)
        pd.DataFrame(consumables_data).to_excel(writer, sheet_name='Verbrauchsmaterial', index=False)
        pd.DataFrame(history_data).to_excel(writer, sheet_name='Verlauf', index=False)
    
    print("Test-Excel-Datei 'test_import.xlsx' erstellt!")
    print("Sie können diese Datei über die Admin-Oberfläche importieren.")

if __name__ == "__main__":
    create_test_excel() 