# app/constants.py
class Routes:
    # Admin Routes
    ADMIN_DASHBOARD = 'admin.dashboard'
    ADMIN_MANUAL_LENDING = 'admin.manual_lending'
    
    # Inventory Routes
    TOOLS_INDEX = 'inventory.tools'
    CONSUMABLES_INDEX = 'inventory.consumables'
    WORKERS_INDEX = 'inventory.workers'
    
    # Add Routes
    ADD_TOOL = 'inventory.add_tool'
    ADD_CONSUMABLE = 'inventory.add_consumable'
    ADD_WORKER = 'inventory.add_worker'
    
    # Detail Routes
    TOOL_DETAILS = 'inventory.tool_details'
    CONSUMABLE_DETAILS = 'inventory.consumable_details'
    WORKER_DETAILS = 'inventory.worker_details'
    
    # Auth Routes
    LOGIN = 'auth.login'
    LOGOUT = 'auth.logout'
    
    # Index Route
    INDEX = 'index.index'

class URLs:
    # Tools
    TOOLS_INDEX = 'inventory.tools'
    ADD_TOOL = 'inventory.add_tool'
    TOOL_DETAILS = 'inventory.tool_details'
    
    # Consumables
    CONSUMABLES_INDEX = 'inventory.consumables'
    ADD_CONSUMABLE = 'consumables.add'
    CONSUMABLE_DETAILS = 'consumables.details'
    
    # Workers
    WORKERS_INDEX = 'inventory.workers'
    ADD_WORKER = 'inventory.add_worker'
    WORKER_DETAILS = 'inventory.worker_details'
    
    # Auth
    LOGIN = 'auth.login'
    LOGOUT = 'auth.logout'