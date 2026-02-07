// Buyer Brief Website JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // ============================================
    // NAVIGATION
    // ============================================

    const navbar = document.getElementById('navbar');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const mobileMenu = document.getElementById('mobileMenu');

    // Navbar scroll effect
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Mobile menu toggle
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('active');
        });

        // Close mobile menu when clicking a link
        mobileMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                mobileMenu.classList.remove('active');
            });
        });
    }

    // ============================================
    // SCROLL ANIMATIONS
    // ============================================

    const animateOnScroll = () => {
        const elements = document.querySelectorAll('.animate-on-scroll');

        elements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;

            if (elementTop < windowHeight - 100) {
                element.classList.add('visible');
            }
        });
    };

    window.addEventListener('scroll', animateOnScroll);
    animateOnScroll(); // Run on load

    // ============================================
    // NUMBER COUNTER ANIMATION
    // ============================================

    const animateCounters = () => {
        const counters = document.querySelectorAll('.stat-number[data-count]');

        counters.forEach(counter => {
            if (counter.classList.contains('counted')) return;

            const rect = counter.getBoundingClientRect();
            if (rect.top < window.innerHeight && rect.bottom > 0) {
                counter.classList.add('counted');

                const target = parseInt(counter.getAttribute('data-count'));
                const duration = 2000;
                const start = performance.now();

                const updateCounter = (currentTime) => {
                    const elapsed = currentTime - start;
                    const progress = Math.min(elapsed / duration, 1);

                    // Easing function
                    const easeOutQuart = 1 - Math.pow(1 - progress, 4);
                    const current = Math.floor(target * easeOutQuart);

                    counter.textContent = current;

                    if (progress < 1) {
                        requestAnimationFrame(updateCounter);
                    } else {
                        counter.textContent = target;
                    }
                };

                requestAnimationFrame(updateCounter);
            }
        });
    };

    window.addEventListener('scroll', animateCounters);
    animateCounters(); // Run on load

    // ============================================
    // SECTION NAVIGATION (Hero choices)
    // ============================================

    const hero = document.getElementById('hero');
    const startSection = document.getElementById('start');
    const voiceSection = document.getElementById('voiceSection');
    const formSection = document.getElementById('formSection');
    const successSection = document.getElementById('successSection');

    // Get all elements that need to be hidden/shown
    const mainSections = [
        document.querySelector('.navbar'),
        hero,
        document.getElementById('how-it-works'),
        document.getElementById('features'),
        document.getElementById('team'),
        startSection,
        document.querySelector('footer')
    ];

    const hideMainSections = () => {
        mainSections.forEach(section => {
            if (section) section.style.display = 'none';
        });
    };

    const showMainSections = () => {
        mainSections.forEach(section => {
            if (section) section.style.display = '';
        });
        voiceSection.style.display = 'none';
        formSection.style.display = 'none';
        successSection.style.display = 'none';
    };

    // Voice choice button (in start section)
    const voiceChoiceBtn = document.querySelector('#voiceChoice .choice-btn');
    if (voiceChoiceBtn) {
        voiceChoiceBtn.addEventListener('click', function() {
            hideMainSections();
            voiceSection.style.display = 'flex';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Form choice button (in start section)
    const formChoiceBtn = document.querySelector('#formChoice .choice-btn');
    if (formChoiceBtn) {
        formChoiceBtn.addEventListener('click', function() {
            hideMainSections();
            formSection.style.display = 'block';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Back buttons
    const backFromVoice = document.getElementById('backFromVoice');
    if (backFromVoice) {
        backFromVoice.addEventListener('click', function() {
            showMainSections();
            document.getElementById('start').scrollIntoView({ behavior: 'smooth' });
        });
    }

    const backFromForm = document.getElementById('backFromForm');
    if (backFromForm) {
        backFromForm.addEventListener('click', function() {
            showMainSections();
            document.getElementById('start').scrollIntoView({ behavior: 'smooth' });
        });
    }

    // ============================================
    // MULTI-STEP FORM
    // ============================================

    const form = document.getElementById('buyerBriefForm');
    const progressBar = document.getElementById('progressBar');
    const progressSteps = document.querySelectorAll('.progress-step');
    const formSteps = document.querySelectorAll('.form-step');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const submitBtn = document.getElementById('submitBtn');

    let currentStep = 1;
    const totalSteps = formSteps.length;

    const updateProgress = () => {
        const progress = (currentStep / totalSteps) * 100;
        progressBar.style.setProperty('--progress', `${progress}%`);

        progressSteps.forEach((step, index) => {
            step.classList.remove('active', 'completed');
            if (index + 1 === currentStep) {
                step.classList.add('active');
            } else if (index + 1 < currentStep) {
                step.classList.add('completed');
            }
        });
    };

    const showStep = (step) => {
        formSteps.forEach((formStep, index) => {
            formStep.classList.remove('active');
            if (index + 1 === step) {
                formStep.classList.add('active');
            }
        });

        // Show/hide navigation buttons
        prevBtn.style.visibility = step === 1 ? 'hidden' : 'visible';

        if (step === totalSteps) {
            nextBtn.style.display = 'none';
            submitBtn.style.display = 'flex';
        } else {
            nextBtn.style.display = 'flex';
            submitBtn.style.display = 'none';
        }

        updateProgress();
    };

    // Navigation buttons
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (currentStep < totalSteps) {
                currentStep++;
                showStep(currentStep);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentStep > 1) {
                currentStep--;
                showStep(currentStep);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }

    // Number selectors (+/- buttons)
    document.querySelectorAll('.num-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            const input = document.getElementById(target);
            const isPlus = this.classList.contains('plus');
            let value = parseInt(input.value) || 0;

            if (isPlus) {
                value = Math.min(value + 1, parseInt(input.max) || 10);
            } else {
                value = Math.max(value - 1, parseInt(input.min) || 0);
            }

            input.value = value;
        });
    });

    // Format currency inputs
    const currencyInputs = ['budgetMin', 'budgetMax', 'stretchBudget'];
    currencyInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('blur', function() {
                let value = this.value.replace(/[^0-9]/g, '');
                if (value) {
                    this.value = parseInt(value).toLocaleString();
                }
            });
            input.addEventListener('focus', function() {
                let value = this.value.replace(/[^0-9]/g, '');
                this.value = value;
            });
        }
    });

    // Form submission
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            submitBtn.disabled = true;
            submitBtn.innerHTML = `
                <svg class="spinner" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 12a9 9 0 11-6.219-8.56"/>
                </svg>
                Submitting...
            `;

            // Collect form data
            const formData = new FormData(form);
            const data = {};

            for (let [key, value] of formData.entries()) {
                if (data[key]) {
                    if (Array.isArray(data[key])) {
                        data[key].push(value);
                    } else {
                        data[key] = [data[key], value];
                    }
                } else {
                    data[key] = value;
                }
            }

            data.submittedAt = new Date().toISOString();
            console.log('Form Data:', data);

            try {
                // Submit to backend API
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    // Show success
                    formSection.style.display = 'none';
                    successSection.style.display = 'flex';
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                } else {
                    throw new Error(result.error || 'Submission failed');
                }

            } catch (error) {
                console.error('Submission error:', error);
                alert('There was an error submitting your form. Please try again.');
                submitBtn.disabled = false;
                submitBtn.innerHTML = `
                    Submit Brief
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                `;
            }
        });
    }

    // ============================================
    // VOICE CALL - Now uses tel: link directly
    // ============================================
    // The "Call Ava Now" buttons are now anchor tags with tel:+61485027700
    // which opens the phone dialer directly on mobile/desktop

    // ============================================
    // SMOOTH SCROLL FOR ANCHOR LINKS
    // ============================================

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Initialize
    showStep(currentStep);
});
