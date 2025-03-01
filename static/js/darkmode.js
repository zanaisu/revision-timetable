/**
 * Theme system for Revision Timetable
 * Handles theme switching between light, dark, and custom themes
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initThemeSelector();
  
  // Add event listener to theme toggle buttons
  document.querySelectorAll('.theme-toggle, [data-action="toggle-theme"]').forEach(btn => {
    btn.addEventListener('click', toggleTheme);
  });
});

/**
 * Initialize theme from localStorage or system preference
 */
function initTheme() {
  // Check if user has previously set a theme preference
  const savedTheme = localStorage.getItem('theme');
  
  if (savedTheme) {
    // Use saved theme preference
    setTheme(savedTheme);
  } else {
    // Check for system dark mode preference
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    setTheme(prefersDark ? 'dark' : 'light');
  }
}

/**
 * Initialize theme selector controls 
 */
function initThemeSelector() {
  const selector = document.getElementById('themeSelector');
  if (!selector) return;
  
  // Add click event listeners for theme options
  document.querySelectorAll('.theme-option').forEach(option => {
    option.addEventListener('click', function() {
      const theme = this.getAttribute('data-theme');
      if (theme) {
        setTheme(theme);
        // Update active state
        document.querySelectorAll('.theme-option').forEach(opt => {
          opt.classList.remove('active');
        });
        this.classList.add('active');
      }
    });
    
    // Mark the current theme as active
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    if (option.getAttribute('data-theme') === currentTheme) {
      option.classList.add('active');
    }
  });
}

/**
 * Toggle between light and dark themes
 */
function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
  // Toggle between light and dark, preserving other themes
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  setTheme(newTheme);
}

/**
 * Set theme to the specified value
 * @param {string} theme - The theme to set ('light', 'dark', 'kimono', 'calm', 'forest', 'neon')
 * Note: 'kimono' is now styled as Kimbie Dark, but retains the name 'kimono' for backward compatibility
 */
function setTheme(theme) {
  // Set theme attribute on html element
  document.documentElement.setAttribute('data-theme', theme);
  
  // Save theme preference to localStorage
  localStorage.setItem('theme', theme);
  
  // Update theme toggle icons and text
  updateThemeIcons(theme);
}

/**
 * Update all theme toggle icons to reflect current theme
 * @param {string} theme - The current theme
 */
function updateThemeIcons(theme) {
  // Update any theme toggle icons in the document
  document.querySelectorAll('[id^="themeIcon"]').forEach(icon => {
    // Set the appropriate icon based on theme
    switch(theme) {
      case 'light':
        icon.className = 'fas fa-moon';
        break;
      case 'dark':
        icon.className = 'fas fa-sun';
        break;
      case 'kimono': // Kimbie Dark theme
        icon.className = 'fas fa-fan';
        break;
      case 'calm':
        icon.className = 'fas fa-water';
        break;
      case 'forest':
        icon.className = 'fas fa-leaf';
        break;
      case 'neon':
        icon.className = 'fas fa-bolt';
        break;
      default:
        icon.className = 'fas fa-palette';
    }
  });
  
  // Update any theme toggle text elements
  document.querySelectorAll('[id^="themeText"]').forEach(text => {
    // Add special case for kimono to show as "Kimbie Dark"
    if (theme === 'kimono') {
      text.textContent = 'Kimbie Dark Theme';
    } else {
      text.textContent = theme.charAt(0).toUpperCase() + theme.slice(1) + ' Theme';
    }
  });
}