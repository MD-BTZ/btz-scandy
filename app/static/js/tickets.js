

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
    if (confirm('Möchten Sie dieses Ticket wirklich löschen? Es wird in den Papierkorb verschoben.')) {
        fetch(`/tickets/${ticketId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('success', 'Ticket wurde erfolgreich gelöscht');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showToast('error', data.message || 'Fehler beim Löschen des Tickets');
            }
        })
        .catch(error => {
            showToast('error', 'Ein Fehler ist aufgetreten');
        });
    }
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

// Event Listener für DOMContentLoaded, der das Modal und seine Formulare behandelt
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded - Initialisiere Ticket-Funktionen');
    
    // Event-Listener für "Material hinzufügen" - EXAKT wie Arbeit hinzufügen
    const addMaterialBtn = document.getElementById('addMaterialBtn');
    console.log('addMaterialBtn gefunden:', addMaterialBtn);
    if (addMaterialBtn) {
        addMaterialBtn.addEventListener('click', addMaterialRow);
    } else {
        console.log('addMaterialBtn NICHT gefunden!');
    }

    // Event-Listener für "Arbeit hinzufügen" - funktioniert bereits
    const addArbeitBtn = document.getElementById('addArbeitBtn');
    console.log('addArbeitBtn gefunden:', addArbeitBtn);
    if (addArbeitBtn) {
        addArbeitBtn.addEventListener('click', addArbeitRow);
    } else {
        console.log('addArbeitBtn NICHT gefunden!');
    }

    // Event-Listener für bestehende Zeilen initialisieren
    initializeExistingRows();
    
    // Initiale Berechnungen durchführen
    updateSummeMaterial();
    updateSummeArbeit();
    updateGesamtsumme();
    
    // Formular-Event-Listener (nur für AJAX-Requests)
    const form = document.getElementById('ticket_details_form');
    if (form && form.getAttribute('data-ajax') === 'true') {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const data = collectAuftragDetails();
            const ticketId = form.closest('.modal')?.dataset.ticketId || 
                            window.location.pathname.split('/')[2];
        
            fetch(`/tickets/${ticketId}/update-details`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('success', 'Auftragsdetails erfolgreich gespeichert');
                    const modal = document.querySelector('.modal');
                    if (modal) {
                        modal.close();
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        window.location.reload();
                    }
                } else {
                    showToast('error', data.message || 'Fehler beim Speichern');
                }
            })
            .catch(error => {
                console.error('Fehler:', error);
                showToast('error', 'Ein Fehler ist aufgetreten');
            });
        });
    }
});

// Funktion zum Initialisieren bestehender Zeilen
function initializeExistingRows() {
    
    // Materialzeilen
    document.querySelectorAll('#materialRows .material-row').forEach(row => {
        initializeMaterialRowEvents(row);
    });
    
    // Arbeitszeilen
    document.querySelectorAll('#arbeitenRows .arbeit-row').forEach(row => {
        initializeArbeitRowEvents(row);
});
}

// Funktion zum Hinzufügen einer neuen Materialzeile - EXAKT wie addArbeitRow
function addMaterialRow() {
    console.log('addMaterialRow aufgerufen');
    
    const tbody = document.getElementById('materialRows');
    console.log('materialRows tbody gefunden:', tbody);
    
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
    console.log('Neue Materialzeile hinzugefügt');
    initializeMaterialRowEvents(newRow);
}

// Mache die Funktion global verfügbar
window.addMaterialRow = addMaterialRow;

function initializeMaterialRowEvents(row) {
    
    // Event-Listener für Menge und Einzelpreis
    const mengeInput = row.querySelector('.menge-input');
    const einzelpreisInput = row.querySelector('.einzelpreis-input');
    
    if (mengeInput) {
        mengeInput.addEventListener('input', () => {
            
            updateRowSum(row);
        });
    }
    
    if (einzelpreisInput) {
        einzelpreisInput.addEventListener('input', () => {
            
            updateRowSum(row);
        });
    }
    
    // Event-Listener für Löschen-Button
    const deleteBtn = row.querySelector('.delete-material-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => {
            
            row.remove();
            updateSummeMaterial();
            updateGesamtsumme();
        });
    }
    
    // Initiale Berechnung
    updateRowSum(row);
}

// Funktion zum Hinzufügen einer neuen Arbeitszeile
function addArbeitRow() {
    
    const tbody = document.getElementById('arbeitenRows');
    const newRow = document.createElement('tr');
    newRow.className = 'arbeit-row';
    newRow.innerHTML = `
        <td><input type="text" name="arbeit" class="arbeit-input input input-bordered w-full"></td>
        <td><input type="number" name="arbeitsstunden" class="arbeitsstunden-input input input-bordered w-full" min="0" step="0.5"></td>
        <td><input type="text" name="leistungskategorie" class="leistungskategorie-input input input-bordered w-full"></td>
        <td><button type="button" class="btn btn-error btn-sm delete-arbeit-btn"><i class="fas fa-trash"></i></button></td>
    `;
    tbody.appendChild(newRow);
    initializeArbeitRowEvents(newRow);
}

function initializeArbeitRowEvents(row) {
    
    
    // Event-Listener für Arbeitsstunden
    const arbeitsstundenInput = row.querySelector('.arbeitsstunden-input');
    if (arbeitsstundenInput) {
        arbeitsstundenInput.addEventListener('input', () => {
            
            updateSummeArbeit();
            updateGesamtsumme();
        });
    }
    
    // Event-Listener für Löschen-Button
    const deleteBtn = row.querySelector('.delete-arbeit-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => {
            
        row.remove();
            updateSummeArbeit();
            updateGesamtsumme();
        });
    }
}

function updateRowSum(row) {
    
    
    const mengeInput = row.querySelector('.menge-input');
    const einzelpreisInput = row.querySelector('.einzelpreis-input');
    const gesamtpreisInput = row.querySelector('input[name="gesamtpreis"]');
    
    if (!mengeInput || !einzelpreisInput || !gesamtpreisInput) {
        
        return;
    }
    
    const menge = parseFloat(mengeInput.value) || 0;
    const einzelpreis = parseFloat(einzelpreisInput.value) || 0;
    const gesamtpreis = menge * einzelpreis;
    
    
    
    gesamtpreisInput.value = gesamtpreis.toFixed(2);
    
    updateSummeMaterial();
    updateGesamtsumme();
}

function updateSummeMaterial() {
    
    let summe = 0;
    
    document.querySelectorAll('#materialRows .material-row').forEach(row => {
        const gesamtpreisInput = row.querySelector('input[name="gesamtpreis"]');
        if (gesamtpreisInput) {
            const gesamtpreis = parseFloat(gesamtpreisInput.value) || 0;
            summe += gesamtpreis;
            
        }
    });
    
    const summeElement = document.getElementById('summeMaterial');
    if (summeElement) {
        summeElement.textContent = summe.toFixed(2) + ' €';
        console.log('Materialsumme gesetzt auf:', summe.toFixed(2));
    }
    
    updateGesamtsumme();
}

function updateSummeArbeit() {
    
    let summe = 0;
    
    document.querySelectorAll('#arbeitenRows .arbeit-row').forEach(row => {
        const arbeitsstundenInput = row.querySelector('.arbeitsstunden-input');
        if (arbeitsstundenInput) {
            const stunden = parseFloat(arbeitsstundenInput.value) || 0;
            summe += stunden;
            
        }
    });
    
    const summeElement = document.getElementById('summeArbeit');
    if (summeElement) {
        summeElement.textContent = summe.toFixed(2) + ' h';
        console.log('Arbeitssumme gesetzt auf:', summe.toFixed(2));
    }
    
    updateGesamtsumme();
}

function updateGesamtsumme() {
    
    
    const summeMaterialElement = document.getElementById('summeMaterial');
    const gesamtsummeElement = document.getElementById('gesamtsumme');
    
    if (!summeMaterialElement || !gesamtsummeElement) {
        
        return;
    }
    
    const summeMaterialText = summeMaterialElement.textContent;
    const summeMaterial = parseFloat(summeMaterialText.replace(' €', '')) || 0;
    
    
    
    gesamtsummeElement.textContent = summeMaterial.toFixed(2) + ' €';
    console.log('Gesamtsumme gesetzt auf:', summeMaterial.toFixed(2));
}

// Daten-Sammelfunktionen
function collectAuftragDetails() {
    const form = document.getElementById('ticket_details_form');
    const formData = new FormData(form);
    const data = {};

    for (let [key, value] of formData.entries()) {
        if (key.endsWith('[]')) {
            let realKey = key.slice(0, -2);
            if (!data[realKey]) {
                data[realKey] = [];
            }
            data[realKey].push(value);
        } else {
            data[key] = value;
        }
    }

    // Verarbeite den Auftraggeber-Typ (Radio-Button)
    const auftraggeberTyp = data.auftraggeber_typ || '';
    data.auftraggeber_intern = auftraggeberTyp === 'intern';
    data.auftraggeber_extern = auftraggeberTyp === 'extern';
    
    data.material_list = collectMaterialList();
    data.arbeit_list = collectArbeitList();

    return data;
}

function collectMaterialList() {
    const materialList = [];
    document.querySelectorAll('#materialRows .material-row').forEach(row => {
        const material = row.querySelector('.material-input')?.value.trim();
        const menge = parseFloat(row.querySelector('.menge-input')?.value) || 0;
        const einzelpreis = parseFloat(row.querySelector('.einzelpreis-input')?.value) || 0;
        
        // Sammle alle Zeilen, auch leere (für das Hinzufügen neuer Zeilen)
        materialList.push({
            material: material,
            menge: menge,
            einzelpreis: einzelpreis
        });
    });
    return materialList;
}

function collectArbeitList() {
    const arbeitList = [];
    document.querySelectorAll('#arbeitenRows .arbeit-row').forEach(row => {
        const arbeit = row.querySelector('.arbeit-input')?.value.trim();
        const arbeitsstunden = parseFloat(row.querySelector('.arbeitsstunden-input')?.value) || 0;
        const leistungskategorie = row.querySelector('.leistungskategorie-input')?.value.trim();
        
        // Sammle alle Zeilen, auch leere (für das Hinzufügen neuer Zeilen)
        arbeitList.push({
            arbeit: arbeit,
            arbeitsstunden: arbeitsstunden,
            leistungskategorie: leistungskategorie
        });
    });
    return arbeitList;
} 
