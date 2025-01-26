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

document.getElementById('myForm').addEventListener('submit', function (e) {
    e.preventDefault(); // Prevent the default form submission

    const formData = new FormData(this);

    fetch(this.action, {
        method: 'POST',
        body: formData
    })
    .then(response => response.text()) // Get the response as HTML text
    .then(html => {
        // Replace the entire page's HTML with the new HTML
        document.documentElement.innerHTML = html;
    })
    .catch(error => {
        console.error('Error:', error);
    });
});