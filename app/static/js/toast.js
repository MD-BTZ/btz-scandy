class Toast {
    constructor() {
        this.createToastContainer();
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-4 right-4 z-[9999] flex flex-col gap-2';
        document.body.appendChild(container);
    }

    show(message, type = 'info') {
        const toast = document.createElement('div');
        
        // Vereinfachte Farben: Grün für Erfolg, Rot für Fehler, Blau für Info, Gelb für Warnung
        const colors = {
            success: { bg: '#10b981', color: '#ffffff', icon: '✓' },
            error:   { bg: '#ef4444', color: '#ffffff', icon: '✕' },
            info:    { bg: '#3b82f6', color: '#ffffff', icon: 'ℹ' },
            warning: { bg: '#f59e0b', color: '#ffffff', icon: '⚠' }
        };

        const color = colors[type] || colors.info;

        toast.className = `toast toast-enter rounded-lg shadow-lg p-4 pr-12 relative min-w-[300px] max-w-[400px]`;
        toast.style.backgroundColor = color.bg;
        toast.style.color = color.color;
        toast.style.border = 'none';
        toast.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)';

        toast.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0 mr-3">
                    <span class="text-lg font-bold">${color.icon}</span>
                </div>
                <div class="flex-1">
                    <span class="text-sm font-medium">${message}</span>
                </div>
                <button class="close-btn absolute top-2 right-2 text-white hover:text-gray-200 transition-colors duration-200" onclick="this.parentElement.parentElement.remove()">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
        `;

        const container = document.getElementById('toast-container');
        container.appendChild(toast);

        // Nach 6 Sekunden ausblenden (erhöht von 3 auf 6 Sekunden)
        const timeout = setTimeout(() => {
            this.hideToast(toast);
        }, 6000);

        // Timeout beim Schließen löschen
        toast.addEventListener('click', (e) => {
            if (e.target.closest('.close-btn')) {
                clearTimeout(timeout);
            }
        });
    }

    hideToast(toast) {
        toast.classList.remove('toast-enter');
        toast.classList.add('toast-exit');
        setTimeout(() => {
            if (toast.parentElement) {
                toast.parentElement.removeChild(toast);
            }
        }, 300);
    }

    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }
}

// Globale Toast-Instanz erstellen
window.toast = new Toast();

// Globale showToast Funktion definieren
window.showToast = function(type, message) {
    window.toast.show(message, type);
}; 