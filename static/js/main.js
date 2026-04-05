/**
 * Navigates to the directory view.
 * Triggered when a user clicks anywhere on the folder card (except the delete button).
 */
function openDirectory(dirName) {
    // Redirects to your backend route to view files in the directory
    // Adjust this URL to match whatever your actual FastAPI route is for viewing a directory!
    window.location.href = `/view_files?dir_name=${dirName}`;
}

/**
 * Opens the delete confirmation modal and sets the target directory.
 * @param {string} dirName - The name of the directory to delete.
 */
function openDeleteModal(dirName) {
    // Stop the click event from bubbling up to the folder card's onclick (openDirectory)
    event.stopPropagation();

    const modal = document.getElementById('deleteModal');
    const deleteForm = document.getElementById('confirmDeleteForm')

    deleteForm.action = `/rmdir?dir_name=${dirName}`
    
    // Show the modal
    modal.classList.add('show');
}

/**
 * Closes the deletion modal.
 */
function closeModal() {
    const modal = document.getElementById('deleteModal');
    modal.classList.remove('show');
}

// Close modal if user clicks outside of the white box
window.onclick = function(event) {
    const modal = document.getElementById('deleteModal');
    if (event.target === modal) {
        closeModal();
    }
}