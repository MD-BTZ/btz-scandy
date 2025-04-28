// Backup-Verwaltung
document.addEventListener('DOMContentLoaded', () => {
    loadBackups();
    setupBackupHandlers();
});

// Backups laden
async function loadBackups() {
    try {
        const response = await fetch('/admin/backup/list');
        const data = await response.json();
        
        if (data.status === 'success') {
            const backupsList = document.getElementById('backupsList');
            backupsList.innerHTML = '';
            
            data.backups.forEach(backup => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${backup.name}</td>
                    <td>${formatFileSize(backup.size)}</td>
                    <td>${new Date(backup.created * 1000).toLocaleString('de-DE')}</td>
                    <td class="text-right">
                        <button onclick="downloadBackup('${backup.name}')" class="btn btn-primary btn-xs mr-2">
                            <i class="fas fa-download"></i>
                        </button>
                        <button onclick="restoreBackup('${backup.name}')" class="btn btn-warning btn-xs mr-2">
                            <i class="fas fa-undo-alt"></i>
                        </button>
                        <button onclick="deleteBackup('${backup.name}')" class="btn btn-danger btn-xs">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                `;
                backupsList.appendChild(row);
            });
        } else {
            showError('Fehler beim Laden der Backups');
        }
    } catch (error) {
        showError('Fehler beim Laden der Backups');
        console.error(error);
    }
}

// Event Handler einrichten
function setupBackupHandlers() {
    // Backup hochladen
    const uploadForm = document.getElementById('uploadBackupForm');
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(uploadForm);
        
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
            showError('Fehler beim Hochladen des Backups');
            console.error(error);
        }
    });
}

// Backup erstellen
async function createBackup() {
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
        showError('Fehler beim Erstellen des Backups');
        console.error(error);
    }
}

// Aktuelle Datenbank herunterladen
async function downloadCurrentDatabase() {
    try {
        window.location.href = '/admin/backup/download/db';
    } catch (error) {
        showError('Fehler beim Herunterladen der Datenbank');
        console.error(error);
    }
}

// Backup herunterladen
async function downloadBackup(filename) {
    try {
        window.location.href = `/admin/backup/download/backup/${filename}`;
    } catch (error) {
        showError('Fehler beim Herunterladen des Backups');
        console.error(error);
    }
}

// Backup wiederherstellen
async function restoreBackup(filename) {
    try {
        const response = await fetch(`/admin/backup/restore/${filename}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess('Backup wurde erfolgreich wiederhergestellt');
            loadBackups();
        } else {
            showError(data.message || 'Fehler beim Wiederherstellen des Backups');
        }
    } catch (error) {
        showError('Fehler beim Wiederherstellen des Backups');
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
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            showSuccess('Backup wurde erfolgreich gelöscht');
            loadBackups(); // Liste aktualisieren
        } else {
            const data = await response.json();
            showError(data.message || 'Fehler beim Löschen des Backups');
        }
    } catch (error) {
        showError('Fehler beim Löschen des Backups');
        console.error(error);
    }
}

// Hilfsfunktionen
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showSuccess(message) {
    // Implementierung der Erfolgsmeldung
    alert(message); // Temporär, sollte durch bessere UI ersetzt werden
}

function showError(message) {
    // Implementierung der Fehlermeldung
    alert(message); // Temporär, sollte durch bessere UI ersetzt werden
} 