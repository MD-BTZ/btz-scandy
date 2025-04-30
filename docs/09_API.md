# API-Dokumentation

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Authentifizierung](#authentifizierung)
3. [Endpunkte](#endpunkte)
4. [Fehlerbehandlung](#fehlerbehandlung)
5. [Beispiele](#beispiele)

## Übersicht

Die Scandy-API ermöglicht den programmatischen Zugriff auf die Anwendungsfunktionen. Die API folgt REST-Prinzipien und verwendet JSON für die Datenübertragung.

### Basis-URL
```
https://your-domain.com/api/v1
```

### Format
- **Request**: JSON
- **Response**: JSON
- **Content-Type**: application/json

### Versionierung
- Aktuelle Version: v1
- Versionspfad in URL
- Abwärtskompatibilität

## Authentifizierung

### API-Schlüssel
1. **Generierung**
   ```bash
   # Admin-Tool
   python generate_api_key.py
   ```

2. **Verwendung**
   ```http
   Authorization: Bearer YOUR_API_KEY
   ```

### OAuth 2.0
1. **Token-Request**
   ```http
   POST /oauth/token
   Content-Type: application/json
   
   {
     "grant_type": "password",
     "username": "user",
     "password": "pass"
   }
   ```

2. **Token-Response**
   ```json
   {
     "access_token": "token",
     "token_type": "bearer",
     "expires_in": 3600
   }
   ```

## Endpunkte

### Werkzeuge

#### Werkzeuge abrufen
```http
GET /tools
Authorization: Bearer YOUR_API_KEY

Response:
{
  "tools": [
    {
      "id": 1,
      "barcode": "123456",
      "name": "Hammer",
      "category": "Handwerkzeug",
      "status": "available"
    }
  ]
}
```

#### Werkzeug erstellen
```http
POST /tools
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "barcode": "123457",
  "name": "Schraubendreher",
  "category": "Handwerkzeug"
}

Response:
{
  "id": 2,
  "status": "created"
}
```

#### Werkzeug aktualisieren
```http
PUT /tools/{id}
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "status": "maintenance"
}

Response:
{
  "id": 1,
  "status": "updated"
}
```

### Material

#### Material abrufen
```http
GET /consumables
Authorization: Bearer YOUR_API_KEY

Response:
{
  "consumables": [
    {
      "id": 1,
      "name": "Schrauben",
      "quantity": 100,
      "min_quantity": 50
    }
  ]
}
```

#### Material entnehmen
```http
POST /consumables/{id}/withdraw
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "amount": 10,
  "reason": "Projekt XYZ"
}

Response:
{
  "id": 1,
  "new_quantity": 90
}
```

### Ausleihen

#### Ausleihe erstellen
```http
POST /lendings
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "tool_id": 1,
  "worker_id": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-01-07"
}

Response:
{
  "id": 1,
  "status": "created"
}
```

#### Ausleihe beenden
```http
PUT /lendings/{id}/return
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "condition": "good",
  "notes": "Alles in Ordnung"
}

Response:
{
  "id": 1,
  "status": "returned"
}
```

### Benutzer

#### Benutzer abrufen
```http
GET /users
Authorization: Bearer YOUR_API_KEY

Response:
{
  "users": [
    {
      "id": 1,
      "username": "john",
      "role": "user"
    }
  ]
}
```

#### Benutzer erstellen
```http
POST /users
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "username": "newuser",
  "password": "secret",
  "role": "user"
}

Response:
{
  "id": 2,
  "status": "created"
}
```

### Tickets

#### Tickets abrufen
```http
GET /tickets
Authorization: Bearer YOUR_API_KEY

Response:
{
  "tickets": [
    {
      "id": 1,
      "title": "Werkzeug defekt",
      "description": "Hammer ist kaputt",
      "status": "open",
      "priority": "high",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

#### Ticket erstellen
```http
POST /tickets
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "title": "Neues Problem",
  "description": "Beschreibung des Problems",
  "priority": "medium"
}

Response:
{
  "id": 2,
  "status": "created"
}
```

#### Ticket löschen
```http
DELETE /tickets/{id}
Authorization: Bearer YOUR_API_KEY

Response:
{
  "id": 1,
  "status": "deleted"
}
```

## Fehlerbehandlung

### Fehlercodes
- 200: Erfolg
- 400: Ungültige Anfrage
- 401: Nicht autorisiert
- 403: Verboten
- 404: Nicht gefunden
- 500: Server-Fehler

### Fehler-Response
```json
{
  "error": {
    "code": 400,
    "message": "Ungültige Eingabe",
    "details": {
      "field": "barcode",
      "issue": "bereits vergeben"
    }
  }
}
```

## Beispiele

### Python
```python
import requests

# Konfiguration
API_URL = "https://your-domain.com/api/v1"
API_KEY = "YOUR_API_KEY"

# Header
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Werkzeug abrufen
response = requests.get(f"{API_URL}/tools", headers=headers)
tools = response.json()

# Ausleihe erstellen
data = {
    "tool_id": 1,
    "worker_id": 1,
    "start_date": "2024-01-01",
    "end_date": "2024-01-07"
}
response = requests.post(f"{API_URL}/lendings", headers=headers, json=data)
```

### JavaScript
```javascript
// Konfiguration
const API_URL = "https://your-domain.com/api/v1";
const API_KEY = "YOUR_API_KEY";

// Header
const headers = {
    "Authorization": `Bearer ${API_KEY}`,
    "Content-Type": "application/json"
};

// Werkzeug abrufen
fetch(`${API_URL}/tools`, { headers })
    .then(response => response.json())
    .then(data => console.log(data));

// Material entnehmen
const data = {
    amount: 10,
    reason: "Projekt XYZ"
};
fetch(`${API_URL}/consumables/1/withdraw`, {
    method: "POST",
    headers,
    body: JSON.stringify(data)
})
.then(response => response.json())
.then(data => console.log(data));
```

### cURL
```bash
# Werkzeug abrufen
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-domain.com/api/v1/tools

# Ausleihe erstellen
curl -X POST \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"tool_id":1,"worker_id":1,"start_date":"2024-01-01","end_date":"2024-01-07"}' \
     https://your-domain.com/api/v1/lendings
``` 