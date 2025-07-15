// Versions-Updater für Scandy
// Aktualisiert die Versionsinformationen periodisch

class VersionUpdater {
    constructor() {
        this.updateInterval = 5 * 60 * 1000; // 5 Minuten
        this.versionDisplay = null;
        this.init();
    }

    init() {
        this.versionDisplay = document.querySelector('.version-display');
        if (this.versionDisplay) {
            this.startPeriodicUpdate();
        }
    }

    async updateVersionInfo() {
        try {
            const response = await fetch('/admin/version/check', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.updateVersionDisplay(data);
            }
        } catch (error) {
            console.error('Fehler beim Aktualisieren der Versionsinformationen:', error);
        }
    }

    updateVersionDisplay(versionInfo) {
        if (!this.versionDisplay) return;

        // Lokale Version aktualisieren
        const localVersion = this.versionDisplay.querySelector('.version-local');
        if (localVersion) {
            localVersion.textContent = versionInfo.local_version || 'Unbekannt';
        }

        // GitHub Version aktualisieren
        const githubVersion = this.versionDisplay.querySelector('.version-github');
        if (githubVersion) {
            if (versionInfo.github_version) {
                githubVersion.textContent = `GitHub: ${versionInfo.github_version}`;
                githubVersion.style.display = 'block';
                
                // Farbe basierend auf Status
                if (versionInfo.is_up_to_date) {
                    githubVersion.className = 'version-github text-success';
                } else if (versionInfo.update_available) {
                    githubVersion.className = 'version-github text-warning';
                } else {
                    githubVersion.className = 'version-github text-base-content/70';
                }
            } else {
                githubVersion.style.display = 'none';
            }
        }

        // Status-Indikator aktualisieren
        const statusIndicator = this.versionDisplay.querySelector('.version-status');
        if (statusIndicator) {
            if (versionInfo.github_version) {
                if (versionInfo.is_up_to_date) {
                    statusIndicator.textContent = '✓ Aktuell';
                    statusIndicator.className = 'version-status up-to-date';
                } else if (versionInfo.update_available) {
                    statusIndicator.textContent = '⚠ Update';
                    statusIndicator.className = 'version-status update-available';
                } else {
                    statusIndicator.textContent = '? Unbekannt';
                    statusIndicator.className = 'version-status unknown';
                }
            } else {
                statusIndicator.textContent = '? Verbindung fehlgeschlagen';
                statusIndicator.className = 'version-status error';
            }
        }
    }

    startPeriodicUpdate() {
        // Erste Aktualisierung nach 30 Sekunden
        setTimeout(() => {
            this.updateVersionInfo();
        }, 30000);

        // Periodische Aktualisierung
        setInterval(() => {
            this.updateVersionInfo();
        }, this.updateInterval);
    }

    // Manuelle Aktualisierung (für Debugging)
    forceUpdate() {
        this.updateVersionInfo();
    }
}

// Initialisiere den Version Updater wenn das DOM geladen ist
document.addEventListener('DOMContentLoaded', () => {
    window.versionUpdater = new VersionUpdater();
});

// Export für globale Verwendung
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VersionUpdater;
} 