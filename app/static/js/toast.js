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
        const colors = {
            success: { bg: 'hsl(142.1 76.2% 36.3%)', color: '#fff' },
            error:   { bg: 'hsl(0 84.2% 60.2%)', color: '#fff' },
            info:    { bg: 'hsl(199 89% 48%)', color: '#fff' },
            warning: { bg: 'hsl(48 96% 53%)', color: '#fff' }
        };

        toast.className = `alert alert-${type} shadow-lg toast-enter`;
        toast.innerHTML = `
            <div>
                ${this.getIcon(type)}
                <span>${message}</span>
            </div>
        `;

        // Farben direkt setzen
        toast.style.backgroundColor = colors[type].bg;
        toast.style.color = colors[type].color;
        toast.style.border = 'none';
        toast.style.boxShadow = '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)';

        const container = document.getElementById('toast-container');
        container.appendChild(toast);

        // Nach 3 Sekunden ausblenden
        setTimeout(() => {
            toast.classList.remove('toast-enter');
            toast.classList.add('toast-exit');
            setTimeout(() => {
                container.removeChild(toast);
            }, 300);
        }, 3000);
    }

    getIcon(type) {
        const icons = {
            success: '<svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>',
            error: '<svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>',
            warning: '<svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>',
            info: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current flex-shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
        };
        return icons[type];
    }
}

// Globale Toast-Instanz erstellen
window.toast = new Toast();

// Globale showToast Funktion definieren
window.showToast = function(type, message) {
    window.toast.show(message, type);
}; 