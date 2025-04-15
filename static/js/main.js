// Add any shared functionality here

// Helper function to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Helper function to format dates
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

// Helper function to calculate rental duration
function calculateRentalDays(startDate, endDate) {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end - start);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // +1 to include start day
    return diffDays;
}

// Handle date input validation
document.addEventListener('DOMContentLoaded', function() {
    // Find all start and end date input pairs
    const startDateInputs = document.querySelectorAll('input[name="start_date"]');
    const endDateInputs = document.querySelectorAll('input[name="end_date"]');
    
    startDateInputs.forEach(startInput => {
        // Set min date to today
        const today = new Date().toISOString().split('T')[0];
        if (!startInput.value) {
            startInput.min = today;
        }
        
        // Update the associated end date min value when start date changes
        startInput.addEventListener('change', function() {
            const form = startInput.closest('form');
            const endInput = form.querySelector('input[name="end_date"]');
            
            if (endInput) {
                endInput.min = startInput.value;
                
                // If end date is before start date, update it
                if (endInput.value && endInput.value < startInput.value) {
                    endInput.value = startInput.value;
                }
            }
        });
    });
});
