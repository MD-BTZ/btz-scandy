# Kantinenplan API-Dokumentation

## Übersicht

Die neue API-basierte Lösung ersetzt die CSV-Datei-Übertragung durch eine zentrale REST-API. Dies bietet mehrere Vorteile:

### ✅ Vorteile der API-Lösung

1. **Zentrale Datenverwaltung**: Alle Daten bleiben in der Scandy-Datenbank
2. **Skalierbarkeit**: Mehrere WordPress-Server können die gleiche API nutzen
3. **Sicherheit**: Keine SFTP-Credentials mehr nötig
4. **Performance**: Caching auf WordPress-Seite reduziert API-Aufrufe
5. **Wartbarkeit**: Einfache Updates ohne Datei-Übertragung
6. **Monitoring**: API-Zugriffe können protokolliert werden

## API-Endpunkte

### 1. Aktuelle Woche abrufen
```
GET /api/canteen/current_week
```

**Parameter:**
- `api_key` (optional): API-Schlüssel für Authentifizierung

**Response:**
```json
{
  "success": true,
  "week": [
    {
      "date": "Montag, 15.01.2024",
      "meat_dish": "Schnitzel mit Pommes",
      "vegan_dish": "Veganes Curry mit Reis",
      "weekday": "Montag"
    },
    {
      "date": "Dienstag, 16.01.2024",
      "meat_dish": "Hähnchenbrust mit Gemüse",
      "vegan_dish": "Vegetarische Lasagne",
      "weekday": "Dienstag"
    }
  ],
  "generated_at": "2024-01-15T10:30:00"
}
```

### 2. Status abrufen
```
GET /api/canteen/status
```

**Response:**
```json
{
  "success": true,
  "feature_enabled": true,
  "sftp_configured": false,
  "last_update": "2024-01-15T10:30:00",
  "server_info": {
    "host": null,
    "path": null
  }
}
```

## WordPress-Integration

### 1. Neue PHP-Datei erstellen

Erstellen Sie `kantine_api.php` auf beiden WordPress-Servern:

```php
<?php
// Konfiguration
$scandy_api_url = 'https://your-scandy-server.com/api/canteen/current_week';
$api_key = 'your-api-key-here'; // Optional
$cache_duration = 300; // 5 Minuten Cache

// Cache-Datei
$cache_file = __DIR__ . '/canteen_cache.json';

// ... Rest der Datei siehe kantine_api.php
?>
```

### 2. Konfiguration anpassen

**Für Server 1:**
```php
$scandy_api_url = 'https://scandy-server1.com/api/canteen/current_week';
```

**Für Server 2:**
```php
$scandy_api_url = 'https://scandy-server2.com/api/canteen/current_week';
```

### 3. WordPress einbinden

Ersetzen Sie die alte `kantine.php` durch die neue `kantine_api.php`:

```php
// In WordPress-Template
include_once get_template_directory() . '/includes/kantine_api.php';
```

## Sicherheit

### API-Key (Optional)
```bash
# In .env Datei
CANTEEN_API_KEY=your-secure-api-key-here
```

### CORS-Konfiguration
```python
# Erlaubte Domains für API-Zugriff
CANTEEN_API_ALLOWED_ORIGINS=wordpress1.com,wordpress2.com
```

## Caching-Strategie

### WordPress-Cache
- **Primär-Cache**: 5 Minuten
- **Fallback-Cache**: 1 Stunde (bei API-Fehlern)
- **Cache-Datei**: `canteen_cache.json`

### Cache-Invalidierung
- Automatisch nach 5 Minuten
- Bei API-Fehlern wird Fallback-Cache verwendet
- Cache wird bei jedem API-Aufruf aktualisiert

## Migration von CSV zu API

### Schritt 1: API aktivieren
1. Scandy-App starten
2. Kantinenplan-Feature aktivieren
3. API-Endpunkte testen

### Schritt 2: WordPress anpassen
1. `kantine_api.php` auf beide Server kopieren
2. API-URLs konfigurieren
3. Alte `kantine.php` ersetzen

### Schritt 3: Testen
1. Kantinenplan in Scandy eingeben
2. WordPress-Seiten prüfen
3. Cache-Funktionalität testen

## Fehlerbehandlung

### API-Fehler
- **HTTP 401**: Ungültiger API-Key
- **HTTP 500**: Server-Fehler
- **Timeout**: Netzwerk-Probleme

### Fallback-Mechanismus
1. Versuche API-Aufruf
2. Bei Fehler: Verwende Cache
3. Bei Cache-Fehler: Zeige Warnung

## Monitoring

### Logs
```python
# API-Zugriffe werden protokolliert
logger.info(f"API-Anfrage von {request.remote_addr}")
```

### Status-Seite
```
GET /api/canteen/status
```

## Performance-Optimierung

### Caching
- WordPress-Cache reduziert API-Aufrufe
- Scandy-Cache für Datenbank-Abfragen
- CDN für statische Inhalte

### Rate Limiting
```python
# Maximal 100 Anfragen pro Stunde
CANTEEN_API_RATE_LIMIT = '100/hour'
```

## Backup-Strategie

### Daten-Sicherung
- MongoDB-Backup für Kantinenplan-Daten
- API-Response-Cache als Backup
- WordPress-Cache als lokales Backup

### Disaster Recovery
1. Scandy-Server fällt aus → WordPress-Cache
2. WordPress-Server fällt aus → Anderer Server
3. Beide Server fallen aus → Manuelle CSV-Übertragung

## Vergleich: CSV vs API

| Aspekt | CSV-Datei | API |
|--------|-----------|-----|
| **Skalierbarkeit** | ❌ Begrenzt | ✅ Unbegrenzt |
| **Sicherheit** | ⚠️ SFTP-Credentials | ✅ API-Key |
| **Performance** | ⚠️ Datei-Übertragung | ✅ HTTP-Cache |
| **Wartung** | ❌ Manuell | ✅ Automatisch |
| **Monitoring** | ❌ Kein Monitoring | ✅ Vollständig |
| **Backup** | ⚠️ Datei-Backup | ✅ Datenbank-Backup |

## Fazit

Die API-Lösung ist deutlich überlegen:
- ✅ Einfacher zu warten
- ✅ Sicherer
- ✅ Skalierbarer
- ✅ Besser zu überwachen
- ✅ Zukunftssicherer

**Empfehlung: Sofortige Migration zur API-Lösung!** 