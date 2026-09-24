/**
 * Enterprise Finance Dashboard & Expense Submission - Client-Side Interactivity
 */

document.addEventListener('DOMContentLoaded', () => {
    // ==========================================
    // 1. Mobile & Tablet Sidebar Navigation
    // ==========================================
    const sidebarToggleBtn = document.getElementById('sidebarToggle');
    const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
    const sidebar = document.getElementById('sidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    function openSidebar() {
        if (sidebar && sidebarBackdrop) {
            sidebar.classList.add('show');
            sidebarBackdrop.classList.add('show');
            if (sidebarToggleBtn) {
                sidebarToggleBtn.setAttribute('aria-expanded', 'true');
            }
            document.body.style.overflow = 'hidden';
        }
    }

    function closeSidebar() {
        if (sidebar && sidebarBackdrop) {
            sidebar.classList.remove('show');
            sidebarBackdrop.classList.remove('show');
            if (sidebarToggleBtn) {
                sidebarToggleBtn.setAttribute('aria-expanded', 'false');
            }
            document.body.style.overflow = '';
        }
    }

    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (sidebar && sidebar.classList.contains('show')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    if (sidebarCloseBtn) {
        sidebarCloseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeSidebar();
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', () => {
            closeSidebar();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar && sidebar.classList.contains('show')) {
            closeSidebar();
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth >= 1200) {
            closeSidebar();
        }
    });

    // ==========================================
    // 2. Expense Submission Form Interactivity
    // ==========================================
    const expenseForm = document.getElementById('expenseSubmissionForm');
    const receiptYesRadio = document.getElementById('receiptYes');
    const receiptNoRadio = document.getElementById('receiptNo');
    const receiptContainer = document.getElementById('receiptFieldsContainer');
    const merchantInput = document.getElementById('merchant');
    const receiptDateInput = document.getElementById('receipt_date');
    const receiptAmountInput = document.getElementById('receipt_amount');
    const btnClearForm = document.getElementById('btnClearForm');

    // File Upload Elements
    const receiptFileInput = document.getElementById('receipt_file');
    const receiptDropzone = document.getElementById('receiptDropzone');
    const receiptFilePreview = document.getElementById('receiptFilePreview');
    const receiptFileName = document.getElementById('receiptFileName');
    const receiptFileSize = document.getElementById('receiptFileSize');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const receiptImageThumbnail = document.getElementById('receiptImageThumbnail');
    const pdfPreviewContainer = document.getElementById('pdfPreviewContainer');
    const btnReplaceFile = document.getElementById('btnReplaceFile');
    const btnRemoveFile = document.getElementById('btnRemoveFile');
    const fileValidationError = document.getElementById('fileValidationError');

    const ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png'];
    const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB

    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function resetFileUpload() {
        if (receiptFileInput) receiptFileInput.value = '';
        if (receiptFilePreview) receiptFilePreview.classList.add('d-none');
        if (receiptDropzone) receiptDropzone.classList.remove('d-none');
        if (imagePreviewContainer) imagePreviewContainer.classList.add('d-none');
        if (pdfPreviewContainer) pdfPreviewContainer.classList.add('d-none');
        if (receiptImageThumbnail) receiptImageThumbnail.src = '#';
        if (fileValidationError) {
            fileValidationError.textContent = '';
            fileValidationError.classList.add('d-none');
        }
    }

    function handleFileSelection(file) {
        if (!file) return;

        if (fileValidationError) {
            fileValidationError.textContent = '';
            fileValidationError.classList.add('d-none');
        }

        const ext = file.name.split('.').pop().toLowerCase();

        // 1. Validate File Extension
        if (!ALLOWED_EXTENSIONS.includes(ext)) {
            if (fileValidationError) {
                fileValidationError.innerHTML = '<i class="bi bi-exclamation-circle me-1"></i> Invalid file format. Only PDF, JPG, JPEG, and PNG files are supported.';
                fileValidationError.classList.remove('d-none');
            }
            if (receiptFileInput) receiptFileInput.value = '';
            return;
        }

        // 2. Validate File Size
        if (file.size > MAX_FILE_SIZE) {
            if (fileValidationError) {
                fileValidationError.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i> File size (${formatBytes(file.size)}) exceeds the 5 MB limit.`;
                fileValidationError.classList.remove('d-none');
            }
            if (receiptFileInput) receiptFileInput.value = '';
            return;
        }

        // Display Metadata
        if (receiptFileName) receiptFileName.textContent = file.name;
        if (receiptFileSize) receiptFileSize.textContent = formatBytes(file.size) + ' • ' + ext.toUpperCase();

        // Display Preview (Image vs PDF)
        if (['jpg', 'jpeg', 'png'].includes(ext)) {
            const reader = new FileReader();
            reader.onload = (e) => {
                if (receiptImageThumbnail) {
                    receiptImageThumbnail.src = e.target.result;
                }
                if (imagePreviewContainer) imagePreviewContainer.classList.remove('d-none');
                if (pdfPreviewContainer) pdfPreviewContainer.classList.add('d-none');
            };
            reader.readAsDataURL(file);
        } else if (ext === 'pdf') {
            if (imagePreviewContainer) imagePreviewContainer.classList.add('d-none');
            if (pdfPreviewContainer) pdfPreviewContainer.classList.remove('d-none');
        }

        // Toggle dropzone / preview cards
        if (receiptDropzone) receiptDropzone.classList.add('d-none');
        if (receiptFilePreview) receiptFilePreview.classList.remove('d-none');
    }

    // Dropzone Click & Change Listeners
    if (receiptDropzone && receiptFileInput) {
        receiptDropzone.addEventListener('click', () => {
            receiptFileInput.click();
        });

        // Drag & Drop
        receiptDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            receiptDropzone.classList.add('border-primary', 'bg-primary-subtle');
        });

        receiptDropzone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            receiptDropzone.classList.remove('border-primary', 'bg-primary-subtle');
        });

        receiptDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            receiptDropzone.classList.remove('border-primary', 'bg-primary-subtle');
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                receiptFileInput.files = e.dataTransfer.files;
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });
    }

    if (receiptFileInput) {
        receiptFileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });
    }

    if (btnReplaceFile && receiptFileInput) {
        btnReplaceFile.addEventListener('click', () => {
            receiptFileInput.click();
        });
    }

    if (btnRemoveFile) {
        btnRemoveFile.addEventListener('click', () => {
            resetFileUpload();
        });
    }

    // Show / Hide Receipt Details & File Upload Container
    function toggleReceiptFields() {
        if (!receiptContainer) return;

        if (receiptYesRadio && receiptYesRadio.checked) {
            receiptContainer.classList.remove('d-none');
        } else {
            receiptContainer.classList.add('d-none');
            // Clear receipt fields and file upload when not available
            if (merchantInput) {
                merchantInput.value = '';
                merchantInput.classList.remove('is-invalid');
            }
            if (receiptDateInput) {
                receiptDateInput.value = '';
                receiptDateInput.classList.remove('is-invalid');
            }
            if (receiptAmountInput) {
                receiptAmountInput.value = '';
                receiptAmountInput.classList.remove('is-invalid');
            }
            resetFileUpload();
        }
    }

    if (receiptYesRadio) {
        receiptYesRadio.addEventListener('change', toggleReceiptFields);
    }
    if (receiptNoRadio) {
        receiptNoRadio.addEventListener('change', toggleReceiptFields);
    }

    // Client-side Validation on Submit + Loading State
    if (expenseForm) {
        expenseForm.addEventListener('submit', (event) => {
            let isValid = true;

            const employeeName = document.getElementById('employee_name');
            const expenseCategory = document.getElementById('expense_category');
            const claimedAmount = document.getElementById('claimed_amount');
            const expenseDate = document.getElementById('expense_date');
            const purpose = document.getElementById('purpose');

            // Reset field validity classes
            const allInputs = expenseForm.querySelectorAll('.form-control, .form-select');
            allInputs.forEach(input => input.classList.remove('is-invalid'));

            // 1. Employee Name
            if (!employeeName.value.trim() || employeeName.value.trim().length < 2) {
                employeeName.classList.add('is-invalid');
                isValid = false;
            }

            // 2. Expense Category
            if (!expenseCategory.value) {
                expenseCategory.classList.add('is-invalid');
                isValid = false;
            }

            // 3. Claimed Amount
            const amountVal = parseFloat(claimedAmount.value);
            if (isNaN(amountVal) || amountVal <= 0) {
                claimedAmount.classList.add('is-invalid');
                isValid = false;
            }

            // 4. Expense Date
            if (!expenseDate.value) {
                expenseDate.classList.add('is-invalid');
                isValid = false;
            }

            // 5. Purpose
            if (!purpose.value.trim()) {
                purpose.classList.add('is-invalid');
                isValid = false;
            }

            // 6. Conditional Receipt Details
            if (receiptYesRadio && receiptYesRadio.checked) {
                if (merchantInput && !merchantInput.value.trim()) {
                    merchantInput.classList.add('is-invalid');
                    isValid = false;
                }
                if (receiptDateInput && !receiptDateInput.value) {
                    receiptDateInput.classList.add('is-invalid');
                    isValid = false;
                }
                if (receiptAmountInput) {
                    const rcptAmt = parseFloat(receiptAmountInput.value);
                    if (isNaN(rcptAmt) || rcptAmt <= 0) {
                        receiptAmountInput.classList.add('is-invalid');
                        isValid = false;
                    }
                }
            }

            if (!isValid) {
                event.preventDefault();
                event.stopPropagation();
                // Focus first invalid element
                const firstInvalid = expenseForm.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            } else {
                // If form is valid, trigger loading spinner on submit button
                const submitBtn = expenseForm.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Auditing with AI Agent...';
                }
            }
        });
    }

    // Clear Form Button
    if (btnClearForm && expenseForm) {
        btnClearForm.addEventListener('click', () => {
            expenseForm.reset();
            const allInputs = expenseForm.querySelectorAll('.form-control, .form-select');
            allInputs.forEach(input => input.classList.remove('is-invalid'));
            
            if (receiptNoRadio) {
                receiptNoRadio.checked = true;
            }
            toggleReceiptFields();

            const firstInput = document.getElementById('employee_name');
            if (firstInput) {
                firstInput.focus();
            }
        });
    }
});
