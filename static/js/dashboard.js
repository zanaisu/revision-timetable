/**
 * Dashboard functionality for Revision Timetable
 */

// Main initialization when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize sidebar
    initSidebar();
    
    // Set current day and load appropriate tasks
    setCurrentDay();
    
    // Handle task checkboxes
    initTaskTracking();
    
    // Handle theme changes
    initThemeObserver();
    
    // Handle task completion forms
    initTaskCompletionForms();
});

/**
 * Initialize sidebar functionality
 */
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarIcon = document.getElementById('sidebarIcon');
    const miniSidebar = document.getElementById('sidebarMini');
    
    // If sidebar doesn't exist, we're not on a page with a sidebar
    if (!sidebar) return;
    
    // Set initial state from localStorage if available
    const savedState = localStorage.getItem('sidebarOpen');
    const sidebarOpen = savedState ? savedState === 'true' : true;
    
    if (sidebarOpen) {
        document.body.classList.add('sidebar-open');
        sidebar.classList.remove('sidebar-collapsed');
        if (sidebarIcon) sidebarIcon.classList.replace('fa-bars', 'fa-times');
        if (miniSidebar) miniSidebar.classList.add('hidden');
    } else {
        document.body.classList.remove('sidebar-open');
        sidebar.classList.add('sidebar-collapsed');
        if (sidebarIcon) sidebarIcon.classList.replace('fa-times', 'fa-bars');
        if (miniSidebar) miniSidebar.classList.remove('hidden');
    }
    
    // Toggle sidebar on click
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // Handle mini sidebar buttons
    document.querySelectorAll('.mini-button').forEach(btn => {
        btn.addEventListener('click', function() {
            if (this.dataset.action === 'toggle') {
                toggleSidebar();
            }
        });
    });
}

/**
 * Toggle sidebar open/closed state
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarIcon = document.getElementById('sidebarIcon');
    const miniSidebar = document.getElementById('sidebarMini');
    
    document.body.classList.toggle('sidebar-open');
    sidebar.classList.toggle('sidebar-collapsed');
    
    const isOpen = document.body.classList.contains('sidebar-open');
    
    // Update icon and mini sidebar visibility
    if (isOpen) {
        if (sidebarIcon) sidebarIcon.classList.replace('fa-bars', 'fa-times');
        if (miniSidebar) miniSidebar.classList.add('hidden');
    } else {
        if (sidebarIcon) sidebarIcon.classList.replace('fa-times', 'fa-bars');
        if (miniSidebar) miniSidebar.classList.remove('hidden');
    }
    
    // Save state to localStorage
    localStorage.setItem('sidebarOpen', isOpen);
}

/**
 * Set current day and show relevant tasks
 */
function setCurrentDay() {
    const date = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December'];
    
    // Update current day display if it exists
    const currentDayEl = document.getElementById('current-day');
    if (currentDayEl) {
        currentDayEl.textContent = `${days[date.getDay()]}, ${months[date.getMonth()]} ${date.getDate()}`;
    }
    
    // Show tasks for today
    showTasksForDay(days[date.getDay()]);
    
    // Handle weekend tasks container if it exists
    const weekendContainer = document.getElementById('weekend-tasks-container');
    if (weekendContainer) {
        const isWeekend = date.getDay() === 0 || date.getDay() === 6;
        weekendContainer.style.display = isWeekend ? 'block' : 'none';
    }
}

/**
 * Display tasks for a specific day
 */
function showTasksForDay(day) {
    const dayContainers = document.querySelectorAll('.day-tasks');
    dayContainers.forEach(container => {
        container.style.display = container.id === `tasks-${day}` ? 'block' : 'none';
    });
}

/**
 * Initialize task checkbox functionality
 */
function initTaskTracking() {
    const checkboxes = document.querySelectorAll('.task-checkbox');
    const pointsDisplay = document.getElementById('total-points');
    
    // Exit if there are no checkboxes or points display
    if (!checkboxes.length || !pointsDisplay) return;
    
    // Update points when checkboxes change
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updatePoints);
    });
    
    // Initial points calculation
    updatePoints();
}

/**
 * Calculate and update total points from checked tasks
 */
function updatePoints() {
    const checkboxes = document.querySelectorAll('.task-checkbox');
    const pointsDisplay = document.getElementById('total-points');
    
    // Exit if there are no checkboxes or points display
    if (!checkboxes.length || !pointsDisplay) return;
    
    let total = 0;
    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            total += parseInt(checkbox.getAttribute('data-points') || 0);
        }
    });
    
    pointsDisplay.textContent = total;
}

/**
 * Toggle between showing today's tasks and the full week
 */
function toggleCalendarView() {
    const dayContainers = document.querySelectorAll('.day-tasks');
    const showingToday = dayContainers[0].style.display === 'none';
    
    if (showingToday) {
        // Show only today's tasks
        setCurrentDay();
    } else {
        // Show all days
        dayContainers.forEach(container => {
            container.style.display = 'block';
        });
    }
    
    // Update button text if it exists
    const toggleButton = document.querySelector('button[onclick="toggleCalendarView()"]');
    if (toggleButton) {
        toggleButton.textContent = showingToday ? 'Show All Days' : 'Show Today Only';
    }
}

/**
 * Open the calendar modal
 */
function openCalendarModal() {
    const modal = document.querySelector('.calendar-modal');
    const overlay = document.querySelector('.modal-overlay');
    
    if (modal && overlay) {
        modal.style.display = 'block';
        overlay.style.display = 'block';
        
        // Initialize exam markers as clickable
        setTimeout(initializeExamMarkers, 100);
    }
}

/**
 * Close the calendar modal
 */
function closeCalendarModal() {
    const modal = document.querySelector('.calendar-modal');
    const overlay = document.querySelector('.modal-overlay');
    
    if (modal && overlay) {
        modal.style.display = 'none';
        overlay.style.display = 'none';
    }
}

/**
 * Initialize theme observer to update UI when theme changes
 */
function initThemeObserver() {
    // Watch for theme attribute changes on the root element to update UI components
    const observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            if (mutation.attributeName === 'data-theme') {
                const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                updateThemeUI(isDark);
            }
        });
    });
    
    observer.observe(document.documentElement, { attributes: true });
    
    // Initial UI update
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    updateThemeUI(isDark);
}

/**
 * Update UI elements based on current theme
 */
function updateThemeUI(isDark) {
    // Update theme toggle icon text if it exists
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.textContent = isDark ? '☀️' : '🌙';
    }
    
    // Update theme text if it exists
    const themeText = document.getElementById('themeText');
    if (themeText) {
        themeText.textContent = isDark ? 'Light Mode' : 'Dark Mode';
    }
}

/**
 * Initialize exam markers to show tooltips and scroll to exam details
 * This is called when the calendar modal is opened
 */
function initializeExamMarkers() {
    // Add hover behavior to exam days
    document.querySelectorAll('.day-card.has-exam').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('highlight-exam');
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('highlight-exam');
        });
        
        // Add click behavior to scroll to subject section
        card.addEventListener('click', function() {
            const examTag = this.querySelector('.exam-tag');
            if (examTag) {
                const subject = examTag.dataset.subject;
                const targetSection = document.getElementById(`subject-${subject.toLowerCase()}`);
                if (targetSection) {
                    // Scroll to the section
                    targetSection.scrollIntoView({ behavior: 'smooth' });
                    // Highlight it temporarily
                    targetSection.classList.add('highlight-section');
                    setTimeout(() => {
                        targetSection.classList.remove('highlight-section');
                    }, 2000);
                }
            }
        });
    });
    
    // Make exam links in the list clickable
    document.querySelectorAll('.exam-item').forEach(item => {
        item.style.cursor = 'pointer';
        item.addEventListener('click', function() {
            const subject = this.querySelector('strong').innerText.replace(':', '').trim();
            const targetSection = document.getElementById(`subject-${subject.toLowerCase()}`);
            if (targetSection) {
                // Scroll to the section
                targetSection.scrollIntoView({ behavior: 'smooth' });
                // Highlight it temporarily
                targetSection.classList.add('highlight-section');
                setTimeout(() => {
                    targetSection.classList.remove('highlight-section');
                }, 2000);
            }
        });
    });
}

/**
 * Initialize task completion form handling
 */
function initTaskCompletionForms() {
    const taskCompleteForms = document.querySelectorAll('.task-complete-form');
    
    taskCompleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Prevent default form submission
            e.preventDefault();
            
            // Find the task container
            const taskCard = this.closest('.task-card');
            const taskItem = this.closest('.task-item');
            const taskContainer = taskCard || taskItem;
            
            if (!taskContainer) return;
            
            // If task is already completed, do nothing
            if (taskContainer.classList.contains('completed')) {
                return;
            }
            
            // Get the button and show a visual feedback
            const btn = this.querySelector('button');
            const originalHtml = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            btn.disabled = true;
            
            // Get form data
            const formData = new FormData(this);
            const taskName = formData.get('task');
            const subject = formData.get('subject');
            
            // Send AJAX request to complete_task endpoint
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Success - mark task as complete
                    btn.innerHTML = originalHtml;
                    
                    // Add completed class for styling
                    taskContainer.classList.add('task-complete-animation');
                    setTimeout(() => {
                        taskContainer.classList.add('completed');
                        taskContainer.classList.remove('task-complete-animation');
                    }, 300);
                    
                    // Show success message
                    showToast(`Task "${taskName}" marked as complete!`, 'success');
                } else {
                    // Error
                    btn.innerHTML = originalHtml;
                    btn.disabled = false;
                    showToast('Error: ' + (data.message || 'Could not complete task'), 'danger');
                }
            })
            .catch(error => {
                btn.innerHTML = originalHtml;
                btn.disabled = false;
                showToast('Error: ' + error.message, 'danger');
            });
        });
    });
}

// Toast notification function
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center border-0 bg-${type} text-white`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    const toastContent = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toast.innerHTML = toastContent;
    toastContainer.appendChild(toast);
    
    // Initialize Bootstrap toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    
    // Show the toast
    bsToast.show();
    
    // Remove from DOM after hiding
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Create toast container if it doesn't exist
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '5';
    document.body.appendChild(container);
    return container;
}