/**
 * Enhanced Date Picker Navigation
 * Adds hierarchical navigation to Dash DatePickerRange:
 * - Click month header -> Month selector
 * - Click year -> Year/decade selector
 */

// Wait for the date picker to be rendered
document.addEventListener('DOMContentLoaded', function() {
    console.log('Date picker enhancement script loaded');

    // Monitor for date picker elements being added to DOM
    const observer = new MutationObserver(function(mutations) {
        enhanceDatePickers();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Initial enhancement
    setTimeout(enhanceDatePickers, 500);
});

function enhanceDatePickers() {
    // Find all date picker month headers
    const datePickerContainers = document.querySelectorAll('.DateRangePicker, .SingleDatePicker');

    datePickerContainers.forEach(container => {
        // Find month/year navigation elements
        const navPrev = container.querySelector('.DayPickerNavigation_button:first-child');
        const navNext = container.querySelector('.DayPickerNavigation_button:last-child');
        const caption = container.querySelector('.CalendarMonth_caption');

        if (caption && !caption.hasAttribute('data-enhanced')) {
            caption.style.cursor = 'pointer';
            caption.style.userSelect = 'none';
            caption.setAttribute('data-enhanced', 'true');
            caption.setAttribute('title', 'Click to select month/year');

            // Add hover effect
            caption.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'rgba(99, 102, 241, 0.1)';
                this.style.borderRadius = '4px';
            });

            caption.addEventListener('mouseleave', function() {
                this.style.backgroundColor = 'transparent';
            });

            // Add click handler
            caption.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleMonthYearPicker(caption, container);
            });
        }
    });
}

function toggleMonthYearPicker(caption, container) {
    // Parse current month/year from caption
    const text = caption.textContent.trim();
    const parts = text.split(' ');
    const month = parts[0];
    const year = parseInt(parts[1]);

    // Check if custom picker already exists
    let customPicker = container.querySelector('.custom-month-year-picker');

    if (customPicker) {
        // Remove existing picker
        customPicker.remove();
        return;
    }

    // Create month/year selector
    customPicker = document.createElement('div');
    customPicker.className = 'custom-month-year-picker';
    customPicker.style.cssText = `
        position: absolute;
        z-index: 1000;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        min-width: 280px;
    `;

    // Year selector header
    const yearHeader = document.createElement('div');
    yearHeader.style.cssText = `
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        padding: 8px;
        font-weight: 600;
        font-size: 14px;
    `;

    const yearPrev = createNavButton('‹', -1);
    const yearDisplay = document.createElement('span');
    yearDisplay.textContent = year;
    yearDisplay.style.cursor = 'pointer';
    yearDisplay.style.padding = '4px 8px';
    yearDisplay.style.borderRadius = '4px';
    yearDisplay.title = 'Click to select year';

    // Year display click -> decade view
    yearDisplay.addEventListener('click', function() {
        showDecadeView(customPicker, year, container, caption);
    });

    yearDisplay.addEventListener('mouseenter', function() {
        this.style.backgroundColor = 'rgba(99, 102, 241, 0.1)';
    });

    yearDisplay.addEventListener('mouseleave', function() {
        this.style.backgroundColor = 'transparent';
    });

    const yearNext = createNavButton('›', 1);

    yearHeader.appendChild(yearPrev);
    yearHeader.appendChild(yearDisplay);
    yearHeader.appendChild(yearNext);

    // Month grid
    const monthGrid = document.createElement('div');
    monthGrid.style.cssText = `
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
    `;

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const currentYear = year;

    months.forEach((m, idx) => {
        const monthBtn = document.createElement('button');
        monthBtn.textContent = m;
        monthBtn.style.cssText = `
            padding: 8px 12px;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            background: white;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.15s;
        `;

        monthBtn.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#6366f1';
            this.style.color = 'white';
            this.style.borderColor = '#6366f1';
        });

        monthBtn.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
            this.style.color = 'black';
            this.style.borderColor = '#e5e7eb';
        });

        monthBtn.addEventListener('click', function() {
            // Navigate to selected month
            navigateToMonth(container, currentYear, idx);
            customPicker.remove();
        });

        monthGrid.appendChild(monthBtn);
    });

    // Year navigation handlers
    yearPrev.addEventListener('click', function() {
        yearDisplay.textContent = parseInt(yearDisplay.textContent) - 1;
        updateMonthButtons();
    });

    yearNext.addEventListener('click', function() {
        yearDisplay.textContent = parseInt(yearDisplay.textContent) + 1;
        updateMonthButtons();
    });

    function updateMonthButtons() {
        const newYear = parseInt(yearDisplay.textContent);
        monthGrid.querySelectorAll('button').forEach((btn, idx) => {
            btn.onclick = function() {
                navigateToMonth(container, newYear, idx);
                customPicker.remove();
            };
        });
    }

    customPicker.appendChild(yearHeader);
    customPicker.appendChild(monthGrid);

    // Position picker
    const calendarMonth = container.querySelector('.CalendarMonth');
    if (calendarMonth) {
        calendarMonth.style.position = 'relative';
        calendarMonth.appendChild(customPicker);
    }

    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', function closePickerHandler(e) {
            if (!customPicker.contains(e.target) && e.target !== caption) {
                customPicker.remove();
                document.removeEventListener('click', closePickerHandler);
            }
        });
    }, 100);
}

function showDecadeView(customPicker, currentYear, container, caption) {
    // Clear current content
    customPicker.innerHTML = '';

    const startYear = Math.floor(currentYear / 10) * 10;
    const endYear = startYear + 9;

    // Decade header
    const decadeHeader = document.createElement('div');
    decadeHeader.style.cssText = `
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        padding: 8px;
        font-weight: 600;
        font-size: 14px;
    `;

    const decadePrev = createNavButton('‹', -10);
    const decadeDisplay = document.createElement('span');
    decadeDisplay.textContent = `${startYear} - ${endYear}`;
    const decadeNext = createNavButton('›', 10);

    decadeHeader.appendChild(decadePrev);
    decadeHeader.appendChild(decadeDisplay);
    decadeHeader.appendChild(decadeNext);

    // Year grid
    const yearGrid = document.createElement('div');
    yearGrid.style.cssText = `
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
    `;

    for (let y = startYear; y <= endYear; y++) {
        const yearBtn = document.createElement('button');
        yearBtn.textContent = y;
        yearBtn.style.cssText = `
            padding: 8px 12px;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            background: white;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.15s;
        `;

        yearBtn.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#6366f1';
            this.style.color = 'white';
            this.style.borderColor = '#6366f1';
        });

        yearBtn.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
            this.style.color = 'black';
            this.style.borderColor = '#e5e7eb';
        });

        yearBtn.addEventListener('click', function() {
            // Go back to month view for selected year
            customPicker.remove();
            navigateToMonth(container, y, 0);
        });

        yearGrid.appendChild(yearBtn);
    }

    // Decade navigation
    decadePrev.addEventListener('click', function() {
        showDecadeView(customPicker, currentYear - 10, container, caption);
    });

    decadeNext.addEventListener('click', function() {
        showDecadeView(customPicker, currentYear + 10, container, caption);
    });

    customPicker.appendChild(decadeHeader);
    customPicker.appendChild(yearGrid);
}

function createNavButton(text, direction) {
    const btn = document.createElement('button');
    btn.textContent = text;
    btn.style.cssText = `
        padding: 4px 8px;
        border: 1px solid #e5e7eb;
        border-radius: 4px;
        background: white;
        cursor: pointer;
        font-size: 18px;
        font-weight: bold;
        transition: all 0.15s;
    `;

    btn.addEventListener('mouseenter', function() {
        this.style.backgroundColor = '#f3f4f6';
    });

    btn.addEventListener('mouseleave', function() {
        this.style.backgroundColor = 'white';
    });

    return btn;
}

function navigateToMonth(container, year, monthIndex) {
    // Find and click the appropriate navigation buttons
    // This is a simplified approach - you may need to adjust based on current position
    const navPrev = container.querySelector('.DayPickerNavigation_button:first-child');
    const navNext = container.querySelector('.DayPickerNavigation_button:last-child');

    // Get current displayed month/year
    const caption = container.querySelector('.CalendarMonth_caption');
    if (!caption) return;

    const currentText = caption.textContent.trim();
    const parts = currentText.split(' ');
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
    const currentMonth = monthNames.indexOf(parts[0]);
    const currentYear = parseInt(parts[1]);

    const targetDate = new Date(year, monthIndex, 1);
    const currentDate = new Date(currentYear, currentMonth, 1);

    const monthDiff = (year - currentYear) * 12 + (monthIndex - currentMonth);

    // Click next/prev buttons to navigate
    const button = monthDiff > 0 ? navNext : navPrev;
    const clicks = Math.abs(monthDiff);

    for (let i = 0; i < clicks; i++) {
        setTimeout(() => button.click(), i * 50);
    }
}
