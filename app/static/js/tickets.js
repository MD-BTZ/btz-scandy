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

function createTicket() {
    const form = document.getElementById('ticketForm');
    const formData = new FormData(form);
    
    // Konvertiere FormData zu JSON
    const data = {};
    formData.forEach((value, key) => {
        data[key] = value;
    });
    
    // Sende POST-Request
    fetch('/tickets/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('success', data.message);
            // Formular zurücksetzen
            form.reset();
            // Weiterleitung zur Create-Seite
            window.location.href = '/tickets/create';
        } else {
            showToast('error', data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('error', 'Ein Fehler ist aufgetreten');
    });
}

// Event Listener für DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded Event');
    
    // Filter-Formular
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        const inputs = filterForm.querySelectorAll('select, input');
        
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
            const data = {};
            formData.forEach((value, key) => {
                data[key] = value;
            });
            
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
                    // Formular zurücksetzen
                    this.reset();
                    // Weiterleitung zur Create-Seite
                    window.location.href = '/tickets/create';
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

    // Auftragsdetails-Formular
    const auftragDetailsForm = document.getElementById('auftragDetailsForm');
    if (auftragDetailsForm) {
        auftragDetailsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Speichern...';
            
            const details = collectAuftragDetails();
            
            fetch(this.action, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(details)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('success', 'Auftragsdetails erfolgreich gespeichert');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    throw new Error(data.message || 'Ein Fehler ist aufgetreten');
                }
            })
            .catch(error => {
                console.error('Fehler:', error);
                showToast('error', error.message || 'Ein Fehler ist aufgetreten');
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Speichern';
            });
        });
    }

    // Initialisiere die Summen beim Laden
    updateGesamtsumme();
});

// Funktion zum Sammeln der Materialliste
function collectMaterialList() {
    const rows = document.querySelectorAll('#materialRows tr');
    const materialList = [];
    
    rows.forEach(row => {
        const material = row.querySelector('input[name="material"]').value;
        const menge = parseFloat(row.querySelector('input[name="menge"]').value) || 0;
        const einzelpreis = parseFloat(row.querySelector('input[name="einzelpreis"]').value) || 0;
        
        if (material && (menge > 0 || einzelpreis > 0)) {
            materialList.push({
                material: material,
                menge: menge,
                einzelpreis: einzelpreis,
                gesamtpreis: menge * einzelpreis
            });
        }
    });
    
    return materialList;
}

// Funktion zum Sammeln der Auftragsdetails
function collectAuftragDetails() {
    const form = document.getElementById('auftragDetailsForm');
    const formData = new FormData(form);
    const data = {};
    
    // Sammle alle Formularfelder
    formData.forEach((value, key) => {
        // Spezielle Behandlung für Checkboxen
        if (key === 'auftraggeber_intern' || key === 'auftraggeber_extern') {
            data[key] = value === 'on' || value === 'true' || value === '1';
        } else {
            data[key] = value;
        }
    });
    
    // Sammle Materialliste
    const materialList = [];
    const materialRows = document.querySelectorAll('.material-row');
    materialRows.forEach(row => {
        const material = row.querySelector('.material-input').value;
        const menge = parseFloat(row.querySelector('.menge-input').value) || 0;
        const einzelpreis = parseFloat(row.querySelector('.einzelpreis-input').value) || 0;
        
        if (material) {
            materialList.push({
                material: material,
                menge: menge,
                einzelpreis: einzelpreis
            });
        }
    });
    
    data.material_list = materialList;
    
    console.log('Gesammelte Auftragsdetails:', data);
    return data;
}

// Funktion zum Aktualisieren der Materialsumme
function updateSumme(input) {
    const row = input.closest('tr');
    const menge = parseFloat(row.querySelector('input[name="menge"]').value) || 0;
    const einzelpreis = parseFloat(row.querySelector('input[name="einzelpreis"]').value) || 0;
    const gesamtpreis = menge * einzelpreis;
    
    row.querySelector('input[name="gesamtpreis"]').value = gesamtpreis.toFixed(2);
    updateGesamtsumme();
}

// Funktion zum Aktualisieren der Gesamtsumme
function updateGesamtsumme() {
    const rows = document.querySelectorAll('#materialRows tr');
    let summe = 0;
    
    rows.forEach(row => {
        const gesamtpreis = parseFloat(row.querySelector('input[name="gesamtpreis"]').value) || 0;
        summe += gesamtpreis;
    });
    
    document.getElementById('summeMaterial').textContent = summe.toFixed(2) + ' €';
}

// Funktion zum Hinzufügen einer neuen Materialzeile
function addMaterialRow() {
    const tbody = document.getElementById('materialRows');
    const newRow = document.createElement('tr');
    
    newRow.innerHTML = `
        <td><input type="text" name="material" class="input input-bordered w-full"></td>
        <td><input type="number" name="menge" class="input input-bordered w-24" min="0" step="any" onchange="updateSumme(this)"></td>
        <td><input type="number" name="einzelpreis" class="input input-bordered w-24" min="0" step="any" onchange="updateSumme(this)"></td>
        <td><input type="text" name="gesamtpreis" class="input input-bordered w-32" readonly></td>
        <td><button type="button" class="btn btn-error btn-sm" onclick="removeMaterialRow(this)"><i class="fas fa-trash"></i></button></td>
    `;
    
    tbody.appendChild(newRow);
}

// Funktion zum Entfernen einer Materialzeile
function removeMaterialRow(button) {
    const row = button.closest('tr');
    row.remove();
    updateGesamtsumme();
} 