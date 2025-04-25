document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('diagnosticForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validate required fields
            const customerProblem = document.getElementById('customerProblem').value.trim();
            const diagnosticFiles = document.getElementById('diagnosticFiles').files;
            
            if (!customerProblem) {
                alert('Please enter the customer problem description.');
                return;
            }
            
            if (diagnosticFiles.length === 0) {
                alert('Please upload at least one diagnostic file.');
                return;
            }
            
            // Show loading state
            analyzeBtn.classList.add('loading');
            analyzeBtn.disabled = true;
            analyzeBtn.innerText = ' Analyzing...';
            loadingSpinner.classList.remove('d-none');
            
            // Create FormData object
            const formData = new FormData();
            formData.append('customer_problem', customerProblem);
            
            // Append all files
            for (let i = 0; i < diagnosticFiles.length; i++) {
                formData.append('diagnostic_files', diagnosticFiles[i]);
            }
            
            // Send data to server
            fetch('/analyze', {
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
                    analyzeBtn.innerText = 'Analyze';
                    loadingSpinner.classList.add('d-none');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while processing your request.');
                // Reset loading state
                analyzeBtn.classList.remove('loading');
                analyzeBtn.disabled = false;
                analyzeBtn.innerText = 'Analyze';
                loadingSpinner.classList.add('d-none');
            });
        });
    }
});