/*
 * main.js
 *
 * This file contains global JavaScript functionalities for the Robert Sichomba / Perturbation Labs portfolio website.
 * It aims to enhance the user experience with subtle animations, navigation aids, and interactive elements.
 *
 * Contents:
 * 1. Document Ready Initialization
 * 2. Scroll Animation Logic (Intersection Observer)
 * 3. Back to Top Button Functionality
 * 4. Smooth Scrolling for Anchor Links
 * 5. Password Toggle for Input Fields
 * 6. Form Submission Spinner
 * 7. Django Messages Close Button (if not using Bootstrap's default dismiss)
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("main.js loaded and DOM fully parsed.");

    // --- 2. Scroll Animation Logic (Intersection Observer) ---
    // Elements with the 'data-animate' attribute will animate into view.
    const animateElements = document.querySelectorAll('[data-animate]');

    if (animateElements.length > 0) {
        const observerOptions = {
            root: null, // viewport
            rootMargin: '0px',
            threshold: 0.1 // Trigger when 10% of the element is visible
        };

        const observer = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate');
                    observer.unobserve(entry.target); // Stop observing once animated
                }
            });
        }, observerOptions);

        animateElements.forEach(element => {
            observer.observe(element);
        });
    }

    // --- 3. Back to Top Button Functionality ---
    const backToTopBtn = document.getElementById('backToTopBtn');

    if (backToTopBtn) {
        // Show/hide button based on scroll position
        window.addEventListener('scroll', function() {
            if (window.scrollY > 300) { // Show button after scrolling down 300px
                backToTopBtn.classList.add('show');
            } else {
                backToTopBtn.classList.remove('show');
            }
        });

        // Smooth scroll to top when button is clicked
        backToTopBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // --- 4. Smooth Scrolling for Anchor Links ---
    // Applies to internal links that point to IDs on the same page.
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();

            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                // Adjust scroll position to account for fixed navbar
                const navbarHeight = document.querySelector('.navbar').offsetHeight;
                const offsetTop = targetElement.getBoundingClientRect().top + window.scrollY - navbarHeight;

                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });

                // Optional: Update URL hash without jumping
                if (history.pushState) {
                    history.pushState(null, null, targetId);
                } else {
                    location.hash = targetId;
                }
            }
        });
    });

    // --- 5. Password Toggle for Input Fields ---
    // This now handles all password fields consistently.
    window.togglePassword = function(fieldId) {
        const field = document.getElementById(fieldId);
        // Find the icon that is a sibling of the field
        // This assumes the icon is either `nextElementSibling` or within a common parent.
        // A more robust way might be to give the icon an ID or specific class.
        // For now, let's assume it's `nextElementSibling` as in your HTML.
        let icon = field.nextElementSibling;
        
        // If the direct sibling isn't the icon (e.g., if there's a div wrapping the icon),
        // you might need a more specific selector, like:
        // icon = field.closest('.position-relative').querySelector('.password-toggle');
        
        // Basic check to ensure we have an icon
        if (!icon || !icon.classList.contains('password-toggle')) {
            console.warn("Password toggle icon not found for field:", fieldId);
            return;
        }

        const isPassword = field.type === 'password';

        field.type = isPassword ? 'text' : 'password';
        icon.classList.toggle('fa-eye-slash', isPassword); // Toggle slash icon if showing text
        icon.classList.toggle('fa-eye', !isPassword);       // Toggle eye icon if showing password
        icon.setAttribute('aria-label', isPassword ? 'Show password' : 'Hide password');
    };

    // --- 6. Form Submission Spinner ---
    // Adds a loading spinner to all forms with a submit button
    document.querySelectorAll('form').forEach(form => {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            form.addEventListener('submit', function() {
                // Add a small delay to ensure UI update is visible before navigation
                setTimeout(() => {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
                }, 50); // Small delay
            });
        }
    });

    // --- 7. Django Messages Close Button ---
    // Make Django message alerts dismissable using Bootstrap's default behavior
    // If you're using Bootstrap 5's JS, this might be handled automatically.
    // If not, uncomment and use this or a similar custom solution.
    /*
    document.querySelectorAll('.messages .alert .btn-close').forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.alert').remove();
        });
    });
    */
});