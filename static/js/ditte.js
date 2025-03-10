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
 * @param {string} fieldName - The field to update (e.g., "accesso", "badge", "blocca_accesso")
 */
function handleCheckboxClick(buttonElement, entityId, fieldName) {
    // Determine the entity type based on the field name or current page context
    let entityType;
    
    // If we're on the dipendenti page or using dipendente-specific fields
    if (fieldName === "accesso" || fieldName === "badge" || fieldName === "badge_sospeso") {
        entityType = "dipendente";
    } else if (fieldName === "ditta_individuale") {
        entityType = "ditta";
    } else {
        entityType = "ditta";
    }
    
    // Determine the current state by checking if the button contains a checkmark
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
        const contentType = response.headers.get('content-type');
        
        // If it's JSON, process normally
        if (contentType && contentType.includes('application/json')) {
            return response.json().then(data => {
                if (!response.ok) {
                    throw new Error(data.error || 'Errore nella risposta del server');
                }
                return data;
            });
        } 
        
        // If it's HTML, check for specific error patterns
        return response.text().then(html => {
            if (html.includes("Il suo account non dispone delle autorizzazioni necessarie")) {
                throw new Error('Non hai i permessi necessari per questa operazione');
            } else if (html.includes("Il suo account è stato disabilitato")) {
                throw new Error('Account disabilitato. Contatta l\'amministratore');
            } else if (html.includes("Sessione scaduta") || html.includes("login")) {
                throw new Error('Sessione scaduta. Effettua nuovamente il login');
            } else {
                throw new Error('Operazione non riuscita. Ricarica la pagina e riprova');
            }
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