document.addEventListener('DOMContentLoaded', () => {
    const roleSelect = document.getElementById('role');
    const inputText = document.getElementById('input');
    const outputDiv = document.getElementById('output');
    const submitButton = document.getElementById('submit');
    const clearButton = document.getElementById('clear');
    const loadingOverlay = document.getElementById('loading');
    const feedbackForm = document.getElementById('feedback-form');
    const ratingButtons = document.querySelectorAll('.rating-btn');
    const feedbackText = document.getElementById('feedback-text');
    const submitFeedbackButton = document.getElementById('submit-feedback');

    let selectedRating = null;

    async function analyzeCode() {
        const role = roleSelect.value;
        const input = inputText.value.trim();

        if (!input) {
            alert('Please enter some code or a question to analyze.');
            return;
        }

        try {
            showLoading();
            const response = await fetch('code_analysis/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    role: role,
                    input: input
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to analyze code');
            }

            // For Model Response to Html
            outputDiv.innerHTML = data.response;
            
            // Show feedback form after successful analysis
            feedbackForm.classList.remove('hidden');
            resetFeedbackForm();
            
        } catch (error) {
            outputDiv.textContent = `Error: ${error.message}`;
        } finally {
            hideLoading();
        }
    }

    async function submitFeedback() {
        if (!selectedRating) {
            alert('Please select a rating');
            return;
        }

        try {
            const response = await fetch('code_analysis/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    role: roleSelect.value,
                    rating: selectedRating,
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
            alert(`Error submitting feedback: ${error.message}`);
        }
    }

    function resetFeedbackForm() {
        selectedRating = null;
        feedbackText.value = '';
        ratingButtons.forEach(btn => {
            btn.classList.remove('bg-blue-600', 'text-white');
            btn.classList.add('hover:bg-gray-100');
        });
    }

    function clearAll() {
        inputText.value = '';
        outputDiv.textContent = '';
        feedbackForm.classList.add('hidden');
        resetFeedbackForm();
    }

    function showLoading() {
        loadingOverlay.classList.remove('hidden');
        submitButton.disabled = true;
    }

    function hideLoading() {
        loadingOverlay.classList.add('hidden');
        submitButton.disabled = false;
    }

    // Event listeners
    submitButton.addEventListener('click', analyzeCode);
    clearButton.addEventListener('click', clearAll);
    submitFeedbackButton.addEventListener('click', submitFeedback);

    // Rating button event listeners
    ratingButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            selectedRating = parseInt(btn.dataset.rating);
            ratingButtons.forEach(b => {
                b.classList.remove('bg-blue-600', 'text-white');
                b.classList.add('hover:bg-gray-100');
            });
            btn.classList.remove('hover:bg-gray-100');
            btn.classList.add('bg-blue-600', 'text-white');
        });
    });

    // Allow Ctrl+Enter to submit
    inputText.addEventListener('keydown', (e) => {
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
        const repoPath = document.getElementById('input').value.trim();
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
            document.getElementById('output').innerHTML = `Error: ${error.message}`;
        } finally {
            // Hide loading overlay
            document.getElementById('loading').classList.add('hidden');
        }
    });
}); 