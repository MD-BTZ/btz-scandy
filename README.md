# Scandy - Werkzeug- und Materialverwaltung

## 🎉 Beta v1.0.0 - Erste Beta-Version für Produktivtest

**Status:** Beta für Produktivtest  
**Version:** 1.0.0-beta  
**Datum:** 25. Juni 2025

## 🚀 Neue Features in Beta v1.0.0

### ✅ Datenbankinkonsistenzen behoben
- **Notice-System:** Inkonsistente Feldnamen behoben (`active` → `is_active`)
- **MongoDB-Funktionen:** Vollständig implementiert (keine TODO-Kommentare mehr)
- **Automatische Inkonsistenzbehebung:** Nach Backup-Import
- **Performance-Indizes:** Fehlende Datenbankindizes erstellt

### 🔧 Verbesserungen
- **Reparatur-Skripte:** `fix_database_inconsistencies.py`
- **Bessere Fehlerbehandlung:** Für Index-Konflikte
- **Datenbankintegritätsprüfung:** Automatische Validierung

## 📋 Über Scandy

Scandy ist eine moderne Webanwendung zur Verwaltung von Werkzeugen, Verbrauchsmaterial und Mitarbeitern. Die Anwendung bietet ein umfassendes System für Ausleihe, Rückgabe und Bestandsverwaltung.

### 🎯 Hauptfunktionen

- **Werkzeugverwaltung:** Vollständige CRUD-Operationen für Werkzeuge
- **Mitarbeiterverwaltung:** Verwaltung von Mitarbeitern und Abteilungen
- **Verbrauchsmaterial:** Bestandsverwaltung und Verbrauchserfassung
- **Ausleihsystem:** Einfache Ausleihe und Rückgabe von Werkzeugen
- **Ticket-System:** Support-Tickets für Wartung und Reparaturen
- **Backup-System:** Automatische Sicherung und Wiederherstellung
- **Notice-System:** Ankündigungen und Hinweise für Benutzer

## 🛠️ Technische Details

### Architektur
- **Backend:** Flask (Python)
- **Datenbank:** MongoDB
- **Frontend:** HTML, CSS, JavaScript (Bootstrap)
- **Container:** Docker & Docker Compose

### Datenbankinkonsistenzen behoben
- ✅ 10 Kategorien synchronisiert
- ✅ 15 Standorte aktualisiert  
- ✅ 8 Abteilungen korrigiert
- ✅ 0 Integritätsprobleme gefunden

## 📦 Installation

### Docker (Empfohlen)

```bash
# Repository klonen
git clone <repository-url>
cd Scandy2

# Produktionsversion starten
docker-compose up -d

# Oder Test-Version (separate Ports)
docker-compose -f docker-compose.test.yml up -d
```

### Manuelle Installation

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Datenbankinkonsistenzen beheben (falls vorhanden)
python fix_database_inconsistencies.py

# Anwendung starten
python -m flask run
```

## 🔧 Wartung

### Automatische Inkonsistenzbehebung
Nach jedem Backup-Import wird automatisch die Kategorien-Inkonsistenz behoben.

### Manuelle Reparatur
```bash
# Alle Inkonsistenzen beheben
python fix_database_inconsistencies.py

# Nur Kategorien-Inkonsistenz
python fix_category_inconsistency.py
```

## 🧪 Testing

### Test-Umgebung
```bash
# Test-Container starten
./test_app.sh

# Zugriff: http://localhost:5002
# MongoDB: localhost:27019
```

### Funktionen getestet
- [x] Admin-Setup und Benutzerverwaltung
- [x] Werkzeug-Verwaltung (CRUD)
- [x] Mitarbeiter-Verwaltung
- [x] Verbrauchsmaterial-Verwaltung
- [x] Ausleihe/Rückgabe-System
- [x] Ticket-System
- [x] Backup/Restore-Funktionen
- [x] Notice-System

## 📊 Ports

### Produktionsversion
- **Scandy App:** http://localhost:5000
- **MongoDB:** localhost:27017

### Test-Version
- **Scandy App:** http://localhost:5002
- **MongoDB:** localhost:27019

## 🚨 Bekannte Probleme

### ⚠️ Hinweise
- **Docker Compose Version:** `version` Attribut ist obsolete (harmlos)
- **Development-Server:** Für Produktion WSGI-Server verwenden

### 🔄 Geplante Verbesserungen
- [ ] Logo-Upload-Funktionalität implementieren
- [ ] Update-System vervollständigen
- [ ] Performance-Monitoring hinzufügen

## 📞 Support

Bei Problemen:
1. **Logs prüfen:** `docker-compose logs -f scandy`
2. **Datenbank-Reparatur:** `python fix_database_inconsistencies.py`
3. **Backup erstellen:** Vor größeren Änderungen

## 📋 Release Notes

Detaillierte Informationen zu dieser Beta-Version findest du in [BETA_RELEASE_NOTES.md](BETA_RELEASE_NOTES.md).

## 🎯 Nächste Schritte

1. **Produktivtest:** Umfassende Tests in Produktionsumgebung
2. **Feedback sammeln:** Benutzer-Feedback zu neuen Features
3. **Performance-Monitoring:** Überwachung der Datenbank-Performance
4. **Stable Release:** Nach erfolgreichem Produktivtest

---

**Diese Beta-Version ist bereit für den Produktivtest!** 🚀 