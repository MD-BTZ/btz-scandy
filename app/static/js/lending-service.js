// Sofort ausgeführte Funktion mit Debug-Logging
(function() {
    console.log('=== LENDING SERVICE INITIALIZATION START ===');
    console.log('Script location:', document.currentScript?.src || 'Unknown location');
    
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

// Event-Listener für Rückgabe-Buttons
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initialisiere Rückgabe-Buttons');
    const returnButtons = document.querySelectorAll('[data-barcode]');
    returnButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const barcode = button.getAttribute('data-barcode');
            console.log('Rückgabe-Button geklickt für Barcode:', barcode);
            if (barcode) {
                window.LendingService.returnItem(barcode);
            } else {
                console.error('Kein Barcode gefunden für Button:', button);
            }
        });
    });
}); 