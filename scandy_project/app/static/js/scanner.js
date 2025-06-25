class BarcodeScanner {
    constructor() {
        this.stream = null;
        this.activeCamera = 'environment';
        this.scanStep = 1;
        this.firstBarcode = null;
        this.isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    }

    async startScanning(videoElement, resultCallback, validateCallback) {
        try {
            const constraints = {
                video: {
                    facingMode: this.activeCamera,
                    width: { ideal: this.isMobile ? 1280 : 1920 },
                    height: { ideal: this.isMobile ? 720 : 1080 }
                }
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            videoElement.srcObject = this.stream;
            
            if ('BarcodeDetector' in window) {
                const barcodeDetector = new BarcodeDetector({
                    formats: ['qr_code', 'ean_13', 'ean_8', 'code_128']
                });
                
                const detectLoop = async () => {
                    try {
                        const barcodes = await barcodeDetector.detect(videoElement);
                        if (barcodes.length > 0) {
                            const barcode = barcodes[0].rawValue;
                            if (await validateCallback(barcode, this.scanStep)) {
                                resultCallback(barcode, this.scanStep);
                            }
                        }
                    } catch (error) {
                        console.error('Barcode Erkennungsfehler:', error);
                    }
                    
                    if (this.stream) {
                        requestAnimationFrame(detectLoop);
                    }
                };
                
                requestAnimationFrame(detectLoop);
            }
        } catch (error) {
            console.error('Kamera Zugriffsfehler:', error);
            throw error;
        }
    }

    stopScanning() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }

    switchCamera() {
        if (this.isMobile) {
            this.activeCamera = this.activeCamera === 'environment' ? 'user' : 'environment';
            this.stopScanning();
            // Neustart des Scanners mit neuer Kamera
            const videoElement = document.querySelector('#video');
            if (videoElement) {
                this.startScanning(videoElement, this.resultCallback, this.validateCallback);
            }
        }
    }
}

async function openQuickScan(event) {
    event.preventDefault();
    
    // Überprüfen der Browser-Unterstützung
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Ihr Browser unterstützt keine Kamera-Funktionen. Bitte verwenden Sie einen modernen Browser oder aktivieren Sie HTTPS.');
        return;
    }

    try {
        // Überprüfen der Kamera-Berechtigung
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        stream.getTracks().forEach(track => track.stop()); // Stream wieder freigeben

        // Wenn die Berechtigung erfolgreich war, Modal öffnen
        window.location.href = '/quick_scan';
    } catch (error) {
        console.error('Kamera-Fehler:', error);
        
        if (error.name === 'NotAllowedError') {
            alert('Bitte erlauben Sie den Zugriff auf die Kamera, um den Scanner zu nutzen.');
        } else if (error.name === 'NotFoundError') {
            alert('Keine Kamera gefunden. Bitte stellen Sie sicher, dass Ihr Gerät über eine Kamera verfügt.');
        } else {
            alert('Es gab einen Fehler beim Zugriff auf die Kamera. Bitte versuchen Sie es erneut oder verwenden Sie einen anderen Browser.');
        }
    }
}

// Wenn das Dokument geladen ist
document.addEventListener('DOMContentLoaded', function() {
    // Überprüfen der HTTPS-Verbindung
    if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
        console.warn('Scanner funktioniert am besten mit HTTPS');
    }
}); 