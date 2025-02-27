document.addEventListener('DOMContentLoaded', function() {
    // Update points automatically
    const checkboxes = document.querySelectorAll('.task-checkbox');
    const pointsDisplay = document.getElementById('total-points');
    
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updatePoints);
    });

    function updatePoints() {
        let total = 0;
        checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                total += parseInt(checkbox.getAttribute('data-points'));
            }
        });
        pointsDisplay.textContent = total;
    }

    // Show current day's tasks and handle weekend tasks
    const today = new Date().getDay();
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    
    // Handle weekday tasks visibility
    const allDayTasks = document.querySelectorAll('.day-tasks');
    allDayTasks.forEach(dayDiv => {
        dayDiv.style.display = 'none';
    });

    // Show only current day's tasks if it's a weekday
    if (today !== 0 && today !== 6) {
        const currentDayTasks = document.getElementById(`tasks-${dayNames[today]}`);
        if (currentDayTasks) {
            currentDayTasks.style.display = 'block';
        }
    }

    // Handle weekend tasks visibility
    const weekendTasksContainer = document.getElementById('weekend-tasks-container');
    if (weekendTasksContainer) {
        weekendTasksContainer.style.display = (today === 0 || today === 6) ? 'block' : 'none';
    }
});

function toggleCalendar() {
    const allDayTasks = document.querySelectorAll('.day-tasks');
    const currentDisplay = allDayTasks[0].style.display;
    
    allDayTasks.forEach(dayDiv => {
        dayDiv.style.display = currentDisplay === 'none' ? 'block' : 'none';
    });

    // Update button text
    const button = document.querySelector('button[onclick="toggleCalendar()"]');
    button.textContent = currentDisplay === 'none' ? 'Show Today Only' : 'Show Full Week';
}
