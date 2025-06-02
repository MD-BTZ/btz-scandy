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

// Funktion zum Hinzufügen einer neuen Materialzeile
function addMaterialRow() {
    console.log('Materialzeile hinzufügen');
    const tbody = document.querySelector('#materialTable tbody');
    const newRow = document.createElement('tr');
    newRow.className = 'material-row';
    newRow.innerHTML = `
        <td><input type="text" class="input input-bordered w-full material-input" placeholder="Material"></td>
        <td><input type="number" class="input input-bordered w-full menge-input" placeholder="Menge" min="0" step="0.01" onchange="updateMaterialSum(this)"></td>
        <td><input type="number" class="input input-bordered w-full einzelpreis-input" placeholder="Einzelpreis" min="0" step="0.01" onchange="updateMaterialSum(this)"></td>
        <td><input type="number" class="input input-bordered w-full summe-input" placeholder="Summe" readonly></td>
        <td>
            <button type="button" class="btn btn-error btn-sm" onclick="deleteRow(this)">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    tbody.appendChild(newRow);
}

// Funktion zum Hinzufügen einer neuen Arbeitszeile
function addArbeitRow() {
    console.log('Arbeitszeile hinzufügen');
    const tbody = document.querySelector('#arbeitTable tbody');
    const newRow = document.createElement('tr');
    newRow.className = 'arbeit-row';
    newRow.innerHTML = `
        <td><input type="text" class="input input-bordered w-full arbeit-input" placeholder="Arbeit"></td>
        <td><input type="number" class="input input-bordered w-full stunden-input" placeholder="Stunden" min="0" step="0.5" onchange="updateArbeitSum(this)"></td>
        <td><input type="number" class="input input-bordered w-full stundensatz-input" placeholder="Stundensatz" min="0" step="0.01" onchange="updateArbeitSum(this)"></td>
        <td><input type="number" class="input input-bordered w-full summe-input" placeholder="Summe" readonly></td>
        <td>
            <button type="button" class="btn btn-error btn-sm" onclick="deleteRow(this)">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    tbody.appendChild(newRow);
}

// Funktion zum Löschen einer Zeile
function deleteRow(button) {
    const row = button.closest('tr');
        row.remove();
    updateGesamtsumme();
}

// Funktion zum Aktualisieren der Materialsumme
function updateMaterialSum(input) {
    const row = input.closest('tr');
    const menge = parseFloat(row.querySelector('.menge-input').value) || 0;
    const einzelpreis = parseFloat(row.querySelector('.einzelpreis-input').value) || 0;
    const summe = menge * einzelpreis;
    row.querySelector('.summe-input').value = summe.toFixed(2);
    updateGesamtsumme();
}

// Funktion zum Aktualisieren der Arbeitssumme
function updateArbeitSum(input) {
    const row = input.closest('tr');
    const stunden = parseFloat(row.querySelector('.stunden-input').value) || 0;
    const stundensatz = parseFloat(row.querySelector('.stundensatz-input').value) || 0;
    const summe = stunden * stundensatz;
    row.querySelector('.summe-input').value = summe.toFixed(2);
    updateGesamtsumme();
}

// Funktion zum Aktualisieren der Gesamtsumme
function updateGesamtsumme() {
    let materialSum = 0;
    let arbeitSum = 0;

    // Materialsumme berechnen
    document.querySelectorAll('#materialTable .summe-input').forEach(input => {
        materialSum += parseFloat(input.value) || 0;
    });

    // Arbeitssumme berechnen
    document.querySelectorAll('#arbeitTable .summe-input').forEach(input => {
        arbeitSum += parseFloat(input.value) || 0;
    });

    const gesamtSum = materialSum + arbeitSum;
    document.getElementById('gesamtsumme').value = gesamtSum.toFixed(2);
}

// Funktion zum Sammeln der Auftragsdetails
function collectAuftragDetails() {
    const form = document.getElementById('auftragDetailsForm');
    const formData = new FormData(form);
    const data = {};

    // Basis-Formulardaten
    for (let [key, value] of formData.entries()) {
        if (key === 'auftraggeber_intern' || key === 'auftraggeber_extern') {
            data[key] = value === '1';
        } else {
            data[key] = value;
        }
    }

    // Materialliste sammeln
    data.material_list = collectMaterialList();
    
    // Arbeitenliste sammeln
    data.arbeit_list = collectArbeitList();

    // Gesamtsumme hinzufügen
    data.gesamtsumme = parseFloat(document.getElementById('gesamtsumme').value) || 0;

    console.log('Gesammelte Daten:', data);
    return data;
}

// Funktion zum Sammeln der Materialliste
function collectMaterialList() {
    const materialList = [];
    document.querySelectorAll('.material-row').forEach(row => {
        const material = row.querySelector('.material-input').value;
        const menge = parseFloat(row.querySelector('.menge-input').value) || 0;
        const einzelpreis = parseFloat(row.querySelector('.einzelpreis-input').value) || 0;
        
        if (material || menge || einzelpreis) {
            materialList.push({
                material: material,
                menge: menge,
                einzelpreis: einzelpreis
            });
        }
    });
    return materialList;
}

// Funktion zum Sammeln der Arbeitenliste
function collectArbeitList() {
    const arbeitList = [];
    document.querySelectorAll('.arbeit-row').forEach(row => {
        const arbeit = row.querySelector('.arbeit-input').value;
        const stunden = parseFloat(row.querySelector('.stunden-input').value) || 0;
        const stundensatz = parseFloat(row.querySelector('.stundensatz-input').value) || 0;
        
        if (arbeit || stunden || stundensatz) {
            arbeitList.push({
                arbeit: arbeit,
                stunden: stunden,
                stundensatz: stundensatz
            });
        }
    });
    return arbeitList;
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

// Funktion zum Löschen eines Templates
function deleteTemplate(templateId) {
    if (!confirm('Möchten Sie dieses Template wirklich löschen?')) {
        return;
    }
    
    fetch(`/tickets/templates/${templateId}/delete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('success', data.message);
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast('error', data.message || 'Fehler beim Löschen des Templates');
        }
    })
    .catch(error => {
        console.error('Fehler:', error);
        showToast('error', 'Ein Fehler ist aufgetreten');
    });
} 