# Scandy App Update

## 📋 Übersicht

Dieses Dokument erklärt, wie Sie die Scandy-App aktualisieren können. Das Update muss über das Host-System durchgeführt werden, da der Docker-Container während des Updates heruntergefahren wird.

## ⚠️ Wichtige Hinweise

- **Downtime:** Die App ist während des Updates für ca. 10-15 Minuten nicht erreichbar
- **Benutzer:** Stellen Sie sicher, dass keine anderen Benutzer aktiv sind
- **Backup:** Das Update erstellt automatisch ein Backup vor dem Update
- **Daten:** Alle Daten in MongoDB bleiben erhalten

## 🔄 Update-Methoden

### Methode 1: Update-Script (Empfohlen)

Das einfachste Update erfolgt über das bereitgestellte `update.sh` Script:

```bash
# 1. Zum Projektverzeichnis wechseln
cd /pfad/zu/scandy2

# 2. Update-Script ausführen
./update.sh

# 3. Warten bis das Update abgeschlossen ist
# Die App ist dann automatisch wieder verfügbar
```

### Methode 2: Manuelles Docker-Compose Update

Alternativ können Sie das Update auch manuell durchführen:

```bash
# 1. Zum Projektverzeichnis wechseln
cd /pfad/zu/scandy2

# 2. Neuesten Code von GitHub holen
git pull origin main

# 3. Container stoppen
docker-compose down

# 4. Container neu bauen und starten
docker-compose up -d --build
```

## 📁 Was wird aktualisiert?

- ✅ **Scandy App:** Neueste Version mit Bugfixes und Features
- ✅ **Python-Abhängigkeiten:** Aktualisierte Libraries
- ✅ **Frontend-Assets:** Neue CSS/JS-Dateien
- 🔒 **MongoDB:** Bleibt unverändert
- 🔒 **Mongo Express:** Bleibt unverändert
- 💾 **Daten:** Alle Benutzerdaten bleiben erhalten

## 🔍 Update-Status prüfen

Nach dem Update können Sie prüfen, ob alles funktioniert:

```bash
# Container-Status prüfen
docker-compose ps

# Logs der Scandy-App anzeigen
docker-compose logs scandy-app

# App im Browser aufrufen
http://localhost:5000
```

## 🚨 Fehlerbehebung

### App ist nach Update nicht erreichbar

1. **Container-Status prüfen:**
   ```bash
   docker-compose ps
   ```

2. **Logs prüfen:**
   ```bash
   docker-compose logs scandy-app
   ```

3. **Container neu starten:**
   ```bash
   docker-compose restart scandy-app
   ```

4. **Bei Problemen: Vollständiger Neustart**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Update-Script funktioniert nicht

1. **Berechtigungen prüfen:**
   ```bash
   chmod +x update.sh
   ```

2. **Git-Status prüfen:**
   ```bash
   git status
   ```

3. **Manuelles Update durchführen** (siehe Methode 2)

## 📞 Support

Bei Problemen mit dem Update:

1. Prüfen Sie die Logs: `docker-compose logs scandy-app`
2. Kontaktieren Sie den Administrator
3. Im Notfall: Backup wiederherstellen

---

**Hinweis:** Das Update-Script ist für Linux/macOS optimiert. Unter Windows verwenden Sie `update.bat`. 