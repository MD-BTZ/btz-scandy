# **📚 Kantinenplan API-Integration - Vollständige Dokumentation**

## ** Übersicht**

Diese Dokumentation beschreibt die **vollständige Migration** vom CSV-basierten Kantinenplan zur **API-basierten Lösung** mit Scandy.

---

## **📋 1. System-Architektur**

### **🔄 Alte vs. Neue Lösung:**

| **Aspekt** | **Alte Lösung (CSV)** | **Neue Lösung (API)** |
|------------|----------------------|---------------------|
| **Datenquelle** | CSV-Datei auf Server | Scandy MongoDB |
| **Übertragung** | SFTP/SCP | HTTP/HTTPS API |
| **Sicherheit** | Credentials in Datei | API-Key (optional) |
| **Caching** | Kein Cache | 5-Minuten Cache |
| **Skalierbarkeit** | Ein Server | Mehrere WordPress-Server |
| **Wartung** | Manuelle Datei-Übertragung | Automatische API-Synchronisation |

### **🏗️ Neue Architektur:**

```
┌─────────────────┐    HTTP/HTTPS    ┌─────────────────┐
│   WordPress     │ ◄──────────────► │   Scandy API    │
│   Server 1      │                  │   (MongoDB)      │
└─────────────────┘                  └─────────────────┘
         │                                    │
         │                                    │
         ▼                                    ▼
┌─────────────────┐                  ┌─────────────────┐
│   WordPress     │                  │   Cache (5 Min)  │
│   Server 2      │                  │   + Fallback     │
└─────────────────┘                  └─────────────────┘
```

---

## **🔧 2. Scandy-Implementierung**

### **A) Feature-Toggle aktivieren:**

1. **Scandy Admin-Panel öffnen**: `http://localhost:5000/admin/feature_settings`
2. **Kantinenplan-Feature aktivieren**: Checkbox "Kantinenplan" aktivieren
3. **Speichern**

### **B) Benutzer-Berechtigungen:**

1. **Admin-Panel**: `http://localhost:5000/admin/users`
2. **Benutzer bearbeiten**: "Kantinenplan-Eingabe" aktivieren
3. **Speichern**

### **C) Kantinenplan-Eingabe:**

1. **Einloggen**: `http://localhost:5000/auth/login`
2. **Kantinenplan öffnen**: `http://localhost:5000/canteen`
3. **2 Wochen Daten eingeben**:
   - **Woche 1**: Montag-Freitag (aktuelle Woche)
   - **Woche 2**: Montag-Freitag (nächste Woche)
   - **Felder**: Menü 1 (Fleisch), Menü 2 (Vegan), Dessert
4. **Speichern**

### **D) API-Endpunkte:**

#### **Aktuelle Woche (WordPress-Anzeige):**
```
GET /api/canteen/current_week
```

**Response:**
```json
{
  "success": true,
  "week": [
    {
      "date": "Montag, 04.08.2025",
      "meat_dish": "Schnitzel mit Pommes",
      "vegan_dish": "Veganes Curry mit Reis",
      "dessert": "Apfelkuchen",
      "weekday": "Montag"
    }
  ],
  "generated_at": "2025-08-05T15:30:00"
}
```

#### **2 Wochen (Eingabe):**
```
GET /api/canteen/two_weeks
```

#### **Status:**
```
GET /api/canteen/status
```

---

## **🌐 3. WordPress-Integration**

### **A) Vorbereitung:**

#### **1. Backup erstellen:**
```bash
# Backup der alten kantine.php
cp /var/www/html/wp-content/themes/generatepress-child/includes/dl/kantine.php \
   /var/www/html/wp-content/themes/generatepress-child/includes/dl/kantine.php.backup
```

#### **2. Neue Datei installieren:**
```bash
# Kopieren Sie die neue Datei
cp kantine_api_production.php \
   /var/www/html/wp-content/themes/generatepress-child/includes/dl/kantine.php
```

#### **3. Berechtigungen setzen:**
```bash
chmod 644 /var/www/html/wp-content/themes/generatepress-child/includes/dl/kantine.php
```

### **B) Konfiguration:**

#### **1. Server-IP eintragen:**

Öffnen Sie die neue `kantine.php` und ändern Sie:

**Für lokale Tests:**
```php
$scandy_api_url = 'http://localhost:5000/api/canteen/current_week';
```

**Für Produktion:**
```php
$scandy_api_url = 'http://195.37.23.143:5000/api/canteen/current_week';
```

**Für HTTPS:**
```php
$scandy_api_url = 'https://scandy.your-domain.com/api/canteen/current_week';
```

#### **2. Optional: API-Key setzen:**

Falls Sie einen API-Key verwenden möchten:

**In Scandy konfigurieren:**
```bash
# In app/config/canteen_api.py
CANTEEN_API_KEY = "your-secret-api-key"
```

**In WordPress eintragen:**
```php
$api_key = 'your-secret-api-key';
```

### **C) WordPress-Einbindung:**

#### **1. In WordPress-Seite einbinden:**

```php
<?php
// In Ihrer WordPress-Seite oder Template
include_once get_template_directory() . '/includes/dl/kantine.php';
?>
```

#### **2. Mit Shortcode (optional):**

Erstellen Sie einen Shortcode in `functions.php`:

```php
function canteen_shortcode() {
    ob_start();
    include_once get_template_directory() . '/includes/dl/kantine.php';
    return ob_get_clean();
}
add_shortcode('kantinenplan', 'canteen_shortcode');
```

Verwendung: `[kantinenplan]`

---

## **🧪 4. Testing & Validierung**

### **A) Scandy-Tests:**

#### **1. API-Endpunkte testen:**
```bash
# Aktuelle Woche
curl -s http://localhost:5000/api/canteen/current_week | jq '.'

# Status
curl -s http://localhost:5000/api/canteen/status | jq '.'

# 2 Wochen
curl -s http://localhost:5000/api/canteen/two_weeks | jq '.'
```

#### **2. Datenbank prüfen:**
```bash
# MongoDB-Verbindung testen
docker exec -it scandy-mongodb-scandy mongosh
use scandy
db.canteen_meals.find().pretty()
```

### **B) WordPress-Tests:**

#### **1. Cache-Datei prüfen:**
```bash
cat /var/www/html/wp-content/themes/generatepress-child/includes/dl/canteen_cache.json
```

#### **2. Logs prüfen:**
```bash
tail -f /var/log/apache2/error.log
```

#### **3. Browser-Test:**
1. **WordPress-Seite öffnen**
2. **Kantinenplan-Tabelle prüfen**
3. **Heutiger Tag sollte hervorgehoben sein**
4. **Cache-Info sollte angezeigt werden**

---

## **🔧 5. Konfiguration & Anpassungen**

### **A) Cache-Einstellungen:**

#### **Cache-Dauer ändern:**
```php
// In kantine.php
$cache_duration = 600; // 10 Minuten statt 5
```

#### **Cache deaktivieren (nur für Tests):**
```php
$cache_duration = 0; // Kein Cache
```

### **B) Styling anpassen:**

#### **Bootstrap-Klassen ändern:**
```php
// In der display_canteen_table Funktion
echo '<table class="table table-striped table-hover">';
echo '<tr class="table-primary">'; // Heutiger Tag
```

#### **Eigene CSS-Klassen:**
```css
/* In Ihrem WordPress-Theme */
.canteen-table {
    width: 100%;
    border-collapse: collapse;
}

.canteen-today {
    background-color: #e3f2fd !important;
    font-weight: bold;
}
```

### **C) Fehlerbehandlung:**

#### **API-Fehler abfangen:**
```php
if (!$api_data) {
    echo '<div class="alert alert-warning">';
    echo '<strong>Hinweis:</strong> Kantinenplan-Daten konnten nicht geladen werden.';
    echo '<br><small>Bitte prüfen Sie die API-Verbindung oder versuchen Sie es später erneut.</small>';
    echo '</div>';
    return;
}
```

---

## **📊 6. Monitoring & Wartung**

### **A) Logs überwachen:**

#### **Scandy-Logs:**
```bash
docker logs scandy-app-scandy --tail 50
```

#### **WordPress-Logs:**
```bash
tail -f /var/log/apache2/error.log
tail -f /var/log/nginx/error.log
```

### **B) Cache-Management:**

#### **Cache manuell löschen:**
```bash
rm /var/www/html/wp-content/themes/generatepress-child/includes/dl/canteen_cache.json
```

#### **Cache-Status prüfen:**
```bash
ls -la /var/www/html/wp-content/themes/generatepress-child/includes/dl/canteen_cache.json
```

### **C) Performance-Monitoring:**

#### **API-Response-Zeit:**
```bash
time curl -s http://localhost:5000/api/canteen/current_week > /dev/null
```

#### **Cache-Hit-Rate:**
```bash
# Prüfen Sie die Cache-Datei-Größe und -Alter
stat /var/www/html/wp-content/themes/generatepress-child/includes/dl/canteen_cache.json
```

---

## **🚨 7. Troubleshooting**

### **A) Häufige Probleme:**

#### **1. "Netzwerkfehler beim Speichern":**
- **Ursache**: Benutzer nicht eingeloggt
- **Lösung**: `http://localhost:5000/auth/login`

#### **2. "404 - Seite nicht gefunden":**
- **Ursache**: Route nicht registriert
- **Lösung**: Container neu starten: `docker restart scandy-app-scandy`

#### **3. "API-Daten konnten nicht geladen werden":**
- **Ursache**: Falsche Server-IP
- **Lösung**: `$scandy_api_url` korrigieren

#### **4. "Keine Daten für heute gefunden":**
- **Ursache**: Keine Daten in der aktuellen Woche
- **Lösung**: Daten in Scandy eingeben

### **B) Debug-Routen:**

#### **Scandy-Debug:**
```bash
curl -s http://localhost:5000/canteen/debug
```

#### **WordPress-Debug:**
```php
// Temporär in kantine.php hinzufügen
error_reporting(E_ALL);
ini_set('display_errors', 1);
```

### **C) Rollback-Verfahren:**

#### **Zurück zur alten Version:**
```bash
cp /var/www/html/wp-content/themes/generatepress-child/includes/dl/kantine.php.backup \
   /var/www/html/wp-content/themes/generatepress-child/includes/dl/kantine.php
```

---

## **📈 8. Erweiterungen & Optimierungen**

### **A) Zusätzliche Features:**

#### **1. E-Mail-Benachrichtigungen:**
```php
// Bei API-Fehlern E-Mail senden
if (!$api_data) {
    wp_mail('admin@example.com', 'Kantinenplan API-Fehler', 'API konnte nicht erreicht werden');
}
```

#### **2. Slack-Integration:**
```php
// Slack-Webhook bei Fehlern
$slack_webhook = 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL';
$message = json_encode(['text' => 'Kantinenplan API-Fehler']);
file_get_contents($slack_webhook, false, stream_context_create([
    'http' => ['method' => 'POST', 'content' => $message]
]));
```

#### **3. Erweiterte Caching-Strategie:**
```php
// Redis-Cache statt Datei-Cache
$redis = new Redis();
$redis->connect('127.0.0.1', 6379);
$cache_data = $redis->get('canteen_data');
```

### **B) Performance-Optimierungen:**

#### **1. CDN-Integration:**
```php
// Cache-Headers setzen
header('Cache-Control: public, max-age=300');
header('ETag: "' . md5($cache_data) . '"');
```

#### **2. Gzip-Kompression:**
```php
// API-Response komprimieren
if (extension_loaded('zlib')) {
    ob_start('ob_gzhandler');
}
```

---

## **📋 9. Checkliste für Produktions-Deployment**

### **✅ Pre-Deployment:**

- [ ] Scandy-Container läuft stabil
- [ ] API-Endpunkte funktionieren
- [ ] Test-Daten in Scandy eingegeben
- [ ] Backup der alten `kantine.php` erstellt
- [ ] Server-IP korrekt konfiguriert
- [ ] Berechtigungen gesetzt

### **✅ Deployment:**

- [ ] Neue `kantine.php` installiert
- [ ] Konfiguration getestet
- [ ] WordPress-Seite lädt korrekt
- [ ] Kantinenplan-Tabelle angezeigt
- [ ] Cache funktioniert
- [ ] Fehlerbehandlung aktiv

### **✅ Post-Deployment:**

- [ ] Monitoring eingerichtet
- [ ] Logs überwacht
- [ ] Performance getestet
- [ ] Backup-Strategie dokumentiert
- [ ] Rollback-Verfahren getestet

---

## **📞 10. Support & Kontakt**

### **Bei Problemen:**

1. **Logs prüfen**: Docker- und Apache-Logs
2. **API testen**: `curl`-Befehle ausführen
3. **Cache löschen**: Cache-Datei entfernen
4. **Container neu starten**: `docker restart scandy-app-scandy`

### **Dokumentation:**

- **Scandy-Docs**: `http://localhost:5000/about`
- **API-Docs**: `http://localhost:5000/api/canteen/status`
- **Admin-Panel**: `http://localhost:5000/admin`

---

## **🎯 Fazit**

Die neue **API-basierte Kantinenplan-Lösung** bietet:

✅ **Bessere Sicherheit** (keine Credentials in Dateien)  
✅ **Höhere Skalierbarkeit** (mehrere WordPress-Server)  
✅ **Automatisches Caching** (5-Minuten Cache)  
✅ **Einfachere Wartung** (zentrale Datenverwaltung)  
✅ **Bessere Performance** (weniger API-Aufrufe)  
✅ **Vollständige Kompatibilität** (gleiche Ausgabe wie alte Lösung)  

**Die Migration ist erfolgreich abgeschlossen!** 🎉 