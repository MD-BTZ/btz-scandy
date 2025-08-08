// Mobile Quickscan mit Kamera-Vorschau und BarcodeDetector
(function() {
  let mediaStream = null;
  let useEnvironment = true;
  let torchOn = false;
  let selectedItem = null; // { barcode, type, name, status, quantity }
  let selectedWorker = null; // { barcode, firstname, lastname }
  let currentStep = null; // 'item' | 'worker'
  let detectionActive = false;

  const els = {};

  function $(id) { return document.getElementById(id); }

  function setButtonState() {
    const confirmBtn = $('confirmMobileQuickscan');
    confirmBtn.disabled = !(selectedItem && selectedWorker);
    // Menge/Rückgabedatum erst bei bestätigungsbereit anzeigen
    const showQty = selectedItem && selectedWorker && selectedItem.type === 'consumable';
    const showReturn = selectedItem && selectedWorker && selectedItem.type === 'tool' && selectedItem.status !== 'ausgeliehen';
    const showActionBar = !!(selectedItem && selectedWorker);
    $('actionBar').classList.toggle('hidden', !showActionBar);
    $('quantityRow').classList.toggle('hidden', !showQty);
    $('returnDateRow').classList.toggle('hidden', !showReturn);
  }

  function setStep(step) {
    currentStep = step; // 'item' | 'worker'
    // UI-Karten hervorheben
    const itemBtn = $('scanItemBtn');
    const workerBtn = $('scanWorkerBtn');
    itemBtn.classList.remove('border-primary');
    workerBtn.classList.remove('border-primary');
    if (step === 'item') itemBtn.classList.add('border-primary');
    if (step === 'worker') workerBtn.classList.add('border-primary');
    $('scanHint').textContent = step === 'item' ? 'Scanne Artikel-Barcode…' : 'Scanne Mitarbeiter-Barcode…';
  }

  async function startCamera() {
    try {
      stopCamera();
      const constraints = {
        video: {
          facingMode: useEnvironment ? 'environment' : 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      };
      mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      els.video.srcObject = mediaStream;
      els.video.play().catch(() => {});
      // Versuche Torch (Blitz) zu setzen falls verfügbar
      await applyTorch(torchOn);
      startDetectLoop();
    } catch (e) {
      console.warn('Kamera konnte nicht gestartet werden:', e);
    }
  }

  function stopCamera() {
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop());
      mediaStream = null;
    }
    detectionActive = false;
  }

  async function applyTorch(on) {
    try {
      if (!mediaStream) return;
      const track = mediaStream.getVideoTracks()[0];
      const capabilities = track.getCapabilities?.();
      if (capabilities && capabilities.torch) {
        await track.applyConstraints({ advanced: [{ torch: !!on }] });
        torchOn = !!on;
        return true;
      }
    } catch (e) {
      console.debug('Torch nicht verfügbar:', e);
    }
    return false;
  }

  async function detectOnce() {
    if (!('BarcodeDetector' in window)) return;
    try {
      const detector = new BarcodeDetector({ formats: ['qr_code', 'ean_13', 'ean_8', 'code_128', 'code_39', 'codabar'] });
      const barcodes = await detector.detect(els.video);
      if (barcodes?.length) {
        handleBarcode(barcodes[0].rawValue.trim());
      }
    } catch (e) {
      // Ignorieren, weiter versuchen
    }
  }

  function startDetectLoop() {
    detectionActive = true;
    const loop = async () => {
      if (!detectionActive) return;
      await detectOnce();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  async function handleBarcode(code) {
    if (!code || !currentStep) return;
    if (currentStep === 'item') {
      await lookupItem(code);
      if (selectedItem) setStep('worker');
    } else if (currentStep === 'worker') {
      await lookupWorker(code);
    }
    setButtonState();
  }

  async function lookupItem(barcode) {
    try {
      // Erst Tool, sonst Consumable
      let res = await fetch(`/api/inventory/tools/${encodeURIComponent(barcode)}`);
      let data = await res.json();
      if (!data.success) {
        res = await fetch(`/api/inventory/consumables/${encodeURIComponent(barcode)}`);
        data = await res.json();
      }
      if (data.success) {
        const item = data.tool || data.consumable;
        selectedItem = {
          barcode: item.barcode,
          type: data.tool ? 'tool' : 'consumable',
          name: item.name || 'Artikel',
          status: item.status,
          quantity: typeof item.quantity === 'number' ? item.quantity : (item.current_stock || item.current_amount || 0)
        };
        $('itemSummary').textContent = `${selectedItem.name}`;
        $('scanItemBtn').classList.add('border-success');
        // Felder erst beim bestätigungsbereiten Zustand anzeigen (in setButtonState)
      } else {
        toast('error', 'Artikel nicht gefunden');
      }
    } catch (e) {
      toast('error', 'Fehler bei Artikelsuche');
    }
  }

  async function lookupWorker(barcode) {
    try {
      const res = await fetch(`/api/inventory/workers/${encodeURIComponent(barcode)}`);
      const data = await res.json();
      if (data.success) {
        const w = data.worker;
        selectedWorker = { barcode: w.barcode, firstname: w.firstname || '', lastname: w.lastname || '' };
        $('workerSummary').textContent = `${selectedWorker.firstname} ${selectedWorker.lastname}`.trim();
        $('scanWorkerBtn').classList.add('border-success');
      } else {
        toast('error', 'Mitarbeiter nicht gefunden');
      }
    } catch (e) {
      toast('error', 'Fehler bei Mitarbeitersuche');
    }
  }

  async function confirmAction() {
    if (!selectedItem || !selectedWorker) return;
    const payload = {
      item_barcode: selectedItem.barcode,
      worker_barcode: selectedWorker.barcode,
      action: selectedItem.type === 'consumable' ? 'use' : (selectedItem.status === 'ausgeliehen' ? 'return' : 'lend')
    };
    if (selectedItem.type === 'consumable') {
      const qty = parseInt($('qtyInput').value || '1', 10);
      payload.quantity = Math.max(1, isNaN(qty) ? 1 : qty);
    }
    if (selectedItem.type === 'tool' && selectedItem.status !== 'ausgeliehen') {
      const dateVal = $('returnDateInput').value;
      if (dateVal) payload.expected_return_date = dateVal;
    }
    try {
      const res = await fetch('/quick_scan/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && !data.error) {
        toast('success', data.message || 'Vorgang erfolgreich');
        resetState(true);
      } else {
        toast('error', data.error || 'Fehler bei der Verarbeitung');
      }
    } catch (e) {
      toast('error', 'Netzwerkfehler');
    }
  }

  function resetState(keepCamera = false) {
    selectedItem = null;
    selectedWorker = null;
    $('itemSummary').textContent = 'Tippen zum Scannen';
    $('workerSummary').textContent = 'Tippen zum Scannen';
    $('scanItemBtn').classList.remove('border-success', 'border-primary');
    $('scanWorkerBtn').classList.remove('border-success', 'border-primary');
    $('quantityRow').classList.add('hidden');
    $('returnDateRow').classList.add('hidden');
    $('qtyInput').value = '1';
    setStep('item');
    setButtonState();
    if (!keepCamera) stopCamera();
  }

  function toast(type, message) {
    if (typeof window.showToast === 'function') {
      window.showToast(type, message);
    } else {
      console.log(type.toUpperCase() + ': ' + message);
    }
  }

  function bindEvents() {
    $('scanItemBtn').addEventListener('click', async () => {
      setStep('item');
      await startCamera(); // iOS: getUserMedia im User-Gesture-Kontext
    });
    $('scanWorkerBtn').addEventListener('click', async () => {
      setStep('worker');
      await startCamera(); // iOS: getUserMedia im User-Gesture-Kontext
    });
    $('switchCameraBtn').addEventListener('click', async () => {
      useEnvironment = !useEnvironment;
      await startCamera();
    });
    $('toggleTorchBtn').addEventListener('click', async () => {
      const ok = await applyTorch(!torchOn);
      if (!ok) toast('info', 'Blitz nicht verfügbar');
    });
    $('qtyDec').addEventListener('click', (e) => {
      e.preventDefault();
      const el = $('qtyInput');
      const v = Math.max(1, (parseInt(el.value || '1', 10) || 1) - 1);
      el.value = String(v);
    });
    $('qtyInc').addEventListener('click', (e) => {
      e.preventDefault();
      const el = $('qtyInput');
      const v = Math.max(1, (parseInt(el.value || '1', 10) || 1) + 1);
      el.value = String(v);
    });
    $('confirmMobileQuickscan').addEventListener('click', confirmAction);
  }

  document.addEventListener('DOMContentLoaded', async () => {
    els.video = $('cameraPreview');
    if (!('mediaDevices' in navigator) || !navigator.mediaDevices.getUserMedia) {
      toast('warning', 'Kamera wird von diesem Browser nicht unterstützt');
      return;
    }
    bindEvents();
    setStep('item');
    setButtonState();
    // WICHTIG: Kamera erst nach User-Tap starten (iOS Safari-Anforderung)
  });
})();

