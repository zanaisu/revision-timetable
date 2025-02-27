function togglePassword(inputId, toggleId) {
    const passwordInput = document.getElementById(inputId);
    const toggleButton = document.getElementById(toggleId);
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleButton.textContent = '👁️';
    } else {
        passwordInput.type = 'password';
        toggleButton.textContent = '👁️‍🗨️';
    }
}
