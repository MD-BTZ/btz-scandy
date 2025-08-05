# Kantinenplan 2-Wochen-System Dokumentation

## Übersicht

Das neue System ermöglicht die Eingabe von 2 Wochen Kantinenplan-Daten, zeigt aber nur die aktuelle Woche an. Dies bietet mehrere Vorteile:

### ✅ Vorteile des 2-Wochen-Systems

1. **Planungssicherheit**: 2 Wochen können im Voraus geplant werden
2. **Benutzerfreundlichkeit**: Nur aktuelle Woche wird angezeigt (weniger Verwirrung)
3. **Flexibilität**: Einfache Anpassung der Anzeige-Logik
4. **Datenintegrität**: Alle Daten bleiben in der Datenbank gespeichert

## System-Architektur

### 📊 Datenfluss

```
Scandy-Eingabe (2 Wochen) → MongoDB (2 Wochen) → API (2 Wochen) → WordPress (1 Woche)
```

### 🔧 API-Endpunkte

#### 1. Aktuelle Woche (Anzeige)
```bash
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
      "vegan_dish": "Veganes Curry",
      "weekday": "Montag"
    }
    // ... 5 Tage
  ]
}
```

#### 2. Zwei Wochen (Eingabe)
```bash
GET /api/canteen/two_weeks
```
**Response:**
```json
{
  "success": true,
  "two_weeks": [
    {
      "date": "W1 - Montag, 04.08.2025",
      "meat_dish": "Schnitzel mit Pommes",
      "vegan_dish": "Veganes Curry",
      "weekday": "Montag",
      "week": 1
    }
    // ... 10 Tage
  ]
}
```

## Benutzeroberfläche

### 📝 Scandy-Eingabemaske

- **2 Wochen Eingabe**: 10 Zeilen (5 Tage × 2 Wochen)
- **Wochen-Badges**: W1 und W2 zur besseren Übersicht
- **Visuelle Trennung**: Border zwischen den Wochen
- **Datum-Automatik**: Automatische Datumsberechnung

### 🖥️ WordPress-Anzeige

- **Nur aktuelle Woche**: 5 Tage werden angezeigt
- **Automatische Erkennung**: Heutiger Tag wird hervorgehoben
- **Cache-System**: 5 Minuten Cache für Performance

## Technische Implementierung

### 🗄️ Datenbank-Struktur

```javascript
// MongoDB Collection: canteen_meals
{
  "_id": ObjectId,
  "date": "2025-08-04",           // ISO-Datum
  "meat_dish": "Schnitzel mit Pommes",
  "vegan_dish": "Veganes Curry",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### 🔄 Service-Methoden

```python
# CanteenService
def get_current_week_meals() -> List[Dict]:     # 5 Tage
def get_two_weeks_meals() -> List[Dict]:        # 10 Tage
def save_meals(meals_data: List[Dict]):         # Speichert 10 Tage
```

### 🌐 API-Logik

```python
# current_week API
- Lädt nur aktuelle Woche (5 Tage)
- Formatiert für WordPress-Anzeige
- Cache-freundlich

# two_weeks API  
- Lädt 2 Wochen (10 Tage)
- Formatiert mit Wochen-Nummern
- Für Eingabe-Maske
```

## WordPress-Integration

### 📄 PHP-Dateien

#### 1. Standard-Anzeige (1 Woche)
```php
// kantine_api.php
$scandy_api_url = 'https://your-server.com/api/canteen/current_week';
```

#### 2. Erweiterte Anzeige (2 Wochen)
```php
// kantine_api_2weeks.php  
$scandy_api_url = 'https://your-server.com/api/canteen/two_weeks';
```

### 🎨 CSS-Styling

```css
.week-section {
    margin-bottom: 2rem;
    border: 1px solid #ddd;
    padding: 1rem;
}

.today {
    background-color: #e8f5e8;
    font-weight: bold;
}

.badge {
    background-color: #007bff;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
}
```

## Workflow

### 📋 Eingabe-Workflow

1. **Admin öffnet Scandy**: `/canteen`
2. **2 Wochen eingeben**: 10 Zeilen ausfüllen
3. **Speichern**: Daten werden in MongoDB gespeichert
4. **API verfügbar**: Sofort über API abrufbar

### 🖥️ Anzeige-Workflow

1. **WordPress lädt Seite**: `kantine_api.php`
2. **API-Aufruf**: `/api/canteen/current_week`
3. **Cache prüfen**: 5 Minuten Cache
4. **Anzeige**: Nur aktuelle Woche (5 Tage)

## Konfiguration

### ⚙️ Scandy-Konfiguration

```python
# app/services/canteen_service.py
CACHE_DURATION = 300  # 5 Minuten
WEEKS_TO_SHOW = 1     # Anzeige: 1 Woche
WEEKS_TO_INPUT = 2    # Eingabe: 2 Wochen
```

### 🌐 WordPress-Konfiguration

```php
// kantine_api.php
$cache_duration = 300;        // 5 Minuten Cache
$api_key = 'your-key';        // Optional
$show_current_week_only = true; // Nur aktuelle Woche
```

## Migration von 1-Wochen-System

### 🔄 Automatische Migration

- **Bestehende Daten**: Werden automatisch erweitert
- **Leere Tage**: Werden mit Platzhaltern gefüllt
- **Rückwärtskompatibel**: Alte APIs funktionieren weiter

### 📊 Daten-Migration

```python
# Automatische Erweiterung
for week in range(2):
    for day in range(5):
        date = monday + timedelta(days=(week * 7) + day)
        # Erstelle Eintrag falls nicht vorhanden
```

## Monitoring

### 📈 Metriken

- **API-Aufrufe**: Anzahl pro Stunde
- **Cache-Hit-Rate**: Performance-Monitoring
- **Fehler-Rate**: API-Fehler überwachen
- **Daten-Integrität**: Vollständigkeit der 2 Wochen

### 🔍 Logs

```python
# API-Zugriffe
logger.info(f"API-Anfrage: {endpoint} von {ip}")

# Daten-Änderungen  
logger.info(f"Kantinenplan aktualisiert: {count} Tage")

# Cache-Status
logger.info(f"Cache-Hit: {cache_age}s alt")
```

## Vorteile im Detail

### ✅ Für Admins

1. **Planungssicherheit**: 2 Wochen im Voraus planbar
2. **Weniger Arbeit**: Einmalige Eingabe für 2 Wochen
3. **Flexibilität**: Einfache Anpassungen möglich
4. **Übersicht**: Klare Trennung zwischen Wochen

### ✅ Für Benutzer

1. **Einfache Anzeige**: Nur aktuelle Woche sichtbar
2. **Keine Verwirrung**: Keine zukünftigen Daten
3. **Schnelle Ladezeiten**: Weniger Daten zu übertragen
4. **Mobile-freundlich**: Kompakte Darstellung

### ✅ Für System

1. **Performance**: Optimierte API-Aufrufe
2. **Skalierbarkeit**: Einfache Erweiterung auf 3+ Wochen
3. **Wartbarkeit**: Klare Trennung von Eingabe/Anzeige
4. **Sicherheit**: API-basierte Lösung

## Zukunftserweiterungen

### 🔮 Mögliche Erweiterungen

1. **3-4 Wochen Eingabe**: Für längere Planung
2. **Wochen-Wechsel**: Automatischer Übergang
3. **Vorlagen**: Häufige Gerichte als Vorlagen
4. **Statistiken**: Beliebtheit von Gerichten
5. **Benachrichtigungen**: Änderungen per E-Mail

### 🎯 Roadmap

- **Phase 1**: 2-Wochen-System (aktuell)
- **Phase 2**: Automatische Wochen-Wechsel
- **Phase 3**: Vorlagen-System
- **Phase 4**: Erweiterte Statistiken

## Fazit

Das 2-Wochen-System bietet die perfekte Balance zwischen:
- **Planungssicherheit** (2 Wochen Eingabe)
- **Benutzerfreundlichkeit** (1 Woche Anzeige)
- **Technischer Effizienz** (API-basiert)
- **Skalierbarkeit** (einfache Erweiterung)

**Das System ist bereit für den produktiven Einsatz!** 🚀 