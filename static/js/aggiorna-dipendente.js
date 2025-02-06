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
});