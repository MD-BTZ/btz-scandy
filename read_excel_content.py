#!/usr/bin/env python3
"""
Skript zum Lesen und Anzeigen des Inhalts der Excel-Datei
"""

import pandas as pd
import sys
from pathlib import Path

def read_excel_file(file_path):
    """Liest eine Excel-Datei und zeigt den Inhalt aller Arbeitsblätter"""
    
    try:
        # Excel-Datei lesen
        excel_file = pd.ExcelFile(file_path)
        
        print(f"Excel-Datei: {file_path}")
        print(f"Anzahl Arbeitsblätter: {len(excel_file.sheet_names)}")
        print(f"Arbeitsblätter: {excel_file.sheet_names}")
        print("-" * 80)
        
        # Jedes Arbeitsblatt durchgehen
        for sheet_name in excel_file.sheet_names:
            print(f"\n=== Arbeitsblatt: {sheet_name} ===")
            
            # Arbeitsblatt lesen
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            print(f"Dimensionen: {df.shape[0]} Zeilen x {df.shape[1]} Spalten")
            print(f"Spaltennamen: {list(df.columns)}")
            
            # Erste 10 Zeilen anzeigen
            print("\nErste 10 Zeilen:")
            print(df.head(10).to_string(index=False))
            
            # Datentypen anzeigen
            print(f"\nDatentypen:")
            for col, dtype in df.dtypes.items():
                print(f"  {col}: {dtype}")
            
            # Nicht-leere Werte pro Spalte
            print(f"\nNicht-leere Werte pro Spalte:")
            for col in df.columns:
                non_null_count = df[col].notna().sum()
                print(f"  {col}: {non_null_count}/{len(df)} ({non_null_count/len(df)*100:.1f}%)")
            
            print("-" * 80)
            
    except Exception as e:
        print(f"Fehler beim Lesen der Excel-Datei: {e}")
        return None

def main():
    # Excel-Datei-Pfad
    excel_file = "scandy_gesamtexport_20250528_104419.xlsx"
    
    if not Path(excel_file).exists():
        print(f"Fehler: Datei {excel_file} nicht gefunden!")
        sys.exit(1)
    
    # Excel-Datei lesen
    read_excel_file(excel_file)

if __name__ == "__main__":
    main() 