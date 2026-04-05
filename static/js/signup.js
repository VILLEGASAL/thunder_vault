/**
 * Dynamically toggles the visibility of any password field.
 * @param {string} inputId - The ID of the input field to toggle.
 * @param {string} iconId - The ID of the eye icon to change.
 */
function toggleVisibility(inputId, iconId) {
    const passInput = document.getElementById(inputId);
    const eyeIcon = document.getElementById(iconId);
    
    if (passInput.type === 'password') {
        passInput.type = 'text';
        eyeIcon.textContent = 'visibility_off';
    } else {
        passInput.type = 'password';
        eyeIcon.textContent = 'visibility';
    }
}

/**
 * Validates that the passwords match before allowing the form to submit.
 */
document.getElementById('signupForm').addEventListener('submit', function(event) {
    const pass1 = document.getElementById('password').value;
    const pass2 = document.getElementById('confirm_password').value;
    const errorText = document.getElementById('passwordError');
    
    // Check if the passwords DO NOT match
    if (pass1 !== pass2) {
        // PREVENT SUBMISSION: This stops the browser from sending the POST request
        event.preventDefault();
        
        // Show the error message
        errorText.textContent = "Passwords do not match!";
        errorText.style.display = 'block';
        
        // Visually highlight the error with our Danger Red color
        document.getElementById('confirm_password').style.borderColor = 'var(--danger-red)';
    } else {
        // Clear errors if they match and allow the submission to continue naturally
        errorText.style.display = 'none';
        document.getElementById('confirm_password').style.borderColor = 'var(--border-color)';
    }
});