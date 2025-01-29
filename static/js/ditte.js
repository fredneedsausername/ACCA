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

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('[id="form-elimina-ditta"]').forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault(); // Prevent default submission
            
            // Show confirmation dialog
            const isConfirmed = confirm('Sei sicuro di voler eliminare questa ditta?');

            // If confirmed, submit the form
            if (isConfirmed) {
                this.submit();
            }
        });
    });
});


