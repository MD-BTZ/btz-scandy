// Hilfsfunktion für formatierte Debug-Ausgaben
function debug(area, message, data = null) {
    const timestamp = new Date().toISOString().split('T')[1];  // Nur die Uhrzeit
    const baseMsg = `[${timestamp}] [${area}] ${message}`;
    if (data) {
        console.log(baseMsg, data);
    } else {
        console.log(baseMsg);
    }
}

// Sofort ausgeführte Funktion mit Debug-Logging
(function() {
    console.log('=== LENDING SERVICE INITIALIZATION START ===');
    console.log('Script location:', document.currentScript?.src || 'Unknown location');
    
    debug('INIT', 'Starting LendingService initialization');

    // LendingService-Klasse definieren
    class LendingService {
        constructor() {
            this.isInitialized = false;
            this.scanDebug = false; // Debug-Modus deaktiviert
        }

        // Neue Funktion für Broadcast-Events
        broadcastChange() {
            // Sende eine Nachricht an alle Tabs
            if (window.BroadcastChannel) {
                const bc = new BroadcastChannel('lending_updates');
                bc.postMessage({ type: 'update' });
            }
            // Aktualisiere die aktuelle Seite
            window.location.reload();
        }

        async processLending(itemData, workerData) {
            debug('LENDING', 'ProcessLending called with:', { itemData, workerData });
            
            try {
                // Eingabevalidierung
                if (!itemData) {
                    debug('LENDING', 'Error: No item data provided');
                    throw new Error('Keine Artikeldaten vorhanden');
                }
                if (!workerData) {
                    debug('LENDING', 'Error: No worker data provided');
                    throw new Error('Keine Mitarbeiterdaten vorhanden');
                }

                const requestData = {
                    tool_barcode: itemData.barcode,
                    worker_barcode: workerData.barcode,
                    action: itemData.type === 'tool' ? 'lend' : 'consume',
                    quantity: itemData.amount || 1
                };
                
                debug('LENDING', 'Prepared request data:', requestData);

                const response = await fetch('/admin/manual-lending', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                });

                debug('LENDING', 'Response received:', {
                    status: response.status,
                    statusText: response.statusText
                });

                const result = await response.json();
                debug('LENDING', 'Parsed response:', result);
                
                if (result.success) {
                    showToast('success', result.message || 'Aktion erfolgreich durchgeführt');
                    this.broadcastChange();
                    return true;
                } else {
                    showToast('error', result.message || 'Ein Fehler ist aufgetreten');
                    return false;
                }

            } catch (error) {
                debug('LENDING', 'Error in processLending:', error);
                showToast('error', `Fehler: ${error.message}`);
                return false;
            }
        }

        async returnItem(barcode) {
            try {
                debug('RETURN', 'ReturnItem called with barcode:', barcode);
                
                const requestData = {
                    item_barcode: barcode,
                    action: 'return'
                };

                debug('RETURN', 'Sending request data:', requestData);

                const response = await fetch('/admin/manual-lending', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                debug('RETURN', 'Return result:', result);
                
                if (result.success) {
                    showToast('success', result.message || 'Werkzeug erfolgreich zurückgegeben');
                    this.broadcastChange();
                    return true;
                } else {
                    showToast('error', result.message || 'Ein Fehler ist aufgetreten');
                    return false;
                }
            } catch (error) {
                debug('RETURN', 'Error in returnItem:', error);
                showToast('error', `Fehler bei der Rückgabe: ${error.message}`);
                return false;
            }
        }

        async returnTool(barcode) {
            debug('RETURN', 'ReturnTool called with barcode:', barcode);
            
            try {
                const response = await fetch('/admin/process_return', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        item_barcode: barcode
                    })
                });

                debug('RETURN', 'Response received:', {
                    status: response.status,
                    statusText: response.statusText
                });

                const result = await response.json();
                debug('RETURN', 'Return result:', result);
                
                if (!response.ok) {
                    throw new Error(result.message || 'Fehler bei der Rückgabe');
                }

                // Seite neu laden nach erfolgreicher Rückgabe
                location.reload();
                return result;

            } catch (error) {
                debug('RETURN', 'Error in returnTool:', error);
                throw error;
            }
        }

        async lendItem(toolBarcode, workerBarcode) {
            try {
                const requestData = {
                    tool_barcode: toolBarcode,
                    worker_barcode: workerBarcode,
                    action: 'lend'
                };

                const response = await fetch('/admin/manual-lending', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });

                const result = await response.json();
                
                if (result.success) {
                    this.broadcastChange();
                    showToast('success', result.message || 'Werkzeug erfolgreich ausgeliehen');
                    return true;
                } else {
                    showToast('error', result.message || 'Ein Fehler ist aufgetreten');
                    return false;
                }
            } catch (error) {
                console.error('Fehler bei der Ausleihe:', error);
                showToast('error', `Fehler bei der Ausleihe: ${error.message}`);
                return false;
            }
        }
    }

    // Initialisierung abschließen
    debug('INIT', 'LendingService initialization completed');
    debug('INIT', 'Available endpoints:', {
        processLending: '/admin/process_lending',
        processReturn: '/admin/process_return'
    });

    // Umgebung überprüfen
    window.ScanDebug.checkEnvironment();

    console.log('=== LENDING SERVICE INITIALIZATION COMPLETE ===');
})();

// Manual Lending Namespace
window.ManualLending = {
    selectedItem: null,
    selectedWorker: null,

    updateConfirmButton() {
        const confirmButton = document.getElementById('confirmButton');
        if (confirmButton) {
            confirmButton.disabled = !(this.selectedItem && this.selectedWorker);
        }
    },

    async returnTool(barcode) {
        try {
            console.log('Starte Rückgabe für:', barcode);
            
            const response = await fetch('/admin/manual-lending', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    item_barcode: barcode,
                    action: 'return'
                })
            });

            const result = await response.json();
            console.log('Rückgabe Ergebnis:', result);
            
            if (result.success) {
                showToast('success', result.message || 'Werkzeug erfolgreich zurückgegeben');
                // Broadcast-Event senden und Seite neu laden
                if (window.LendingService) {
                    window.LendingService.broadcastChange();
                } else {
                    window.location.reload();
                }
            } else {
                showToast('error', result.message || 'Ein Fehler ist aufgetreten');
            }
        } catch (error) {
            console.error('Fehler bei der Rückgabe:', error);
            showToast('error', `Fehler bei der Rückgabe: ${error.message}`);
        }
    },

    switchType(type) {
        document.querySelectorAll('[data-tab]').forEach(btn => {
            btn.classList.toggle('btn-active', btn.dataset.tab === type);
        });
        
        document.getElementById('toolsList').classList.toggle('hidden', type !== 'tools');
        document.getElementById('consumablesList').classList.toggle('hidden', type !== 'consumables');
        
        const amountField = document.getElementById('amountField');
        if (type === 'consumables') {
            amountField.classList.remove('hidden');
        } else {
            amountField.classList.add('hidden');
        }
        
        document.getElementById('itemSearch').value = '';
        document.getElementById('itemDetails').classList.add('hidden');
        document.getElementById('previewItem').textContent = 'Kein Artikel ausgewählt';
        this.selectedItem = null;
        this.updateConfirmButton();
    },

    selectItem(value) {
        const [type, id, barcode, name] = value.split(':');
        this.selectedItem = { type, id, barcode, name };
        document.getElementById('previewItem').textContent = `${name} (${barcode})`;
        
        const amountField = document.getElementById('amountField');
        if (type === 'consumable') {
            amountField.classList.remove('hidden');
        } else {
            amountField.classList.add('hidden');
        }
        this.updateConfirmButton();
    },

    selectWorker(value) {
        const [type, id, barcode, name] = value.split(':');
        this.selectedWorker = { 
            id, 
            barcode: barcode,
            name 
        };
        document.getElementById('previewWorker').textContent = `${name} (${barcode})`;
        this.updateConfirmButton();
    },

    async processLending() {
        try {
            if (!this.selectedItem || !this.selectedWorker) {
                showToast('error', 'Bitte Artikel und Mitarbeiter auswählen');
                return;
            }

            const itemData = {
                type: this.selectedItem.type,
                barcode: this.selectedItem.barcode,
                amount: this.selectedItem.type === 'consumable' 
                        ? parseInt(document.getElementById('amount').value) || 1 
                        : 1
            };

            const workerData = {
                barcode: this.selectedWorker.barcode
            };

            const result = await window.LendingService.processLending(itemData, workerData);

            if (result) {
                window.location.reload();
            }

        } catch (error) {
            console.error('Error in processLending:', error);
            showToast('error', 'Fehler bei der Ausleihe: ' + error.message);
        }
    }
}; 

function manualLending(event) {
    event.preventDefault();
    
    const toolBarcode = document.getElementById('toolBarcode').value;
    const workerBarcode = document.getElementById('workerBarcode').value;
    
    if (!toolBarcode || !workerBarcode) {
        alert('Bitte beide Barcodes eingeben');
        return;
    }
    
    const formData = new FormData();
    formData.append('tool_barcode', toolBarcode);
    formData.append('worker_barcode', workerBarcode);
    
    fetch('/tools/manual_lending', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Ausleihe erfolgreich');
            window.location.reload();
        } else {
            alert('Fehler: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Fehler bei der Ausleihe');
    });
} 

function processLending(barcode) {
    // ... existing code ...
    fetch('/admin/lending/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            window.dispatchEvent(new Event('toolLent'));
        } else {
            showToast(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Ein Fehler ist aufgetreten', 'error');
    });
}

function processReturn(barcode) {
    // ... existing code ...
    fetch('/admin/lending/return', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            window.dispatchEvent(new Event('toolReturned'));
        } else {
            showToast(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Ein Fehler ist aufgetreten', 'error');
    });
} 

// Funktion zum Behandeln der Rückgabe
function handleReturn(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const button = e.currentTarget;
    const barcode = button.dataset.barcode;
    
    if (!barcode) {
        console.error('Kein Barcode gefunden für Button:', button);
        return;
    }
    
    console.log('Rückgabe-Button geklickt für Barcode:', barcode);
    
    if (confirm('Möchten Sie dieses Werkzeug wirklich zurückgeben?')) {
        window.LendingService.returnItem(barcode)
            .then(success => {
                if (success) {
                    window.location.reload();
                }
            })
            .catch(error => {
                console.error('Fehler bei der Rückgabe:', error);
                showToast('error', `Fehler bei der Rückgabe: ${error.message}`);
            });
    }
}

// Funktion zum Initialisieren der Rückgabe-Buttons
function initializeReturnButtons() {
    console.log('Initialisiere Event-Listener');
    
    // Warte auf DOM-Änderungen
    const observer = new MutationObserver((mutations) => {
        // Erweiterte Button-Selektoren
        const returnButtons = document.querySelectorAll(
            'button[data-barcode], .btn-error[data-barcode], [data-barcode], .return-btn'
        );
        console.log('Gefundene Rückgabe-Buttons:', returnButtons.length);
        
        if (returnButtons.length > 0) {
            returnButtons.forEach(button => {
                if (!button.hasAttribute('data-initialized')) {
                    console.log('Initialisiere Button mit Barcode:', button.dataset.barcode);
                    button.setAttribute('data-initialized', 'true');
                    button.addEventListener('click', handleReturn);
                }
            });
            observer.disconnect(); // Stoppe den Observer, wenn Buttons gefunden wurden
        }
    });

    // Starte Beobachtung des gesamten Dokuments
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Initiale Prüfung
    const returnButtons = document.querySelectorAll(
        'button[data-barcode], .btn-error[data-barcode], [data-barcode], .return-btn'
    );
    if (returnButtons.length > 0) {
        returnButtons.forEach(button => {
            if (!button.hasAttribute('data-initialized')) {
                console.log('Initialisiere Button mit Barcode:', button.dataset.barcode);
                button.setAttribute('data-initialized', 'true');
                button.addEventListener('click', handleReturn);
            }
        });
        observer.disconnect();
    } else {
        console.log('Keine Rückgabe-Buttons gefunden, warte auf DOM-Änderungen...');
    }
}

// Warte auf DOM-Content-Loaded und initialisiere dann die Buttons
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeReturnButtons);
} else {
    initializeReturnButtons();
} 

function updateRowSum(row) {
    const menge = parseFloat(row.querySelector('.menge-input')?.value) || 0;
    const einzelpreis = parseFloat(row.querySelector('.einzelpreis-input')?.value) || 0;
    const gesamtpreis = menge * einzelpreis;
    const gesamtpreisInput = row.querySelector('input[name="gesamtpreis"]');
    if (gesamtpreisInput) {
        gesamtpreisInput.value = gesamtpreis.toFixed(2);
    }
    updateSummeMaterial();
    updateGesamtsumme();
}

function addMaterialRow() {
    console.log('Füge neue Materialzeile hinzu');
    const materialRows = document.getElementById('materialRows');
    if (!materialRows) {
        console.error('Tabellenkörper für Material nicht gefunden');
        return;
    }
    const newRow = document.createElement('tr');
    newRow.className = 'material-row';
    newRow.innerHTML = `
        <td><input type="text" name="material" class="material-input input input-bordered w-full"></td>
        <td><input type="number" name="menge" class="menge-input input input-bordered w-24" min="0" step="any"></td>
        <td><input type="number" name="einzelpreis" class="einzelpreis-input input input-bordered w-24" min="0" step="any"></td>
        <td><input type="text" name="gesamtpreis" class="input input-bordered w-32" readonly></td>
        <td><button type="button" class="btn btn-error btn-sm delete-material-btn"><i class="fas fa-trash"></i></button></td>
    `;
    materialRows.appendChild(newRow);
    
    // Event-Listener für die neuen Inputs
    const mengeInput = newRow.querySelector('.menge-input');
    const einzelpreisInput = newRow.querySelector('.einzelpreis-input');
    
    // Event-Listener für Änderungen
    mengeInput.addEventListener('input', () => updateRowSum(newRow));
    einzelpreisInput.addEventListener('input', () => updateRowSum(newRow));
    
    // Event-Listener für den Lösch-Button
    const deleteBtn = newRow.querySelector('.delete-material-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function() {
            removeMaterialRow(this);
            updateSummeMaterial();
            updateGesamtsumme();
        });
    }
}

function updateSummeMaterial() {
    const rows = document.querySelectorAll('#materialRows tr');
    let summe = 0;
    rows.forEach(row => {
        const gesamtpreis = parseFloat(row.querySelector('input[name="gesamtpreis"]')?.value) || 0;
        summe += gesamtpreis;
    });
    const summeMaterial = document.getElementById('summeMaterial');
    if (summeMaterial) {
        summeMaterial.textContent = summe.toFixed(2) + ' €';
    }
}

function updateGesamtsumme() {
    const summeMaterial = document.getElementById('summeMaterial');
    const summeArbeit = document.getElementById('summeArbeit');
    let material = 0;
    let arbeit = 0;
    
    if (summeMaterial) {
        material = parseFloat(summeMaterial.textContent.replace('€','').replace(',','.').trim()) || 0;
    }
    if (summeArbeit) {
        arbeit = parseFloat(summeArbeit.textContent.replace('h','').replace(',','.').trim()) || 0;
    }
    
    const gesamtsumme = material + arbeit;
    const gesamtsummeElem = document.getElementById('gesamtsumme');
    if (gesamtsummeElem) {
        gesamtsummeElem.textContent = gesamtsumme.toFixed(2) + ' €';
    }
}

function removeMaterialRow(button) {
    console.log('Entferne Materialzeile');
    const row = button.closest('.material-row');
    if (row) {
        row.remove();
        updateSummeMaterial();
        updateGesamtsumme();
    }
}

function addArbeitRow() {
    console.log('Füge neue Arbeitszeile hinzu');
    const arbeitenRows = document.getElementById('arbeitenRows');
    if (!arbeitenRows) {
        console.error('Tabellenkörper für Arbeiten nicht gefunden');
        return;
    }
    const newRow = document.createElement('tr');
    newRow.className = 'arbeit-row';
    newRow.innerHTML = `
        <td><input type="text" name="arbeit" class="arbeit-input input input-bordered w-full"></td>
        <td><input type="number" name="arbeitsstunden" class="arbeitsstunden-input input input-bordered w-full" min="0" step="0.5"></td>
        <td><input type="text" name="leistungskategorie" class="leistungskategorie-input input input-bordered w-full"></td>
        <td><button type="button" class="btn btn-error btn-sm delete-arbeit-btn"><i class="fas fa-trash"></i></button></td>
    `;
    arbeitenRows.appendChild(newRow);
    // Event-Listener für den Lösch-Button
    const deleteBtn = newRow.querySelector('.delete-arbeit-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function() {
            removeArbeitRow(this);
            updateSummeArbeit();
            updateGesamtsumme();
        });
    }
    // Event-Listener für Arbeitsstunden-Eingabe
    const arbeitsstundenInput = newRow.querySelector('.arbeitsstunden-input');
    if (arbeitsstundenInput) {
        arbeitsstundenInput.addEventListener('input', function() {
            updateSummeArbeit();
            updateGesamtsumme();
        });
    }
}

function updateSummeArbeit() {
    const rows = document.querySelectorAll('#arbeitenRows tr');
    let summe = 0;
    rows.forEach(row => {
        const arbeitsstunden = parseFloat(row.querySelector('.arbeitsstunden-input')?.value) || 0;
        summe += arbeitsstunden;
    });
    const summeArbeit = document.getElementById('summeArbeit');
    if (summeArbeit) {
        summeArbeit.textContent = summe.toFixed(2) + ' h';
    }
}

function removeArbeitRow(button) {
    console.log('Entferne Arbeitszeile');
    const row = button.closest('.arbeit-row');
    if (row) {
        row.remove();
    }
}

function initializeMaterialRowEvents(row) {
    const mengeInput = row.querySelector('.menge-input');
    const einzelpreisInput = row.querySelector('.einzelpreis-input');
    const deleteBtn = row.querySelector('.delete-material-btn');
    
    if (mengeInput) {
        mengeInput.addEventListener('input', () => updateRowSum(row));
    }
    if (einzelpreisInput) {
        einzelpreisInput.addEventListener('input', () => updateRowSum(row));
    }
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function() {
            removeMaterialRow(this);
        });
    }
    
    // Initiale Berechnung für die Zeile
    updateRowSum(row);
}

function loadAuftragDetailsModal() {
    console.log('Leite zur Auftragsdetails-Seite weiter...');
    
    // Extrahiere die Ticket-ID aus der URL
    const urlParts = window.location.pathname.split('/');
    const ticketId = urlParts[urlParts.length - 1];
    
    if (!ticketId) {
        console.error('Keine Ticket-ID gefunden in der URL');
        return;
    }
    
    console.log('Verwende Ticket-ID:', ticketId);
    
    // Weiterleitung zur eigenen Auftragsdetails-Seite
    window.location.href = `/tickets/${ticketId}/auftrag-details`;
}