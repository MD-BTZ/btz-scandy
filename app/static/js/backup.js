// Backup-Verwaltung
document.addEventListener('DOMContentLoaded', () => {
    // Nur noch die eindeutigen Backup-Buttons initialisieren
    const createBackupBtn = document.getElementById('createBackupBtn');
    const downloadCurrentBtn = document.getElementById('downloadCurrentBtn');

    if (createBackupBtn) {
        createBackupBtn.onclick = createBackup;
    }
    
    if (downloadCurrentBtn) {
        downloadCurrentBtn.onclick = downloadCurrentDatabase;
    }
    
    // Initialisiere Backup-System
    loadBackups();
    setupBackupHandlers();
    
    // Initialisiere Auto-Backup-System
    initAutoBackup();
});

// Hilfsfunktionen
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showToast(type, message) {
    // Verwende die zentrale window.showToast Funktion
    if (typeof window.showToast === 'function') {
        window.showToast(type, message);
    } else {
        // Fallback für den Fall, dass window.showToast nicht verfügbar ist
        alert(`${type.toUpperCase()}: ${message}`);
    }
}

// Backups laden
async function loadBackups() {
    try {
        const response = await fetch('/admin/backup/list');
        const data = await response.json();
        const backupsList = document.getElementById('backupsList');
        
        if (data.status === 'success') {
            backupsList.innerHTML = '';
            
            if (data.backups && data.backups.length > 0) {
                data.backups.forEach(backup => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${backup.name}</td>
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
            showToast('error', 'Fehler beim Laden der Backups: ' + (data.message || 'Unbekannter Fehler'));
        }
    } catch (error) {
        showToast('error', 'Fehler beim Laden der Backups: ' + error.message);
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

// Backup erstellen
async function createBackup() {
    // Frage nach E-Mail-Adresse für Backup-Versand
    const emailRecipient = prompt('E-Mail-Adresse für Backup-Versand (optional, leer lassen für keinen Versand):');
    
    try {
        const formData = new FormData();
        if (emailRecipient && emailRecipient.trim()) {
            formData.append('email_recipient', emailRecipient.trim());
        }
        
        const response = await fetch('/admin/backup/create', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showToast('success', data.message || 'Backup wurde erfolgreich erstellt');
            loadBackups();
        } else {
            showToast('error', data.message || 'Fehler beim Erstellen des Backups');
        }
    } catch (error) {
        showToast('error', 'Fehler beim Erstellen des Backups: ' + error.message);
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
            showToast('error', data.message || 'Fehler beim Erstellen des Backups');
        }
    } catch (error) {
        showToast('error', 'Fehler beim Herunterladen der Datenbank: ' + error.message);
    }
}

// Backup herunterladen
async function downloadBackup(filename) {
    try {
        window.location.href = `/admin/backup/download/${filename}`;
    } catch (error) {
        showToast('error', 'Fehler beim Herunterladen des Backups: ' + error.message);
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
            showToast('success', 'Backup wurde erfolgreich wiederhergestellt. Die Seite wird neu geladen.');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showToast('error', data.message || 'Fehler beim Wiederherstellen des Backups');
        }
    } catch (error) {
        showToast('error', 'Fehler beim Wiederherstellen des Backups: ' + error.message);
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
            showToast('success', 'Backup wurde erfolgreich gelöscht');
            loadBackups();
        } else {
            showToast('error', data.message || 'Fehler beim Löschen des Backups');
        }
    } catch (error) {
        showToast('error', 'Fehler beim Löschen des Backups: ' + error.message);
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
                showToast('error', 'Bitte wählen Sie eine Datei aus');
                return;
            }
            
            if (!fileInput.files[0].name.endsWith('.json')) {
                showToast('error', 'Nur .json-Dateien erlaubt!');
                return;
            }
            
            try {
                const response = await fetch('/admin/backup/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    showToast('success', 'Backup erfolgreich hochgeladen und aktiviert');
                    loadBackups();
                    uploadForm.reset();
                } else {
                    showToast('error', data.message || 'Fehler beim Hochladen des Backups');
                }
            } catch (error) {
                console.error('Fehler beim Hochladen des Backups:', error);
                showToast('error', 'Fehler beim Hochladen des Backups: ' + error.message);
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
    
    // Status alle 30 Sekunden aktualisieren
    setInterval(loadAutoBackupStatus, 30000);
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
            showToast('success', data.message);
            loadAutoBackupStatus();
        } else {
            showToast('error', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Starten:', error);
        showToast('error', 'Fehler beim Starten');
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
            showToast('success', data.message);
            loadAutoBackupStatus();
        } else {
            showToast('error', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Stoppen:', error);
        showToast('error', 'Fehler beim Stoppen');
    }
} 