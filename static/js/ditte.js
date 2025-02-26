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

/**
 * Handle button click for toggling state and send updates to the server
 * 
 * @param {HTMLElement} buttonElement - The button element that was clicked
 * @param {string} entityId - The ID of the entity to update
 * @param {string} fieldName - The field to update (e.g., "blocca_accesso")
 */
function handleCheckboxClick(buttonElement, entityId, fieldName) {
    // Entity type is always "ditta" in this context
    const entityType = "ditta";
    
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
    buttonElement.classList.add('rotating');
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
        // First get the JSON regardless of success/error status
        return response.json().then(data => {
            if (!response.ok) {
                // If request failed, create an error with the server's message
                throw new Error(data.error || 'Errore nella risposta del server');
            }
            return data;
        });
    })
    .then(data => {
        // Success handling
        console.log('Aggiornamento completato:', data.success);
        
        // Update the UI based on the new state
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
        alert(error.message);
    })
    .finally(() => {
        // Re-enable the button and remove rotation
        buttonElement.disabled = false;
        buttonElement.classList.remove('rotating');
    });
}