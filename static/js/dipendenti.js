/* Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details */
async function confirmAction(action, id) {
    // Build a confirmation message
    const actionText = (action === 'elimina') ? 'eliminare' : 'aggiornare';
    const confirmMessage = `Sei sicuro di voler ${actionText} questo dipendente?`;
    
    if (action === 'elimina') {
        if (confirm(confirmMessage)) {
            // POST for "delete"
            await fetch('/elimina-dipendente', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ id: id })
            })
            .then(response => {
                // If Flask sends a redirect (e.g., after deletion) we can follow it
                if (response.redirected) {
                    window.location.href = response.url;
                } else if (!response.ok) {
                    throw new Error('Errore durante l\'eliminazione');
                }
            })
            .catch(error => {
                console.error('Errore:', error);
                alert('Errore durante l\'eliminazione del dipendente');
            });
        }
        
    } else if (action === 'aggiorna') {
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