document.addEventListener('DOMContentLoaded', () => {
    const repoUrlInput = document.getElementById('repoUrl');
    const analyzeButton = document.getElementById('analyze');
    const clearButton = document.getElementById('clear');
    const structureDiv = document.getElementById('structure');
    const languagesDiv = document.getElementById('languages');
    const loadingOverlay = document.getElementById('loading');

    function extractRepoInfo(url) {
        try {
            const urlObj = new URL(url);
            if (urlObj.hostname !== 'github.com') {
                throw new Error('Not a GitHub URL');
            }
            const parts = urlObj.pathname.split('/').filter(Boolean);
            if (parts.length < 2) {
                throw new Error('Invalid repository URL');
            }
            return {
                owner: parts[0],
                repo: parts[1]
            };
        } catch (error) {
            throw new Error('Invalid GitHub repository URL');
        }
    }

    async function analyzeRepository() {
        const url = repoUrlInput.value.trim();
        if (!url) {
            alert('Please enter a GitHub repository URL');
            return;
        }

        try {
            showLoading();
            const repoInfo = extractRepoInfo(url);
            
            const response = await fetch('/api/analyze-repo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(repoInfo)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to analyze repository');
            }

            // Display directory structure
            structureDiv.textContent = data.structure;

            // Display language analysis
            const languageContent = Object.entries(data.languages)
                .map(([lang, percentage]) => `${lang}: ${percentage.toFixed(1)}%`)
                .join('\n');
            languagesDiv.textContent = languageContent;

        } catch (error) {
            structureDiv.textContent = `Error: ${error.message}`;
            languagesDiv.textContent = '';
        } finally {
            hideLoading();
        }
    }

    function clearAll() {
        repoUrlInput.value = '';
        structureDiv.textContent = '';
        languagesDiv.textContent = '';
    }

    function showLoading() {
        loadingOverlay.classList.remove('hidden');
        analyzeButton.disabled = true;
    }

    function hideLoading() {
        loadingOverlay.classList.add('hidden');
        analyzeButton.disabled = false;
    }

    // Event listeners
    analyzeButton.addEventListener('click', analyzeRepository);
    clearButton.addEventListener('click', clearAll);

    // Allow Enter key to submit
    repoUrlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            analyzeRepository();
        }
    });
}); 