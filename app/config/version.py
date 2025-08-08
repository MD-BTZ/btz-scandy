"""
Versionsverwaltung für Scandy
"""

# Version im Format MAJOR.MINOR.PATCH
# MAJOR: Inkompatible API-Änderungen
# MINOR: Neue Funktionalität, abwärtskompatibel
# PATCH: Fehlerbehebungen, abwärtskompatibel
VERSION = "Beta 0.9.0"

# Autor
AUTHOR = "Andreas Klann"

def get_version():
    """Gibt die aktuelle Version zurück"""
    return VERSION

def get_author():
    """Gibt den Autor zurück"""
    return AUTHOR 