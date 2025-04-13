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

    // MODIFIED: Handle cancellation button click - removed automatic date setting
    cancelDateBtn.addEventListener('click', function() {
        dateInput.value = '';
        clearDateFlag.value = "1";
        cancelDateBtn.style.opacity = '0'; // Hide button after cancellation
        
        // No longer automatically setting the date when badge_temporaneo is checked
        // Will be enforced by form validation instead
    });

    // MODIFIED: Show the button when user enters a date - removed automatic date setting
    dateInput.addEventListener('input', function() {
        if (dateInput.value) {
            cancelDateBtn.style.opacity = '1'; // Show with fade in (transition in CSS)
            clearDateFlag.value = "0";
        } else {
            cancelDateBtn.style.opacity = '0'; // Hide when empty
            clearDateFlag.value = "1";
            
            // No longer automatically setting the date when badge_temporaneo is checked
            // Will be enforced by form validation instead
        }
    });

    // Reset flag if form is cancelled
    cancelForm.addEventListener('click', function() {
        // This is just for UI consistency, since the form won't be submitted anyway
        clearDateFlag.value = "0";
    });
    
    // Function to set expiration date to 14 days from now (kept for reference but no longer called automatically)
    function setDefaultExpirationDate() {
        const twoWeeksFromNow = new Date();
        twoWeeksFromNow.setDate(twoWeeksFromNow.getDate() + 14);
        
        // Format date as YYYY-MM-DD for the input
        const year = twoWeeksFromNow.getFullYear();
        const month = String(twoWeeksFromNow.getMonth() + 1).padStart(2, '0');
        const day = String(twoWeeksFromNow.getDate()).padStart(2, '0');
        
        dateInput.value = `${year}-${month}-${day}`;
        clearDateFlag.value = "0";
        cancelDateBtn.style.opacity = '1';
    }
    
    // Badge temporaneo functionality
    function toggleBadgeTemporaneo() {
        const isBadgeTemporaneo = document.getElementById('is_badge_temporaneo').checked;
        const numeroBadgeContainer = document.getElementById('numero_badge_container');
        const numeroBadgeInput = document.getElementById('numero_badge');
        
        // Show/hide and enable/disable the numero_badge field
        numeroBadgeContainer.style.display = isBadgeTemporaneo ? 'block' : 'none';
        numeroBadgeInput.disabled = !isBadgeTemporaneo;
        
        // Clear the numero_badge field if badge_temporaneo is unchecked
        if (!isBadgeTemporaneo) {
            numeroBadgeInput.value = '';
        }
        
        // MODIFIED: No longer automatically setting date when badge_temporaneo is checked
        // Form validation will still ensure a date is provided at submission
    }
    
    // Initialize badge_temporaneo behavior
    toggleBadgeTemporaneo();
    
    // Add event listener for badge_temporaneo checkbox
    document.getElementById('is_badge_temporaneo').addEventListener('change', toggleBadgeTemporaneo);
    
    // Form validation - unchanged
    document.querySelector('form').addEventListener('submit', function(e) {
        const isBadgeTemporaneo = document.getElementById('is_badge_temporaneo').checked;
        
        // If badge_temporaneo is checked, ensure a date is set
        if (isBadgeTemporaneo && !dateInput.value) {
            e.preventDefault();
            alert('È necessario specificare una data di scadenza per i badge temporanei');
        }
    });
});