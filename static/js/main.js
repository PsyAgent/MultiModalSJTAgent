// Main JavaScript for SJT Agent Application

// Utility functions
const utils = {
    // Show loading indicator
    showLoading: function(loadingElement) {
        if (loadingElement) {
            loadingElement.style.display = 'block';
        }
    },

    // Hide loading indicator
    hideLoading: function(loadingElement) {
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    },

    // Show error message
    showError: function(errorElement, message) {
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }
    },

    // Hide error message
    hideError: function(errorElement) {
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    },

    // Format JSON for display
    formatJSON: function(data) {
        return JSON.stringify(data, null, 2);
    },

    // Fetch API wrapper with error handling
    fetchAPI: async function(url, options = {}) {
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    }
};

// Highlight active navigation link
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.style.backgroundColor = 'var(--primary-color)';
        }
    });
});

// Export utils for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = utils;
}

// Add smooth scroll behavior
document.documentElement.style.scrollBehavior = 'smooth';

// Add form validation helper
function validateForm(formData) {
    const errors = [];

    if (!formData.trait_id) {
        errors.push('请选择人格特质');
    }

    if (!formData.item_id) {
        errors.push('请选择或输入题目编号');
    }

    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

// Console welcome message
console.log('%c SJT Agent ', 'background: #4a90e2; color: white; font-size: 20px; padding: 10px;');
console.log('%c 情境判断测试生成系统 ', 'color: #4a90e2; font-size: 14px;');
console.log('Based on NEO-PI-R personality assessment framework');
