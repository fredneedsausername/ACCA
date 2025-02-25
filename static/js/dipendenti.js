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

/**
 * Handle button click for toggling state and send updates to the server
 * 
 * @param {HTMLElement} buttonElement - The button element that was clicked
 * @param {string} entityId - The ID of the entity to update
 * @param {string} fieldName - The field to update (e.g., "accesso", "badge")
 */
function handleCheckboxClick(buttonElement, entityId, fieldName) {
    // Entity type is always "dipendente" in this context
    const entityType = "dipendente";
    
    // Determine the current state by checking if the button contains a checkmark
    // We'll invert this to get the new state to set
    const currentStateHasCheckmark = buttonElement.innerHTML.includes('✅');
    const newState = currentStateHasCheckmark ? 0 : 1;
    
    // Create the request data
    const requestData = {
        type: entityType,
        id: entityId,
        field: fieldName,
        clicked: newState
    };
    
    // Show loading state
    const originalContent = buttonElement.innerHTML;
    buttonElement.innerHTML = ' ⟳ ';
    buttonElement.disabled = true;
    
    // Send the request to the server
    fetch('/checkbox-pressed', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(requestData),
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Errore nella risposta del server');
        }
        return response.json();
    })
    .then(data => {
        // Success handling
        console.log('Aggiornamento completato:', data.success);
        
        // Update the UI based on the new state
        // Keep using emojis for visual display while using 0/1 internally
        if (newState === 1) {
            buttonElement.innerHTML = ' ✅ ';
        } else {
            buttonElement.innerHTML = ' ❌ ';
        }
    })
    .catch(error => {
        console.error('Errore durante l\'aggiornamento:', error);
        
        // On error, revert to original content
        buttonElement.innerHTML = originalContent;
        
        // Show error message to user
        alert('Si è verificato un errore durante l\'aggiornamento. Riprova più tardi.');
    })
    .finally(() => {
        // Re-enable the button
        buttonElement.disabled = false;
    });
}