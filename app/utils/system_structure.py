import glob
import os
from ..models.database import Database
import sqlite3

def get_blueprint_info(path):
    """Extrahiert Informationen aus Blueprint-Dateien"""
    name = os.path.basename(path).replace('.py', '')
    routes = []
    
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
        # Einfache Route-Erkennung
        for line in content.split('\n'):
            if '@bp.route' in line:
                route = line.split("'")[1] if "'" in line else line.split('"')[1]
                routes.append(route)
    
    return {
        'name': name,
        'path': path,
        'routes': routes
    }

def get_template_info(path):
    """Analysiert Template-Dateien"""
    name = os.path.basename(path)
    rel_path = os.path.relpath(path, 'app/templates')
    
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
        # Einfache Block-Erkennung
        blocks = [line for line in content.split('\n') 
                 if '{% block' in line and 'endblock' not in line]
        
    return {
        'name': name,
        'path': rel_path,
        'blocks': blocks
    }

def get_table_schema(table):
    """Holt das Schema einer Datenbanktabelle"""
    try:
        schema = Database.query(f"PRAGMA table_info({table})")
        return [{
            'name': col['name'],
            'type': col['type'],
            'primary_key': bool(col['pk']),
            'nullable': not bool(col['notnull'])
        } for col in schema]
    except sqlite3.Error:
        return []

def get_system_structure():
    """Generiert die aktuelle Systemstruktur"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    structure = {
        'blueprints': {},
        'templates': {},
        'database': {},
        'connections': []
    }
    
    # Blueprints analysieren
    blueprint_paths = glob.glob(os.path.join(base_path, 'routes', '*.py'))
    for path in blueprint_paths:
        if not os.path.basename(path).startswith('__'):
            structure['blueprints'][os.path.basename(path)] = get_blueprint_info(path)
    
    # Templates analysieren
    template_paths = glob.glob(os.path.join(base_path, 'templates', '**', '*.html'), recursive=True)
    for path in template_paths:
        structure['templates'][os.path.relpath(path, os.path.join(base_path, 'templates'))] = get_template_info(path)
    
    # Datenbank analysieren
    try:
        tables = Database.query("SELECT name FROM sqlite_master WHERE type='table'")
        for table in tables:
            table_name = table['name']
            if not table_name.startswith('sqlite_'):
                structure['database'][table_name] = get_table_schema(table_name)
    except sqlite3.Error:
        pass
    
    # Verbindungen analysieren
    for bp_name, bp_info in structure['blueprints'].items():
        for route in bp_info.get('routes', []):
            structure['connections'].append({
                'from': f"bp_{bp_name}",
                'to': 'templates',
                'type': 'renders'
            })
    
    return structure 