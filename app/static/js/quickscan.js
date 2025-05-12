const QuickScan = {
    currentStep: 1,
    scannedItem: null,
    scannedWorker: null,
    confirmationBarcode: null,
    lastKeyTime: 0,
    keyBuffer: '',
    isInitialized: false,
    activeInputType: null, // 'item' oder 'worker'
    
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

        // Event-Listener für das neue sichtbare Eingabefeld
        const activeInput = document.getElementById('quickScanActiveInput');
        if (activeInput) {
            activeInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    const value = activeInput.value.trim();
                    const upperValue = value.toUpperCase();
                    if (upperValue === 'DANCE') {
                        QuickScan.showDancingEmojis();
                        showToast('success', '🦓 Zebra-Party! 🦓');
                        activeInput.value = '';
                        return;
                    }
                    if (upperValue === 'VIBE') {
                        // VIBE Easter Egg (wie in handleScannerInput)
                        const overlay = document.createElement('div');
                        overlay.className = 'zebra-overlay';
                        document.body.appendChild(overlay);
                        const videoLeft = document.createElement('video');
                        videoLeft.src = "/static/videos/vibe.mp4";
                        videoLeft.className = 'dancing-zebra left';
                        videoLeft.loop = true;
                        videoLeft.autoplay = true;
                        const videoRight = document.createElement('video');
                        videoRight.src = "/static/videos/vibe.mp4";
                        videoRight.className = 'dancing-zebra right';
                        videoRight.loop = true;
                        videoRight.autoplay = true;
                        document.body.appendChild(videoLeft);
                        document.body.appendChild(videoRight);
                        setTimeout(() => {
                            overlay.remove();
                            videoLeft.remove();
                            videoRight.remove();
                        }, 10000);
                        activeInput.value = '';
                        return;
                    }
                    if (upperValue === 'AIIO') {
                        // AIIO Easter Egg (wie in handleScannerInput)
                        const overlay = document.createElement('div');
                        overlay.className = 'zebra-overlay';
                        document.body.appendChild(overlay);
                        const video = document.createElement('video');
                        video.src = "/static/videos/aiio.webm";
                        video.className = 'dancing-zebra';
                        video.loop = true;
                        video.autoplay = true;
                        video.style.position = 'fixed';
                        video.style.width = '640px';
                        video.style.height = '480px';
                        video.style.zIndex = 2147483647;
                        document.body.appendChild(video);
                        let x = Math.random() * (window.innerWidth - 640);
                        let y = Math.random() * (window.innerHeight - 480);
                        let dx = 5.0 * (Math.random() > 0.5 ? 1 : -1);
                        let dy = 5.0 * (Math.random() > 0.5 ? 1 : -1);
                        function animateDVDLogo() {
                            x += dx;
                            y += dy;
                            if (x <= 0 || x + 640 >= window.innerWidth) dx *= -1;
                            if (y <= 0 || y + 480 >= window.innerHeight) dy *= -1;
                            video.style.left = x + 'px';
                            video.style.top = y + 'px';
                            if (!video._stopAnimation) {
                                requestAnimationFrame(animateDVDLogo);
                            }
                        }
                        animateDVDLogo();
                        const modal = document.getElementById('quickScanModal');
                        let oldModalOverflow = null;
                        if (modal) {
                            modal.appendChild(video);
                            oldModalOverflow = modal.style.overflow;
                            modal.style.overflow = 'visible';
                        } else {
                            document.body.appendChild(video);
                        }
                        if (modal) {
                            modal.addEventListener('close', function removeAiioVideo() {
                                overlay.remove();
                                video._stopAnimation = true;
                                video.remove();
                                if (oldModalOverflow !== null) {
                                    modal.style.overflow = oldModalOverflow;
                                }
                                modal.removeEventListener('close', removeAiioVideo);
                            });
                        }
                        activeInput.value = '';
                        return;
                    }
                    // Normale Verarbeitung
                    if (value) {
                        if (this.activeInputType === 'item') {
                            this.handleItemScan(value);
                        } else if (this.activeInputType === 'worker') {
                            this.handleWorkerScan(value);
                        }
                        // Nach Scan/Eingabe Feld wieder ausblenden
                        document.getElementById('quickScanActiveInputContainer').classList.add('hidden');
                        this.activeInputType = null;
                    }
                }
            });
        }
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

        // Easter Egg Checks - Case Insensitive
        const upperBarcode = barcode.toUpperCase();
        console.log('[DEBUG] Checking for Easter Eggs with:', upperBarcode);
        console.log('[DEBUG] Is AIIO?', upperBarcode === 'AIIO');
        
        if (upperBarcode === 'DANCE') {
            console.log("[DEBUG] Easter Egg: DANCE detected!");
            this.showDancingEmojis();
            showToast('success', '🦓 Zebra-Party! 🦓');
            this.keyBuffer = '';
            this.updateDisplay(this.keyBuffer, input.id === 'workerScanInput');
            return;
        }

        if (upperBarcode === 'VIBE') {
            console.log("[DEBUG] Easter Egg: VIBE detected!");
            const overlay = document.createElement('div');
            overlay.className = 'zebra-overlay';
            document.body.appendChild(overlay);
            
            const videoLeft = document.createElement('video');
            videoLeft.src = "/static/videos/vibe.mp4";
            videoLeft.className = 'dancing-zebra left';
            videoLeft.loop = true;
            videoLeft.autoplay = true;
            
            const videoRight = document.createElement('video');
            videoRight.src = "/static/videos/vibe.mp4";
            videoRight.className = 'dancing-zebra right';
            videoRight.loop = true;
            videoRight.autoplay = true;
            
            document.body.appendChild(videoLeft);
            document.body.appendChild(videoRight);
            
            setTimeout(() => {
                overlay.remove();
                videoLeft.remove();
                videoRight.remove();
            }, 10000);
            
            this.keyBuffer = '';
            this.updateDisplay(this.keyBuffer, input.id === 'workerScanInput');
            return;
        }

        if (upperBarcode === 'AIIO') {
            console.log("[DEBUG] Easter Egg: AIIO detected!");
            const overlay = document.createElement('div');
            overlay.className = 'zebra-overlay';
            document.body.appendChild(overlay);

            // Video-Element erzeugen
            const video = document.createElement('video');
            video.src = "/static/videos/aiio.webm";
            video.className = 'dancing-zebra';
            video.loop = true;
            video.autoplay = true;
            video.style.position = 'fixed';
            video.style.width = '640px';
            video.style.height = '480px';
            video.style.zIndex = 2147483647;
            document.body.appendChild(video);

            // Startposition und Geschwindigkeit
            let x = Math.random() * (window.innerWidth - 640);
            let y = Math.random() * (window.innerHeight - 480);
            let dx = 5.0 * (Math.random() > 0.5 ? 1 : -1);
            let dy = 5.0 * (Math.random() > 0.5 ? 1 : -1);

            function animateDVDLogo() {
                x += dx;
                y += dy;
                // Kollision mit Rändern
                if (x <= 0 || x + 640 >= window.innerWidth) dx *= -1;
                if (y <= 0 || y + 480 >= window.innerHeight) dy *= -1;
                video.style.left = x + 'px';
                video.style.top = y + 'px';
                if (!video._stopAnimation) {
                    requestAnimationFrame(animateDVDLogo);
                }
            }
            animateDVDLogo();

            // Modal in den Hintergrund schicken
            const modal = document.getElementById('quickScanModal');
            let oldModalOverflow = null;
            if (modal) {
                // Video INS Modal einfügen
                modal.appendChild(video);
                // Modal-Overflow sichtbar machen, damit das Video nicht beschnitten wird
                oldModalOverflow = modal.style.overflow;
                modal.style.overflow = 'visible';
            } else {
                document.body.appendChild(video);
            }

            // Entferne das Video, wenn das Modal geschlossen wird
            if (modal) {
                modal.addEventListener('close', function removeAiioVideo() {
                    overlay.remove();
                    video._stopAnimation = true;
                    video.remove();
                    if (oldModalOverflow !== null) {
                        modal.style.overflow = oldModalOverflow;
                    }
                    modal.removeEventListener('close', removeAiioVideo);
                });
            }

            this.keyBuffer = '';
            this.updateDisplay(this.keyBuffer, input.id === 'workerScanInput');
            return;
        }

        // Normale Barcode-Verarbeitung
        if (this.confirmationBarcode && barcode.includes(this.confirmationBarcode)) {
            // Bestätigungscode-Logik
            if (this.currentStep === 1) {
                this.currentStep = 2;
                this.goToStep(2);
            } else if (this.currentStep === 2) {
                this.executeStoredProcess();
            }
        } else {
            if (this.currentStep === 1) {
                this.handleItemScan(barcode);
            } else if (this.currentStep === 2) {
                this.handleWorkerScan(barcode);
            }
        }
    },

    setCardState(type, state) {
        // type: 'item' oder 'worker', state: 'active', 'success', 'default'
        const card = document.getElementById(type === 'item' ? 'itemCard' : 'workerCard');
        // Entferne alle Hintergrundfarben
        card.style.backgroundColor = '';
        if (state === 'active') {
            card.style.backgroundColor = '#FEF08A'; // Tailwind yellow-200
        } else if (state === 'success') {
            card.style.backgroundColor = '#BBF7D0'; // Tailwind green-200
        } else {
            card.style.backgroundColor = '';
        }
    },

    async handleItemScan(barcode) {
        try {
            const response = await fetch(`/api/inventory/tools/${barcode}`);
            const data = await response.json();
            if (!data.success) {
                this.showError("Artikel nicht gefunden", 'item');
                this.setCardState('item', 'active');
                return;
            }
            const item = data.data;
            this.scannedItem = item;
            // Bestandswert robust ermitteln
            let quantity = (typeof item.quantity === 'number') ? item.quantity :
                           (typeof item.current_stock === 'number') ? item.current_stock :
                           (typeof item.current_amount === 'number') ? item.current_amount : 0;
            let min_quantity = (typeof item.min_quantity === 'number') ? item.min_quantity : 0;
            // Anzeige auf Karte aktualisieren
            const itemCardContent = document.getElementById('itemCardContent');
            if (itemCardContent) {
                let html = `<div class='font-bold mb-1'>${item.name || 'Unbek. Artikel'}</div>`;
                html += `<div class='badge badge-lg ${item.type === 'consumable' ? 'badge-info' : 'badge-neutral'} mb-1'>${item.type === 'consumable' ? 'Verbrauchsmaterial' : 'Werkzeug'}</div>`;
                html += `<div class='badge badge-lg mb-1'>${item.status_text || (item.type === 'consumable' ? (quantity > 0 ? 'Verfügbar' : 'Fehlt') : 'Unbekannt')}</div>`;
                if (item.type === 'consumable') {
                    html += `<div class='text-sm mt-1'>Bestand: <span class='font-mono'>${quantity}</span> / <span class='font-mono'>${min_quantity}</span> (min)</div>`;
                }
                html += `<div class='text-xs text-gray-400 mt-2'>(erneut klicken zum Ändern)</div>`;
                itemCardContent.innerHTML = html;
            }
            this.setCardState('item', 'success');
            this.setCardState('worker', this.activeInputType === 'worker' ? 'active' : (this.scannedWorker ? 'success' : 'default'));
            this.updateConfirmButtonState();
            // Mengen-Modal für Verbrauchsgüter anzeigen
            if (item.type === 'consumable') {
                this.showQuantityModal();
            }
        } catch (error) {
            this.showError("Fehler beim Abrufen des Artikels", 'item');
        }
    },

    async handleWorkerScan(barcode) {
        try {
            const response = await fetch(`/api/inventory/workers/${barcode}`);
            const result = await response.json();
            if (!result.success) {
                this.showError(result.message || 'Mitarbeiter nicht gefunden', 'worker');
                this.setCardState('worker', 'active');
                return;
            }
            const worker = result.data;
            this.scannedWorker = worker;
            // Anzeige auf Karte aktualisieren
            const workerCardContent = document.getElementById('workerCardContent');
            if (workerCardContent) {
                let html = `<div class='font-bold mb-1'>${worker.firstname || ''} ${worker.lastname || ''}</div>`;
                html += `<div class='text-sm mb-1'>${worker.department || 'Keine Abteilung'}</div>`;
                html += `<div class='text-xs text-gray-400 mt-2'>(erneut klicken zum Ändern)</div>`;
                workerCardContent.innerHTML = html;
            }
            this.setCardState('worker', 'success');
            this.setCardState('item', this.activeInputType === 'item' ? 'active' : (this.scannedItem ? 'success' : 'default'));
            this.updateConfirmButtonState();
        } catch (error) {
            this.showError("Fehler beim Abrufen des Mitarbeiters", 'worker');
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
                    action: this.scannedItem.type === 'consumable' ? 'consume' : 'lend',
                    item_type: this.scannedItem.type,
                    quantity: this.scannedItem.type === 'consumable' ? (this.currentProcess.quantity || 1) : 1
                })
            });

            const data = await response.json();
            console.log("Server-Antwort:", data);

            if (data.success) {
                showToast('success', data.message || 'Vorgang erfolgreich!');
                
                // Schließe das Modal
                const modal = document.getElementById('quickScanModal');
                if (modal) {
                    modal.close();
                }
                
                // Aktualisiere die Verbrauchshistorie, wenn es sich um ein Verbrauchsmaterial handelt
                if (this.scannedItem.type === 'consumable') {
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
        this.scannedItem = null;
        this.scannedWorker = null;
        this.keyBuffer = '';
        this.activeInputType = null;
        // Karten zurücksetzen
        const itemCardContent = document.getElementById('itemCardContent');
        if (itemCardContent) {
            itemCardContent.innerHTML = `<p class='text-base opacity-50'>Klicken &amp; Barcode scannen oder eingeben</p>`;
        }
        const workerCardContent = document.getElementById('workerCardContent');
        if (workerCardContent) {
            workerCardContent.innerHTML = `<p class='text-base opacity-50'>Klicken &amp; Barcode scannen oder eingeben</p>`;
        }
        // Kartenfarben zurücksetzen
        this.setCardState('item', 'default');
        this.setCardState('worker', 'default');
        // Eingabefeld ausblenden
        const inputContainer = document.getElementById('quickScanActiveInputContainer');
        if (inputContainer) inputContainer.classList.add('hidden');
        this.updateConfirmButtonState();
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
        this.focusCurrentInput(); // Fokus wieder aktivieren
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
        if (input === 'AIIO') {
            console.log("[DEBUG] Easter Egg: AIIO detected!");
            const overlay = document.createElement('div');
            overlay.className = 'zebra-overlay';
            document.body.appendChild(overlay);
            
            const videoLeft = document.createElement('video');
            videoLeft.src = "/static/videos/aiio.webm";
            videoLeft.className = 'dancing-zebra left';
            videoLeft.loop = true;
            videoLeft.autoplay = true;
            
            const videoRight = document.createElement('video');
            videoRight.src = "/static/videos/aiio.webm";
            videoRight.className = 'dancing-zebra right';
            videoRight.loop = true;
            videoRight.autoplay = true;
            
            document.body.appendChild(videoLeft);
            document.body.appendChild(videoRight);
            
            setTimeout(() => {
                overlay.remove();
                videoLeft.remove();
                videoRight.remove();
            }, 10000);
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

    showError(message, type = null) {
        console.error("Fehler:", message);
        showToast('error', message);
        if (type === 'item') {
            // Nur Item-Eingabe zurücksetzen
            this.scannedItem = null;
            const itemCardContent = document.getElementById('itemCardContent');
            if (itemCardContent) {
                itemCardContent.innerHTML = `<p class='text-sm opacity-50'>Klicken &amp; Barcode scannen oder eingeben</p>`;
            }
            this.setCardState('item', 'active');
            this.updateConfirmButtonState();
        } else if (type === 'worker') {
            // Nur Worker-Eingabe zurücksetzen
            this.scannedWorker = null;
            const workerCardContent = document.getElementById('workerCardContent');
            if (workerCardContent) {
                workerCardContent.innerHTML = `<p class='text-sm opacity-50'>Klicken &amp; Barcode scannen oder eingeben</p>`;
            }
            this.setCardState('worker', 'active');
            this.updateConfirmButtonState();
        } else {
            // Fallback: alles zurücksetzen
            this.reset();
        }
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
            this.closeQuantityModal();
            // Nach Mengenbestätigung: Karte bleibt grün, kein weiterer Scan nötig
            this.setCardState('item', 'success');
            this.updateConfirmButtonState();
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
    },

    activateInput(type) {
        // Zeige das sichtbare Eingabefeld an und setze Typ
        this.activeInputType = type;
        const inputContainer = document.getElementById('quickScanActiveInputContainer');
        const input = document.getElementById('quickScanActiveInput');
        if (inputContainer && input) {
            input.value = '';
            inputContainer.classList.remove('hidden');
            input.focus();
            input.placeholder = type === 'item' ? 'Werkzeug/Verbrauchsgut scannen oder eingeben' : 'Mitarbeiter scannen oder eingeben';
        }
        // Kartenfarben setzen
        this.setCardState('item', type === 'item' ? 'active' : (this.scannedItem ? 'success' : 'default'));
        this.setCardState('worker', type === 'worker' ? 'active' : (this.scannedWorker ? 'success' : 'default'));
    },

    // Button-Status aktualisieren
    updateConfirmButtonState() {
        const btn = document.getElementById('quickScanConfirmBtn');
        if (btn) {
            btn.disabled = !(this.scannedItem && this.scannedWorker);
        }
    },

    // Bestätigen-Button (hier nur Demo)
    async confirm() {
        if (this.scannedItem && this.scannedWorker) {
            try {
                // Bestimme Aktion für Werkzeuge: 'lend' oder 'return'
                let action = 'lend';
                if (this.scannedItem.type !== 'consumable') {
                    if (this.scannedItem.current_status === 'ausgeliehen') {
                        action = 'return';
                    }
                } else {
                    action = 'consume';
                }
                const response = await fetch('/api/quickscan/process_lending', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        item_barcode: this.scannedItem.barcode,
                        worker_barcode: this.scannedWorker.barcode,
                        action: action,
                        item_type: this.scannedItem.type,
                        quantity: this.scannedItem.type === 'consumable' ? (this.currentProcess.quantity || 1) : 1
                    })
                });
                const data = await response.json();
                if (data.success) {
                    showToast('success', data.message || 'Vorgang erfolgreich!');
                    const modal = document.getElementById('quickScanModal');
                    if (modal) modal.close();
                    this.reset();
                } else {
                    this.showError(data.message || 'Fehler bei der Verarbeitung');
                }
            } catch (error) {
                this.showError('Fehler bei der Verarbeitung');
            }
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

// Neue Toast-Funktion für unten rechts
function showToast(type, message) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3000);
} 