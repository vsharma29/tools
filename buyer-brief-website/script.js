// Buyer Brief Form JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('buyerBriefForm');
    const successMessage = document.getElementById('successMessage');

    // Toggle sections based on purchase purpose
    const purchasePurposeRadios = document.querySelectorAll('input[name="purchasePurpose"]');
    const investmentSection = document.getElementById('investmentSection');
    const lifestyleSection = document.getElementById('lifestyleSection');

    purchasePurposeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'investment' || this.value === 'smsf') {
                investmentSection.style.display = 'block';
                lifestyleSection.style.display = 'none';
            } else {
                investmentSection.style.display = 'none';
                lifestyleSection.style.display = 'block';
            }
        });
    });

    // Toggle first home buyer grants
    const fhbRadios = document.querySelectorAll('input[name="firstHomeBuyer"]');
    const fhbGrants = document.getElementById('fhbGrants');

    fhbRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            fhbGrants.style.display = this.value === 'yes' ? 'block' : 'none';
        });
    });

    // Toggle pet details
    const petRadios = document.querySelectorAll('input[name="pets"]');
    const petDetails = document.getElementById('petDetails');

    petRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            petDetails.style.display = this.value === 'yes' ? 'block' : 'none';
        });
    });

    // Format currency inputs
    const currencyInputs = ['budgetMin', 'budgetMax', 'stretchBudget', 'deposit'];
    currencyInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('blur', function() {
                let value = this.value.replace(/[^0-9]/g, '');
                if (value) {
                    this.value = '$' + parseInt(value).toLocaleString();
                }
            });
            input.addEventListener('focus', function() {
                let value = this.value.replace(/[^0-9]/g, '');
                this.value = value;
            });
        }
    });

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const submitBtn = form.querySelector('.submit-btn');
        submitBtn.disabled = true;
        submitBtn.classList.add('loading');
        submitBtn.textContent = 'Submitting...';

        // Collect form data
        const formData = new FormData(form);
        const data = {};

        // Process form data
        for (let [key, value] of formData.entries()) {
            if (data[key]) {
                // Handle multiple values (checkboxes)
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }

        // Add timestamp
        data.submittedAt = new Date().toISOString();

        console.log('Form Data:', data);

        // Simulate API call (replace with actual endpoint)
        try {
            // For now, just simulate success
            await new Promise(resolve => setTimeout(resolve, 1500));

            // In production, send to your backend:
            // const response = await fetch('/api/buyer-brief', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify(data)
            // });

            // Show success message
            form.style.display = 'none';
            successMessage.style.display = 'block';

            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });

        } catch (error) {
            console.error('Submission error:', error);
            alert('There was an error submitting your form. Please try again.');
            submitBtn.disabled = false;
            submitBtn.classList.remove('loading');
            submitBtn.textContent = 'Submit Buyer Brief';
        }
    });

    // Smooth scroll for better UX
    const sections = document.querySelectorAll('.form-section');
    sections.forEach(section => {
        const inputs = section.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                // Optional: smooth scroll section into view
            });
        });
    });
});
