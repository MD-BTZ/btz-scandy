document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin Dashboard Script geladen');
    
    // Initial laden
    console.log('Starte initiales Laden...');
    loadDepartments();
    loadLocations();
    loadCategories();
    
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
});

// Lade-Funktionen
async function loadDepartments() {
    const departmentsList = document.getElementById('departmentsList');
    if (!departmentsList) return;
    
    try {
        console.log('Lade Abteilungen...');
        const response = await fetch('/admin/departments/list');
        console.log('Abteilungen Response:', response);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Abteilungen Daten:', data);
        
        if (data.success && data.departments) {
            departmentsList.innerHTML = data.departments.map(dept => `
                <tr>
                    <td>${dept.name}</td>
                    <td class="text-right">
                        <button class="btn btn-error btn-xs" onclick="deleteDepartment('${dept.name}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Fehler beim Laden der Abteilungen:', error);
    }
}

async function loadLocations() {
    const locationsList = document.getElementById('locationsList');
    if (!locationsList) return;
    
    try {
        console.log('Lade Standorte...');
        const response = await fetch('/admin/locations/list');
        console.log('Standorte Response:', response);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Standorte Daten:', data);
        
        if (data.success && data.locations) {
            locationsList.innerHTML = data.locations.map(loc => `
                <tr>
                    <td>${loc.name}</td>
                    <td class="text-right">
                        <button class="btn btn-error btn-xs" onclick="deleteLocation('${loc.name}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Fehler beim Laden der Standorte:', error);
    }
}

async function loadCategories() {
    const categoriesList = document.getElementById('categoriesList');
    if (!categoriesList) return;
    
    try {
        console.log('Lade Kategorien...');
        const response = await fetch('/admin/categories/list');
        console.log('Kategorien Response:', response);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Kategorien Daten:', data);
        
        if (data.success && data.categories) {
            categoriesList.innerHTML = data.categories.map(cat => `
                <tr>
                    <td>${cat.name}</td>
                    <td class="text-right">
                        <button class="btn btn-error btn-xs" onclick="deleteCategory('${cat.name}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Fehler beim Laden der Kategorien:', error);
    }
}

// Lösch-Funktionen
window.deleteDepartment = async function(name) {
    if (!confirm(`Möchten Sie die Abteilung "${name}" wirklich löschen?`)) return;
    try {
        const response = await fetch(`/admin/departments/${encodeURIComponent(name)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        const data = await response.json();
        if (data.success) {
            loadDepartments();
        } else {
            alert(data.message || 'Fehler beim Löschen der Abteilung');
        }
    } catch (error) {
        console.error('Fehler:', error);
        alert('Fehler beim Löschen der Abteilung');
    }
};

window.deleteLocation = async function(name) {
    if (!confirm(`Möchten Sie den Standort "${name}" wirklich löschen?`)) return;
    try {
        const response = await fetch(`/admin/locations/${encodeURIComponent(name)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        const data = await response.json();
        if (data.success) {
            loadLocations();
        } else {
            alert(data.message || 'Fehler beim Löschen des Standorts');
        }
    } catch (error) {
        console.error('Fehler:', error);
        alert('Fehler beim Löschen des Standorts');
    }
};

window.deleteCategory = async function(name) {
    if (!confirm(`Möchten Sie die Kategorie "${name}" wirklich löschen?`)) return;
    try {
        const response = await fetch(`/admin/categories/${encodeURIComponent(name)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        const data = await response.json();
        if (data.success) {
            loadCategories();
        } else {
            alert(data.message || 'Fehler beim Löschen der Kategorie');
        }
    } catch (error) {
        console.error('Fehler:', error);
        alert('Fehler beim Löschen der Kategorie');
    }
}; 