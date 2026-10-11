/**
 * EHE 2.0 Client-side Interactions
 * English Handwriting Evaluation
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Password Visibility Toggle
  initPasswordToggles();

  // 2. Drag & Drop File Upload with Image Preview
  initDropzoneUpload();

  // 3. Prevent Double Submits with honest loading state
  initFormSubmitButtons();
});

function initPasswordToggles() {
  const toggleBtns = document.querySelectorAll(".password-toggle-btn");
  toggleBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      const targetId = this.getAttribute("data-target");
      const input = document.getElementById(targetId);
      if (!input) return;

      if (input.type === "password") {
        input.type = "text";
        this.setAttribute("aria-label", "Hide password");
        this.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
      } else {
        input.type = "password";
        this.setAttribute("aria-label", "Show password");
        this.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
      }
    });
  });
}

function initDropzoneUpload() {
  const dropzone = document.getElementById("upload-dropzone");
  const fileInput = document.getElementById("image-input");
  const previewContainer = document.getElementById("preview-container");
  const previewImg = document.getElementById("image-preview");
  const fileNameDisplay = document.getElementById("file-name-display");

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("click", () => fileInput.click());

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      fileInput.files = files;
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener("change", function () {
    if (this.files.length > 0) {
      handleFileSelected(this.files[0]);
    }
  });

  function handleFileSelected(file) {
    if (!file) return;

    // Check size limit (10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert("File exceeds maximum allowed size of 10MB.");
      fileInput.value = "";
      if (previewContainer) previewContainer.style.display = "none";
      return;
    }

    if (fileNameDisplay) {
      fileNameDisplay.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }

    if (previewImg && previewContainer) {
      const reader = new FileReader();
      reader.onload = function (e) {
        previewImg.src = e.target.result;
        previewContainer.style.display = "block";
      };
      reader.readAsDataURL(file);
    }
  }
}

function initFormSubmitButtons() {
  const uploadForm = document.getElementById("evaluation-upload-form");
  if (!uploadForm) return;

  uploadForm.addEventListener("submit", function () {
    const submitBtn = document.getElementById("submit-evaluate-btn");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <svg class="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite; margin-right: 6px;">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10"></path>
        </svg>
        Processing Handwriting Sample...
      `;
    }
  });
}
