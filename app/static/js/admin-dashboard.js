// Admin Dashboard Script
console.log('Admin Dashboard Script geladen');

// Initialisierung
document.addEventListener('DOMContentLoaded', function() {
    console.log('Starte initiales Laden...');
    
    // Lade Abteilungen
    loadDepartments();
    
    // Lade Standorte
    loadLocations();
    
    // Lade Kategorien
    loadCategories();
    
    // Lade Ticket-Kategorien (falls verfügbar)
    loadTicketCategories();

    // Event Listener für Formulare
    const addDepartmentForm = document.getElementById('addDepartmentForm');
    const addLocationForm = document.getElementById('addLocationForm');
    const addCategoryForm = document.getElementById('addCategoryForm');
    const addTicketCategoryForm = document.getElementById('addTicketCategoryForm');

    if (addDepartmentForm) {
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
    }

    if (addLocationForm) {
        addLocationForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            
            try {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Hinzufügen...';
                
                const formData = new FormData(this);
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
    }

    if (addCategoryForm) {
        addCategoryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            
            try {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Hinzufügen...';
                
                const formData = new FormData(this);
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
    }

    if (addTicketCategoryForm) {
        addTicketCategoryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            
            try {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Hinzufügen...';
                
                const formData = new FormData(this);
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
    }
});

// Lade Abteilungen
async function loadDepartments() {
    const tbody = document.getElementById('departmentsList');
    if (!tbody) return;

    try {
        const response = await fetch('/admin/departments');
        const data = await response.json();
        if (data.success) {
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
    if (!tbody) return;

    try {
        const response = await fetch('/admin/locations');
        const data = await response.json();
        if (data.success) {
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
        const response = await fetch('/admin/categories');
        const data = await response.json();
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
        const response = await fetch('/admin/ticket_categories');
        const data = await response.json();
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