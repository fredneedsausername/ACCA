/* Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details */
document.addEventListener('DOMContentLoaded', function() {
    const selectedInput = document.getElementById('selected-ditta');
    const dropdown = document.getElementById('ditta-dropdown');
    const search = document.getElementById('ditta-search');
    const options = document.querySelectorAll('.option');
    const hiddenInput = document.getElementById('ditta-value');

    selectedInput.addEventListener('click', () => {
        dropdown.style.display = 'block';
        search.focus();
    });

    search.addEventListener('input', function(e) {
        const value = e.target.value.toLowerCase();
        options.forEach(option => {
            const isMatch = option.textContent.toLowerCase().includes(value);
            option.style.display = isMatch ? '' : 'none';
        });
    });

    options.forEach(option => {
        option.addEventListener('click', function() {
            selectedInput.value = this.textContent;
            hiddenInput.value = this.dataset.value;
            dropdown.style.display = 'none';
        });
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.custom-select')) {
            dropdown.style.display = 'none';
        }
    });
    
    // Date cancellation functionality
    const cancelDateBtn = document.getElementById('cancella-scadenza');
    const dateInput = document.getElementById('scadenza-autorizzazione');
    const clearDateFlag = document.getElementById('clear-date-flag');
    const cancelForm = document.querySelector('.annulla-button');

    // Initialize the button visibility based on date input
    if (dateInput.value) {
        cancelDateBtn.style.opacity = '1'; // Fully visible when date exists
    } else {
        cancelDateBtn.style.opacity = '0'; // Hidden when no date
        clearDateFlag.value = "1"; // Still set the flag value for server
    }

    // Handle cancellation button click
    cancelDateBtn.addEventListener('click', function() {
        dateInput.value = '';
        clearDateFlag.value = "1";
        cancelDateBtn.style.opacity = '0'; // Hide button after cancellation
    });

    // Show the button when user enters a date
    dateInput.addEventListener('input', function() {
        if (dateInput.value) {
            cancelDateBtn.style.opacity = '1'; // Show with fade in (transition in CSS)
            clearDateFlag.value = "0";
        } else {
            cancelDateBtn.style.opacity = '0'; // Hide when empty
            clearDateFlag.value = "1";
        }
    });

    // Reset flag if form is cancelled
    cancelForm.addEventListener('click', function() {
        // This is just for UI consistency, since the form won't be submitted anyway
        clearDateFlag.value = "0";
    });
});