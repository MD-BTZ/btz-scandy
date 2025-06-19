// Theme handling
document.addEventListener('DOMContentLoaded', function() {
    // Setze Standard-Theme
    if (!localStorage.getItem('theme')) {
        localStorage.setItem('theme', 'light');
    }
    
    // Wende Theme an
    document.documentElement.setAttribute('data-theme', localStorage.getItem('theme'));
}); 