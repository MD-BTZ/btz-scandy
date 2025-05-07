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

            // Event-Listener für Bestätigungs-Button (manuelle Bestätigung via Klick)
            // Die IDs müssen mit denen im HTML übereinstimmen!
            const confirmItemBtnElement = document.getElementById('confirmItemBtn');
            if (confirmItemBtnElement) {
                confirmItemBtnElement.addEventListener('click', () => {
                    this.confirmItem(); // Ruft handleScannerInput mit keyBuffer, falls vorhanden
                });
            }

            // Event-Listener für Rückgängig-Button
            const undoItemBtnElement = document.getElementById('undoItemBtn');
            if (undoItemBtnElement) {
                undoItemBtnElement.addEventListener('click', () => {
                    this.undoLastInput('item');
                });
            }

            // Minimaler Input-Listener, um den Buffer zu leeren, falls der Scanner ohne Enter sendet
            // Die Hauptlogik ist in handleKeyInput
            itemInput.addEventListener('input', (e) => {
                if (e.target.value && e.target.value.length > this.keyBuffer.length && e.target.value.includes(this.keyBuffer)) {
                    // Wenn der Input-Wert den Buffer enthält und länger ist (typisch für schnelles Scannen ohne explizites Enter)
                    // dann nehmen wir an, dass der Scanner fertig ist und leiten den vollen Wert weiter.
                    // Dies ist ein Versuch, Scanner abzufangen, die kein Enter senden.
                    console.log(`[DEBUG] itemInput 'input' event, potenzieller Scanner-Input ohne Enter: ${e.target.value}`);
                    this.handleScannerInput(e.target.value, itemInput); 
                    e.target.value = ''; // Input leeren
                    this.keyBuffer = ''; // Buffer auch leeren
                } else if (!e.target.value) {
                     // Wenn das Feld geleert wird (z.B. durch Backspace), Buffer auch leeren.
                    this.keyBuffer = '';
                }
            });

            // Fokus wiederherstellen bei Klick außerhalb
            itemInput.addEventListener('blur', () => {
                if (this.currentStep === 1) {
                    // setTimeout(() => this.focusCurrentInput(), 100); // Testweise deaktiviert, um zu sehen ob es hilft
                }
            });
            }

        // Event-Listener für Worker-Scan
        const workerInput = document.getElementById('workerScanInput');
        if (workerInput) {
            workerInput.addEventListener('keydown', (e) => {
                this.handleKeyInput(e, workerInput);
            });

            const confirmWorkerBtnElement = document.getElementById('confirmWorkerButton');
            if (confirmWorkerBtnElement) {
                confirmWorkerBtnElement.addEventListener('click', () => {
                    this.confirmWorker();
                });
            }

            const undoWorkerBtnElement = document.getElementById('undoWorkerButton');
            if (undoWorkerBtnElement) {
                undoWorkerBtnElement.addEventListener('click', () => {
                    this.undoLastInput('worker');
                });
            }
            
            workerInput.addEventListener('input', (e) => {
                 if (e.target.value && e.target.value.length > this.keyBuffer.length && e.target.value.includes(this.keyBuffer)) {
                    console.log(`[DEBUG] workerInput 'input' event, potenzieller Scanner-Input ohne Enter: ${e.target.value}`);
                    this.handleScannerInput(e.target.value, workerInput);
                    e.target.value = '';
                    this.keyBuffer = '';
                } else if (!e.target.value) {
                    this.keyBuffer = '';
                }
            });

            // Fokus wiederherstellen bei Klick außerhalb
            workerInput.addEventListener('blur', () => {
                if (this.currentStep === 2) {
                    // setTimeout(() => this.focusCurrentInput(), 100); // Testweise deaktiviert
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
        
        if (display) {
            if (buffer && buffer.length > 0) {
                display.textContent = buffer;
                display.classList.remove('opacity-50');
                if (confirmBtn) {
                    confirmBtn.classList.remove('hidden');
                }
            } else {
                display.textContent = 'Keine Eingabe';
                display.classList.add('opacity-50');
                if (confirmBtn) {
                    confirmBtn.classList.add('hidden');
                }
            }
        }
    },

    handleScannerInput(barcode, input) {
        console.log('[DEBUG] handleScannerInput - Barcode:', barcode, 'Input ID:', input.id);

        // Easter Egg Check
        if (barcode.toUpperCase() === 'DANCE') { 
            console.log("[DEBUG] Easter Egg: DANCE detected!");
            this.showDancingEmojis(); // Rufe die Funktion auf
            showToast('success', '🦓 Zebra-Party! 🦓');
            this.keyBuffer = ''; // Buffer leeren
            this.updateDisplay(this.keyBuffer, input.id === 'workerScanInput'); // Anzeige zurücksetzen
            return; // Verarbeitung hier beenden
        }

        // Prüfe ZUERST auf Bestätigungscode
        if (this.confirmationBarcode && barcode.includes(this.confirmationBarcode)) {
            console.log('[DEBUG] Bestätigungscode erkannt');
            if (input.id === 'itemScanInput') {
                console.log('[DEBUG] Bestätigung für itemScanInput');
                // Artikel wurde bestätigt
                this.currentProcess.confirmed = true;
                // Verstecke die Bestätigungskarte und zeige den Worker-Scan
                document.getElementById('itemConfirm').classList.add('hidden');
                document.getElementById('step1').classList.add('hidden');
                document.getElementById('step2').classList.remove('hidden');
                this.currentStep = 2;
                this.focusCurrentInput();
                this.confirmationBarcode = null;

                // Stelle sicher, dass die Mitarbeiterinfo im oberen Display zurückgesetzt ist
                const workerNameDisplay = document.getElementById('processedWorkerInput');
                const workerDepartmentDisplay = document.getElementById('workerDepartmentDisplay');
                if (workerNameDisplay) {
                    workerNameDisplay.textContent = 'Noch kein Mitarbeiter gescannt';
                    workerNameDisplay.classList.add('opacity-50');
                }
                if (workerDepartmentDisplay) {
                    workerDepartmentDisplay.textContent = 'Abteilung wird nach Scan angezeigt';
                    workerDepartmentDisplay.classList.add('opacity-50');
                }

            } else if (input.id === 'workerScanInput') {
                console.log('[DEBUG] Bestätigung für workerScanInput');
                // Mitarbeiter wurde bestätigt, jetzt können wir die Aktion ausführen
                document.getElementById('workerScanPrompt').classList.add('hidden');
                document.getElementById('finalConfirm').classList.remove('hidden');
                this.executeStoredProcess();
            }
            return;
        }

        console.log('[DEBUG] Kein Bestätigungscode. Barcode-Länge:', barcode.length, 'Current Step:', this.currentStep);
        // Wenn kein Bestätigungscode, verarbeite als normalen Scan
        if (barcode.length >= 3) { // Mindestlänge für Barcodes angepasst, oft sind es mehr als 3
            if (input.id === 'itemScanInput' && this.currentStep === 1) {
                console.log('[DEBUG] Rufe handleItemScan für Barcode:', barcode);
                this.handleItemScan(barcode);
            } else if (input.id === 'workerScanInput' && this.currentStep === 2) {
                console.log('[DEBUG] Rufe handleWorkerScan für Barcode:', barcode);
                this.handleWorkerScan(barcode);
            } else {
                console.log('[DEBUG] Bedingungen für handleItemScan/handleWorkerScan nicht erfüllt. Input ID:', input.id, 'Current Step:', this.currentStep);
            }
        } else {
            console.log('[DEBUG] Barcode zu kurz oder falscher Schritt.');
        }
    },

    async handleItemScan(barcode) {
        console.log("[DEBUG] handleItemScan - Barcode:", barcode);
        
        try {
            const response = await fetch(`/api/inventory/tools/${barcode}`);
            const data = await response.json();
            
            if (!data.success) {
                this.showError("Artikel nicht gefunden");
                return;
            }
            
            const item = data.data;
            console.log("[DEBUG] Gefundener Artikel:", item);
            
            this.scannedItem = item;
            
            const processedItemInputDisplay = document.getElementById('processedItemInput');
            const itemTypeDisplay = document.getElementById('itemTypeDisplay');
            const itemStatusDisplay = document.getElementById('itemStatusDisplay');
            
            if (processedItemInputDisplay) {
                processedItemInputDisplay.textContent = item.name || 'Unbek. Artikel';
                processedItemInputDisplay.classList.remove('opacity-50');
                console.log("[DEBUG] processedItemInputDisplay textContent gesetzt auf:", processedItemInputDisplay.textContent);
            }
            
            if (itemTypeDisplay) {
                itemTypeDisplay.textContent = item.type === 'consumable' ? 'Verbrauchsmaterial' : 'Werkzeug';
                itemTypeDisplay.className = 'badge badge-lg '; // Reset classes
                if (item.type === 'consumable') {
                    itemTypeDisplay.classList.add('badge-info');
                } else {
                    itemTypeDisplay.classList.add('badge-neutral');
                }
                console.log("[DEBUG] itemTypeDisplay textContent gesetzt auf:", itemTypeDisplay.textContent, "Class:", itemTypeDisplay.className);
            }
            
            if (itemStatusDisplay) {
                itemStatusDisplay.textContent = item.status_text || (item.type === 'consumable' ? (item.quantity > 0 ? 'Verfügbar' : 'Fehlt') : 'Unbekannt');
                itemStatusDisplay.className = 'badge badge-lg '; // Reset classes
                let statusClass = 'badge-ghost'; 
                if (item.type === 'tool') {
                    if (item.current_status === 'verfügbar') statusClass = 'badge-success';
                    else if (item.current_status === 'ausgeliehen') statusClass = 'badge-warning';
                    else if (item.current_status === 'defekt') statusClass = 'badge-error';
                } else if (item.type === 'consumable') {
                    if (item.quantity > item.min_quantity) statusClass = 'badge-success';
                    else if (item.quantity > 0) statusClass = 'badge-warning';
                    else statusClass = 'badge-error';
                }
                itemStatusDisplay.classList.add(statusClass);
                console.log("[DEBUG] itemStatusDisplay textContent gesetzt auf:", itemStatusDisplay.textContent, "Class:", itemStatusDisplay.className);
            }
            
            let action;
            if (item.type === 'consumable') {
                action = 'consume';
            } else {
                action = item.current_status === 'verfügbar' ? 'lend' : 'return';
            }
            
            this.currentProcess = {
                item_barcode: item.barcode,
                item_type: item.type,
                action: action,
                quantity: item.type === 'consumable' ? 1 : undefined // Menge für Verbrauchsmaterial initial auf 1
            };
            
            const itemConfirmCard = document.getElementById('itemConfirm');
            if (itemConfirmCard) {
                itemConfirmCard.classList.remove('hidden');
                console.log("[DEBUG] itemConfirm wird jetzt angezeigt.");
            }
            
            this.confirmationBarcode = Math.random().toString(36).substring(2, 8).toUpperCase();
            const canvas = document.getElementById('itemConfirmBarcode');
            if (canvas) { 
                JsBarcode(canvas, this.confirmationBarcode, {
                    format: "CODE128",
                    width: 2,
                    height: 50,
                    displayValue: true
                });
                console.log("[DEBUG] Bestätigungs-Barcode generiert:", this.confirmationBarcode);
            } else {
                console.error("[FEHLER] Canvas-Element 'itemConfirmBarcode' nicht gefunden!");
            }

            // Mengenmodal für Verbrauchsmaterialien wieder aktivieren
            if (item.type === 'consumable') {
                console.log("[DEBUG] Artikel ist Verbrauchsmaterial, zeige Mengenmodal.");
                this.showQuantityModal();
            } else {
                // Für Werkzeuge direkt zum nächsten Schritt (implizit durch Bestätigungsscan)
                // oder hier Logik, falls keine Bestätigung per Scan gewünscht wäre.
            }

            showToast('success', `Artikel erkannt: ${item.name || 'Unbek. Artikel'} (${item.type === 'consumable' ? 'Verbrauchsmaterial' : 'Werkzeug'})`);
            
        } catch (error) {
            console.error("Fehler beim Abrufen des Artikels:", error);
            this.showError("Fehler beim Abrufen des Artikels");
        }
    },

    async handleWorkerScan(barcode) {
        console.log("[DEBUG] handleWorkerScan - Barcode:", barcode);
        try {
            const response = await fetch(`/api/inventory/workers/${barcode}`);
            const result = await response.json(); // Renamed data to result to avoid conflict with outer scope if any
            
            if (!result.success) { // Assuming API returns {success: boolean, ...}
                this.showError(result.message || 'Mitarbeiter nicht gefunden');
                this.keyBuffer = ''; // Clear buffer to allow new scan
                this.updateDisplay(this.keyBuffer, true); // Update display for worker
                return;
            }
            
            const worker = result.data; // Assuming worker data is in result.data
            console.log("[DEBUG] Gefundener Mitarbeiter:", worker);
            
            this.scannedWorker = worker; // Store full worker object
            this.scannedWorker.barcode = barcode; // Ensure barcode is part of the stored object
            
            const workerNameDisplay = document.getElementById('processedWorkerInput');
            const workerDepartmentDisplay = document.getElementById('workerDepartmentDisplay');
            
            if (workerNameDisplay) {
                workerNameDisplay.textContent = `${worker.firstname || 'N/A'} ${worker.lastname || 'N/A'}`;
                workerNameDisplay.classList.remove('opacity-50');
                console.log("[DEBUG] workerNameDisplay textContent gesetzt auf:", workerNameDisplay.textContent);
            }
            
            if (workerDepartmentDisplay) {
                workerDepartmentDisplay.textContent = worker.department || 'Keine Abteilung';
                workerDepartmentDisplay.classList.remove('opacity-50');
                console.log("[DEBUG] workerDepartmentDisplay textContent gesetzt auf:", workerDepartmentDisplay.textContent);
            }
            
            showToast('success', `Mitarbeiter erkannt: ${worker.firstname || ''} ${worker.lastname || ''}`);
            
            // Generiere finalen Bestätigungsbarcode
            this.confirmationBarcode = Math.random().toString(36).substring(2, 8).toUpperCase();
            const canvas = document.getElementById('finalConfirmBarcode');
            if (canvas) {
                JsBarcode(canvas, this.confirmationBarcode, {
                    format: "CODE128",
                    width: 2,
                    height: 50,
                    displayValue: true
                });
                console.log("[DEBUG] Finaler Bestätigungs-Barcode generiert:", this.confirmationBarcode);
            } else {
                console.error("[FEHLER] Canvas-Element 'finalConfirmBarcode' nicht gefunden!");
            }
            
            // Verstecke den normalen Scan-Prompt und zeige die finale Bestätigungskarte
            const workerScanPrompt = document.getElementById('workerScanPrompt');
            const finalConfirmCard = document.getElementById('finalConfirm');
            if (workerScanPrompt) workerScanPrompt.classList.add('hidden');
            if (finalConfirmCard) finalConfirmCard.classList.remove('hidden');
            console.log("[DEBUG] FinalConfirmCard wird angezeigt, workerScanPrompt versteckt.");
            
        } catch (error) {
            console.error("Fehler beim Abrufen des Mitarbeiters:", error);
            this.showError("Fehler beim Abrufen des Mitarbeiters");
            this.keyBuffer = ''; // Clear buffer on error
            this.updateDisplay(this.keyBuffer, true);
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
        this.currentProcess = {
            item: null,
            worker: null,
            action: null,
            confirmed: false,
            quantity: 1 // Standardmenge beim Reset
        };
        this.confirmationBarcode = null;

        // Explizit das Zebra-Overlay entfernen, falls vorhanden
        const zebraOverlay = document.querySelector('.zebra-overlay');
        if (zebraOverlay) {
            console.log("Removing existing zebra overlay in reset.");
            zebraOverlay.remove();
        }
        // Auch die Zebras selbst entfernen, falls der Timeout noch nicht lief
        document.querySelectorAll('.dancing-zebra').forEach(el => el.remove());
        // TODO: Auch die Musik stoppen? (Falls sie noch läuft)
        // Aktuell wird die Musik im Timeout von showDancingEmojis gestoppt.
        // Wenn das Modal vorher geschlossen wird, läuft sie evtl. weiter.

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
        const processedItemInput = document.getElementById('processedItemInput');
        const itemTypeDisplay = document.getElementById('itemTypeDisplay');
        const itemStatusDisplay = document.getElementById('itemStatusDisplay');
        const processedWorkerInput = document.getElementById('processedWorkerInput');
        const workerDepartmentDisplay = document.getElementById('workerDepartmentDisplay');
        
        if (processedItemInput) {
            processedItemInput.textContent = 'Noch kein Artikel gescannt';
            processedItemInput.classList.add('opacity-50');
        }
        if (itemTypeDisplay) {
            itemTypeDisplay.textContent = '';
            itemTypeDisplay.className = 'badge badge-lg';
        }
        if (itemStatusDisplay) {
            itemStatusDisplay.textContent = '';
            itemStatusDisplay.className = 'badge badge-lg';
        }
        if (processedWorkerInput) {
            processedWorkerInput.textContent = 'Noch kein Mitarbeiter gescannt';
            processedWorkerInput.classList.add('opacity-50');
        }
        if (workerDepartmentDisplay) {
            workerDepartmentDisplay.textContent = 'Abteilung wird nach Scan angezeigt';
            workerDepartmentDisplay.classList.add('opacity-50');
        }

        // Setze Schritt zurück
        this.goToStep(1);
        
        // Fokus auf das aktuelle Eingabefeld (ENTFERNT BEIM RESET)
        // this.focusCurrentInput(); 
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
        // this.focusCurrentInput(); // Auch hier auskommentieren
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
        console.log("Showing dancing emojis");
        // Vorhandene Zebras entfernen, falls welche da sind
        document.querySelectorAll('.dancing-zebra').forEach(el => el.remove());
        
        const overlay = document.createElement('div');
        overlay.className = 'zebra-overlay';
        document.body.appendChild(overlay);
        
        const zebraLeft = document.createElement('img');
        zebraLeft.src = '/static/images/dancing_zebra.gif'; // Pfad zum animierten GIF
        zebraLeft.className = 'dancing-zebra left';
        
        const zebraRight = document.createElement('img');
        zebraRight.src = '/static/images/dancing_zebra.gif';
        zebraRight.className = 'dancing-zebra right';
        
        document.body.appendChild(zebraLeft);
        document.body.appendChild(zebraRight);
        
        // Optional: Musik abspielen
        const audio = new Audio('/static/audio/zebra_party.mp3'); // Pfad zur Musikdatei
        audio.play().catch(error => console.warn("Autoplay wurde verhindert:", error));
        
        // Nach einiger Zeit wieder entfernen
        setTimeout(() => {
            zebraLeft.remove();
            zebraRight.remove();
            overlay.remove();
            audio.pause();
            audio.currentTime = 0;
        }, 10000); // 10 Sekunden
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
        const quantityInput = document.getElementById('quantityInput');
        const quantity = parseInt(quantityInput.value);

        if (quantity > 0) {
            this.currentProcess.quantity = quantity;
            console.log("[DEBUG] Menge bestätigt:", this.currentProcess.quantity);
            this.closeQuantityModal();
            // Fokus auf das itemScanInput, um den Bestätigungsbarcode zu scannen
            // oder Hinweis geben, den angezeigten Barcode zu scannen.
            // Da das itemScanInput readonly ist, muss der Nutzer den Barcode scannen.
            // Ein expliziter Fokus ist hier nicht unbedingt nötig, aber schadet nicht.
            const itemInput = document.getElementById('itemScanInput');
            if(itemInput) itemInput.focus(); 
            showToast('info', 'Bitte scannen Sie jetzt den Bestätigungs-Barcode für den Artikel.');
        } else {
            showToast('error', 'Bitte eine gültige Menge eingeben.');
        }
    },

    openModal() {
        const modal = document.getElementById('quickScanModal');
        if (modal) {
            modal.showModal();
            this.init();
        } else {
            console.error("Cannot open QuickScan modal - modal not found!");
        }
    }
};

// QuickScan initialisieren wenn Modal geöffnet wird
document.addEventListener('DOMContentLoaded', () => {
    // console.log("QuickScan DOMContentLoaded"); 
    const modal = document.getElementById('quickScanModal');
    const trigger = document.getElementById('quickScanTrigger'); 

    if (modal) {
        // Listener für das 'close'-Event des Modals
        modal.addEventListener('close', () => {
            // console.log("QuickScan modal closed, resetting and reloading."); 
            QuickScan.reset();
            // WORKAROUND: Seite neu laden...
            // TODO: Ursache finden...
            window.location.reload(); 
        });
    } else {
        console.error("QuickScan Modal not found!");
    }

    // Event Listener für den Trigger Button hinzufügen
    if (trigger) {
        trigger.addEventListener('click', () => {
            // console.log("QuickScan trigger clicked"); 
            if (modal) {
                modal.showModal(); 
                QuickScan.init(); 
            } else {
                console.error("Cannot open QuickScan modal - modal not found!");
            }
        });
    } else {
        console.error("QuickScan trigger button not found!");
    }

    // Event listener to open the modal when the trigger is clicked
    const quickScanTrigger = document.getElementById('quickScanTrigger');
    if (quickScanTrigger) {
        quickScanTrigger.addEventListener('click', () => {
            QuickScan.openModal();
        });
    }
});

// Aktualisiere den Buffer im UI
function updateBufferDisplay(buffer, isWorker = false) {
    if (typeof updateScanBuffer === 'function') {
        updateScanBuffer(buffer, isWorker);
    }
} 