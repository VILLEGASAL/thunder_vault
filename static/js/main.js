// Notification if a directory exists
const notif_box = document.getElementById("notif");

if(notif_box){

    window.history.replaceState({}, document.title, window.location.pathname);

    setTimeout(() => { notif_box.remove(); }, 3000);    
}

// File Uploading
const input_files = document.querySelectorAll(".input-file");
input_files.forEach(input => {
    input.addEventListener("change", (event) => {
        const fileInput = event.target;
        const parentForm = fileInput.closest('.upload-form');
        const uploadBtn = parentForm.querySelector('.btn-upload');
        const labelText = parentForm.querySelector('.label-text');

        if (fileInput.files.length > 0) {
            labelText.textContent = fileInput.files[0].name;
            labelText.style.color = "#2b8a3e"; 
            uploadBtn.disabled = false;
        }
    });
});

// Openning a Directory
document.querySelectorAll(".btn_open").forEach(btn => {
    btn.addEventListener("click", () => {
        window.location.href = `/view_files/${btn.value}`;
    });
});

// Custom Modal
const modal = document.getElementById("deleteModal");
const confirmBtn = document.getElementById("confirmDelete");
const cancelBtn = document.getElementById("cancelDelete");
const targetSpan = document.getElementById("targetDirName");
let directoryToDelete = "";

document.querySelectorAll(".btn_delete").forEach(btn => {
    btn.addEventListener("click", () => {
        directoryToDelete = btn.value;
        targetSpan.textContent = `"${directoryToDelete}"`;
        modal.classList.add("show");
    });
});

cancelBtn.addEventListener("click", () => {
    modal.classList.remove("show");
});

confirmBtn.addEventListener("click", async () => {
    const result = await fetch(`/rmdir?dir_name=${directoryToDelete}`, {
        method: "DELETE"
    });
    if (result.status == "200") {
        window.location.href = "/";
    }
});

// Close modal if clicking outside the box
window.onclick = (event) => {
    if (event.target == modal) {
        modal.classList.remove("show");
    }
}