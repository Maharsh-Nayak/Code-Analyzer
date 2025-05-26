document.addEventListener('DOMContentLoaded', () => {
    const roleSelect = document.getElementById('role');
    const analysisTypeSelect = document.getElementById('analysis-type');
    const codeInput = document.getElementById('input');
    const submitButton = document.getElementById('submit');
    const codeButton = document.getElementById('code-submit');
    const clearButton = document.getElementById('clear');
    const outputDiv = document.getElementById('output');
    const loadingOverlay = document.getElementById('loading');
    const feedbackForm = document.getElementById('feedback-form');
    const ratingButtons = document.querySelectorAll('.rating-btn');
    const feedbackText = document.getElementById('feedback-text');
    const submitFeedbackButton = document.getElementById('submit-feedback');
    const copyButton = document.querySelector('.copy-btn');
    const navItems = document.querySelectorAll('.nav-item');

    let currentRating = null;

    async function analyzeCode() {
        const role = roleSelect.value;
        const input = codeInput.value.trim();

        if (!input) {
            alert('Please enter some code or a question to analyze.');
            return;
        }

        console.log("sending code to server")
        console.log(role)
        console.log(input)
        console.log(analysisTypeSelect.value)

        try {
            showLoading();
            const response = await fetch('code-analyzer/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code: input,
                    role: role,
                    analysisType: analysisTypeSelect.value,
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to analyze code');
            }

            console.log(data)
            displayOutput(data.response);
            showFeedbackForm();
            
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoading();
        }
    }



    async function submitFeedback() {
        if (!currentRating) {
            alert('Please select a rating');
            return;
        }

        try {
            const response = await fetch('/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    rating: currentRating,
                    feedback_text: feedbackText.value.trim()
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to submit feedback');
            }

            alert('Thank you for your feedback!');
            feedbackForm.classList.add('hidden');
            resetFeedbackForm();
            
        } catch (error) {
            showError(error.message);
        }
    }

    function resetFeedbackForm() {
        currentRating = null;
        feedbackText.value = '';
        ratingButtons.forEach(btn => {
            btn.classList.remove('bg-blue-600', 'text-white');
            btn.classList.add('hover:bg-gray-100');
        });
    }

    function clearAll() {
        codeInput.value = '';
        outputDiv.textContent = '';
        feedbackForm.classList.add('hidden');
        resetFeedbackForm();
    }

    function showLoading() {
        loadingOverlay.classList.remove('hidden');
        codeButton.disabled = true;
    }

    function hideLoading() {
        loadingOverlay.classList.add('hidden');
        codeButton.disabled = false;
    }

    function showFeedbackForm() {
        feedbackForm.classList.remove('hidden');
    }

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        const container = document.querySelector('.analysis-container');
        container.insertBefore(errorDiv, container.firstChild);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        
        const container = document.querySelector('.analysis-container');
        container.insertBefore(successDiv, container.firstChild);
        
        setTimeout(() => {
            successDiv.remove();
        }, 5000);
    }

    function displayOutput(text) {
        outputDiv.innerHTML = text;
        Prism.highlightElement(outputDiv);
    }

    function handleCopy() {
        const text = outputDiv.textContent;
        if (!text) return;

        navigator.clipboard.writeText(text).then(() => {
            const originalText = copyButton.innerHTML;
            copyButton.innerHTML = `
                <svg class="copy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 6L9 17l-5-5"></path>
                </svg>
            `;
            setTimeout(() => {
                copyButton.innerHTML = originalText;
            }, 2000);
        });
    }

    function handleNavigation(event) {
        const section = event.currentTarget.dataset.section;
        navItems.forEach(item => item.classList.remove('active'));
        event.currentTarget.classList.add('active');
        
        if (section === 'repo-analyzer') {
            window.location.href = '/repo-analyzer';
        }
    }

    // Event listeners
    codeButton.addEventListener('click', analyzeCode);
    submitButton.addEventListener('click', analyzeCodebase);
    clearButton.addEventListener('click', clearAll);
    submitFeedbackButton.addEventListener('click', submitFeedback);
    copyButton.addEventListener('click', handleCopy);
    navItems.forEach(item => item.addEventListener('click', handleNavigation));

    // Rating button event listeners
    ratingButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            currentRating = parseInt(btn.dataset.rating);
            ratingButtons.forEach(b => {
                b.classList.remove('bg-blue-600', 'text-white');
                b.classList.add('hover:bg-gray-100');
            });
            btn.classList.remove('hover:bg-gray-100');
            btn.classList.add('bg-blue-600', 'text-white');
        });
    });

    // Allow Ctrl+Enter to submit
    codeInput.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            analyzeCode();
        }
    });

    // Codebase Analysis
    async function analyzeCodebase(repoPath) {
        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ repo_path: repoPath })
            });

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            const report = await response.json();
            return report;
        } catch (error) {
            console.error('Error analyzing codebase:', error);
            throw error;
        }
    }

    // Update the submit button handler
    document.getElementById('submit').addEventListener('click', async () => {
        const repoPath = codeInput.value.trim();
        if (!repoPath) {
            alert('Please enter a repository path');
            return;
        }

        // Show loading overlay
        document.getElementById('loading').classList.remove('hidden');

        try {
            const report = await analyzeCodebase(repoPath);
            
            // Render the report
            const outputDiv = document.getElementById('output');
            outputDiv.innerHTML = ''; // Clear previous content
            
            // Create and mount the AnalysisReport component
            const reportContainer = document.createElement('div');
            reportContainer.id = 'analysis-report';
            outputDiv.appendChild(reportContainer);
            
            // Initialize React component
            ReactDOM.render(
                React.createElement(AnalysisReport, { report }),
                reportContainer
            );

            // Show feedback form
            document.getElementById('feedback-form').classList.remove('hidden');
        } catch (error) {
            showError(error.message);
        } finally {
            // Hide loading overlay
            document.getElementById('loading').classList.add('hidden');
        }
    });
}); 