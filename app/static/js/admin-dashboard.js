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
});

// Abteilungen laden
function loadDepartments() {
    console.log('Lade Abteilungen...');
    fetch('/admin/departments/list')
        .then(response => response.json())
        .then(data => {
            const departmentsList = document.getElementById('departmentsList');
            departmentsList.innerHTML = '';
            if (data.departments && Array.isArray(data.departments)) {
                data.departments.slice(0, 10).forEach(department => {
                    const name = department.name || department;
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${name}</td>
                        <td class="text-right">
                            <button class="btn btn-error btn-xs delete-btn" data-name="${name}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    `;
                    departmentsList.appendChild(row);
                });
                // Event-Listener für Löschen-Buttons
                departmentsList.querySelectorAll('.delete-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const name = this.dataset.name;
                        deleteDepartment(name);
                    });
                });
            }
        })
        .catch(error => console.error('Fehler beim Laden der Abteilungen:', error));
}

// Standorte laden
function loadLocations() {
    console.log('Lade Standorte...');
    fetch('/admin/locations/list')
        .then(response => response.json())
        .then(data => {
            const locationsList = document.getElementById('locationsList');
            locationsList.innerHTML = '';
            if (data.locations && Array.isArray(data.locations)) {
                data.locations.slice(0, 10).forEach(location => {
                    const name = location.name || location;
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${name}</td>
                        <td class="text-right">
                            <button class="btn btn-error btn-xs delete-btn" data-name="${name}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    `;
                    locationsList.appendChild(row);
                });
                // Event-Listener für Löschen-Buttons
                locationsList.querySelectorAll('.delete-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const name = this.dataset.name;
                        deleteLocation(name);
                    });
                });
            }
        })
        .catch(error => console.error('Fehler beim Laden der Standorte:', error));
}

// Kategorien laden
function loadCategories() {
    console.log('Lade Kategorien...');
    fetch('/admin/categories/list')
        .then(response => response.json())
        .then(data => {
            const categoriesList = document.getElementById('categoriesList');
            categoriesList.innerHTML = '';
            if (data.categories && Array.isArray(data.categories)) {
                data.categories.slice(0, 10).forEach(category => {
                    const name = category.name || category;
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${name}</td>
                        <td class="text-right">
                            <button class="btn btn-error btn-xs delete-btn" data-name="${name}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    `;
                    categoriesList.appendChild(row);
                });
                // Event-Listener für Löschen-Buttons
                categoriesList.querySelectorAll('.delete-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const name = this.dataset.name;
                        deleteCategory(name);
                    });
                });
            }
        })
        .catch(error => console.error('Fehler beim Laden der Kategorien:', error));
}

// Abteilung löschen
function deleteDepartment(name) {
    if (confirm('Möchten Sie diese Abteilung wirklich löschen?')) {
        fetch(`/admin/departments/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadDepartments();
            } else {
                alert('Fehler beim Löschen der Abteilung: ' + data.message);
            }
        })
        .catch(error => console.error('Fehler beim Löschen der Abteilung:', error));
    }
}

// Standort löschen
function deleteLocation(name) {
    if (confirm('Möchten Sie diesen Standort wirklich löschen?')) {
        fetch(`/admin/locations/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadLocations();
            } else {
                alert('Fehler beim Löschen des Standorts: ' + data.message);
            }
        })
        .catch(error => console.error('Fehler beim Löschen des Standorts:', error));
    }
}

// Kategorie löschen
function deleteCategory(name) {
    if (confirm('Möchten Sie diese Kategorie wirklich löschen?')) {
        fetch(`/admin/categories/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadCategories();
            } else {
                alert('Fehler beim Löschen der Kategorie: ' + data.message);
            }
        })
        .catch(error => console.error('Fehler beim Löschen der Kategorie:', error));
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
                        <td>${new Date(row.timestamp).toLocaleString()}</td>
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
const addDepartmentForm = document.getElementById('addDepartmentForm');

console.log('Departments List Element:', departmentsList);
console.log('Add Department Form:', addDepartmentForm);

if (addDepartmentForm) {
    addDepartmentForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        try {
            const response = await fetch('/admin/departments/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: formData.get('department')
                })
            });
            const data = await response.json();
            if (data.success) {
                loadDepartments();
                this.reset();
            } else {
                alert(data.message || 'Fehler beim Hinzufügen der Abteilung');
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Hinzufügen der Abteilung');
        }
    });
}

// Standortverwaltung
const locationsList = document.getElementById('locationsList');
const addLocationForm = document.getElementById('addLocationForm');

if (addLocationForm) {
    addLocationForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        try {
            const response = await fetch('/admin/locations/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: formData.get('location')
                })
            });
            const data = await response.json();
            if (data.success) {
                loadLocations();
                this.reset();
            } else {
                alert(data.message || 'Fehler beim Hinzufügen des Standorts');
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Hinzufügen des Standorts');
        }
    });
}

// Kategorieverwaltung
const categoriesList = document.getElementById('categoriesList');
const addCategoryForm = document.getElementById('addCategoryForm');

if (addCategoryForm) {
    addCategoryForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        try {
            const response = await fetch('/admin/categories/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: formData.get('category')
                })
            });
            const data = await response.json();
            if (data.success) {
                loadCategories();
                this.reset();
            } else {
                alert(data.message || 'Fehler beim Hinzufügen der Kategorie');
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Hinzufügen der Kategorie');
        }
    });
} 