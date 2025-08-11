// Version Check für das Menü
document.addEventListener('DOMContentLoaded', function() {
    const versionNumber = document.getElementById('versionNumber');
    const updateStatus = document.getElementById('updateStatus');
    
    if (!versionNumber || !updateStatus) return;
    
    // Update-Status anzeigen
    updateStatus.style.opacity = '1';
    
    // Update-Überprüfung durchführen
    checkForUpdates();
    
    // Alle 30 Minuten erneut prüfen
    setInterval(checkForUpdates, 30 * 60 * 1000);
});

async function checkForUpdates() {
    const updateStatus = document.getElementById('updateStatus');
    const versionNumber = document.getElementById('versionNumber');
    
    try {
        const response = await fetch('/admin/version_check');
        
        // Prüfe ob die Antwort erfolgreich ist
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.update_available) {
            // Update verfügbar
            versionNumber.classList.add('text-warning');
            versionNumber.classList.remove('text-base-content');
            updateStatus.textContent = 'Update verfügbar!';
            updateStatus.classList.add('text-warning');
            updateStatus.classList.remove('text-base-content');
            updateStatus.style.opacity = '1';
        } else {
            // Kein Update verfügbar
            versionNumber.classList.remove('text-warning');
            versionNumber.classList.add('text-base-content');
            updateStatus.textContent = 'Aktuell';
            updateStatus.classList.remove('text-warning');
            updateStatus.classList.add('text-success');
            updateStatus.style.opacity = '0.7';
        }
    } catch (error) {
        console.error('Fehler bei der Update-Überprüfung:', error);
        updateStatus.textContent = 'Prüfung fehlgeschlagen';
        updateStatus.classList.add('text-error');
        updateStatus.classList.remove('text-success', 'text-warning');
        updateStatus.style.opacity = '0.7';
        
        // Zeige die Versionsnummer normal an
        versionNumber.classList.remove('text-warning');
        versionNumber.classList.add('text-base-content');
    }
} 