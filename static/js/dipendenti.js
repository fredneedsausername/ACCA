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

function handleDropDownCercaDitteItemSelected(id) {
    window.location.href = `/dipendenti?id_ditta=${id}`
}

document.addEventListener("DOMContentLoaded", function () {
    // Select all forms with the ID or class for deleting employees
    document.querySelectorAll('[id="form-elimina-dipendente"]').forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault(); // Prevent default submission

            // Show confirmation dialog
            const isConfirmed = confirm('Sei sicuro di voler eliminare questo dipendente?');

            // If confirmed, submit the form
            if (isConfirmed) {
                this.submit(); // "this" refers to the form
            }
        });
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const toggleButton = document.getElementById("search-by-cognome-toggle");
    const dropdown = document.getElementById("search-by-cognome-dropdown");
    const searchButton = document.getElementById("search-by-cognome-submit");
    const searchInput = document.getElementById("search-by-cognome-input");

    // Toggle dropdown visibility
    toggleButton.addEventListener("click", function (event) {
        event.stopPropagation(); // Prevent event bubbling
        dropdown.classList.toggle("show");
    });

    // Hand le search submission
    function handleSearch() {
        const surname = searchInput.value.trim();
        if (surname) {
            window.location.href = `/dipendenti?cognome=${encodeURIComponent(surname)}`;
        } else {
            alert("Inserisci un cognome prima di cercare.");
        }
    }

    searchButton.addEventListener("click", handleSearch);

    // Allow "Enter" key to trigger search
    searchInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            handleSearch();
        }
    });

    // Close dropdown if clicking outside
    document.addEventListener("click", function (event) {
        if (!dropdown.contains(event.target) && !toggleButton.contains(event.target)) {
            dropdown.classList.remove("show");
        }
    });
});

function handleCheckboxClick(button, dipendente_id, clicked) {
    fetch("/checkbox-pressed", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        credentials: "include", // Sends cookies with request
        body: JSON.stringify({
            type: "dipendente",
            id: dipendente_id,
            clicked: clicked
        })
    })
    .catch(error => {
        console.error("Error:", error);
    });

    if (button.innerHTML.trim() === "✅") {
        button.innerHTML = "❌";
    } else {
        button.innerHTML = "✅";
    }
}