// Lending Service - Zentrale Verwaltung für Ausleihe/Rückgabe
(function() {
    'use strict';

    // Utility-Funktionen
    function log(message, data = null) {
        // Logging deaktiviert für Produktion
    }

    // Service-Initialisierung
    function initializeLendingService() {
        log('=== LENDING SERVICE INITIALIZATION START ===');
        log('Script location:', document.currentScript?.src || 'Unknown location');
        
        // Event-Listener für Rückgabe-Buttons
        initializeReturnButtons();
        
        // Event-Listener für Ausleihe-Buttons
        initializeLendButtons();
        
        // Event-Listener für Material-Entnahme
        initializeMaterialConsumption();
        
        // Event-Listener für Arbeitszeiten
        initializeWorkTimeTracking();
        
        log('=== LENDING SERVICE INITIALIZATION COMPLETE ===');
    }

    // Rückgabe-Funktionalität
    function returnTool(barcode, button = null) {
        log('Starte Rückgabe für:', barcode);
        
        // Bestätigung in einem separaten Task
        Promise.resolve().then(() => {
            if (!confirm('Möchten Sie dieses Werkzeug wirklich zurückgeben?')) {
                if (button) {
                    button.disabled = false;
                    button.style.opacity = '1';
                }
                return;
            }

            // Fetch in einem separaten Task
            Promise.resolve().then(() => {
                fetch('/api/lending/return', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_barcode: barcode
                    })
                })
                .then(response => response.json())
                .then(result => {
                    log('Rückgabe Ergebnis:', result);
                    if (result.success) {
                        showToast('success', 'Werkzeug erfolgreich zurückgegeben');
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        showToast('error', result.message || 'Fehler bei der Rückgabe');
                        if (button) {
                            button.disabled = false;
                            button.style.opacity = '1';
                        }
                    }
                })
                .catch(error => {
                    showToast('error', 'Ein Fehler ist aufgetreten');
                    if (button) {
                        button.disabled = false;
                        button.style.opacity = '1';
                    }
                });
            });
        });
    }

    // Ausleihe-Funktionalität
    function lendTool(toolBarcode, workerBarcode) {
        fetch('/api/lending/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tool_barcode: toolBarcode,
                worker_barcode: workerBarcode,
                action: 'lend'
            })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showToast('success', 'Werkzeug erfolgreich ausgeliehen');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showToast('error', result.message || 'Fehler bei der Ausleihe');
            }
        })
        .catch(error => {
            showToast('error', 'Ein Fehler ist aufgetreten');
        });
    }

    // Material-Verbrauch
    function consumeMaterial(materialBarcode, workerBarcode, quantity) {
        fetch('/api/lending/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                item_barcode: materialBarcode,
                worker_barcode: workerBarcode,
                action: 'consume',
                item_type: 'consumable',
                quantity: quantity
            })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showToast('success', 'Material erfolgreich entnommen');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showToast('error', result.message || 'Fehler bei der Materialentnahme');
            }
        })
        .catch(error => {
            showToast('error', 'Ein Fehler ist aufgetreten');
        });
    }

    // Event-Listener für Rückgabe-Buttons
    function initializeReturnButtons() {
        log('Initialisiere Event-Listener');
        
        // Event-Delegation statt individuelle Event-Listener
        document.addEventListener('click', function(e) {
            const button = e.target.closest('[data-action="return"]');
            if (!button) return;
            
            e.preventDefault();
            e.stopPropagation();
            
            const barcode = button.dataset.barcode;
            if (!barcode) return;
            
            // Verhindere mehrfache Klicks
            if (button.disabled) return;
            
            button.disabled = true;
            button.style.opacity = '0.6';
            
            // Sofortige visuelle Rückmeldung
            requestAnimationFrame(() => {
                returnTool(barcode, button);
            });
        });
    }

    // Event-Listener für Ausleihe-Buttons
    function initializeLendButtons() {
        function addLendButtonListeners() {
            const lendButtons = document.querySelectorAll('[data-action="lend"]');
            
            lendButtons.forEach(button => {
                const barcode = button.dataset.barcode;
                log('Initialisiere Button mit Barcode:', barcode);
                
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    const workerBarcode = prompt('Bitte geben Sie den Mitarbeiter-Barcode ein:');
                    if (workerBarcode) {
                        lendTool(barcode, workerBarcode);
                    }
                });
            });
        }

        addLendButtonListeners();
    }

    // Material-Verbrauch Event-Listener
    function initializeMaterialConsumption() {
        // Material-Zeile hinzufügen
        window.addMaterialRow = function() {
            log('Füge neue Materialzeile hinzu');
            const materialContainer = document.getElementById('materialContainer');
            if (!materialContainer) return;

            const materialRow = document.createElement('div');
            materialRow.className = 'material-row flex gap-2 mb-2';
            materialRow.innerHTML = `
                <input type="text" name="material_barcode[]" placeholder="Material-Barcode" class="input input-bordered flex-1" required>
                <input type="number" name="material_quantity[]" placeholder="Menge" class="input input-bordered w-24" min="1" value="1" required>
                <button type="button" class="btn btn-error btn-sm" onclick="removeMaterialRow(this)">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            materialContainer.appendChild(materialRow);
        };

        // Material-Zeile entfernen
        window.removeMaterialRow = function(button) {
            log('Entferne Materialzeile');
            button.closest('.material-row').remove();
        };
    }

    // Arbeitszeiten Event-Listener
    function initializeWorkTimeTracking() {
        // Arbeitszeit-Zeile hinzufügen
        window.addWorkTimeRow = function() {
            log('Füge neue Arbeitszeile hinzu');
            const workTimeContainer = document.getElementById('workTimeContainer');
            if (!workTimeContainer) return;

            const workTimeRow = document.createElement('div');
            workTimeRow.className = 'work-time-row flex gap-2 mb-2';
            workTimeRow.innerHTML = `
                <input type="date" name="work_date[]" class="input input-bordered" required>
                <input type="number" name="work_hours[]" placeholder="Stunden" class="input input-bordered w-24" min="0.5" step="0.5" value="8" required>
                <input type="text" name="work_description[]" placeholder="Beschreibung" class="input input-bordered flex-1" required>
                <button type="button" class="btn btn-error btn-sm" onclick="removeWorkTimeRow(this)">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            workTimeContainer.appendChild(workTimeRow);
        };

        // Arbeitszeit-Zeile entfernen
        window.removeWorkTimeRow = function(button) {
            log('Entferne Arbeitszeile');
            button.closest('.work-time-row').remove();
        };
    }

    // Auftragsdetails speichern
    window.saveAuftragDetails = function(ticketId) {
        log('Leite zur Auftragsdetails-Seite weiter...');
        
        // Sammle alle Formulardaten
        const formData = new FormData();
        
        // Material-Daten
        const materialBarcodes = document.querySelectorAll('input[name="material_barcode[]"]');
        const materialQuantities = document.querySelectorAll('input[name="material_quantity[]"]');
        
        for (let i = 0; i < materialBarcodes.length; i++) {
            if (materialBarcodes[i].value && materialQuantities[i].value) {
                formData.append('material_barcode[]', materialBarcodes[i].value);
                formData.append('material_quantity[]', materialQuantities[i].value);
            }
        }
        
        // Arbeitszeit-Daten
        const workDates = document.querySelectorAll('input[name="work_date[]"]');
        const workHours = document.querySelectorAll('input[name="work_hours[]"]');
        const workDescriptions = document.querySelectorAll('input[name="work_description[]"]');
        
        for (let i = 0; i < workDates.length; i++) {
            if (workDates[i].value && workHours[i].value && workDescriptions[i].value) {
                formData.append('work_date[]', workDates[i].value);
                formData.append('work_hours[]', workHours[i].value);
                formData.append('work_description[]', workDescriptions[i].value);
            }
        }
        
        // Speichere Daten
        fetch(`/tickets/${ticketId}/auftrag-details`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showToast('success', 'Auftragsdetails erfolgreich gespeichert');
                setTimeout(() => {
                    window.location.href = `/tickets/${ticketId}/auftrag-details`;
                }, 1000);
            } else {
                showToast('error', result.message || 'Fehler beim Speichern');
            }
        })
        .catch(error => {
            showToast('error', 'Ein Fehler ist aufgetreten');
        });
    };

    // Toast-Funktion
    function showToast(type, message) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} fixed bottom-4 right-4 z-50`;
        toast.innerHTML = `
            <div class="alert alert-${type}">
                <span>${message}</span>
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    // Globale returnItem-Funktion für manuelle Ausleihe
    window.LendingService = {
        returnItem: function(barcode) {
            return new Promise((resolve, reject) => {
                // Verhindere mehrfache Klicks
                const button = event?.target?.closest('[data-action="return"]');
                if (button) {
                    button.disabled = true;
                    button.style.opacity = '0.6';
                }
                
                // Bestätigung in einem separaten Task
                Promise.resolve().then(() => {
                    if (!confirm('Möchten Sie dieses Werkzeug wirklich zurückgeben?')) {
                        if (button) {
                            button.disabled = false;
                            button.style.opacity = '1';
                        }
                        resolve(false);
                        return;
                    }

                    // Fetch in einem separaten Task
                    Promise.resolve().then(() => {
                        fetch('/api/lending/return', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'
                            },
                            body: JSON.stringify({
                                tool_barcode: barcode,
                                worker_barcode: null  // Wird vom Server automatisch ermittelt
                            })
                        })
                        .then(response => response.json())
                        .then(result => {
                            if (result.success) {
                                showToast('success', 'Werkzeug erfolgreich zurückgegeben');
                                resolve(true);
                            } else {
                                showToast('error', result.message || 'Fehler bei der Rückgabe');
                                if (button) {
                                    button.disabled = false;
                                    button.style.opacity = '1';
                                }
                                resolve(false);
                            }
                        })
                        .catch(error => {
                            console.error('Fehler bei der Rückgabe:', error);
                            showToast('error', 'Ein Fehler ist aufgetreten');
                            if (button) {
                                button.disabled = false;
                                button.style.opacity = '1';
                            }
                            resolve(false);
                        });
                    });
                });
            });
        }
    };

    // Service starten wenn DOM geladen ist
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeLendingService);
    } else {
        initializeLendingService();
    }

})();