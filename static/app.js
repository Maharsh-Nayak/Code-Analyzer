document.addEventListener('DOMContentLoaded', () => {
    const roleSelect = document.getElementById('role');
    const inputText = document.getElementById('input');
    const outputDiv = document.getElementById('output');
    const submitButton = document.getElementById('submit');
    const clearButton = document.getElementById('clear');
    const loadingOverlay = document.getElementById('loading');

    // Store feedback history
    let feedbackHistory = [];

    async function analyzeCode() {
        const role = roleSelect.value;
        const input = inputText.value.trim();

        if (!input) {
            alert('Please enter some code or a question to analyze.');
            return;
        }

        // Clear any existing feedback elements
        clearFeedbackElements();

        try {
            showLoading();
            const response = await fetch('/code-analyzer/api/analyze', {
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

            outputDiv.textContent = data.response;
            
            // Show feedback form if feedback is required
            if (data.requires_feedback) {
                showFeedbackForm(data.feedback_type, data.feedback_context);
            }
        } catch (error) {
            outputDiv.textContent = `Error: ${error.message}`;
        } finally {
            hideLoading();
        }
    }

    function clearAll() {
        inputText.value = '';
        outputDiv.textContent = '';
        clearFeedbackElements();
        feedbackHistory = [];
    }

    function showLoading() {
        loadingOverlay.classList.remove('hidden');
        submitButton.disabled = true;
    }

    function hideLoading() {
        loadingOverlay.classList.add('hidden');
        submitButton.disabled = false;
    }

    function clearFeedbackElements() {
        // Remove any existing feedback forms or thank you messages
        const existingFeedback = document.querySelector('.mt-6.p-4.bg-blue-50');
        const thankYouMessage = document.querySelector('.text-green-600');
        if (existingFeedback) existingFeedback.remove();
        if (thankYouMessage) thankYouMessage.remove();
    }

    function showFeedbackForm(type, context) {
        const feedbackHtml = `
            <div class="mt-6 p-4 bg-blue-50 rounded-lg">
                <h3 class="text-lg font-medium text-blue-800 mb-2">How was your experience?</h3>
                <div class="flex space-x-2 mb-3">
                    ${[1, 2, 3, 4, 5].map(rating => `
                        <button class="rating-btn px-3 py-1 rounded-full border border-blue-300 hover:bg-blue-100"
                                data-rating="${rating}">
                            ${rating}
                        </button>
                    `).join('')}
                </div>
                <textarea id="feedback-text" 
                          class="w-full p-2 border border-blue-300 rounded-md mb-3"
                          placeholder="Tell us more about your experience..."></textarea>
                <button id="submit-feedback" 
                        class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">
                    Submit Feedback
                </button>
            </div>
        `;
        
        const feedbackDiv = document.createElement('div');
        feedbackDiv.innerHTML = feedbackHtml;
        outputDiv.parentNode.appendChild(feedbackDiv);

        // Add event listeners for feedback
        const ratingButtons = feedbackDiv.querySelectorAll('.rating-btn');
        let selectedRating = 0;

        ratingButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                ratingButtons.forEach(b => b.classList.remove('bg-blue-200'));
                btn.classList.add('bg-blue-200');
                selectedRating = parseInt(btn.dataset.rating);
            });
        });

        feedbackDiv.querySelector('#submit-feedback').addEventListener('click', async () => {
            const feedbackText = feedbackDiv.querySelector('#feedback-text').value;
            
            if (!selectedRating) {
                alert('Please select a rating');
                return;
            }

            try {
                const response = await fetch('/feedback/api/submit-feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        type: type,
                        rating: selectedRating,
                        feedback_text: feedbackText,
                        additional_data: context
                    })
                });

                const data = await response.json();
                if (response.ok) {
                    // Store feedback in history
                    feedbackHistory.push({
                        type,
                        rating: selectedRating,
                        feedback: feedbackText,
                        context,
                        timestamp: new Date().toISOString()
                    });

                    // Show thank you message
                    feedbackDiv.innerHTML = '<p class="text-green-600">Thank you for your feedback!</p>';
                    
                    // Automatically remove thank you message after 3 seconds
                    setTimeout(() => {
                        const thankYouMessage = document.querySelector('.text-green-600');
                        if (thankYouMessage) {
                            thankYouMessage.remove();
                        }
                    }, 3000);
                } else {
                    throw new Error(data.error || 'Failed to submit feedback');
                }
            } catch (error) {
                feedbackDiv.innerHTML = `<p class="text-red-600">Error: ${error.message}</p>`;
            }
        });
    }

    // Event listeners
    submitButton.addEventListener('click', analyzeCode);
    clearButton.addEventListener('click', clearAll);

    // Allow Ctrl+Enter to submit
    inputText.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            analyzeCode();
        }
    });
}); 