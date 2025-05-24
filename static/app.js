document.addEventListener('DOMContentLoaded', () => {
    const roleSelect = document.getElementById('role');
    const inputText = document.getElementById('input');
    const outputDiv = document.getElementById('output');
    const submitButton = document.getElementById('submit');
    const clearButton = document.getElementById('clear');
    const loadingOverlay = document.getElementById('loading');

    async function analyzeCode() {
        const role = roleSelect.value;
        const input = inputText.value.trim();

        if (!input) {
            alert('Please enter some code or a question to analyze.');
            return;
        }

        try {
            showLoading();
            const response = await fetch('/api/analyze', {
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
        } catch (error) {
            outputDiv.textContent = `Error: ${error.message}`;
        } finally {
            hideLoading();
        }
    }

    function clearAll() {
        inputText.value = '';
        outputDiv.textContent = '';
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

    // Allow Ctrl+Enter to submit
    inputText.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            analyzeCode();
        }
    });
}); 