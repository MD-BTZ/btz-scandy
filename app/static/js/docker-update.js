// Docker Update Management
document.addEventListener('DOMContentLoaded', function() {
    const startUpdateBtn = document.getElementById('startUpdate');
    const confirmModal = document.getElementById('confirmModal');
    const confirmUpdateBtn = document.getElementById('confirmUpdate');
    const cancelUpdateBtn = document.getElementById('cancelUpdate');

    // Event Listeners
    startUpdateBtn.addEventListener('click', showConfirmModal);
    confirmUpdateBtn.addEventListener('click', executeUpdate);
    cancelUpdateBtn.addEventListener('click', hideConfirmModal);

    // Modal-Funktionen
    function showConfirmModal() {
        confirmModal.classList.add('modal-open');
    }

    function hideConfirmModal() {
        confirmModal.classList.remove('modal-open');
    }

    // Update starten
    async function executeUpdate() {
        hideConfirmModal();
        
        try {
            startUpdateBtn.disabled = true;
            startUpdateBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Starte Update...';
            
            const response = await fetch('/admin/docker-update/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                showToast('success', 'Update gestartet! Die App wird in ca. 10-15 Minuten wieder verfügbar sein.');
                
                // Zeige finale Nachricht
                setTimeout(() => {
                    showFinalMessage();
                }, 2000);
            } else {
                showToast('error', result.message);
                startUpdateBtn.disabled = false;
                startUpdateBtn.innerHTML = '<i class="fas fa-play mr-2"></i>Update starten';
            }
            
        } catch (error) {
            console.error('Fehler beim Starten des Updates:', error);
            showToast('error', 'Fehler beim Starten des Updates');
            startUpdateBtn.disabled = false;
            startUpdateBtn.innerHTML = '<i class="fas fa-play mr-2"></i>Update starten';
        }
    }

    // Zeige finale Nachricht
    function showFinalMessage() {
        const cardBody = document.querySelector('.card-body');
        const existingMessage = document.getElementById('finalMessage');
        
        if (existingMessage) {
            existingMessage.remove();
        }
        
        const finalMessage = document.createElement('div');
        finalMessage.id = 'finalMessage';
        finalMessage.className = 'alert alert-info mt-4';
        finalMessage.innerHTML = `
            <i class="fas fa-info-circle"></i>
            <div>
                <h3 class="font-bold">Update läuft</h3>
                <p>Das Update wurde erfolgreich gestartet. Die Scandy-App ist jetzt nicht mehr erreichbar.</p>
                <p class="text-sm mt-2">
                    <strong>Nächste Schritte:</strong><br>
                    • Warten Sie ca. 10-15 Minuten<br>
                    • Versuchen Sie dann, die App neu zu laden<br>
                    • Falls die App nach 15 Minuten nicht erreichbar ist, kontaktieren Sie den Administrator
                </p>
            </div>
        `;
        
        cardBody.appendChild(finalMessage);
        
        // Button deaktivieren
        startUpdateBtn.disabled = true;
        startUpdateBtn.innerHTML = '<i class="fas fa-check mr-2"></i>Update gestartet';
    }

    // Toast-Funktion (falls nicht global verfügbar)
    function showToast(type, message) {
        if (typeof window.showToast === 'function') {
            window.showToast(type, message);
        } else {
            // Fallback: Alert
            alert(`${type.toUpperCase()}: ${message}`);
        }
    }
}); 