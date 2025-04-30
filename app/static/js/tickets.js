console.log('tickets.js wird geladen');

// Globale Funktionen
window.showToast = function(type, message) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `alert ${type === 'error' ? 'alert-error' : 'alert-success'} mb-2`;
    
    toast.innerHTML = `
        <div>
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="${type === 'error' 
                        ? 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z'
                        : 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'}" />
            </svg>
            <span>${message}</span>
        </div>
    `;
    
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
};

window.deleteTicket = function(ticketId) {
    console.log('deleteTicket aufgerufen mit ID:', ticketId);
    if (!confirm('Möchten Sie dieses Ticket wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.')) {
        return;
    }
    
    fetch(`/tickets/${ticketId}/delete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('success', 'Ticket erfolgreich gelöscht');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast('error', data.message || 'Fehler beim Löschen des Tickets');
        }
    })
    .catch(error => {
        console.error('Fehler:', error);
        showToast('error', 'Ein Fehler ist aufgetreten');
    });
};

// Event Listener für DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded Event');
    
    // Filter-Formular
    const form = document.getElementById('filterForm');
    if (form) {
        const inputs = form.querySelectorAll('select, input');
        
        inputs.forEach(input => {
            input.addEventListener('change', function() {
                const params = new URLSearchParams(window.location.search);
                
                inputs.forEach(inp => {
                    if (inp.value) {
                        params.set(inp.name, inp.value);
                    } else {
                        params.delete(inp.name);
                    }
                });
                
                window.location.href = `${window.location.pathname}?${params.toString()}`;
            });
            
            // Setze gespeicherte Werte
            const params = new URLSearchParams(window.location.search);
            const savedValue = params.get(input.name);
            if (savedValue) {
                input.value = savedValue;
            }
        });
    }

    // Ticket-Formular
    const ticketForm = document.getElementById('ticketForm');
    if (ticketForm) {
        ticketForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Speichern...';
            
            const formData = new FormData(this);
            const data = {
                title: formData.get('title'),
                description: formData.get('description'),
                priority: formData.get('priority')
            };
            
            fetch(this.action, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('success', 'Ticket erfolgreich erstellt');
                    setTimeout(() => {
                        window.location.href = data.redirect_url || '/tickets';
                    }, 1000);
                } else {
                    throw new Error(data.message || 'Fehler beim Erstellen des Tickets');
                }
            })
            .catch(error => {
                console.error('Fehler:', error);
                showToast('error', error.message || 'Ein Fehler ist aufgetreten');
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Speichern';
            });
        });
    }
}); 