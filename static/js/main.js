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

// Background generation tasks
//
// Generation runs on the server as a background task. The page only holds a
// task id (kept in localStorage), so navigating away, reloading, or coming back
// later never kills the job — we just resume polling where we left off.
const SJTTasks = {
    POLL_INTERVAL: 2000,

    storageKey: function(kind) {
        return `sjt_task_${kind}`;
    },

    remember: function(kind, taskId) {
        try { localStorage.setItem(this.storageKey(kind), taskId); } catch (e) {}
    },

    recall: function(kind) {
        try { return localStorage.getItem(this.storageKey(kind)); } catch (e) { return null; }
    },

    forget: function(kind) {
        try { localStorage.removeItem(this.storageKey(kind)); } catch (e) {}
    },

    // handlers: { onRunning, onDone, onError, onIdle }
    attach: function(options) {
        const kind = options.kind;
        const endpoint = options.endpoint;
        const handlers = options;
        let timer = null;
        // True while we are following a task that was started before this page
        // was loaded, so the "resumed" wording stays put across polls.
        let resumed = false;

        function stopPolling() {
            if (timer) {
                clearInterval(timer);
                timer = null;
            }
        }

        function finish(taskId) {
            stopPolling();
            SJTTasks.forget(kind);
            // Let the server drop it so it stops showing in the running list.
            fetch(`/api/task/${taskId}`, { method: 'DELETE' }).catch(() => {});
        }

        async function check(taskId) {
            let response;
            try {
                response = await fetch(`/api/task/${taskId}`);
            } catch (error) {
                // Transient network hiccup — keep polling.
                console.warn('Task poll failed, retrying:', error);
                return;
            }

            if (response.status === 404) {
                // Server restarted or the task was already consumed.
                stopPolling();
                SJTTasks.forget(kind);
                if (handlers.onIdle) handlers.onIdle();
                return;
            }

            const task = await response.json();

            if (task.status === 'running') {
                if (handlers.onRunning) handlers.onRunning(task, resumed);
                return;
            }

            finish(taskId);

            if (task.status === 'done') {
                if (handlers.onDone) handlers.onDone(task.result, task);
            } else {
                if (handlers.onError) handlers.onError(task.error || '生成失败', task);
            }
        }

        function watch(taskId, isResume) {
            stopPolling();
            resumed = isResume;
            check(taskId);
            timer = setInterval(() => check(taskId), SJTTasks.POLL_INTERVAL);
        }

        return {
            // Resume a task started before the page was left/reloaded.
            resume: function() {
                const taskId = SJTTasks.recall(kind);
                if (taskId) watch(taskId, true);
                return !!taskId;
            },

            start: async function(payload) {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();

                if (!response.ok || !data.task_id) {
                    throw new Error(data.error || '任务提交失败');
                }

                SJTTasks.remember(kind, data.task_id);
                watch(data.task_id, false);
                return data.task_id;
            },

            stopPolling: stopPolling
        };
    }
};

// Global banner: keeps background jobs visible from any page.
document.addEventListener('DOMContentLoaded', function() {
    const banner = document.getElementById('running-tasks-banner');
    if (!banner) return;

    async function refresh() {
        try {
            const response = await fetch('/api/tasks?status=running');
            const data = await response.json();
            const tasks = data.tasks || [];

            if (tasks.length === 0) {
                banner.style.display = 'none';
                return;
            }

            // 失败会自动重跑，标出来免得用户以为卡住了
            const names = tasks.map(t => (
                t.attempt > 1 ? `${t.label}（重试 ${t.attempt}/${t.attempts}）` : t.label
            )).join('、');
            banner.innerHTML = `<span class="running-tasks-dot"></span>
                <span>${tasks.length} 个任务正在后台生成：${names}（可自由切换页面，结果不会丢失）</span>`;
            banner.style.display = 'flex';
        } catch (error) {
            banner.style.display = 'none';
        }
    }

    refresh();
    setInterval(refresh, 5000);
});

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
