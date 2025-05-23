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

    // Debug-Namespace
    window.ScanDebug = {
        async testLending() {
            debug('TEST', 'Starting lending test');
            try {
                const testData = {
                    itemData: {
                        type: 'tool',
                        barcode: '12345',
                        amount: 1
                    },
                    workerData: {
                        barcode: '67890'
                    }
                };
                debug('TEST', 'Using test data:', testData);
                
                debug('TEST', 'Calling processLending...');
                const result = await window.LendingService.processLending(
                    testData.itemData, 
                    testData.workerData
                );
                debug('TEST', 'Lending test completed successfully:', result);
                return result;
            } catch (error) {
                debug('TEST', 'Test failed with error:', {
                    name: error.name,
                    message: error.message,
                    stack: error.stack
                });
                throw error;
            }
        },

        // Debug-Hilfsfunktionen
        checkEnvironment() {
            debug('ENV', 'Checking environment...');
            const checks = {
                fetch: typeof fetch !== 'undefined',
                json: typeof JSON !== 'undefined',
                lendingService: typeof window.LendingService !== 'undefined',
                scanDebug: typeof window.ScanDebug !== 'undefined'
            };
            debug('ENV', 'Environment check results:', checks);
            return checks;
        }
    };

    // LendingService Definition
    window.LendingService = {
        // Neue Funktion für Broadcast-Events
        broadcastChange() {
            // Sende eine Nachricht an alle Tabs
            if (window.BroadcastChannel) {
                const bc = new BroadcastChannel('lending_updates');
                bc.postMessage({ type: 'update' });
            }
            // Aktualisiere die aktuelle Seite
            window.location.reload();
        },

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
        },

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
        },

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
        },

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
    };

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

function addMaterialRow() {
    console.log('Füge neue Materialzeile hinzu');
    const materialList = document.getElementById('materialList');
    if (!materialList) {
        console.error('Materialliste-Container nicht gefunden');
        return;
    }

    const newRow = document.createElement('div');
    newRow.className = 'material-row grid grid-cols-4 gap-2 items-center mb-2';
    newRow.innerHTML = `
        <input type="text" class="material-input input input-bordered" placeholder="Material">
        <input type="number" class="menge-input input input-bordered" placeholder="Menge" min="0" step="0.01">
        <input type="number" class="einzelpreis-input input input-bordered" placeholder="Einzelpreis" min="0" step="0.01">
        <button type="button" class="btn btn-error btn-sm" onclick="removeMaterialRow(this)">
            <i class="fas fa-trash"></i>
        </button>
    `;
    materialList.appendChild(newRow);
}

function removeMaterialRow(button) {
    console.log('Entferne Materialzeile');
    const row = button.closest('.material-row');
    if (row) {
        row.remove();
    }
}

function addArbeitRow() {
    console.log('Füge neue Arbeitszeile hinzu');
    const arbeitList = document.getElementById('arbeitList');
    if (!arbeitList) {
        console.error('Arbeitsliste-Container nicht gefunden');
        return;
    }
    
    const newRow = document.createElement('div');
    newRow.className = 'arbeit-row grid grid-cols-4 gap-2 items-center mb-2';
    newRow.innerHTML = `
        <div class="form-control">
            <input type="text" name="arbeit" class="arbeit-input input input-bordered w-full" placeholder="Arbeit">
        </div>
        <div class="form-control">
            <input type="number" name="arbeitsstunden" class="arbeitsstunden-input input input-bordered w-full" placeholder="Stunden" min="0" step="0.5">
        </div>
        <div class="form-control">
            <input type="text" name="leistungskategorie" class="leistungskategorie-input input input-bordered w-full" placeholder="Leistungskategorie">
        </div>
        <div class="form-control">
            <button type="button" class="btn btn-error btn-sm" onclick="removeArbeitRow(this)">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    arbeitList.appendChild(newRow);
}

function removeArbeitRow(button) {
    console.log('Entferne Arbeitszeile');
    const row = button.closest('.arbeit-row');
    if (row) {
        row.remove();
    }
}

function loadAuftragDetailsModal() {
    console.log('Lade Auftragsdetails-Modal...');
    
    // Extrahiere die Ticket-ID aus der URL
    const urlParts = window.location.pathname.split('/');
    const ticketId = urlParts[urlParts.length - 1];
    
    if (!ticketId) {
        console.error('Keine Ticket-ID gefunden in der URL');
        return;
    }
    
    console.log('Verwende Ticket-ID:', ticketId);
    
    fetch(`/tickets/${ticketId}/auftrag-details-modal`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(html => {
            console.log('Modal HTML empfangen');
            const container = document.getElementById('auftragDetailsModalContainer');
            if (!container) {
                console.error('Modal Container nicht gefunden!');
                return;
            }
            
            container.innerHTML = html;
            const modal = document.getElementById('auftragDetailsModal');
            if (!modal) {
                console.error('Modal Element nicht gefunden!');
                return;
            }
            
            console.log('Öffne Modal...');
            modal.showModal();
            
            // Event-Listener für das Formular
            const form = document.getElementById('auftragDetailsForm');
            if (!form) {
                console.error('Formular nicht gefunden!');
                return;
            }
            
            // Event-Listener für Material- und Arbeitszeilen
            const addMaterialBtn = document.getElementById('addMaterialBtn');
            if (addMaterialBtn) {
                addMaterialBtn.addEventListener('click', addMaterialRow);
            }
            
            const addArbeitBtn = document.getElementById('addArbeitBtn');
            if (addArbeitBtn) {
                addArbeitBtn.addEventListener('click', addArbeitRow);
            }
            
            // Initialisiere bestehende Zeilen
            const materialList = document.getElementById('materialList');
            if (materialList) {
                materialList.querySelectorAll('.material-row').forEach(row => {
                    const deleteBtn = row.querySelector('.btn-error');
                    if (deleteBtn) {
                        deleteBtn.addEventListener('click', () => removeMaterialRow(deleteBtn));
                    }
                });
            }
            
            const arbeitList = document.getElementById('arbeitList');
            if (arbeitList) {
                arbeitList.querySelectorAll('.arbeit-row').forEach(row => {
                    const deleteBtn = row.querySelector('.btn-error');
                    if (deleteBtn) {
                        deleteBtn.addEventListener('click', () => removeArbeitRow(deleteBtn));
                    }
                });
            }
            
            console.log('Initialisiere Formular-Event-Listener');
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                console.log('Formular abgesendet');
                
                // Formulardaten sammeln
                const formData = new FormData(form);
                const jsonData = {};
                
                // Basis-Formulardaten
                for (let [key, value] of formData.entries()) {
                    if (key === 'auftraggeber_intern' || key === 'auftraggeber_extern') {
                        jsonData[key] = value === '1';
                    } else if (key.endsWith('[]')) {
                        // Array-Felder
                        const baseKey = key.slice(0, -2);
                        if (!jsonData[baseKey]) {
                            jsonData[baseKey] = [];
                        }
                        jsonData[baseKey].push(value);
                    } else {
                        jsonData[key] = value;
                    }
                }
                
                // Materialliste sammeln
                const materialList = [];
                document.querySelectorAll('.material-row').forEach(row => {
                    const material = row.querySelector('.material-input')?.value;
                    const menge = parseFloat(row.querySelector('.menge-input')?.value) || 0;
                    const einzelpreis = parseFloat(row.querySelector('.einzelpreis-input')?.value) || 0;
                    
                    if (material || menge || einzelpreis) {
                        materialList.push({
                            material: material,
                            menge: menge,
                            einzelpreis: einzelpreis
                        });
                    }
                });
                
                // Arbeitsliste sammeln
                const arbeitList = [];
                document.querySelectorAll('.arbeit-row').forEach(row => {
                    const arbeit = row.querySelector('.arbeit-input')?.value;
                    const arbeitsstunden = parseFloat(row.querySelector('.arbeitsstunden-input')?.value) || 0;
                    const leistungskategorie = row.querySelector('.leistungskategorie-input')?.value;
                    
                    if (arbeit && (arbeitsstunden > 0 || leistungskategorie)) {
                        arbeitList.push({
                            arbeit: arbeit,
                            arbeitsstunden: arbeitsstunden,
                            leistungskategorie: leistungskategorie
                        });
                    }
                });
                
                jsonData.material_list = materialList;
                jsonData.arbeit_list = arbeitList;
                
                console.log('Sende Daten:', jsonData);
                
                // AJAX-Request senden
                fetch(`/tickets/${ticketId}/update`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify(jsonData)
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Antwort erhalten:', data);
                    if (data.success) {
                        modal.close();
                        window.location.reload();
                    } else {
                        alert('Fehler beim Speichern: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Fehler beim Speichern:', error);
                    alert('Ein Fehler ist aufgetreten beim Speichern der Daten.');
                });
            });
        })
        .catch(error => {
            console.error('Fehler beim Laden des Modals:', error);
            alert('Ein Fehler ist aufgetreten beim Laden des Modals.');
        });
} 