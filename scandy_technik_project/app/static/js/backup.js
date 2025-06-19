// Backup-Verwaltung
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded and parsed"); // Log 1: DOM ready
    
    // Nur noch die eindeutigen Backup-Buttons initialisieren
    const createBackupBtn = document.getElementById('createBackupBtn');
    const downloadCurrentBtn = document.getElementById('downloadCurrentBtn');
    
    console.log("Attempting to find buttons:", createBackupBtn, downloadCurrentBtn); // Log 2: Buttons found?

    if (createBackupBtn) {
        console.log("createBackupBtn found, attaching onclick handler."); // Log 3: Handler attachment attempt
        createBackupBtn.onclick = createBackup;
    } else {
        console.error("createBackupBtn NOT found!"); // Log 4: Button not found error
    }
    
    if (downloadCurrentBtn) {
        console.log("downloadCurrentBtn found, attaching onclick handler.");
        downloadCurrentBtn.onclick = downloadCurrentDatabase;
    } else {
        console.error("downloadCurrentBtn NOT found!");
    }
    
    // Initialisiere Backup-System
    console.log("Initializing backup system (loadBackups, setupBackupHandlers)"); // Log 5: Before init functions
    loadBackups();
    setupBackupHandlers();
    console.log("Backup system initialization finished."); // Log 6: After init functions
});

// Hilfsfunktionen
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showSuccess(message) {
    // Toast-Nachricht anzeigen
    if (typeof window.showToast === 'function') {
        window.showToast('success', message);
    } else {
        alert('Erfolg: ' + message);
    }
}

function showError(message) {
    // Toast-Nachricht anzeigen
    if (typeof window.showToast === 'function') {
        window.showToast('error', message);
    } else {
        alert('Fehler: ' + message);
    }
}

// Backups laden
async function loadBackups() {
    console.log("loadBackups() wird ausgeführt");
    try {
        const response = await fetch('/admin/backup/list');
        const data = await response.json();
        console.log("Antwort von /admin/backup/list:", data);
        const backupsList = document.getElementById('backupsList');
        console.log("backupsList Element:", backupsList);
        
        if (data.status === 'success') {
            backupsList.innerHTML = '';
            
            if (data.backups && data.backups.length > 0) {
                data.backups.forEach(backup => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${backup.name}</td>
                        <td>${formatFileSize(backup.size)}</td>
                        <td>${new Date(backup.created * 1000).toLocaleString('de-DE')}</td>
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
                console.log("Backups wurden in die Tabelle geschrieben");
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
            showError('Fehler beim Laden der Backups: ' + (data.message || 'Unbekannter Fehler'));
        }
    } catch (error) {
        showError('Fehler beim Laden der Backups: ' + error.message);
        console.error(error);
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
    console.log("createBackup function called!");
    try {
        const response = await fetch('/admin/backup/create', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess('Backup wurde erfolgreich erstellt');
            loadBackups();
        } else {
            showError(data.message || 'Fehler beim Erstellen des Backups');
        }
    } catch (error) {
        showError('Fehler beim Erstellen des Backups: ' + error.message);
        console.error(error);
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
            showError(data.message || 'Fehler beim Erstellen des Backups');
        }
    } catch (error) {
        showError('Fehler beim Herunterladen der Datenbank: ' + error.message);
        console.error(error);
    }
}

// Backup herunterladen
async function downloadBackup(filename) {
    try {
        window.location.href = `/admin/backup/download/${filename}`;
    } catch (error) {
        showError('Fehler beim Herunterladen des Backups: ' + error.message);
        console.error(error);
    }
}

// Backup wiederherstellen
function showRestoreModal(filename) {
    document.getElementById('restoreBackupName').textContent = filename;
    document.getElementById('restoreBackupModal').showModal();
    document.getElementById('confirmRestoreBtn').onclick = function() {
        restoreBackup(filename);
        document.getElementById('restoreBackupModal').close();
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
            showSuccess('Backup wurde erfolgreich wiederhergestellt. Die Seite wird neu geladen.');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showError(data.message || 'Fehler beim Wiederherstellen des Backups');
        }
    } catch (error) {
        showError('Fehler beim Wiederherstellen des Backups: ' + error.message);
        console.error(error);
    }
}

// Backup löschen
async function deleteBackup(filename) {
    if (!confirm('Möchten Sie dieses Backup wirklich löschen?')) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/backup/delete/${filename}`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess('Backup wurde erfolgreich gelöscht');
            loadBackups();
        } else {
            showError(data.message || 'Fehler beim Löschen des Backups');
        }
    } catch (error) {
        showError('Fehler beim Löschen des Backups: ' + error.message);
        console.error(error);
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
                showError('Bitte wählen Sie eine Datei aus');
                return;
            }
            
            if (!fileInput.files[0].name.endsWith('.json')) {
                showError('Nur .json-Dateien erlaubt!');
                return;
            }
            
            try {
                const response = await fetch('/admin/backup/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    showSuccess('Backup erfolgreich hochgeladen und aktiviert');
                    loadBackups();
                    uploadForm.reset();
                } else {
                    showError(data.message || 'Fehler beim Hochladen des Backups');
                }
            } catch (error) {
                console.error('Fehler beim Hochladen des Backups:', error);
                showError('Fehler beim Hochladen des Backups: ' + error.message);
            }
        });
    }
    
    // Backup erstellen Button
    const createBtn = document.getElementById('createBackupBtn');
    if (createBtn) {
        createBtn.onclick = createBackup;
    }
} 