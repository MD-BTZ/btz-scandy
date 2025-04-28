"""
Versionsverwaltung für Scandy
"""

# Version im Format MAJOR.MINOR.PATCH
# MAJOR: Inkompatible API-Änderungen
# MINOR: Neue Funktionalität, abwärtskompatibel
# PATCH: Fehlerbehebungen, abwärtskompatibel
VERSION = "1.0.1"

def get_version():
    """Gibt die aktuelle Version zurück"""
    return VERSION 