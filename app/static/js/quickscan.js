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
            if (input.id === 'itemScanInput' && this.currentStep === 1) {
                this.handleItemScan(barcode);
            } else if (input.id === 'workerScanInput' && this.currentStep === 2) {
                this.handleWorkerScan(barcode);
            }
        }
    },

    async handleItemScan(barcode) {
        console.log("Scanner erkannt:", barcode);
        
        try {
            const response = await fetch(`/api/inventory/tools/${barcode}`);
            const data = await response.json();
            
            if (!data.success) {
                this.showError("Artikel nicht gefunden");
                return;
            }
            
            const item = data.data;
            console.log("Gefundener Artikel:", item);
            
            // Setze den Artikel im Prozess
            this.scannedItem = item;
            
            // Aktualisiere die UI-Elemente
            const itemName = document.getElementById('itemName');
            const itemDetails = document.getElementById('itemDetails');
            const itemStatus = document.getElementById('itemStatus');
            
            if (itemName) {
                itemName.textContent = item.name || 'Unbekannter Artikel';
                itemName.classList.remove('opacity-50');
            }
            
            if (itemDetails) {
                itemDetails.textContent = `${item.location || 'Kein Standort'} - ${item.category || 'Keine Kategorie'}`;
                itemDetails.classList.remove('opacity-50');
            }
            
            if (itemStatus) {
                itemStatus.textContent = item.type === 'consumable' ? 'Verbrauchsmaterial' : 'Werkzeug';
                itemStatus.className = 'badge badge-lg ' + (item.type === 'consumable' ? 'badge-primary' : 'badge-secondary');
            }
            
            // Bestimme die Aktion basierend auf dem Artikeltyp und Status
            let action;
            if (item.type === 'consumable') {
                action = 'consume';
            } else {
                action = item.current_status === 'verfügbar' ? 'lend' : 'return';
            }
            
            // Setze den Prozess
            this.currentProcess = {
                item_barcode: item.barcode,
                item_type: item.type,
                action: action,
                quantity: item.type === 'consumable' ? 1 : undefined
            };
            
            // Zeige die Bestätigungskarte
            document.getElementById('itemConfirm').classList.remove('hidden');
            
            // Generiere Bestätigungscode
            this.confirmationBarcode = Math.random().toString(36).substring(2, 8).toUpperCase();
            const canvas = document.getElementById('itemConfirmBarcode');
            JsBarcode(canvas, this.confirmationBarcode, {
                format: "CODE128",
                width: 2,
                height: 50,
                displayValue: true
            });

            // Zeige Toast-Meldung für erfolgreichen Scan
            showToast('success', `Artikel erkannt: ${item.name || 'Unbekannter Artikel'} (${item.type === 'consumable' ? 'Verbrauchsmaterial' : 'Werkzeug'})`);
            
            // Wenn es ein Verbrauchsmaterial ist, zeige das Mengen-Modal
            if (item.type === 'consumable') {
                this.showQuantityModal();
            }
            
        } catch (error) {
            console.error("Fehler beim Abrufen des Artikels:", error);
            this.showError("Fehler beim Abrufen des Artikels");
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
                
                // Speichere den Mitarbeiter
                this.scannedWorker = result;
                this.scannedWorker.barcode = barcode;  // Explizit den Barcode hinzufügen
                console.log('Gespeicherter Worker:', this.scannedWorker);
                
                // Aktualisiere Worker-Bereich in der Info-Karte
                const workerName = document.getElementById('workerName');
                const workerDepartment = document.getElementById('workerDepartment');
                
                if (workerName) {
                    workerName.textContent = `${result.firstname} ${result.lastname}`;
                    workerName.classList.remove('opacity-50');
                }
                
                if (workerDepartment) {
                    workerDepartment.textContent = result.department || 'Keine Abteilung';
                    workerDepartment.classList.remove('opacity-50');
                }
                
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
                
                // Zeige die finale Bestätigungskarte
                document.getElementById('finalConfirm').classList.remove('hidden');
                
            } catch (error) {
                console.error('Worker-Scan Fehler:', error);
                this.showError('Fehler: ' + error.message);
            }
        },

    async executeStoredProcess() {
        console.log("Aktueller Prozess:", this.currentProcess);
        console.log("Gescanntes Item:", this.scannedItem);
        console.log("Gescannte Worker:", this.scannedWorker);

        if (!this.currentProcess || !this.scannedItem || !this.scannedWorker) {
            console.error("Prozess nicht vollständig:", {
                process: this.currentProcess,
                item: this.scannedItem,
                worker: this.scannedWorker
            });
            this.showError("Prozess nicht vollständig");
            return;
        }

        try {
            const response = await fetch('/api/quickscan/process_lending', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    item_barcode: this.scannedItem.barcode,
                    worker_barcode: this.scannedWorker.barcode,
                    action: this.currentProcess.action,
                    item_type: this.currentProcess.item_type,
                    quantity: this.currentProcess.quantity || 1
                })
            });

            const data = await response.json();
            console.log("Server-Antwort:", data);

            if (data.success) {
                showToast('success', data.message);
                
                // Schließe das Modal
                const modal = document.getElementById('quickScanModal');
                if (modal) {
                    modal.close();
                }
                
                // Aktualisiere die Verbrauchshistorie, wenn es sich um ein Verbrauchsmaterial handelt
                if (this.currentProcess.item_type === 'consumable') {
                    // Lade die Seite neu, um die aktualisierte Historie anzuzeigen
                    window.location.reload();
                }
                
                this.reset();
            } else {
                this.showError(data.message || 'Fehler bei der Verarbeitung');
            }
        } catch (error) {
            console.error("Fehler bei der Verarbeitung:", error);
            this.showError("Fehler bei der Verarbeitung");
        }
    },

    reset() {
        // Reset interne Variablen
        this.keyBuffer = '';
        this.lastKeyTime = Date.now();
        this.currentStep = 1;
        this.scannedItem = null;
        this.scannedWorker = null;
        this.quantity = 1;
        this.currentProcess = {
            item: null,
            worker: null,
            action: null,
            confirmed: false
        };
        this.confirmationBarcode = null;

        // Reset UI-Elemente
        const itemInput = document.getElementById('itemScanInput');
        const workerInput = document.getElementById('workerScanInput');
        if (itemInput) itemInput.value = '';
        if (workerInput) workerInput.value = '';

        // Verstecke alle Bestätigungskarten
        const itemConfirm = document.getElementById('itemConfirm');
        const finalConfirm = document.getElementById('finalConfirm');
        if (itemConfirm) itemConfirm.classList.add('hidden');
        if (finalConfirm) finalConfirm.classList.add('hidden');

        // Reset Mengenanzeige
        const quantityDisplay = document.getElementById('quantityDisplay');
        if (quantityDisplay) {
            quantityDisplay.textContent = '1';
            quantityDisplay.dataset.max = '';
        }

        // Reset Info-Karten
        const itemName = document.getElementById('itemName');
        const itemStatus = document.getElementById('itemStatus');
        const itemDetails = document.getElementById('itemDetails');
        const workerName = document.getElementById('workerName');
        const workerDepartment = document.getElementById('workerDepartment');
        
        if (itemName) {
            itemName.textContent = 'Kein Artikel';
            itemName.classList.add('opacity-50');
        }
        if (itemStatus) {
            itemStatus.textContent = '';
            itemStatus.className = 'badge badge-lg';
        }
        if (itemDetails) {
            itemDetails.textContent = '';
            itemDetails.classList.add('opacity-50');
        }
        if (workerName) {
            workerName.textContent = 'Kein Mitarbeiter';
            workerName.classList.add('opacity-50');
        }
        if (workerDepartment) {
            workerDepartment.textContent = '';
            workerDepartment.classList.add('opacity-50');
        }

        // Setze Schritt zurück
        this.goToStep(1);
        
        // Fokus auf das aktuelle Eingabefeld
        this.focusCurrentInput();
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

        // Füge Musik hinzu
        const audio = new Audio('/static/audio/zebra_party.mp3');
        audio.volume = 0.5; // Lautstärke auf 50% setzen
        audio.play().catch(error => {
            console.log('Audio konnte nicht abgespielt werden:', error);
        });
        
        setTimeout(() => {
            zebraLeft.remove();
            zebraRight.remove();
            overlay.remove();
            audio.pause();
            audio.currentTime = 0;
        }, 17000); // 17 Sekunden = 17000 Millisekunden
    },

    showError(message) {
        console.error("Fehler:", message);
        showToast('error', message);
        this.reset();
    },

    showQuantityModal() {
        document.getElementById('quantityModal').showModal();
    },

    closeQuantityModal() {
        document.getElementById('quantityModal').close();
    },

    confirmQuantity() {
        const quantity = parseInt(document.getElementById('quantityInput').value);
        if (quantity > 0) {
            this.currentProcess.quantity = quantity;
            this.closeQuantityModal();
            // Weiter zum Mitarbeiter-Scan
            document.getElementById('itemConfirm').classList.add('hidden');
            document.getElementById('step1').classList.add('hidden');
            document.getElementById('step2').classList.remove('hidden');
            this.currentStep = 2;
            this.focusCurrentInput();
        } else {
            showToast('Bitte eine gültige Menge eingeben', 'error');
        }
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