// Main Client-Side JavaScript
document.addEventListener("DOMContentLoaded", function () {
    
    // Auto-hide alert banners after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Image Upload Preview Handling
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const previewContainer = document.getElementById('previewContainer');
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnSpinner = document.getElementById('btnSpinner');

    if (imageInput) {
        imageInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (file) {
                // Extension check
                const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
                if (!validTypes.includes(file.type)) {
                    alert('Please select a valid image file (.jpg, .jpeg, .png)');
                    imageInput.value = '';
                    if (previewContainer) previewContainer.classList.add('d-none');
                    return;
                }

                // File size check (Max 10MB)
                if (file.size > 10 * 1024 * 1024) {
                    alert('File size exceeds 10 MB limit.');
                    imageInput.value = '';
                    if (previewContainer) previewContainer.classList.add('d-none');
                    return;
                }

                const reader = new FileReader();
                reader.onload = function (evt) {
                    if (imagePreview) {
                        imagePreview.src = evt.target.result;
                    }
                    if (previewContainer) {
                        previewContainer.classList.remove('d-none');
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', function () {
            if (submitBtn && btnSpinner) {
                submitBtn.disabled = true;
                btnSpinner.classList.remove('d-none');
            }

            const statusContainer = document.getElementById('statusContainer');
            const statusText = document.getElementById('statusText');
            const statusProgressBar = document.getElementById('statusProgressBar');

            if (statusContainer && statusText && statusProgressBar) {
                statusContainer.classList.remove('d-none');

                const steps = [
                    { text: 'Uploading...', progress: 15 },
                    { text: 'Processing image...', progress: 30 },
                    { text: 'Removing ruled lines...', progress: 45 },
                    { text: 'Analyzing handwriting with AI...', progress: 65 },
                    { text: 'Generating evaluation...', progress: 85 },
                    { text: 'Saving result...', progress: 95 }
                ];

                let stepIdx = 0;
                const interval = setInterval(function () {
                    if (stepIdx < steps.length) {
                        statusText.textContent = steps[stepIdx].text;
                        statusProgressBar.style.width = steps[stepIdx].progress + '%';
                        stepIdx++;
                    } else {
                        clearInterval(interval);
                    }
                }, 1200);
            }
        });
    }


    // Role Switcher toggle in Registration
    const roleSelect = document.getElementById('roleSelect');
    const studentFields = document.getElementById('studentFields');
    if (roleSelect && studentFields) {
        roleSelect.addEventListener('change', function () {
            if (roleSelect.value === 'student') {
                studentFields.classList.remove('d-none');
                document.getElementById('roll_number').required = true;
                document.getElementById('department').required = true;
                document.getElementById('year').required = true;
            } else {
                studentFields.classList.add('d-none');
                document.getElementById('roll_number').required = false;
                document.getElementById('department').required = false;
                document.getElementById('year').required = false;
            }
        });
    }
});

/**
 * Render Chart.js line graph for handwriting evaluation progress over time
 */
function renderProgressChart(canvasId, labels, dataScores) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Handwriting Score (0-100)',
                data: dataScores,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                borderWidth: 3,
                pointRadius: 5,
                pointBackgroundColor: '#4f46e5',
                pointHoverRadius: 7,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Overall Evaluation Score'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Evaluation Sequence'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
}
