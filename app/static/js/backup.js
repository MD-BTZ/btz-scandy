// Backup-Verwaltung
document.addEventListener('DOMContentLoaded', () => {
    // Neue vereinheitlichte Backup-Buttons initialisieren
        const createUnifiedBackupBtn = document.getElementById('createUnifiedBackupBtn');
    const createBackupNoMediaBtn = document.getElementById('createBackupNoMediaBtn');
    const downloadCurrentBtn = document.getElementById('downloadCurrentBtn');
    
    if (createUnifiedBackupBtn) {
        createUnifiedBackupBtn.onclick = createUnifiedBackup;
    }
    
    if (createBackupNoMediaBtn) {
        createBackupNoMediaBtn.onclick = createBackupNoMedia;
    }
    
    if (downloadCurrentBtn) {
        downloadCurrentBtn.onclick = downloadCurrentDatabase;
    }
    
    // Initialisiere Backup-System
    loadBackups();
    setupBackupHandlers();
    
    // Initialisiere Auto-Backup-System
    initAutoBackup();
    
    // Initialisiere Backup-Konvertierung
    initBackupConversion();
});

// Hilfsfunktionen
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showBackupToast(type, message) {
    // Robuste Toast-Funktion für Backup
    const showToast = () => {
        if (typeof window.showToast === 'function') {
            try {
                window.showToast(type, message);
                return;
            } catch (e) {
                console.warn('window.showToast failed, using fallback:', e);
            }
        }
        
        // Fallback: Eigene Toast-Implementierung
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'fixed bottom-4 right-4 z-[9999] flex flex-col gap-2';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} rounded-lg shadow-lg p-4 pr-12 relative min-w-[300px] max-w-[400px]`;
        
        // Farben basierend auf Typ
        const colors = {
            success: { bg: '#10b981', color: '#ffffff', icon: '✓' },
            error: { bg: '#ef4444', color: '#ffffff', icon: '✕' },
            info: { bg: '#3b82f6', color: '#ffffff', icon: 'ℹ' },
            warning: { bg: '#f59e0b', color: '#ffffff', icon: '⚠' }
        };
        
        const color = colors[type] || colors.info;
        toast.style.backgroundColor = color.bg;
        toast.style.color = color.color;
        
        toast.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0 mr-3">
                    <span class="text-lg font-bold">${color.icon}</span>
                </div>
                <div class="flex-1">
                    <span class="text-sm font-medium">${message}</span>
                </div>
                <button class="close-btn absolute top-2 right-2 text-white hover:text-gray-200 transition-colors duration-200" onclick="this.parentElement.parentElement.remove()">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Nach 6 Sekunden ausblenden
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 6000);
    };
    
    // Versuche sofort, falls window.showToast bereits verfügbar ist
    if (typeof window.showToast === 'function') {
        showToast();
    } else {
        // Warte auf DOMContentLoaded oder timeout
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', showToast);
        } else {
            // Fallback: Warte kurz und versuche dann
            setTimeout(showToast, 100);
        }
    }
}

// Backups laden
async function loadBackups() {
    try {
        const response = await fetch('/admin/backup/list');
        
        // Prüfe ob die Antwort erfolgreich ist
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // Prüfe Content-Type
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Server hat keine JSON-Antwort gesendet. Möglicherweise ist eine Fehlerseite zurückgegeben worden.');
        }
        
        const data = await response.json();
        const backupsList = document.getElementById('backupsList');
        
        if (data.status === 'success') {
            backupsList.innerHTML = '';
            
            if (data.backups && data.backups.length > 0) {
                data.backups.forEach(backup => {
                    const row = document.createElement('tr');
                    
                    // Bestimme Backup-Typ und Icon
                    let backupType, typeIcon, typeClass;
                    
                    if (backup.type === 'zip' || backup.name.endsWith('.zip')) {
                        backupType = 'ZIP';
                        typeIcon = 'fas fa-archive';
                        typeClass = 'badge-info';
                    } else if (backup.name.startsWith('scandy_native_backup_')) {
                        backupType = 'Native';
                        typeIcon = 'fas fa-database';
                        typeClass = 'badge-success';
                    } else {
                        backupType = 'JSON';
                        typeIcon = 'fas fa-file-code';
                        typeClass = 'badge-primary';
                    }
                    
                    // Zusätzliche Informationen für ZIP-Backups
                    let additionalInfo = '';
                    if (backup.type === 'zip' && backup.includes_media) {
                        additionalInfo = ' <span class="text-xs text-success">(mit Medien)</span>';
                    }
                    
                    row.innerHTML = `
                        <td>${backup.name}${additionalInfo}</td>
                        <td>
                            <span class="badge ${typeClass}">
                                <i class="${typeIcon} mr-1"></i>${backupType}
                            </span>
                        </td>
                        <td>${formatFileSize(backup.size)}</td>
                        <td>${new Date(backup.created * 1000).toLocaleString('de-DE', {
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        })}</td>
                        <td class="text-right">
                            <button class="btn btn-primary btn-xs mr-2 download-btn" data-filename="${backup.name}">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="btn btn-warning btn-xs mr-2 restore-btn" data-filename="${backup.name}">
                                <i class="fas fa-undo-alt"></i>
                            </button>
                            <button class="btn btn-danger btn-xs delete-btn" data-filename="${backup.name}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    `;
                    backupsList.appendChild(row);
                });
                // Event-Handler für die Backup-Aktionen registrieren
                setupBackupButtonHandlers();
            } else {
                backupsList.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center">Keine Backups verfügbar</td>
                    </tr>
                `;
            }
        } else {
            showBackupToast('error', 'Fehler beim Laden der Backups: ' + (data.message || 'Unbekannter Fehler'));
        }
    } catch (error) {
        console.error('Fehler beim Laden der Backups:', error);
        
        // Spezifische Fehlerbehandlung
        if (error.name === 'TypeError' && error.message.includes('JSON')) {
            showBackupToast('error', 'Server hat eine ungültige Antwort gesendet. Bitte laden Sie die Seite neu und versuchen Sie es erneut.');
        } else if (error.message.includes('HTTP 500')) {
            showBackupToast('error', 'Server-Fehler beim Laden der Backups. Bitte kontaktieren Sie den Administrator.');
        } else if (error.message.includes('HTTP 403')) {
            showBackupToast('error', 'Keine Berechtigung zum Laden der Backups.');
        } else {
            showBackupToast('error', 'Fehler beim Laden der Backups: ' + error.message);
        }
        
        // Zeige Fehlermeldung in der Tabelle
        const backupsList = document.getElementById('backupsList');
        if (backupsList) {
            backupsList.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center text-error">
                        <i class="fas fa-exclamation-triangle mr-2"></i>
                        Fehler beim Laden der Backups
                    </td>
                </tr>
            `;
        }
    }
}

// Event-Handler für Backup-Buttons
function setupBackupButtonHandlers() {
    // Download-Buttons
    document.querySelectorAll('.download-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            downloadBackup(filename);
        });
    });
    
    // Restore-Buttons
    document.querySelectorAll('.restore-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            showRestoreModal(filename);
        });
    });
    
    // Delete-Buttons
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            deleteBackup(filename);
        });
    });
}

// Vereinheitlichtes Backup erstellen (mit Medien)
async function createUnifiedBackup() {
    try {
        showBackupToast('info', 'Vereinheitlichtes Backup wird erstellt...');
        
        const response = await fetch('/backup/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                include_media: true,
                compress: true
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showBackupToast('success', data.message || 'Vereinheitlichtes Backup erfolgreich erstellt');
            loadBackups();
        } else {
            showBackupToast('error', data.message || 'Fehler beim Erstellen des Backups');
        }
    } catch (error) {
        console.error('Fehler beim Erstellen des vereinheitlichten Backups:', error);
        showBackupToast('error', 'Fehler beim Erstellen des Backups: ' + error.message);
    }
}

// Backup ohne Medien erstellen
async function createBackupNoMedia() {
    try {
        showBackupToast('info', 'Backup ohne Medien wird erstellt...');
        
        const response = await fetch('/backup/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                include_media: false,
                compress: true
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showBackupToast('success', data.message || 'Backup ohne Medien erfolgreich erstellt');
            loadBackups();
        } else {
            showBackupToast('error', data.message || 'Fehler beim Erstellen des Backups');
        }
    } catch (error) {
        console.error('Fehler beim Erstellen des Backups ohne Medien:', error);
        showBackupToast('error', 'Fehler beim Erstellen des Backups: ' + error.message);
    }
}

// JSON-Backup importieren
async function importJsonBackup() {
    // Datei-Auswahl-Dialog öffnen
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        try {
            showBackupToast('info', 'JSON-Backup wird importiert...');
            
            const formData = new FormData();
            formData.append('json_file', file);
            
            const response = await fetch('/backup/import-json', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                showBackupToast('success', data.message || 'JSON-Backup erfolgreich importiert');
                loadBackups();
            } else {
                showBackupToast('error', data.message || 'Fehler beim Importieren des JSON-Backups');
            }
        } catch (error) {
            console.error('Fehler beim Importieren des JSON-Backups:', error);
            showBackupToast('error', 'Fehler beim Importieren des JSON-Backups: ' + error.message);
        }
    };
    input.click();
}

// Native MongoDB Backup erstellen
async function createNativeBackup() {
    try {
        showBackupToast('info', 'Native MongoDB Backup wird erstellt...');
        
        const response = await fetch('/admin/backup/create-native', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showBackupToast('success', data.message);
            loadBackups(); // Liste aktualisieren
        } else {
            showBackupToast('error', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Erstellen des nativen Backups:', error);
        showBackupToast('error', 'Fehler beim Erstellen des nativen Backups: ' + error.message);
    }
}

// Hybrides Backup erstellen
async function createHybridBackup() {
    try {
        showBackupToast('info', 'Hybrides Backup wird erstellt...');
        
        const response = await fetch('/admin/backup/create-hybrid', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showBackupToast('success', data.message);
            loadBackups(); // Liste aktualisieren
        } else {
            showBackupToast('error', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Erstellen des hybriden Backups:', error);
        showBackupToast('error', 'Fehler beim Erstellen des hybriden Backups: ' + error.message);
    }
}

// Aktuelle Datenbank herunterladen
async function downloadCurrentDatabase() {
    try {
        // Erstelle zuerst ein Backup und lade es dann herunter
        const response = await fetch('/admin/backup/create', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Lade das gerade erstellte Backup herunter
            window.location.href = `/admin/backup/download/${data.filename}`;
        } else {
            showBackupToast('error', data.message || 'Fehler beim Erstellen des Backups');
        }
    } catch (error) {
        showBackupToast('error', 'Fehler beim Herunterladen der Datenbank: ' + error.message);
    }
}

// Backup herunterladen
async function downloadBackup(filename) {
    try {
        window.location.href = `/admin/backup/download/${filename}`;
    } catch (error) {
        showBackupToast('error', 'Fehler beim Herunterladen des Backups: ' + error.message);
    }
}

// Backup wiederherstellen
function showRestoreModal(filename) {
    document.getElementById('restoreBackupName').textContent = filename;
    document.getElementById('restoreBackupModal').showModal();
    document.getElementById('confirmRestoreBtn').onclick = function() {
        restoreBackup(filename);
    };
}

async function restoreBackup(filename) {
    if (!confirm('Möchten Sie dieses Backup wirklich wiederherstellen? Die aktuelle Datenbank wird automatisch gesichert.')) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/backup/restore/${filename}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showBackupToast('success', 'Backup wurde erfolgreich wiederhergestellt. Die Seite wird neu geladen.');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showBackupToast('error', data.message || 'Fehler beim Wiederherstellen des Backups');
        }
    } catch (error) {
        showBackupToast('error', 'Fehler beim Wiederherstellen des Backups: ' + error.message);
    }
}

// Backup löschen
async function deleteBackup(filename) {
    if (!confirm('Möchten Sie dieses Backup wirklich löschen?')) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/backup/delete/${filename}`, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showBackupToast('success', 'Backup wurde erfolgreich gelöscht');
            loadBackups();
        } else {
            showBackupToast('error', data.message || 'Fehler beim Löschen des Backups');
        }
    } catch (error) {
        showBackupToast('error', 'Fehler beim Löschen des Backups: ' + error.message);
    }
}

// Upload-Handler
function setupBackupHandlers() {
    // Backup hochladen
    const uploadForm = document.getElementById('uploadBackupForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(uploadForm);
            const fileInput = uploadForm.querySelector('input[type="file"]');
            
            if (!fileInput.files.length) {
                showBackupToast('error', 'Bitte wählen Sie eine Datei aus');
                return;
            }
            
            const fileName = fileInput.files[0].name.toLowerCase();
            if (!fileName.endsWith('.zip') && !fileName.endsWith('.json')) {
                showBackupToast('error', 'Nur .zip- und .json-Dateien erlaubt!');
                return;
            }
            
            // Prüfe Dateigröße
            if (fileInput.files[0].size === 0) {
                showBackupToast('error', 'Die ausgewählte Datei ist leer. Bitte wählen Sie eine gültige Backup-Datei aus.');
                return;
            }
            
            // Mindestgröße für ZIP-Dateien
            if (fileInput.files[0].size < 1000) {
                showBackupToast('error', 'Die ausgewählte Datei ist zu klein für ein gültiges Backup. Bitte wählen Sie eine gültige Backup-Datei aus.');
                return;
            }
            
            try {
                const response = await fetch('/admin/backup/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    showBackupToast('success', 'Backup erfolgreich hochgeladen und aktiviert');
                    loadBackups();
                    uploadForm.reset();
                } else {
                    showBackupToast('error', data.message || 'Fehler beim Hochladen des Backups');
                }
            } catch (error) {
                console.error('Fehler beim Hochladen des Backups:', error);
                if (error.name === 'TypeError' && error.message.includes('JSON')) {
                    showBackupToast('error', 'Die hochgeladene Datei ist ungültig oder leer. Bitte wählen Sie eine gültige Backup-Datei aus.');
                } else {
                    showBackupToast('error', 'Fehler beim Hochladen des Backups: ' + error.message);
                }
            }
        });
    }
    
    // Backup erstellen Button
    const createBtn = document.getElementById('createBackupBtn');
    if (createBtn) {
        createBtn.onclick = createBackup;
    }
}

// Auto-Backup-System
function initAutoBackup() {
    // Event-Listener für Auto-Backup-Buttons
    const startBtn = document.getElementById('startAutoBackup');
    const stopBtn = document.getElementById('stopAutoBackup');
    
    if (startBtn) {
        startBtn.addEventListener('click', startAutoBackup);
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', stopAutoBackup);
    }
    
    // Status laden
    loadAutoBackupStatus();
    
    // Nur auf Admin-Seiten regelmäßig aktualisieren
    if (window.location.pathname.includes('/admin/') || window.location.pathname.includes('/auto-backup')) {
        // Status alle 5 Minuten aktualisieren (statt 30 Sekunden)
        setInterval(loadAutoBackupStatus, 300000);
    }
}

async function loadAutoBackupStatus() {
    const statusElement = document.getElementById('autoBackupStatus');
    const nextBackupElement = document.getElementById('nextBackupTime');
    const backupTimesElement = document.getElementById('backupTimesDisplay');
    
    if (!statusElement || !nextBackupElement) return;

    try {
        const response = await fetch('/admin/backup/auto/status');
        const data = await response.json();
        
        if (data.success) {
            const status = data.status;
            
            // Status-Indikator
            if (status.running) {
                statusElement.className = 'badge badge-success';
                statusElement.textContent = 'Aktiv';
            } else {
                statusElement.className = 'badge badge-error';
                statusElement.textContent = 'Gestoppt';
            }
            
            // Nächste Backup-Zeit
            nextBackupElement.textContent = status.next_backup;
            
            // Backup-Zeiten anzeigen
            if (backupTimesElement && status.backup_times) {
                backupTimesElement.textContent = status.backup_times.join(' Uhr, ') + ' Uhr';
            }
        } else {
            statusElement.className = 'badge badge-warning';
            statusElement.textContent = 'Fehler';
            nextBackupElement.textContent = 'Unbekannt';
            if (backupTimesElement) {
                backupTimesElement.textContent = 'Unbekannt';
            }
        }
    } catch (error) {
        console.error('Fehler beim Laden des Auto-Backup-Status:', error);
        statusElement.className = 'badge badge-warning';
        statusElement.textContent = 'Fehler';
        nextBackupElement.textContent = 'Unbekannt';
        if (backupTimesElement) {
            backupTimesElement.textContent = 'Unbekannt';
        }
    }
}

async function startAutoBackup() {
    if (!confirm('Automatisches Backup-System starten?')) return;
    
    try {
        const response = await fetch('/admin/backup/auto/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        
        if (data.success) {
            showBackupToast('success', data.message);
            loadAutoBackupStatus();
        } else {
            showBackupToast('error', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Starten:', error);
        showBackupToast('error', 'Fehler beim Starten');
    }
}

async function stopAutoBackup() {
    if (!confirm('Automatisches Backup-System stoppen?')) return;
    
    try {
        const response = await fetch('/admin/backup/auto/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        
        if (data.success) {
            showBackupToast('success', data.message);
            loadAutoBackupStatus();
        } else {
            showBackupToast('error', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Stoppen:', error);
        showBackupToast('error', 'Fehler beim Stoppen');
    }
}

// Backup-Konvertierung Funktionen
function initBackupConversion() {
    const convertAllOldBackupsBtn = document.getElementById('convertAllOldBackupsBtn');
    const listOldBackupsBtn = document.getElementById('listOldBackupsBtn');
    
    if (convertAllOldBackupsBtn) {
        convertAllOldBackupsBtn.onclick = convertAllOldBackups;
    }
    
    if (listOldBackupsBtn) {
        listOldBackupsBtn.onclick = listOldBackups;
    }
}

async function convertAllOldBackups() {
    try {
        showBackupToast('info', 'Konvertiere alle alten Backups...');
        
        const response = await fetch('/admin/backup/convert-all-old', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showBackupToast('success', data.message);
            if (data.converted_backups && data.converted_backups.length > 0) {
                console.log('Konvertierte Backups:', data.converted_backups);
            }
            // Lade Backups neu
            loadBackups();
        } else {
            showBackupToast('error', data.message || 'Fehler bei der Massenkonvertierung');
        }
    } catch (error) {
        console.error('Fehler bei der Massenkonvertierung:', error);
        showBackupToast('error', 'Fehler bei der Massenkonvertierung: ' + error.message);
    }
}

async function listOldBackups() {
    try {
        showBackupToast('info', 'Lade alte Backups...');
        
        const response = await fetch('/admin/backup/list-old');
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayOldBackups(data.old_backups);
            showBackupToast('success', `${data.count} alte Backups gefunden`);
        } else {
            showBackupToast('error', data.message || 'Fehler beim Auflisten alter Backups');
        }
    } catch (error) {
        console.error('Fehler beim Auflisten alter Backups:', error);
        showBackupToast('error', 'Fehler beim Auflisten alter Backups: ' + error.message);
    }
}

function displayOldBackups(oldBackups) {
    const oldBackupsList = document.getElementById('oldBackupsList');
    const oldBackupsContent = document.getElementById('oldBackupsContent');
    
    if (!oldBackupsList || !oldBackupsContent) {
        console.error('Old backups list elements not found');
        return;
    }
    
    if (oldBackups.length === 0) {
        oldBackupsContent.innerHTML = '<p class="text-sm text-base-content/60">Keine alten Backups gefunden</p>';
    } else {
        oldBackupsContent.innerHTML = '';
        
        oldBackups.forEach(backup => {
            const backupItem = document.createElement('div');
            backupItem.className = 'flex justify-between items-center p-2 bg-base-200 rounded-lg';
            
            const createdDate = new Date(backup.created * 1000).toLocaleString('de-DE', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            backupItem.innerHTML = `
                <div class="flex-1">
                    <div class="font-medium">${backup.filename}</div>
                    <div class="text-xs text-base-content/60">
                        ${formatFileSize(backup.size)} • ${createdDate} • ${backup.collections.length} Collections
                    </div>
                </div>
                <div class="flex gap-2">
                    <button class="btn btn-warning btn-xs" onclick="convertSingleBackup('${backup.filename}')">
                        <i class="fas fa-sync-alt mr-1"></i>Konvertieren
                    </button>
                </div>
            `;
            
            oldBackupsContent.appendChild(backupItem);
        });
    }
    
    oldBackupsList.classList.remove('hidden');
}

async function convertSingleBackup(filename) {
    try {
        showBackupToast('info', `Konvertiere Backup: ${filename}`);
        
        const response = await fetch(`/admin/backup/convert-old/${filename}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showBackupToast('success', data.message);
            // Lade Backups neu
            loadBackups();
            // Aktualisiere alte Backups Liste
            listOldBackups();
        } else {
            showBackupToast('error', data.message || 'Fehler beim Konvertieren des Backups');
        }
    } catch (error) {
        console.error('Fehler beim Konvertieren des Backups:', error);
        showBackupToast('error', 'Fehler beim Konvertieren des Backups: ' + error.message);
    }
} 