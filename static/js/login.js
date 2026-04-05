/**
 * Toggles the visibility of the password input field.
 */
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const eyeIcon = document.getElementById('eyeIcon');
    
    // Check the current type of the input
    if (passwordInput.type === 'password') {
        // Switch to text to reveal the password
        passwordInput.type = 'text';
        // Change the icon to the "eye with a slash"
        eyeIcon.textContent = 'visibility_off';
    } else {
        // Switch back to password to hide it
        passwordInput.type = 'password';
        // Change the icon back to the normal eye
        eyeIcon.textContent = 'visibility';
    }
}

