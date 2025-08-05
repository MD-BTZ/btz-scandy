"""
Konfiguration für Kantinenplan-API
"""

import os
from datetime import timedelta

# API-Konfiguration
CANTEEN_API_KEY = os.environ.get('CANTEEN_API_KEY', '')
CANTEEN_API_CACHE_DURATION = int(os.environ.get('CANTEEN_API_CACHE_DURATION', 300))  # 5 Minuten

# CORS-Einstellungen für API-Zugriff
CANTEEN_API_ALLOWED_ORIGINS = os.environ.get('CANTEEN_API_ALLOWED_ORIGINS', '*').split(',')

# Rate Limiting
CANTEEN_API_RATE_LIMIT = os.environ.get('CANTEEN_API_RATE_LIMIT', '100/hour')

# WordPress-Integration
WORDPRESS_CACHE_DURATION = 300  # 5 Minuten Cache für WordPress
WORDPRESS_FALLBACK_CACHE = 3600  # 1 Stunde Fallback-Cache

# API-Endpunkte
API_ENDPOINTS = {
    'current_week': '/api/canteen/current_week',
    'status': '/api/canteen/status',
    'health': '/api/canteen/health'
}

# Beispiel-Konfiguration für WordPress
WORDPRESS_CONFIG_EXAMPLE = """
// WordPress kantine_api.php Konfiguration
$scandy_api_url = 'https://your-scandy-server.com/api/canteen/current_week';
$api_key = 'your-api-key-here'; // Optional für Sicherheit
$cache_duration = 300; // 5 Minuten Cache
""" 