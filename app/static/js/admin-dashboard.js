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

    // Event Listener für Formulare
    const addDepartmentForm = document.getElementById('addDepartmentForm');
    const addLocationForm = document.getElementById('addLocationForm');
    const addCategoryForm = document.getElementById('addCategoryForm');

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
});

// Lade Abteilungen
async function loadDepartments() {
    try {
        const response = await fetch('/admin/departments');
        const data = await response.json();
        if (data.success) {
            const departmentsList = document.getElementById('departmentsList');
            departmentsList.innerHTML = data.departments.map(dept => `
                <tr class="hover:bg-base-200 transition-colors duration-200">
                    <td class="py-3">${dept.name}</td>
                    <td class="text-right py-3">
                        <button onclick="deleteDepartment('${dept.name}')" 
                                class="btn btn-error btn-xs hover:btn-error-focus transition-colors duration-200">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Fehler beim Laden der Abteilungen:', error);
        showToast('error', 'Fehler beim Laden der Abteilungen');
    }
}

// Lade Standorte
async function loadLocations() {
    try {
        const response = await fetch('/admin/locations');
        const data = await response.json();
        if (data.success) {
            const locationsList = document.getElementById('locationsList');
            locationsList.innerHTML = data.locations.map(loc => `
                <tr class="hover:bg-base-200 transition-colors duration-200">
                    <td class="py-3">${loc.name}</td>
                    <td class="text-right py-3">
                        <button onclick="deleteLocation('${loc.name}')" 
                                class="btn btn-error btn-xs hover:btn-error-focus transition-colors duration-200">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Fehler beim Laden der Standorte:', error);
        showToast('error', 'Fehler beim Laden der Standorte');
    }
}

// Lade Kategorien
async function loadCategories() {
    try {
        const response = await fetch('/admin/categories');
        const data = await response.json();
        if (data.success) {
            const categoriesList = document.getElementById('categoriesList');
            categoriesList.innerHTML = data.categories.map(cat => `
                <tr class="hover:bg-base-200 transition-colors duration-200">
                    <td class="py-3">${cat.name}</td>
                    <td class="text-right py-3">
                        <button onclick="deleteCategory('${cat.name}')" 
                                class="btn btn-error btn-xs hover:btn-error-focus transition-colors duration-200">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Fehler beim Laden der Kategorien:', error);
        showToast('error', 'Fehler beim Laden der Kategorien');
    }
}

// Löschfunktionen
async function deleteDepartment(name) {
    if (confirm(`Möchten Sie die Abteilung "${name}" wirklich löschen?`)) {
        try {
            const response = await fetch('/admin/departments/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `department=${encodeURIComponent(name)}`
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

async function deleteLocation(name) {
    if (confirm(`Möchten Sie den Standort "${name}" wirklich löschen?`)) {
        try {
            const response = await fetch('/admin/locations/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `location=${encodeURIComponent(name)}`
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

async function deleteCategory(name) {
    if (confirm(`Möchten Sie die Kategorie "${name}" wirklich löschen?`)) {
        try {
            const response = await fetch('/admin/categories/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `category=${encodeURIComponent(name)}`
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

console.log('Departments List Element:', departmentsList);

// Standortverwaltung
const locationsList = document.getElementById('locationsList');

console.log('Locations List Element:', locationsList);

// Kategorieverwaltung
const categoriesList = document.getElementById('categoriesList');

console.log('Categories List Element:', categoriesList);

// Toast-Funktion
function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} fixed top-4 right-4 z-50 transform transition-all duration-300 ease-in-out translate-x-full opacity-0`;
    
    // Icon basierend auf Typ
    let icon = '';
    switch(type) {
        case 'success':
            icon = '<i class="fas fa-check-circle mr-2"></i>';
            break;
        case 'error':
            icon = '<i class="fas fa-exclamation-circle mr-2"></i>';
            break;
        case 'warning':
            icon = '<i class="fas fa-exclamation-triangle mr-2"></i>';
            break;
        default:
            icon = '<i class="fas fa-info-circle mr-2"></i>';
    }
    
    toast.innerHTML = `
        <div class="alert alert-${type} shadow-lg">
            <div class="flex items-center">
                ${icon}
                <span>${message}</span>
            </div>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Animation starten
    requestAnimationFrame(() => {
        toast.classList.remove('translate-x-full', 'opacity-0');
    });
    
    // Toast nach 3 Sekunden ausblenden
    setTimeout(() => {
        toast.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
} 