# Gitignore Erklärung

## Generierte Dateien werden ignoriert

Das `.gitignore` ist so konfiguriert, dass **generierte Dateien** nicht auf GitHub hochgeladen werden, während **Vorlagen-Dateien** im Repository bleiben.

### ✅ **Im Repository (werden hochgeladen):**
- `app/static/word/btzauftrag.docx` - Word-Vorlage für Aufträge
- `app/static/word/woplan.docx` - Word-Vorlage für Arbeitspläne
- Alle anderen Vorlagen-Dateien

### ❌ **Nicht im Repository (werden ignoriert):**
- `app/uploads/**/*.docx` - Generierte Word-Dokumente
- `app/uploads/**/*.pdf` - Generierte PDF-Dateien
- `app/uploads/**/*.xlsx` - Generierte Excel-Dateien
- `app/static/uploads/**/*.docx` - Generierte Word-Dokumente
- `*ticket_*_export.docx` - Exportierte Ticket-Dokumente
- `*woplan_*.docx` - Generierte Arbeitspläne
- `*auftrag_*.docx` - Generierte Aufträge
- `*tmp*.docx` - Temporäre Word-Dateien

### **Warum diese Konfiguration?**

1. **Vorlagen bleiben verfügbar**: Die ursprünglichen Word-Vorlagen sind für alle Entwickler verfügbar
2. **Generierte Dateien sind lokal**: Jede Installation generiert ihre eigenen Dokumente
3. **Repository bleibt sauber**: Keine großen, sich ändernden Dateien im Git
4. **Sicherheit**: Keine sensiblen Daten in generierten Dokumenten auf GitHub

### **Was passiert bei einem neuen Clone?**

1. Die Vorlagen sind verfügbar
2. Das `uploads/` Verzeichnis wird automatisch erstellt
3. Generierte Dokumente werden lokal erstellt
4. Keine Konflikte zwischen verschiedenen Installationen

### **Falls du eine generierte Datei doch teilen möchtest:**

```bash
# Temporär das .gitignore umgehen
git add -f app/uploads/spezielle_datei.docx
git commit -m "Füge spezielle Datei hinzu"
```

**Hinweis**: Verwende dies nur für Beispieldateien oder Dokumentation, nicht für normale generierte Dokumente. 