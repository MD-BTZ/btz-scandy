// Admin Dashboard Script
console.log('Admin Dashboard Script geladen');

// Initialisierung
document.addEventListener('DOMContentLoaded', function() {
    console.log('Starte initiales Laden...');
    
    // Prüfe ob wir auf der Dashboard-Seite sind
    const isDashboardPage = document.querySelector('.container') !== null;
    
    if (isDashboardPage) {
        console.log('Dashboard-Seite erkannt - lade Dashboard-Funktionen');
        
        // Lade Abteilungen nur wenn das Element existiert
        const departmentsList = document.getElementById('departmentsList');
        if (departmentsList) {
            console.log('Lade Abteilungen...');
            loadDepartments();
        } else {
            console.log('DepartmentsList Element nicht gefunden');
        }
        
        // Lade Standorte nur wenn das Element existiert
        const locationsList = document.getElementById('locationsList');
        if (locationsList) {
            console.log('Lade Standorte...');
            loadLocations();
        } else {
            console.log('LocationsList Element nicht gefunden');
        }
        
        // Lade Kategorien nur wenn das Element existiert
        const categoriesList = document.getElementById('categoriesList');
        if (categoriesList) {
            console.log('Lade Kategorien...');
            loadCategories();
        } else {
            console.log('CategoriesList Element nicht gefunden');
        }
        
        // Lade Ticket-Kategorien nur wenn das Element existiert
        const ticketCategoriesList = document.getElementById('ticketCategoriesList');
        if (ticketCategoriesList) {
            console.log('Lade Ticket-Kategorien...');
            loadTicketCategories();
        } else {
            console.log('TicketCategoriesList Element nicht gefunden');
        }
    } else {
        console.log('Nicht auf Dashboard-Seite - überspringe Dashboard-Funktionen');
    }

    // Event Listener für Formulare - nur wenn sie existieren
    const addDepartmentForm = document.getElementById('addDepartmentForm');
    const addLocationForm = document.getElementById('addLocationForm');
    const addCategoryForm = document.getElementById('addCategoryForm');
    const addTicketCategoryForm = document.getElementById('addTicketCategoryForm');

    if (addDepartmentForm) {
        console.log('Department Form gefunden - Event Listener hinzugefügt');
        addDepartmentForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            
            try {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Hinzufügen...';
                
                const formData = new FormData(this);
                const response = await fetch('/admin/departments/add', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (data.success) {
                    this.reset();
                    await loadDepartments();
                    showToast('success', data.message);
                } else {
                    showToast('error', data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('error', 'Fehler beim Hinzufügen der Abteilung');
            } finally {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        });
    } else {
        console.log('Department Form nicht gefunden');
    }

    if (addLocationForm) {
        console.log('Location Form gefunden - Event Listener hinzugefügt');
        addLocationForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            
            try {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Hinzufügen...';
                
                const formData = new FormData(this);
                const metaDept = document.querySelector('meta[name="current-department"]');
                const dept = metaDept ? metaDept.getAttribute('content') : '';
                if (dept) formData.append('dept', dept);
                const response = await fetch('/admin/locations/add', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (data.success) {
                    this.reset();
                    await loadLocations();
                    showToast('success', data.message);
                } else {
                    showToast('error', data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('error', 'Fehler beim Hinzufügen des Standorts');
            } finally {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        });
    } else {
        console.log('Location Form nicht gefunden');
    }

    if (addCategoryForm) {
        console.log('Category Form gefunden - Event Listener hinzugefügt');
        addCategoryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            
            try {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Hinzufügen...';
                
                const formData = new FormData(this);
                const metaDept = document.querySelector('meta[name="current-department"]');
                const dept = metaDept ? metaDept.getAttribute('content') : '';
                if (dept) formData.append('dept', dept);
                const response = await fetch('/admin/categories/add', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (data.success) {
                    this.reset();
                    await loadCategories();
                    showToast('success', data.message);
                } else {
                    showToast('error', data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('error', 'Fehler beim Hinzufügen der Kategorie');
            } finally {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        });
    } else {
        console.log('Category Form nicht gefunden');
    }

    if (addTicketCategoryForm) {
        console.log('Ticket Category Form gefunden - Event Listener hinzugefügt');
        addTicketCategoryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            
            try {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Hinzufügen...';
                
                const formData = new FormData(this);
                const metaDept = document.querySelector('meta[name="current-department"]');
                const dept = metaDept ? metaDept.getAttribute('content') : '';
                if (dept) formData.append('dept', dept);
                const response = await fetch('/admin/ticket_categories/add', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (data.success) {
                    this.reset();
                    await loadTicketCategories();
                    showToast('success', data.message);
                } else {
                    showToast('error', data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('error', 'Fehler beim Hinzufügen der Ticket-Kategorie');
            } finally {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        });
    } else {
        console.log('Ticket Category Form nicht gefunden');
    }
});

async function fetchJson(url, options) {
    const resp = await fetch(url, Object.assign({headers: {'Accept': 'application/json'}}, options||{}));
    const ct = resp.headers.get('content-type') || '';
    if (resp.redirected || resp.url.includes('/auth/login') || (!ct.includes('application/json') && !ct.includes('json'))) {
        try { window.showToast && window.showToast('error', 'Bitte erneut anmelden'); } catch(e) {}
        window.location.href = '/auth/login';
        throw new Error('Not authenticated');
    }
    if (!resp.ok) {
        throw new Error('Request failed');
    }
    return resp.json();
}

// Lade Abteilungen
async function loadDepartments() {
    const tbody = document.getElementById('departmentsList');
    if (!tbody) {
        console.log('departmentsList Element nicht gefunden');
        return;
    }

    try {
        console.log('Lade Abteilungen von /admin/departments');
        const data = await fetchJson('/admin/departments');
        if (data.success) {
            console.log('Abteilungen geladen:', data.departments);
            tbody.innerHTML = data.departments.map(dept => `
                <tr>
                    <td>${dept.name}</td>
                    <td class="text-right">
                        <button onclick="deleteDepartment('${encodeURIComponent(dept.name)}')" 
                                class="btn btn-error btn-xs">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            console.error('Fehler beim Laden der Abteilungen:', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Laden der Abteilungen:', error);
    }
}

// Lade Standorte
async function loadLocations() {
    const tbody = document.getElementById('locationsList');
    if (!tbody) {
        console.log('locationsList Element nicht gefunden');
        return;
    }

    try {
        const metaDept = document.querySelector('meta[name="current-department"]');
        const dept = metaDept ? metaDept.getAttribute('content') : '';
        console.log('Lade Standorte von /admin/locations für Dept:', dept);
        const url = dept ? `/admin/locations?dept=${encodeURIComponent(dept)}` : '/admin/locations';
        const data = await fetchJson(url);
        if (data.success) {
            console.log('Standorte geladen:', data.locations);
            tbody.innerHTML = data.locations.map(loc => `
                <tr>
                    <td>${loc.name}</td>
                    <td class="text-right">
                        <button onclick="deleteLocation('${encodeURIComponent(loc.name)}')" 
                                class="btn btn-error btn-xs">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            console.error('Fehler beim Laden der Standorte:', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Laden der Standorte:', error);
    }
}

// Lade Kategorien
async function loadCategories() {
    const tbody = document.getElementById('categoriesList');
    if (!tbody) return;

    try {
        const metaDept = document.querySelector('meta[name="current-department"]');
        const dept = metaDept ? metaDept.getAttribute('content') : '';
        const url = dept ? `/admin/categories?dept=${encodeURIComponent(dept)}` : '/admin/categories';
        const data = await fetchJson(url);
        if (data.success) {
            tbody.innerHTML = data.categories.map(cat => `
                <tr>
                    <td>${cat.name}</td>
                    <td class="text-right">
                        <button onclick="deleteCategory('${encodeURIComponent(cat.name)}')" 
                                class="btn btn-error btn-xs">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            console.error('Fehler beim Laden der Kategorien:', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Laden der Kategorien:', error);
    }
}

// Lade Ticket-Kategorien
async function loadTicketCategories() {
    const tbody = document.getElementById('ticketCategoriesList');
    if (!tbody) return;

    try {
        const metaDept = document.querySelector('meta[name="current-department"]');
        const dept = metaDept ? metaDept.getAttribute('content') : '';
        const url = dept ? `/admin/ticket_categories?dept=${encodeURIComponent(dept)}` : '/admin/ticket_categories';
        const data = await fetchJson(url);
        if (data.success) {
            tbody.innerHTML = data.categories.map(cat => `
                <tr>
                    <td>${cat.name}</td>
                    <td class="text-right">
                        <button onclick="deleteTicketCategory('${encodeURIComponent(cat.name)}')" 
                                class="btn btn-error btn-xs">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            console.error('Fehler beim Laden der Ticket-Kategorien:', data.message);
        }
    } catch (error) {
        console.error('Fehler beim Laden der Ticket-Kategorien:', error);
    }
}

// Abteilung löschen
async function deleteDepartment(name) {
    if (confirm(`Möchten Sie die Abteilung "${decodeURIComponent(name)}" wirklich löschen?`)) {
        try {
            const response = await fetch(`/admin/departments/delete/${name}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                loadDepartments();
                showToast('success', data.message);
            } else {
                showToast('error', data.message);
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('error', 'Fehler beim Löschen der Abteilung');
        }
    }
}

// Standort löschen
async function deleteLocation(name) {
    if (confirm(`Möchten Sie den Standort "${decodeURIComponent(name)}" wirklich löschen?`)) {
        try {
            const response = await fetch(`/admin/locations/delete/${name}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                loadLocations();
                showToast('success', data.message);
            } else {
                showToast('error', data.message);
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('error', 'Fehler beim Löschen des Standorts');
        }
    }
}

// Kategorie löschen
async function deleteCategory(name) {
    if (confirm(`Möchten Sie die Kategorie "${decodeURIComponent(name)}" wirklich löschen?`)) {
        try {
            const response = await fetch(`/admin/categories/delete/${name}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                loadCategories();
                showToast('success', data.message);
            } else {
                showToast('error', data.message);
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('error', 'Fehler beim Löschen der Kategorie');
        }
    }
}

// Ticket-Kategorie löschen
async function deleteTicketCategory(name) {
    if (confirm(`Möchten Sie die Ticket-Kategorie "${decodeURIComponent(name)}" wirklich löschen?`)) {
        try {
            const response = await fetch(`/admin/ticket_categories/delete/${name}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                loadTicketCategories();
                showToast('success', data.message);
            } else {
                showToast('error', data.message);
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('error', 'Fehler beim Löschen der Ticket-Kategorie');
        }
    }
}

// Verbrauchstabelle (optional)
const consumableTable = document.querySelector('#consumableUsageTable');
if (consumableTable) {
    // Verbrauchstabellen-Logik
    const headers = consumableTable.querySelectorAll('th');
    
    headers.forEach(header => {
        header.addEventListener('click', function() {
            const column = this.dataset.column;
            let filterValue;
            
            // Verschiedene Filter-Typen je nach Spalte
            switch(column) {
                case 'consumable':
                case 'worker':
                    filterValue = prompt(`Nach ${this.textContent} filtern:`);
                    break;
                case 'amount':
                    filterValue = prompt('Nach Menge filtern (Zahl eingeben):', '1');
                    break;
                case 'date':
                    filterValue = prompt('Nach Datum filtern (YYYY-MM-DD):', new Date().toISOString().split('T')[0]);
                    break;
                default:
                    return;
            }
            
            if (filterValue === null || filterValue.trim() === '') return;

            // AJAX Request zum Server
            fetch('/admin/filter_consumable_usages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `filter_type=${column}&filter_value=${filterValue}`
            })
            .then(response => response.json())
            .then(data => {
                const tbody = consumableTable.querySelector('tbody');
                tbody.innerHTML = '';
                
                data.forEach(row => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${row.consumable_name}</td>
                        <td>${row.worker_name}</td>
                        <td>${row.quantity}</td>
                        <td>${new Date(row.timestamp).toLocaleString('de-DE', {
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        })}</td>
                    `;
                    tbody.appendChild(tr);
                });
            })
            .catch(error => console.error('Error:', error));
        });
    });
}

// Abteilungsverwaltung
const departmentsList = document.getElementById('departmentsList');

console.log('Departments List Element:', departmentsList);

// Standortverwaltung
const locationsList = document.getElementById('locationsList');

console.log('Locations List Element:', locationsList);

// Kategorieverwaltung
const categoriesList = document.getElementById('categoriesList');

console.log('Categories List Element:', categoriesList); 