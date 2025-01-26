/* Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details */
async function confirmAction(action, id) {
    // Build a confirmation message
    const actionText = (action === 'elimina') ? 'eliminare' : 'aggiornare';
    const confirmMessage = `Sei sicuro di voler ${actionText} questo dipendente?`;
    
    if (action === 'aggiorna') {
        // GET for "update" – simply redirect to an update page with the ID
        window.location.href = `/aggiorna-dipendente?id=${id}`;
    }
}

function toggleDropdown() {
    const menu = document.getElementById('cerca-ditta-dropdown-menu');
    menu.classList.toggle('show');
}

function handleDropDownCercaDitteItemSelected(id) {
    window.location.href = `/dipendenti?id_ditta=${id}`
}

document.getElementById('form-elimina-dipendente').addEventListener('submit', function (e) {
    // Prevent the form from submitting immediately
    e.preventDefault();

    // Show a confirmation dialog
    const isConfirmed = confirm('Sei sicuro di voler eliminare questo dipendente?');

    // If the user confirms, submit the form
    if (isConfirmed) {
        this.submit(); // "this" refers to the form
    }
});