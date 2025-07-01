# Scandy - Vollständige Berechtigungsübersicht

## 👥 Benutzerrollen & Berechtigungen

### 🔧 Admin
- **Vollzugriff** auf alle Funktionen
- Kann alle Tickets sehen und bearbeiten
- Kann alle Benutzer verwalten
- Kann System-Einstellungen ändern
- Kann Backups erstellen/wiederherstellen

### 👷 Mitarbeiter
- Kann Werkzeuge und Verbrauchsgüter verwalten
- Kann Mitarbeiter verwalten
- Kann manuelle Ausleihe durchführen
- Kann alle Tickets sehen und bearbeiten
- Kann Wochenberichte erstellen (wenn aktiviert)
- **Kein Zugriff** auf Admin-Funktionen (System, Benutzerverwaltung, etc.)

### 👤 Anwender
- Kann Werkzeuge und Verbrauchsgüter ansehen
- Kann Werkzeuge und Verbrauchsgüter hinzufügen/bearbeiten
- Kann manuelle Ausleihe durchführen
- Kann **eigene Tickets** erstellen, ansehen und bearbeiten
- Kann **zugewiesene Tickets** ansehen und bearbeiten
- Kann **offene Tickets** (noch niemandem zugewiesen) ansehen und bearbeiten
- Kann Wochenberichte erstellen (wenn aktiviert)
- **Kein Zugriff** auf Mitarbeiter-Verwaltung oder Admin-Funktionen

## 📋 Legende
- `@login_required` = Alle eingeloggten Benutzer (admin, mitarbeiter, anwender)
- `@mitarbeiter_required` = Nur admin und mitarbeiter
- `@admin_required` = Nur admin
- Kein Decorator = Öffentlich (auch ohne Login)

---

## 🔐 Authentifizierung (`/auth`)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/auth/login` | GET, POST | Öffentlich | Login-Formular |
| `/auth/setup` | GET, POST | Öffentlich | System-Setup |
| `/auth/logout` | GET | `@login_required` | Logout |
| `/auth/profile` | GET, POST | `@login_required` | Benutzerprofil |

## 🏠 Hauptseiten
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/` | GET | `@login_required` | Dashboard/Startseite |
| `/about` | GET | Öffentlich | Über-Seite |

## 🛠️ Werkzeuge (`/tools`)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/tools/` | GET | `@login_required` | Werkzeug-Übersicht |
| `/tools/add` | GET, POST | `@login_required` | Werkzeug hinzufügen |
| `/tools/<barcode>` | GET | `@login_required` | Werkzeug-Details |
| `/tools/<barcode>/edit` | GET, POST | `@login_required` | Werkzeug bearbeiten |
| `/tools/<barcode>/status` | POST | `@login_required` | Status ändern |

## 📦 Verbrauchsgüter (`/consumables`)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/consumables/` | GET | `@login_required` | Verbrauchsgüter-Übersicht |
| `/consumables/add` | GET, POST | `@login_required` | Verbrauchsgut hinzufügen |
| `/consumables/<barcode>` | GET, POST | `@login_required` | Verbrauchsgut-Details/Bearbeiten |
| `/consumables/<barcode>/adjust-stock` | POST | `@login_required` | Bestand anpassen |
| `/consumables/<barcode>/delete` | DELETE | `@mitarbeiter_required` | Verbrauchsgut löschen |
| `/consumables/<barcode>/forecast` | GET | `@login_required` | Bestandsprognose |

## 👥 Mitarbeiter (`/workers`)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/workers/` | GET | `@mitarbeiter_required` | Mitarbeiter-Übersicht |
| `/workers/add` | GET, POST | `@mitarbeiter_required` | Mitarbeiter hinzufügen |
| `/workers/<barcode>` | GET, POST | `@mitarbeiter_required` | Mitarbeiter-Details |
| `/workers/<barcode>/edit` | GET, POST | `@mitarbeiter_required` | Mitarbeiter bearbeiten |
| `/workers/<barcode>/delete` | DELETE | `@mitarbeiter_required` | Mitarbeiter löschen |
| `/workers/search` | GET | `@mitarbeiter_required` | Mitarbeiter-Suche |
| `/workers/timesheets` | GET | `@login_required` | Wochenberichte-Übersicht |
| `/workers/timesheet/new` | GET, POST | `@login_required` | Neuer Wochenbericht |
| `/workers/timesheet/<id>/edit` | GET, POST | `@login_required` | Wochenbericht bearbeiten |
| `/workers/timesheet/<id>/download` | GET | `@login_required` | Wochenbericht downloaden |

## 📊 Dashboard
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/dashboard/` | GET | `@login_required` | Dashboard |

## 📈 Historie
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/history` | GET | `@login_required` | Ausleih-Historie |

## 🔄 Quick Scan
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/quick_scan/` | GET | `@login_required` | Quick-Scan-Interface |
| `/quick_scan/process` | POST | `@login_required` | Quick-Scan verarbeiten |

## 🎫 Tickets (`/tickets`)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/tickets/` | GET | `@login_required` | Ticket-Übersicht (nur eigene) |
| `/tickets/create` | GET, POST | `@login_required` | Ticket erstellen |
| `/tickets/view/<id>` | GET | `@login_required` | Ticket anzeigen (eigene, zugewiesene oder offene) |
| `/tickets/<id>/message` | POST | `@login_required` | Nachricht hinzufügen |
| `/tickets/<id>` | GET | `@login_required` | Ticket-Details (eigene, zugewiesene oder offene) |
| `/tickets/<id>/delete` | POST | `@login_required` | Ticket löschen |
| `/tickets/<id>/auftrag-details-modal` | GET | `@login_required` | Auftrag-Details Modal |
| `/tickets/<id>/update-status` | POST | `@login_required` | Status aktualisieren |
| `/tickets/<id>/update-assignment` | POST | `@login_required` | Zuweisung aktualisieren |
| `/tickets/<id>/update-details` | POST | `@login_required` | Details aktualisieren |
| `/tickets/<id>/export` | GET | `@login_required` | Ticket exportieren |
| `/tickets/<id>/note` | POST | `@login_required` | Notiz hinzufügen |
| `/tickets/auftrag-neu` | GET, POST | `@login_required` | Neuer Auftrag |
| `/tickets/<id>/auftrag-details` | GET | `@login_required` | Auftrag-Details |

## 🔌 API (`/api`)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/api/workers` | GET | `@mitarbeiter_required` | Mitarbeiter-Liste |
| `/api/inventory/tools/<barcode>` | GET | `@mitarbeiter_required` | Werkzeug-Details |
| `/api/inventory/workers/<barcode>` | GET | `@mitarbeiter_required` | Mitarbeiter-Details |
| `/api/settings/colors` | POST | `@mitarbeiter_required` | Farbeinstellungen |
| `/api/lending/return` | POST | `@mitarbeiter_required` | Rückgabe verarbeiten |
| `/api/inventory/consumables/<barcode>` | GET | `@mitarbeiter_required` | Verbrauchsgut-Details |
| `/api/update_barcode` | POST | `@mitarbeiter_required` | Barcode aktualisieren |
| `/api/consumables/<barcode>/forecast` | GET | `@login_required` | Bestandsprognose |
| `/api/notices` | GET, POST | `@login_required` | Notizen verwalten |
| `/api/notices/<id>` | GET, PUT, DELETE | `@login_required` | Notiz verwalten |
| `/api/quickscan/process_lending` | POST | `@login_required` | Quick-Scan Ausleihe |

## ⚙️ Admin (`/admin`)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/admin/` | GET | `@mitarbeiter_required` | Admin-Startseite |
| `/admin/dashboard` | GET | `@mitarbeiter_required` | Admin-Dashboard |
| `/admin/manual-lending` | GET, POST | `@login_required` | Manuelle Ausleihe |
| `/admin/trash` | GET | `@mitarbeiter_required` | Papierkorb |
| `/admin/trash/restore/<type>/<barcode>` | POST | `@mitarbeiter_required` | Wiederherstellen |

### 🗑️ Lösch-Routen (Admin)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/admin/tools/delete` | DELETE | `@mitarbeiter_required` | Werkzeug löschen |
| `/admin/tools/<barcode>/delete` | DELETE | `@mitarbeiter_required` | Werkzeug löschen |
| `/admin/tools/<barcode>/delete-permanent` | DELETE | `@mitarbeiter_required` | Werkzeug permanent löschen |
| `/admin/consumables/delete` | DELETE | `@mitarbeiter_required` | Verbrauchsgut löschen |
| `/admin/consumables/<barcode>/delete-permanent` | DELETE | `@mitarbeiter_required` | Verbrauchsgut permanent löschen |
| `/admin/workers/delete` | DELETE | `@mitarbeiter_required` | Mitarbeiter löschen |
| `/admin/workers/<barcode>/delete` | DELETE | `@mitarbeiter_required` | Mitarbeiter löschen |
| `/admin/workers/<barcode>/delete-permanent` | DELETE | `@mitarbeiter_required` | Mitarbeiter permanent löschen |

### 🎫 Ticket-Verwaltung (Admin)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/admin/tickets/<id>` | GET | `@login_required` + `@mitarbeiter_required` | Ticket-Details |
| `/admin/tickets/<id>/message` | POST | `@login_required` + `@admin_required` | Nachricht hinzufügen |
| `/admin/tickets/<id>/note` | POST | `@login_required` + `@admin_required` | Notiz hinzufügen |
| `/admin/tickets/<id>/update` | POST | `@login_required` + `@admin_required` | Ticket aktualisieren |
| `/admin/tickets/<id>/export` | GET | `@login_required` + `@admin_required` | Ticket exportieren |
| `/admin/tickets/<id>/update-details` | POST | `@login_required` + `@admin_required` | Details aktualisieren |
| `/admin/tickets` | GET | `@login_required` + `@mitarbeiter_required` | Ticket-Übersicht |
| `/admin/tickets/<id>/update-assignment` | POST | `@login_required` + `@admin_required` | Zuweisung aktualisieren |
| `/admin/tickets/<id>/update-status` | POST | `@login_required` + `@admin_required` | Status aktualisieren |
| `/admin/tickets/<id>/delete` | POST | `@login_required` + `@admin_required` | Ticket löschen |
| `/admin/tickets/<id>/delete-permanent` | DELETE | `@login_required` + `@admin_required` | Ticket permanent löschen |

### 👤 Benutzer-Verwaltung (Admin)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/admin/manage_users` | GET | `@mitarbeiter_required` | Benutzer verwalten |
| `/admin/add_user` | GET, POST | `@mitarbeiter_required` | Benutzer hinzufügen |
| `/admin/edit_user/<id>` | GET, POST | `@mitarbeiter_required` | Benutzer bearbeiten |
| `/admin/delete_user/<id>` | POST | `@mitarbeiter_required` | Benutzer löschen |
| `/admin/user_form` | GET | `@mitarbeiter_required` | Benutzer-Formular |
| `/admin/reset_password` | GET, POST | Öffentlich | Passwort zurücksetzen |
| `/admin/debug/password/<username>` | GET | `@admin_required` | Passwort debuggen |

### 📢 Notizen & System (Admin)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/admin/notices` | GET | `@admin_required` | Notizen verwalten |
| `/admin/create_notice` | GET, POST | `@admin_required` | Notiz erstellen |
| `/admin/edit_notice/<id>` | GET, POST | `@admin_required` | Notiz bearbeiten |
| `/admin/delete_notice/<id>` | POST | `@admin_required` | Notiz löschen |
| `/admin/upload_logo` | POST | `@admin_required` | Logo hochladen |
| `/admin/delete-logo/<filename>` | POST | `@admin_required` | Logo löschen |
| `/admin/add_ticket_category` | POST | `@admin_required` | Ticket-Kategorie hinzufügen |
| `/admin/delete_ticket_category/<category>` | POST | `@admin_required` | Ticket-Kategorie löschen |
| `/admin/system` | GET, POST | `@admin_required` | System-Einstellungen |

### 🏢 Verwaltung (Admin)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/admin/departments` | GET | `@mitarbeiter_required` | Abteilungen verwalten |
| `/admin/departments/add` | POST | `@mitarbeiter_required` | Abteilung hinzufügen |
| `/admin/departments/delete/<name>` | POST | `@mitarbeiter_required` | Abteilung löschen |
| `/admin/categories` | GET | `@mitarbeiter_required` | Kategorien verwalten |
| `/admin/categories/add` | POST | `@mitarbeiter_required` | Kategorie hinzufügen |
| `/admin/categories/delete/<name>` | POST | `@mitarbeiter_required` | Kategorie löschen |
| `/admin/locations` | GET | `@mitarbeiter_required` | Standorte verwalten |
| `/admin/locations/add` | POST | `@mitarbeiter_required` | Standort hinzufügen |
| `/admin/locations/delete/<name>` | POST | `@mitarbeiter_required` | Standort löschen |

### 💾 Backup & Updates (Admin)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/admin/backup/list` | GET | `@mitarbeiter_required` | Backup-Liste |
| `/admin/backup/create` | POST | `@admin_required` | Backup erstellen |
| `/admin/backup/upload` | POST | `@admin_required` | Backup hochladen |
| `/admin/backup/restore/<filename>` | POST | `@admin_required` | Backup wiederherstellen |
| `/admin/backup/download/<filename>` | GET | `@admin_required` | Backup downloaden |
| `/admin/backup/delete/<filename>` | DELETE | `@admin_required` | Backup löschen |
| `/admin/backup/auto/status` | GET | `@login_required` + `@admin_required` | Auto-Backup Status |
| `/admin/backup/auto/start` | POST | `@login_required` + `@admin_required` | Auto-Backup starten |
| `/admin/backup/auto/stop` | POST | `@login_required` + `@admin_required` | Auto-Backup stoppen |
| `/admin/backup/auto/logs` | GET | `@login_required` + `@admin_required` | Auto-Backup Logs |
| `/admin/auto-backup` | GET, POST | `@login_required` + `@admin_required` | Auto-Backup verwalten |
| `/admin/backup/weekly/test` | POST | `@login_required` + `@admin_required` | Wochen-Backup testen |
| `/admin/updates` | GET | `@admin_required` | Updates verwalten |
| `/admin/updates/check` | POST | `@admin_required` | Updates prüfen |
| `/admin/updates/apply` | POST | `@admin_required` | Updates anwenden |
| `/admin/updates/status` | GET | `@admin_required` | Update-Status |
| `/admin/updates/history` | GET | `@admin_required` | Update-Historie |



### 📧 E-Mail (Admin)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/admin/email_settings` | GET, POST | `@admin_required` | E-Mail-Einstellungen |
| `/admin/admin/email/diagnose` | POST | `@login_required` + `@admin_required` | E-Mail diagnostizieren |
| `/admin/admin/email/test-simple` | POST | `@login_required` + `@admin_required` | E-Mail testen |

### 🔧 Debug & Import/Export (Admin)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/admin/debug/barcodes` | GET | `@mitarbeiter_required` | Barcodes debuggen |
| `/admin/debug/clean-barcodes` | POST | `@mitarbeiter_required` | Barcodes bereinigen |
| `/admin/debug` | GET | `@mitarbeiter_required` | Debug-Seite |
| `/admin/debug/test-barcodes` | GET | `@mitarbeiter_required` | Barcodes testen |
| `/admin/available-logos` | GET | `@mitarbeiter_required` | Verfügbare Logos |
| `/admin/export_all_data` | GET | `@admin_required` | Alle Daten exportieren |
| `/admin/import_all_data` | POST | `@admin_required` | Alle Daten importieren |

## ⚙️ Setup (`/setup`)
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/setup/admin` | GET, POST | Öffentlich | Admin-Setup |
| `/setup/settings` | GET, POST | Öffentlich | Einstellungen-Setup |
| `/setup/optional` | GET, POST | Öffentlich | Optionale Einstellungen |

## 🔄 Lending API
| Route | Methode | Berechtigung | Beschreibung |
|-------|---------|--------------|--------------|
| `/api/lending/test` | GET | `@mitarbeiter_required` | Lending-Test |
| `/api/lending/process` | POST | `@mitarbeiter_required` | Lending verarbeiten |

---

## 📊 Zusammenfassung der Berechtigungsstufen

### 🔓 Öffentlich (kein Login erforderlich)
- Login, Setup, About-Seite
- Passwort-Reset

### 🔐 Alle eingeloggten Benutzer (`@login_required`)
- Werkzeuge: Anzeigen, Hinzufügen, Bearbeiten, Status ändern
- Verbrauchsgüter: Anzeigen, Hinzufügen, Bearbeiten, Bestand anpassen
- Wochenberichte: Anzeigen, Erstellen, Bearbeiten, Downloaden
- Tickets: Anzeigen, Erstellen, Bearbeiten, Nachrichten
- Dashboard, Historie, Quick-Scan
- Benutzerprofil

### 👥 Mitarbeiter & Admins (`@mitarbeiter_required`)
- Mitarbeiter verwalten
- Manuelle Ausleihe
- Papierkorb und Wiederherstellung
- Löschen von Werkzeugen, Verbrauchsgütern, Mitarbeitern
- Abteilungen, Kategorien, Standorte verwalten
- Backup-Liste anzeigen
- Debug-Funktionen

### 👑 Nur Admins (`@admin_required`)
- Benutzerverwaltung
- System-Einstellungen
- Notizen verwalten
- Logo-Upload
- Backup erstellen/verwalten
- Updates verwalten
- E-Mail-Einstellungen
- Ticket-Kategorien verwalten
- Daten importieren/exportieren
- Auto-Backup verwalten 