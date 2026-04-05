
//Navigates the browser back to the home root directory.
function goBack() {
    window.location.href = '/'; 
}

//Delete Modal
function openDeleteModal(dirName, fileName) {
    const modal = document.getElementById('deleteModal');
    const deleteForm = document.getElementById('deleteForm');
    
    const descriptionText = modal.querySelector('p');
    descriptionText.textContent = `"${fileName}" will be permanently deleted from Thunder Vault. This action cannot be undone.`;
    
    deleteForm.action = `/rmfile?dir_name=${dirName}&file_name=${fileName}`
    
    // Show the modal
    modal.classList.add('show');
}

// Close the delete modal
function closeModal() {
    const modal = document.getElementById('deleteModal');
    modal.classList.remove('show');
}

/**
 * Handles the visual update when a user selects a file to upload.
 * @param {HTMLInputElement} inputElement - The file input that triggered the event.
 */
function handleFileSelection(inputElement) {
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const submitBtn = document.getElementById('uploadSubmitBtn');
    
    if (inputElement.files && inputElement.files.length > 0) {
        const selectedFileName = inputElement.files[0].name;
        
        fileNameDisplay.textContent = selectedFileName;
        
        submitBtn.disabled = false;
        
        submitBtn.style.cursor = 'pointer';
        submitBtn.style.opacity = '1';
    } else {
        
        fileNameDisplay.textContent = '+ Choose File';
        submitBtn.disabled = true;
        submitBtn.style.cursor = 'not-allowed';
        submitBtn.style.opacity = '0.5';
    }
}

// Close modal if user clicks outside of the white box
window.onclick = function(event) {
    const modal = document.getElementById('deleteModal');
    if (event.target === modal) {
        closeModal();
    }
}