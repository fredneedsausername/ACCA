/* Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details */
function confirmAction(action, id) {
    // Build a confirmation message
    const actionText = (action === 'elimina') ? 'eliminare' : 'aggiornare';
    const confirmMessage = `Sei sicuro di voler ${actionText} questa ditta?`;
    
    if (action === 'aggiorna') {
        // GET for "update" – simply redirect to an update page with the ID
        window.location.href = `/aggiorna-ditta?id=${id}`;
    }
}

document.getElementById("form-elimina-ditta").addEventListener('submit', function (e) {
    // Prevent the form from submitting immediately
    e.preventDefault();

    // Show a confirmation dialog
    const isConfirmed = confirm('Sei sicuro di voler eliminare questa ditta?');

    // If the user confirms, submit the form
    if (isConfirmed) {
        this.submit(); // "this" refers to the form
    }
});
