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
    const toggleButton = document.getElementById("search-by-nome-toggle");
    const dropdown = document.getElementById("search-by-nome-dropdown");
    const searchButton = document.getElementById("search-by-nome-submit");
    const searchInput = document.getElementById("search-by-nome-input");

    // Toggle dropdown visibility
    toggleButton.addEventListener("click", function (event) {
        event.stopPropagation(); // Prevent event bubbling
        dropdown.classList.toggle("show");
    });

    // Handle search submission
    function handleSearch() {
        const name = searchInput.value.trim();
        if (name) {
            window.location.href = `/ditte?nome=${encodeURIComponent(name)}`;
        } else {
            alert("Inserisci un nome ditta prima di cercare.");
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