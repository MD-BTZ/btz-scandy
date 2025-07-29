#!/usr/bin/env python3
"""
Test-Skript für erweiterte Backup-Kompatibilität
Demonstriert die neuen Funktionen für alte JSON-Backups
"""

import sys
import os
from pathlib import Path

# Füge das app-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.backup_manager import backup_manager

def test_backup_compatibility():
    """Testet die Kompatibilität aller verfügbaren Backups"""
    print("🔍 Teste Backup-Kompatibilität...")
    
    # Finde alle Backup-Dateien
    backup_dir = Path("backups")
    if not backup_dir.exists():
        print("❌ Backup-Verzeichnis nicht gefunden")
        return
    
    json_backups = list(backup_dir.glob("*.json"))
    if not json_backups:
        print("❌ Keine JSON-Backups gefunden")
        return
    
    print(f"📁 Gefunden: {len(json_backups)} JSON-Backups")
    
    for backup_file in json_backups:
        print(f"\n{'='*60}")
        print(f"🔍 Analysiere: {backup_file.name}")
        print(f"{'='*60}")
        
        try:
            # Teste Backup-Kompatibilität
            success, result = backup_manager.analyze_backup_compatibility(backup_file.name)
            
            if success:
                report = result
                print(f"✅ Analyse erfolgreich")
                print(f"   - Kompatibilitäts-Score: {report['compatibility_score']}/100")
                print(f"   - Empfehlungen: {len(report['recommendations'])}")
            else:
                print(f"❌ Analyse fehlgeschlagen: {result}")
                
        except Exception as e:
            print(f"💥 Fehler bei der Analyse: {e}")

def test_old_backup_restore_simulation():
    """Simuliert die Wiederherstellung alter Backups ohne tatsächliche Wiederherstellung"""
    print("\n🔄 Teste Backup-Wiederherstellung (Simulation)...")
    
    backup_dir = Path("backups")
    if not backup_dir.exists():
        print("❌ Backup-Verzeichnis nicht gefunden")
        return
    
    json_backups = list(backup_dir.glob("*.json"))
    if not json_backups:
        print("❌ Keine JSON-Backups gefunden")
        return
    
    # Wähle das neueste Backup für den Test
    latest_backup = max(json_backups, key=lambda x: x.stat().st_mtime)
    print(f"📁 Teste Wiederherstellung von: {latest_backup.name}")
    
    try:
        # Teste Backup-Format-Erkennung
        with open(latest_backup, 'r', encoding='utf-8') as f:
            import json
            backup_data = json.load(f)
        
        format_info = backup_manager._detect_old_backup_format(backup_data)
        print(f"   - Format erkannt: {format_info['format_type']} ({format_info['version_estimate']})")
        print(f"   - Collections: {format_info['collections_found']}")
        print(f"   - Dokumente: {format_info['total_documents']}")
        
        # Teste Validierung
        is_valid, validation_message = backup_manager._validate_backup_data(backup_data)
        print(f"   - Gültigkeit: {'✅' if is_valid else '❌'}")
        print(f"   - Validierungsnachricht: {validation_message}")
        
        if is_valid:
            print("✅ Backup ist für Wiederherstellung geeignet")
        else:
            print("❌ Backup hat Validierungsprobleme")
            
    except Exception as e:
        print(f"💥 Fehler beim Testen: {e}")

def demonstrate_format_detection():
    """Demonstriert die erweiterte Format-Erkennung"""
    print("\n🔍 Demonstriere erweiterte Format-Erkennung...")
    
    # Beispiel für verschiedene Backup-Formate
    test_formats = [
        {
            'name': 'Neues Format (2.0+)',
            'data': {
                'metadata': {
                    'version': '2.0',
                    'datatype_preservation': True,
                    'created_at': '2025-01-27T10:00:00'
                },
                'data': {
                    'tools': [{'name': 'Test Tool', '_id': '507f1f77bcf86cd799439011'}],
                    'workers': [{'name': 'Test Worker', '_id': '507f1f77bcf86cd799439012'}],
                    'jobs': [{'title': 'Test Job', '_id': '507f1f77bcf86cd799439013'}]
                }
            }
        },
        {
            'name': 'Altes Format (1.0)',
            'data': {
                'tools': [{'name': 'Old Tool', '_id': '507f1f77bcf86cd799439011'}],
                'workers': [{'name': 'Old Worker', '_id': '507f1f77bcf86cd799439012'}],
                'consumables': [{'name': 'Old Consumable', 'quantity': '10'}]
            }
        },
        {
            'name': 'Sehr altes Format (pre-1.0)',
            'data': {
                'tools': [{'name': 'Very Old Tool', '_id': '507f1f77bcf86cd799439011'}],
                'workers': [{'name': 'Very Old Worker', '_id': '507f1f77bcf86cd799439012'}]
            }
        }
    ]
    
    for test_format in test_formats:
        print(f"\n📋 Test: {test_format['name']}")
        format_info = backup_manager._detect_old_backup_format(test_format['data'])
        print(f"   - Format: {format_info['format_type']}")
        print(f"   - Version: {format_info['version_estimate']}")
        print(f"   - Collections: {format_info['collections_found']}")
        print(f"   - Dokumente: {format_info['total_documents']}")
        print(f"   - Hat Metadata: {format_info['has_metadata']}")
        print(f"   - Datentyp-Erhaltung: {format_info['has_datatype_preservation']}")

if __name__ == "__main__":
    print("🚀 Test der erweiterten Backup-Kompatibilität")
    print("=" * 60)
    
    # Teste Format-Erkennung
    demonstrate_format_detection()
    
    # Teste Backup-Kompatibilität
    test_backup_compatibility()
    
    # Teste Wiederherstellungs-Simulation
    test_old_backup_restore_simulation()
    
    print("\n✅ Tests abgeschlossen")
    print("\n💡 Die erweiterten Backup-Funktionen unterstützen jetzt:")
    print("   - Alte JSON-Backup-Formate (pre-1.0, 1.0, 1.5+)")
    print("   - Erweiterte Datetime-Format-Erkennung")
    print("   - Boolean- und numerische Feld-Konvertierung")
    print("   - Automatische Format-Erkennung und Validierung")
    print("   - Detaillierte Kompatibilitätsanalyse")
    print("   - Fallback-Mechanismen für sehr alte Backups") 