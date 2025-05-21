console.log('tickets.js wird geladen');

// Prüfe ob wir uns auf einer Ticket-Seite befinden
function isTicketPage() {
    return window.location.pathname.includes('/tickets/') || 
           document.getElementById('auftragDetailsModal') !== null;
}

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
    // Nur initialisieren wenn wir auf einer Ticket-Seite sind
    if (!isTicketPage()) {
        console.log('Keine Ticket-Seite - tickets.js wird nicht initialisiert');
        return;
    }
    
    console.log('DOMContentLoaded Event auf Ticket-Seite');
    
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

    // Initialisiere das Modal nur wenn es existiert
    const auftragDetailsModal = document.getElementById('auftragDetailsModal');
    if (auftragDetailsModal) {
        console.log('Auftragsdetails-Modal gefunden');
        // Warte einen kurzen Moment, um sicherzustellen, dass alle DOM-Elemente geladen sind
        setTimeout(() => {
            initializeAuftragDetailsModal();
        }, 100);
    } else {
        console.log('Auftragsdetails-Modal nicht gefunden');
    }
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
    const data = {
        materialList: [],
        arbeitList: []
    };
    
    // Sammle Materialdaten
    const materialRows = document.querySelectorAll('#materialRows tbody tr');
    materialRows.forEach(row => {
        const material = row.querySelector('input[name="material"]').value;
        const menge = parseFloat(row.querySelector('input[name="menge"]').value) || 0;
        const einzelpreis = parseFloat(row.querySelector('input[name="einzelpreis"]').value) || 0;
        const gesamtpreis = parseFloat(row.querySelector('input[name="gesamtpreis"]').value) || 0;
        
        if (material && (menge > 0 || einzelpreis > 0)) {
            data.materialList.push({
                material: material,
                menge: menge,
                einzelpreis: einzelpreis,
                gesamtpreis: gesamtpreis
            });
        }
    });
    
    // Sammle Arbeitsdaten
    const arbeitRows = document.querySelectorAll('#arbeitRows tbody tr');
    arbeitRows.forEach(row => {
        const arbeit = row.querySelector('input[name="arbeit"]').value;
        const stunden = parseFloat(row.querySelector('input[name="stunden"]').value) || 0;
        const stundensatz = parseFloat(row.querySelector('input[name="stundensatz"]').value) || 0;
        const gesamtpreis = parseFloat(row.querySelector('input[name="gesamtpreis"]').value) || 0;
        
        if (arbeit && (stunden > 0 || stundensatz > 0)) {
            data.arbeitList.push({
                arbeit: arbeit,
                stunden: stunden,
                stundensatz: stundensatz,
                gesamtpreis: gesamtpreis
            });
        }
    });
    
    // Hole die Ticket-ID aus dem Modal
    const modal = document.getElementById('auftragDetailsModal');
    if (modal) {
        data.ticketId = modal.dataset.ticketId;
    }
    
    return data;
}

// Funktion zum Aktualisieren der Materialsumme
function updateSummeMaterial() {
    const rows = document.querySelectorAll('#materialRows tbody tr');
    let summe = 0;
    
    rows.forEach(row => {
        const menge = parseFloat(row.querySelector('input[name="menge"]').value) || 0;
        const einzelpreis = parseFloat(row.querySelector('input[name="einzelpreis"]').value) || 0;
        const gesamtpreis = menge * einzelpreis;
        
        row.querySelector('input[name="gesamtpreis"]').value = gesamtpreis.toFixed(2);
        summe += gesamtpreis;
    });
    
    document.getElementById('summeMaterial').textContent = summe.toFixed(2) + ' €';
    updateGesamtsumme();
}

// Funktion zum Hinzufügen einer neuen Materialzeile
function addMaterialRow() {
    const tbody = document.getElementById('materialRows');
    const newRow = document.createElement('tr');
    newRow.className = 'material-row';
    newRow.innerHTML = `
        <td><input type="text" name="material" class="material-input input input-bordered w-full"></td>
        <td><input type="number" name="menge" class="menge-input input input-bordered w-24" min="0" step="any"></td>
        <td><input type="number" name="einzelpreis" class="einzelpreis-input input input-bordered w-24" min="0" step="any"></td>
        <td><input type="text" name="gesamtpreis" class="input input-bordered w-32" readonly></td>
        <td><button type="button" class="btn btn-error btn-sm delete-material-btn"><i class="fas fa-trash"></i></button></td>
    `;
    
    tbody.appendChild(newRow);
    
    // Event-Listener für die neuen Inputs
    const inputs = newRow.querySelectorAll('.menge-input, .einzelpreis-input');
    inputs.forEach(input => {
        input.addEventListener('input', function() {
            updateSumme(this);
        });
    });
    
    // Event-Listener für den Lösch-Button
    const deleteBtn = newRow.querySelector('.delete-material-btn');
    deleteBtn.addEventListener('click', function() {
        removeMaterialRow(this);
    });
}

// Funktion zum Entfernen einer Materialzeile
function removeMaterialRow(button) {
    const row = button.closest('tr');
    if (row) {
        row.remove();
        updateSummeMaterial();
    }
}

// Funktion zum Hinzufügen einer neuen Arbeitszeile
function addArbeitRow() {
    const tbody = document.getElementById('arbeitenRows');
    const newRow = document.createElement('tr');
    newRow.className = 'arbeit-row';
    newRow.innerHTML = `
        <td><input type="text" name="arbeit" class="arbeit-input input input-bordered w-full"></td>
        <td><input type="number" name="arbeitsstunden" class="arbeitsstunden-input input input-bordered w-24" min="0" step="any"></td>
        <td><input type="text" name="leistungskategorie" class="leistungskategorie-input input input-bordered w-full"></td>
        <td><button type="button" class="btn btn-error btn-sm delete-arbeit-btn"><i class="fas fa-trash"></i></button></td>
    `;
    
    tbody.appendChild(newRow);
    
    // Event-Listener für den Lösch-Button
    const deleteBtn = newRow.querySelector('.delete-arbeit-btn');
    deleteBtn.addEventListener('click', function() {
        removeArbeitRow(this);
    });
}

// Funktion zum Entfernen einer Arbeitszeile
function removeArbeitRow(button) {
    const row = button.closest('tr');
    if (row) {
        row.remove();
    }
}

// Funktion zum Aktualisieren der Summe für eine einzelne Zeile
function updateSumme(input) {
    const row = input.closest('tr');
    const mengeInput = row.querySelector('.menge-input');
    const einzelpreisInput = row.querySelector('.einzelpreis-input');
    const gesamtpreisInput = row.querySelector('input[name="gesamtpreis"]');
    
    if (mengeInput && einzelpreisInput && gesamtpreisInput) {
        const menge = parseFloat(mengeInput.value) || 0;
        const einzelpreis = parseFloat(einzelpreisInput.value) || 0;
        const gesamtpreis = menge * einzelpreis;
        
        gesamtpreisInput.value = gesamtpreis.toFixed(2);
        updateSummeMaterial();
    }
}

function updateSummeArbeit() {
    const rows = document.querySelectorAll('#arbeitRows tbody tr');
    let summe = 0;
    
    rows.forEach(row => {
        const stunden = parseFloat(row.querySelector('input[name="stunden"]').value) || 0;
        const stundensatz = parseFloat(row.querySelector('input[name="stundensatz"]').value) || 0;
        const gesamtpreis = stunden * stundensatz;
        
        row.querySelector('input[name="gesamtpreis"]').value = gesamtpreis.toFixed(2);
        summe += gesamtpreis;
    });
    
    document.getElementById('summeArbeit').textContent = summe.toFixed(2) + ' €';
    updateGesamtsumme();
}

function updateGesamtsumme() {
    const materialSumme = parseFloat(document.getElementById('summeMaterial').textContent) || 0;
    const arbeitSumme = parseFloat(document.getElementById('summeArbeit').textContent) || 0;
    const gesamtsumme = materialSumme + arbeitSumme;
    
    document.getElementById('gesamtsumme').textContent = gesamtsumme.toFixed(2) + ' €';
}

// Zentrale Initialisierungsfunktion für das Modal
function initializeAuftragDetailsModal() {
    console.log('Initialisiere Auftragsdetails-Modal...');
    
    // Event-Listener für Material-Buttons
    const addMaterialBtn = document.getElementById('addMaterialBtn');
    if (addMaterialBtn) {
        addMaterialBtn.addEventListener('click', addMaterialRow);
    }
    
    // Event-Listener für Arbeit-Buttons
    const addArbeitBtn = document.getElementById('addArbeitBtn');
    if (addArbeitBtn) {
        addArbeitBtn.addEventListener('click', addArbeitRow);
    }
    
    // Event-Listener für Lösch-Buttons
    document.querySelectorAll('.delete-material-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            removeMaterialRow(this);
        });
    });
    
    document.querySelectorAll('.delete-arbeit-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            removeArbeitRow(this);
        });
    });
    
    // Event-Listener für Summen-Updates
    document.querySelectorAll('.menge-input, .einzelpreis-input').forEach(input => {
        input.addEventListener('input', function() {
            updateSumme(this);
        });
    });
    
    // Initialisiere die Summen
    updateSummeMaterial();
    updateSummeArbeit();
} 