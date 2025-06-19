// Tools page specific JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // QuickScan Button Handler
    const quickScanBtn = document.querySelector('.quickscan-button');
    if (quickScanBtn) {
        quickScanBtn.addEventListener('click', function() {
            const modal = document.getElementById('quickScanModal');
            if (modal) {
                modal.showModal();
                // Fokus auf Input nach kurzem Delay
                setTimeout(() => {
                    const input = document.getElementById('itemScanInput');
                    if (input) input.focus();
                }, 100);
            }
        });
    }
}); 