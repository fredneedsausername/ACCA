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

document.addEventListener("DOMContentLoaded", function () {
    const dropdown = document.getElementById("search-by-nome-dropdown");

    // Handle search submission
    function handleSearch() {
        const name = searchInput.value.trim();
        if (name) {
            window.location.href = `/ditte?nome=${encodeURIComponent(name)}`;
        } else {
            alert("Inserisci un nome ditta prima di cercare.");
        }
    }

    // Close dropdown if clicking outside
    document.addEventListener("click", function (event) {
        if (!dropdown.contains(event.target) && !toggleButton.contains(event.target)) {
            dropdown.classList.remove("show");
        }
    });
});

// Part that manages the cerca per nome ditta searchbar

function filterDitte(searchText) {
    const menu = document.getElementById('cerca-ditta-dropdown-menu');
    const buttons = menu.querySelectorAll('button');
    
    buttons.forEach(button => {
        const text = button.textContent.toLowerCase();
        button.style.display = text.includes(searchText.toLowerCase()) ? '' : 'none';
    });
}

function toggleDropdown() {
    const menu = document.getElementById('cerca-ditta-dropdown-menu');
    menu.classList.toggle('show');
    if (menu.classList.contains('show')) {
        document.getElementById('cerca-ditta-search').focus();
    }
}

document.addEventListener('click', function(event) {
    const menu = document.getElementById('cerca-ditta-dropdown-menu');
    const button = document.querySelector('.cerca-ditta-dropdown-button');
    if (!menu.contains(event.target) && !button.contains(event.target)) {
        menu.classList.remove('show');
    }
});

function handleDropDownCercaDitteItemSelected(nome) {
    window.location.href = `/ditte?nome=${nome}`
}