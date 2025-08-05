# 🧪 Sichere Test-Anleitung für Kantinenplan-API

## Übersicht

Diese Anleitung zeigt, wie Sie das neue API-System sicher testen können, ohne das aktuelle System zu beeinträchtigen.

## 🛡️ Sicherheitsmaßnahmen

### ✅ Isolierte Test-Umgebung
- **Separate Test-Dateien**: Alle Test-Dateien sind vom Hauptsystem getrennt
- **Test-Cache**: Eigene Cache-Dateien für Tests
- **Keine Produktionsdaten**: Tests verwenden keine echten Daten
- **Rückwärtskompatibel**: Altes System bleibt unverändert

## 📋 Test-Schritte

### Schritt 1: Scandy-API testen

```bash
# 1. Scandy-App starten (falls nicht läuft)
cd /path/to/scandy
docker-compose up -d

# 2. API-Endpunkte testen
curl http://localhost:5000/api/canteen/status
curl http://localhost:5000/api/canteen/current_week

# 3. Python-Test-Suite ausführen
python3 test_canteen_api.py
```

**Erwartete Ausgabe:**
```
🚀 Kantinenplan-API Test-Suite
==================================================
🧪 Starte API-Tests...

1️⃣ Teste Status-Endpunkt...
✅ Status-API funktioniert: {'success': True, 'feature_enabled': True}

2️⃣ Teste Current Week Endpunkt...
✅ Current Week API funktioniert
📅 Anzahl Mahlzeiten: 5

3️⃣ Teste API mit Key...
✅ API-Key-Authentifizierung funktioniert (erwarteter 401)
```

### Schritt 2: WordPress-Test-Umgebung

```bash
# 1. Test-PHP-Datei auf WordPress-Server kopieren
scp test_wordpress_canteen.php user@wordpress-server:/var/www/html/test/

# 2. Im Browser öffnen
http://wordpress-server.com/test/test_wordpress_canteen.php
```

**Erwartete Ausgabe:**
- ✅ Test-Modus-Warnung
- ✅ API-Verbindung erfolgreich
- ✅ Cache-Funktionalität getestet
- ✅ Test-Kantinenplan angezeigt

### Schritt 3: Integration testen

```bash
# 1. Kantinenplan in Scandy eingeben
# 2. API erneut aufrufen
curl http://localhost:5000/api/canteen/current_week

# 3. WordPress-Test erneut ausführen
# 4. Prüfen ob neue Daten angezeigt werden
```

## 🔧 Test-Konfiguration

### Scandy-Seite
```python
# In test_canteen_api.py
base_url = "http://localhost:5000"  # Anpassen an Ihre URL
```

### WordPress-Seite
```php
// In test_wordpress_canteen.php
$scandy_api_url = 'http://localhost:5000/api/canteen/current_week';
$api_key = ''; // Leer für Tests
$cache_duration = 60; // 1 Minute für Tests
```

## 📊 Test-Ergebnisse

### ✅ Erfolgreiche Tests
- API-Endpunkte antworten korrekt
- WordPress kann API-Daten abrufen
- Cache-Mechanismus funktioniert
- Performance ist akzeptabel

### ❌ Häufige Probleme

**Problem 1: API nicht erreichbar**
```bash
# Lösung: Scandy-App prüfen
docker ps
docker logs scandy-app-scandy
```

**Problem 2: CORS-Fehler**
```bash
# Lösung: CORS-Header prüfen
curl -H "Origin: http://wordpress-server.com" \
     -H "Access-Control-Request-Method: GET" \
     http://localhost:5000/api/canteen/current_week
```

**Problem 3: Cache-Fehler**
```bash
# Lösung: Berechtigungen prüfen
ls -la test_canteen_cache.json
chmod 644 test_canteen_cache.json
```

## 🚀 Migration nach erfolgreichen Tests

### 1. Produktions-API aktivieren
```bash
# API-Key setzen
echo "CANTEEN_API_KEY=your-secure-key" >> .env

# Scandy-App neu starten
docker-compose restart
```

### 2. WordPress anpassen
```php
// In kantine_api.php (Produktionsversion)
$scandy_api_url = 'https://your-scandy-server.com/api/canteen/current_week';
$api_key = 'your-secure-api-key';
$cache_duration = 300; // 5 Minuten
```

### 3. Alte Systeme deaktivieren
```bash
# SFTP-Credentials entfernen (optional)
# Alte kantine.php umbenennen
mv kantine.php kantine.php.backup
```

## 📁 Test-Dateien

### Erstellte Dateien
- `test_canteen_api.py` - Python-Test-Suite
- `test_wordpress_canteen.php` - WordPress-Test
- `test_canteen_cache.json` - Test-Cache
- `canteen_api_test_report.json` - Test-Report

### Aufräumen nach Tests
```bash
# Test-Dateien entfernen (optional)
rm test_canteen_api.py
rm test_wordpress_canteen.php
rm test_canteen_cache.json
rm canteen_api_test_report.json
```

## 🔍 Monitoring während Tests

### Scandy-Logs
```bash
# API-Zugriffe überwachen
docker logs -f scandy-app-scandy | grep "API"
```

### WordPress-Logs
```bash
# PHP-Fehler überwachen
tail -f /var/log/apache2/error.log
```

### Performance-Monitoring
```bash
# API-Response-Zeiten messen
time curl http://localhost:5000/api/canteen/current_week
```

## ✅ Erfolgskriterien

### Technische Kriterien
- [ ] API-Endpunkte antworten mit HTTP 200
- [ ] WordPress kann API-Daten abrufen
- [ ] Cache-Mechanismus funktioniert
- [ ] Performance < 1 Sekunde pro Anfrage
- [ ] Keine Fehler in Logs

### Funktionale Kriterien
- [ ] Kantinenplan-Daten werden korrekt angezeigt
- [ ] Datum-Formatierung ist korrekt
- [ ] Cache-Invalidierung funktioniert
- [ ] Fallback bei API-Fehlern funktioniert

### Sicherheitskriterien
- [ ] API-Key-Authentifizierung funktioniert
- [ ] Keine sensiblen Daten in Logs
- [ ] CORS-Konfiguration korrekt
- [ ] Rate Limiting aktiv

## 🎯 Nächste Schritte

Nach erfolgreichen Tests:

1. **Produktions-API aktivieren**
2. **WordPress-Server anpassen**
3. **Monitoring einrichten**
4. **Alte Systeme deaktivieren**
5. **Dokumentation aktualisieren**

## 📞 Support

Bei Problemen:
1. Test-Logs prüfen
2. API-Status abfragen
3. Cache-Dateien prüfen
4. Netzwerk-Verbindung testen

**Viel Erfolg beim Testen! 🚀** 