document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('classSelectionForm');
    const analyzeBtn = document.getElementById('analyzeClassesBtn');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const selectAllCheckbox = document.getElementById('selectAllClasses');
    const classCheckboxes = document.querySelectorAll('.class-checkbox');
    
    // Handle "Select All" checkbox
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const isChecked = this.checked;
            classCheckboxes.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
        });
    }
    
    // Update "Select All" status when individual checkboxes change
    classCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const allChecked = Array.from(classCheckboxes).every(cb => cb.checked);
            const anyChecked = Array.from(classCheckboxes).some(cb => cb.checked);
            
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = allChecked;
                selectAllCheckbox.indeterminate = anyChecked && !allChecked;
            }
        });
    });
    
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validate at least one class is selected
            const selectedClasses = document.querySelectorAll('input[name="selected_classes"]:checked');
            if (selectedClasses.length === 0) {
                alert("Please select at least one class to analyze, or click 'Skip Class Analysis'.");
                return;
            }
            
            // Show loading state
            analyzeBtn.classList.add('loading');
            analyzeBtn.disabled = true;
            analyzeBtn.innerText = ' Analyzing...';
            loadingSpinner.classList.remove('d-none');
            
            // Create FormData object
            const formData = new FormData(form);
            
            // Send data to server
            fetch('/analyze_classes', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.redirect) {
                    window.location.href = data.redirect;
                } else {
                    alert('Error: ' + (data.error || 'Unknown error occurred'));
                    // Reset loading state
                    analyzeBtn.classList.remove('loading');
                    analyzeBtn.disabled = false;
                    analyzeBtn.innerText = 'Analyze Selected Classes';
                    loadingSpinner.classList.add('d-none');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while processing your request.');
                // Reset loading state
                analyzeBtn.classList.remove('loading');
                analyzeBtn.disabled = false;
                analyzeBtn.innerText = 'Analyze Selected Classes';
                loadingSpinner.classList.add('d-none');
            });
        });
    }
});
