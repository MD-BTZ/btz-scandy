"""
Unterdrückt lästige Bibliotheks-Warnungen
"""
import warnings
import sys

def suppress_all_deprecation_warnings():
    """Unterdrückt alle Deprecation Warnings"""
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
    warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
    warnings.filterwarnings("ignore", message=".*setuptools.*")

def suppress_docxcompose_warnings():
    """Speziell für docxcompose Warnungen"""
    warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
    warnings.filterwarnings("ignore", category=UserWarning, module="docxcompose")

# Rufe beide Funktionen beim Import auf
suppress_all_deprecation_warnings()
suppress_docxcompose_warnings() 