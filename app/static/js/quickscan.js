const QuickScan = {
    currentStep: 1,
    scannedItem: null,
    scannedWorker: null,
    confirmationBarcode: null,
    lastKeyTime: 0,
    keyBuffer: '',
    isInitialized: false,
    
    // Neuer Zwischenspeicher für den aktuellen Prozess
    currentProcess: {
                item: null,
                worker: null,
        action: null,
        confirmed: false
    },
            
    init() {
        if (this.isInitialized) {
            this.reset();
        } else {
            this.setupEventListeners();
            this.isInitialized = true;
        }
        this.focusCurrentInput();
        console.log('QuickScan initialisiert');
    },

        setupEventListeners() {
        // Event-Listener für Item-Scan
            const itemInput = document.getElementById('itemScanInput');
            if (itemInput) {
            itemInput.addEventListener('keydown', (e) => {
                this.handleKeyInput(e, itemInput);
            });

            // Event-Listener für Bestätigungs-Button
            const confirmItemBtn = document.getElementById('confirmItemBtn');
            if (confirmItemBtn) {
                confirmItemBtn.addEventListener('click', () => {
                    this.confirmItem();
                });
            }

            // Event-Listener für Rückgängig-Button
            const undoItemBtn = document.getElementById('undoItemBtn');
            if (undoItemBtn) {
                undoItemBtn.addEventListener('click', () => {
                    this.undoLastInput('item');
                });
            }

            itemInput.addEventListener('input', (e) => {
                console.log('Input Event:', e.target.value);
                if (e.target.value) {
                    this.handleScannerInput(e.target.value, itemInput);
                        e.target.value = '';
                    }
                });

            // Fokus wiederherstellen bei Klick außerhalb
            itemInput.addEventListener('blur', () => {
                if (this.currentStep === 1) {
                    setTimeout(() => this.focusCurrentInput(), 100);
                    }
                });
            }

        // Event-Listener für Worker-Scan
        const workerInput = document.getElementById('workerScanInput');
        if (workerInput) {
            workerInput.addEventListener('keydown', (e) => {
                this.handleKeyInput(e, workerInput);
            });

            // Event-Listener für Bestätigungs-Button
            const confirmWorkerBtn = document.getElementById('confirmWorkerButton');
            if (confirmWorkerBtn) {
                confirmWorkerBtn.addEventListener('click', () => {
                    this.confirmWorker();
                });
            }

            // Event-Listener für Rückgängig-Button
            const undoWorkerBtn = document.getElementById('undoWorkerButton');
            if (undoWorkerBtn) {
                undoWorkerBtn.addEventListener('click', () => {
                    this.undoLastInput('worker');
                });
            }

            workerInput.addEventListener('input', (e) => {
                console.log('Input Event:', e.target.value);
                if (e.target.value) {
                    this.handleScannerInput(e.target.value, workerInput);
                    e.target.value = '';
                }
            });

            // Fokus wiederherstellen bei Klick außerhalb
            workerInput.addEventListener('blur', () => {
                if (this.currentStep === 2) {
                    setTimeout(() => this.focusCurrentInput(), 100);
                }
            });
        }

        // Event-Listener für Modal-Schließen
        const modal = document.getElementById('quickScanModal');
        if (modal) {
            modal.addEventListener('close', () => {
                this.reset();
            });
        }

        // Event-Listener für Mengeneingabe-Buttons
        document.querySelectorAll('.quantity-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const action = btn.dataset.action;
                if (action === 'decrease') {
                    this.decreaseQuantity();
                } else if (action === 'increase') {
                    this.increaseQuantity();
                }
            });
        });
    },

    handleKeyInput(e, input) {
        // Ignoriere input events, verarbeite nur keydown
        if (e.type !== 'keydown') return;
        
        const key = e.key;
        const currentTime = Date.now();
        const timeDiff = currentTime - this.lastKeyTime;
        const isWorkerInput = input.id === 'workerScanInput';
        
        // Ignoriere Steuerungstasten außer Backspace und Enter
        if (key.length > 1 && key !== 'Backspace' && key !== 'Enter') {
            return;
        }
        
        // Erhöhe die Zeitdifferenz auf 3000ms (3 Sekunden)
        if (timeDiff > 3000) { 
            this.keyBuffer = '';
        }
        
        if (key === 'Enter') {
            if (this.keyBuffer) {
                this.handleScannerInput(this.keyBuffer, input);
                this.keyBuffer = '';
            } else if (this.confirmationBarcode) {
                // Simuliere einen Scan des Bestätigungscodes bei Enter
                this.handleScannerInput(this.confirmationBarcode, input);
            } else if (input.value) {
                // Normale Enter-Verarbeitung für manuelle Eingaben
                const btnId = input.id === 'itemScanInput' ? 'confirmItemBtn' : 'confirmWorkerBtn';
                document.getElementById(btnId)?.click();
            }
            return;
        }
        
        if (key === 'Backspace') {
            e.preventDefault();
            this.keyBuffer = this.keyBuffer.slice(0, -1);
            this.updateDisplay(this.keyBuffer, isWorkerInput);
            return;
        }
        
        // Nur einzelne Zeichen zum Buffer hinzufügen
        if (key.length === 1) {
            this.keyBuffer += key;
            this.updateDisplay(this.keyBuffer, isWorkerInput);
            this.lastKeyTime = currentTime;
        }
    },

    updateDisplay(buffer, isWorker) {
        const inputId = isWorker ? 'processedWorkerInput' : 'processedItemInput';
        const btnId = isWorker ? 'confirmWorkerButton' : 'confirmItemBtn';
        const display = document.getElementById(inputId);
        const confirmBtn = document.getElementById(btnId);
        
        if (buffer && buffer.length > 0) {
            display.textContent = buffer;
            display.classList.remove('opacity-50');
            confirmBtn.classList.remove('hidden');
        } else {
            display.textContent = 'Keine Eingabe';
            display.classList.add('opacity-50');
            confirmBtn.classList.add('hidden');
        }
    },

    handleScannerInput(barcode, input) {
        console.log('Scanner Input erkannt:', barcode);

        // Prüfe ZUERST auf Bestätigungscode
        if (this.confirmationBarcode && barcode.includes(this.confirmationBarcode)) {
            console.log('Bestätigungscode erkannt');
            if (input.id === 'itemScanInput') {
                // Artikel wurde bestätigt
                this.currentProcess.confirmed = true;
                // Verstecke die Bestätigungskarte und zeige den Worker-Scan
                document.getElementById('itemConfirm').classList.add('hidden');
                document.getElementById('step1').classList.add('hidden');
                document.getElementById('step2').classList.remove('hidden');
                this.currentStep = 2;
                this.focusCurrentInput();
                this.confirmationBarcode = null;
            } else if (input.id === 'workerScanInput') {
                // Mitarbeiter wurde bestätigt, jetzt können wir die Aktion ausführen
                document.getElementById('workerScanPrompt').classList.add('hidden');
                document.getElementById('finalConfirm').classList.remove('hidden');
                this.executeStoredProcess();
            }
            return;
        }

        // Wenn kein Bestätigungscode, verarbeite als normalen Scan
        if (barcode.length >= 4) {
            if (input.id === 'itemScanInput') {
                this.handleItemScan(barcode);
            } else {
                this.handleWorkerScan(barcode);
            }
        }
    },

    async handleItemScan(barcode) {
        try {
            // Easter Eggs vor der normalen Verarbeitung prüfen
            if (barcode === 'SCANDY') {
                // Erstelle einen spektakulären Konfettieffekt
                confetti({
                    particleCount: 200,
                    spread: 160,
                    origin: { y: 0.6 },
                    ticks: 200,
                    gravity: 0.8,
                    scalar: 1.2,
                    zIndex: 99999
                });
                // Zusätzlicher Effekt nach kurzer Verzögerung
                setTimeout(() => {
                    confetti({
                        particleCount: 100,
                        angle: 60,
                        spread: 100,
                        origin: { x: 0 },
                        ticks: 200,
                        gravity: 0.8,
                        scalar: 1.2,
                        zIndex: 99999
                    });
                    confetti({
                        particleCount: 100,
                        angle: 120,
                        spread: 100,
                        origin: { x: 1 },
                        ticks: 200,
                        gravity: 0.8,
                        scalar: 1.2,
                        zIndex: 99999
                    });
                }, 250);
                showToast('success', '🎉 SCANDY! 🎉');
                return;
            }
            if (barcode === 'DANCE') {
                this.showDancingEmojis();
                return;
            }
            if (barcode === 'BTZ31189141') {
                showToast('success', 'Das Werkzeug wurde mal wieder gegen die Wand geworfen!');
                return;
            }

            // Entferne mögliche Präfixe für die Suche
            const cleanBarcode = barcode.replace(/^[TC]/, '');
            console.log('Suche Artikel mit bereinigtem Barcode:', cleanBarcode);
            
            // Versuche zuerst als Werkzeug
            const toolResponse = await fetch(`/api/inventory/tools/${cleanBarcode}`);
            let data;
            
            if (toolResponse.ok) {
                const response = await toolResponse.json();
                if (response.success) {
                    data = response.data;
                    data.type = 'tool';
                    data.barcode = cleanBarcode;
                    // Speichere im Prozess
                    this.currentProcess.item = data;
                    this.currentProcess.action = data.current_status === 'verfügbar' ? 'lend' : 'return';
                } else {
                    showToast('error', response.message || 'Fehler beim Laden des Werkzeugs');
                    return;
                }
            } else {
                // Wenn kein Werkzeug gefunden, versuche als Verbrauchsmaterial
                console.log('Versuche Verbrauchsmaterial:', cleanBarcode);
                const consumableResponse = await fetch(`/api/inventory/consumables/${cleanBarcode}`);
                if (consumableResponse.ok) {
                    const response = await consumableResponse.json();
                    if (response.success) {
                        data = response.data;
                        data.type = 'consumable';
                        data.barcode = cleanBarcode;
                        // Speichere im Prozess
                        this.currentProcess.item = data;
                        this.currentProcess.action = 'consume';
                        // Setze Standardmenge auf 1
                        this.currentProcess.quantity = 1;
                    } else {
                        showToast('error', response.message || 'Fehler beim Laden des Verbrauchsmaterials');
                        return;
                    }
                } else {
                    showToast('error', 'Artikel nicht gefunden');
                    return;
                }
            }
            
            // Bestimme Aktion und Farbe basierend auf Artikeltyp und Status
            let action, actionText, statusClass, details;
            
            if (data.type === 'tool') {
                if (data.current_status === 'verfügbar') {
                    action = 'lend';
                    actionText = 'Wird ausgeliehen';
                    statusClass = 'badge-success';
                } else if (data.current_status === 'ausgeliehen') {
                    action = 'return';
                    actionText = 'Wird zurückgegeben';
                    statusClass = 'badge-warning';
                } else if (data.current_status === 'defekt') {
                    action = null;
                    actionText = 'Defekt - keine Aktion möglich';
                    statusClass = 'badge-error';
                }
                details = `${data.category} | ${data.location}`;
            } else {
                action = 'consume';
                actionText = 'Wird ausgegeben';
                statusClass = data.quantity <= data.min_quantity ? 'badge-warning' : 'badge-success';
                details = `Bestand: ${data.quantity} | Mindestbestand: ${data.min_quantity}`;
            }
            
            // Aktualisiere die Info-Karte
            const itemName = document.getElementById('itemName');
            const itemStatusContainer = document.getElementById('itemStatusContainer');
            const itemStatus = document.getElementById('itemStatus');
            const returnIcon = document.getElementById('returnIcon');
            const lendIcon = document.getElementById('lendIcon');
            const itemDetails = document.getElementById('itemDetails');
            const quantityContainer = document.getElementById('quantityContainer');

            itemName.textContent = data.name;
            itemName.classList.remove('opacity-50');
            
            itemStatus.className = `badge badge-lg ${statusClass}`;
            itemStatus.textContent = data.status_text;
            
            // Icons statt Text anzeigen
            returnIcon.classList.add('hidden');
            lendIcon.classList.add('hidden');
            
            if (action === 'return') {
                returnIcon.classList.remove('hidden');
            } else if (action === 'lend' || action === 'consume') {
                lendIcon.classList.remove('hidden');
            }
            
            itemStatusContainer.style.display = 'flex';
            
            itemDetails.textContent = details;
            itemDetails.classList.remove('opacity-50');
            
            // Zeige Mengenauswahl für Verbrauchsmaterial
            if (data.type === 'consumable') {
                quantityContainer.classList.remove('hidden');
                const quantityDisplay = document.getElementById('quantityDisplay');
                if (quantityDisplay) {
                    quantityDisplay.textContent = '1';
                    quantityDisplay.dataset.max = data.quantity;
                    this.currentProcess.quantity = 1;
                }
            } else {
                quantityContainer.classList.add('hidden');
            }
            
            if (action) {
                showToast('success', 'Artikel erkannt: ' + data.name);
                
                // Generiere Bestätigungsbarcode
                this.confirmationBarcode = Math.random().toString(36).substring(2, 8).toUpperCase();
                const canvas = document.getElementById('itemConfirmBarcode');
                JsBarcode(canvas, this.confirmationBarcode, {
                    format: "CODE128",
                    width: 2,
                    height: 50,
                    displayValue: true
                });
                document.getElementById('itemConfirm').classList.remove('hidden');
            } else {
                showToast('error', 'Keine Aktion für diesen Artikel möglich');
            }
            
            } catch (error) {
            showToast('error', 'Fehler beim Scannen des Artikels');
            console.error(error);
        }
    },

        async handleWorkerScan(barcode) {
            try {
                console.log('Verarbeite Worker-Scan:', barcode);
            const response = await fetch(`/api/inventory/workers/${barcode}`);
            const result = await response.json();
                
                if (!response.ok) {
                throw new Error('Mitarbeiter nicht gefunden');
            }
            
            // Speichere im Prozess und füge Barcode hinzu
            result.barcode = barcode;  // Explizit den Barcode hinzufügen
            this.currentProcess.worker = result;
            console.log('Gespeicherter Worker:', this.currentProcess.worker);
            
            // Aktualisiere Worker-Bereich in der Info-Karte
            const workerName = document.getElementById('workerName');
            const workerDepartment = document.getElementById('workerDepartment');
            
            workerName.textContent = `${result.firstname} ${result.lastname}`;
            workerName.classList.remove('opacity-50');
            
            workerDepartment.textContent = result.department || 'Keine Abteilung';
            workerDepartment.classList.remove('opacity-50');
            
            showToast('success', 'Mitarbeiter erkannt: ' + result.firstname + ' ' + result.lastname);
            
            // Generiere Bestätigungsbarcode
            this.confirmationBarcode = Math.random().toString(36).substring(2, 8).toUpperCase();
            const canvas = document.getElementById('finalConfirmBarcode');
            JsBarcode(canvas, this.confirmationBarcode, {
                format: "CODE128",
                width: 2,
                height: 50,
                displayValue: true
            });
            document.getElementById('finalConfirm').classList.remove('hidden');
            
        } catch (error) {
            console.error('Worker-Scan Fehler:', error);
            showToast('error', 'Fehler: ' + error.message);
        }
    },

    async executeStoredProcess() {
        try {
            if (!this.currentProcess.item || !this.currentProcess.worker || !this.currentProcess.confirmed) {
                showToast('error', 'Prozess unvollständig');
                return;
            }

            const requestData = {
                item_barcode: this.currentProcess.item.barcode,
                worker_barcode: this.currentProcess.worker.barcode,
                action: this.currentProcess.action,
                item_type: this.currentProcess.item.type,
                quantity: this.currentProcess.item.type === 'consumable' ? this.currentProcess.quantity : undefined
            };

            console.log('Führe gespeicherten Prozess aus:', requestData);
            console.log('Worker Data:', this.currentProcess.worker);

                const response = await fetch('/api/quickscan/process_lending', {
                    method: 'POST',
                    headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            const result = await response.json();
            console.log('Server Antwort:', result);
            
            if (result.success) {
                const actionText = this.currentProcess.action === 'return' ? 'zurückgegeben' : 
                                 this.currentProcess.action === 'lend' ? 'ausgeliehen' : 
                                 'ausgegeben';
                showToast('success', `${this.currentProcess.item.name} erfolgreich ${actionText}`);
                setTimeout(() => {
                    const modal = document.getElementById('quickScanModal');
                    if (modal) {
                        modal.close();
                    }
                    this.reset();
                }, 2000);
            } else {
                throw new Error(result.message || 'Unbekannter Fehler');
            }
        } catch (error) {
            console.error('Fehler beim Ausführen des Prozesses:', error);
            showToast('error', error.message || 'Fehler beim Verarbeiten der Aktion');
        }
    },

    reset() {
        this.keyBuffer = '';
        this.lastKeyTime = Date.now();
        this.currentStep = 1;
        this.scannedItem = null;
        this.scannedWorker = null;
        this.quantity = 1;
        this.showStep(1);
        this.resetUI();
        this.updateDisplay('', false); // Reset buffer display
    },

    goToStep(step) {
        document.querySelectorAll('.scan-step').forEach(el => el.classList.add('hidden'));
        document.getElementById(`step${step}`).classList.remove('hidden');
        
        document.querySelectorAll('.steps .step').forEach((el, index) => {
            if (index + 1 <= step) {
                el.classList.add('step-primary');
            } else {
                el.classList.remove('step-primary');
            }
        });
        
        this.currentStep = step;
        this.focusCurrentInput();
    },
    
    focusCurrentInput() {
        const currentInput = this.currentStep === 1 ? 'itemScanInput' : 'workerScanInput';
        const input = document.getElementById(currentInput);
        if (input) {
            input.focus();
            input.select(); // Selektiert den vorhandenen Text
        }
    },

    confirmItem() {
        const input = document.getElementById('itemScanInput');
        if (this.keyBuffer) {
            this.handleScannerInput(this.keyBuffer, input);
            this.keyBuffer = '';
        }
    },

    confirmWorker() {
        const input = document.getElementById('workerScanInput');
        if (this.keyBuffer) {
            this.handleScannerInput(this.keyBuffer, input);
            this.keyBuffer = '';
        }
    },

    // Neue Funktionen für Mengenänderung
    decreaseQuantity() {
        const quantityDisplay = document.getElementById('quantityDisplay');
        const currentValue = parseInt(quantityDisplay.textContent);
        if (currentValue > 1) {
            quantityDisplay.textContent = currentValue - 1;
            this.currentProcess.quantity = currentValue - 1;
            // Fokus zurücksetzen
            this.focusCurrentInput();
        }
    },

    increaseQuantity() {
        const quantityDisplay = document.getElementById('quantityDisplay');
        const currentValue = parseInt(quantityDisplay.textContent);
        const maxQuantity = parseInt(quantityDisplay.dataset.max);
        if (currentValue < maxQuantity) {
            quantityDisplay.textContent = currentValue + 1;
            this.currentProcess.quantity = currentValue + 1;
            // Fokus zurücksetzen
            this.focusCurrentInput();
        }
    },

    // Funktion zum Rückgängig machen der letzten Eingabe
    undoLastInput(type) {
        this.keyBuffer = this.keyBuffer.slice(0, -1);
        this.updateDisplay(this.keyBuffer, type === 'worker');
    },

    processScannerInput: function(input, type) {
        if (!input) return;
        
        // Spezielle Barcodes für visuelle Effekte
        if (input === 'SCANDY') {
            this.showConfetti();
            return;
        }
        if (input === 'DANCE') {
            this.showDancingEmojis();
            return;
        }
        
        // Normale Verarbeitung
        if (type === 'item') {
            this.scannedItem = input;
            this.updateDisplay();
            this.currentStep = 'worker';
            document.getElementById('workerInput').focus();
        } else if (type === 'worker') {
            this.scannedWorker = input;
            this.updateDisplay();
            this.executeStoredProcess();
        }
    },

    showConfetti() {
        confetti({
            particleCount: 200,
            spread: 160,
            origin: { y: 0.6 },
            ticks: 200,
            gravity: 0.8,
            scalar: 1.2,
            zIndex: 99999
        });
        setTimeout(() => {
            confetti({
                particleCount: 100,
                angle: 60,
                spread: 100,
                origin: { x: 0 },
                ticks: 200,
                gravity: 0.8,
                scalar: 1.2,
                zIndex: 99999
            });
            confetti({
                particleCount: 100,
                angle: 120,
                spread: 100,
                origin: { x: 1 },
                ticks: 200,
                gravity: 0.8,
                scalar: 1.2,
                zIndex: 99999
            });
        }, 250);
        showToast('success', '🎉 SCANDY! 🎉');
    },

    showDancingEmojis() {
        showToast('success', '🦓 Zebra-Party! 🦓');
        
        // Erstelle den abgedunkelten Hintergrund
        const overlay = document.createElement('div');
        overlay.className = 'zebra-overlay';
        document.body.appendChild(overlay);
        
        const zebraLeft = document.createElement('img');
        zebraLeft.className = 'dancing-zebra left';
        zebraLeft.src = '/static/images/dancing_zebra.gif';
        zebraLeft.alt = 'Tanzendes Zebra';
        document.body.appendChild(zebraLeft);

        const zebraRight = document.createElement('img');
        zebraRight.className = 'dancing-zebra right';
        zebraRight.src = '/static/images/dancing_zebra.gif';
        zebraRight.alt = 'Tanzendes Zebra';
        document.body.appendChild(zebraRight);
        
        setTimeout(() => {
            zebraLeft.remove();
            zebraRight.remove();
            overlay.remove();
        }, 5000);
    }
};

// QuickScan initialisieren wenn Modal geöffnet wird
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('quickScanModal');
    if (modal) {
        modal.addEventListener('show', () => {
            QuickScan.init();
        });
    }
});

// Aktualisiere den Buffer im UI
function updateBufferDisplay(buffer, isWorker = false) {
    if (typeof updateScanBuffer === 'function') {
        updateScanBuffer(buffer, isWorker);
    }
} 