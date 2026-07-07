document.addEventListener('DOMContentLoaded', function() {
    initCarousels();
    initBookingValidation();
    initFlashMessages();
});

function initCarousels() {
    document.querySelectorAll('.house-carousel').forEach(function(carousel) {
        var images = carousel.querySelectorAll('.carousel-img');
        var prevBtn = carousel.querySelector('.carousel-prev');
        var nextBtn = carousel.querySelector('.carousel-next');
        var dots = carousel.querySelectorAll('.carousel-dot');
        var container = carousel.querySelector('.carousel-images');
        if (!container || images.length === 0) return;
        if (images.length === 1) {
            if (prevBtn) prevBtn.style.display = 'none';
            if (nextBtn) nextBtn.style.display = 'none';
            if (carousel.querySelector('.carousel-dots')) carousel.querySelector('.carousel-dots').style.display = 'none';
            return;
        }
        var current = 0;
        function show(idx) {
            if (idx >= images.length) idx = 0;
            if (idx < 0) idx = images.length - 1;
            current = idx;
            container.style.transform = 'translateX(-' + (current * 100) + '%)';
            dots.forEach(function(d, i) { if (d) d.classList.toggle('active', i === current); });
        }
        if (prevBtn) prevBtn.addEventListener('click', function(e) { e.preventDefault(); show(current - 1); });
        if (nextBtn) nextBtn.addEventListener('click', function(e) { e.preventDefault(); show(current + 1); });
        dots.forEach(function(dot, idx) {
            if (dot) dot.addEventListener('click', function(e) { e.preventDefault(); show(idx); });
        });
        var startX = 0;
        carousel.addEventListener('touchstart', function(e) { startX = e.changedTouches[0].screenX; }, {passive:true});
        carousel.addEventListener('touchend', function(e) {
            var diff = startX - e.changedTouches[0].screenX;
            if (Math.abs(diff) > 50) show(current + (diff > 0 ? 1 : -1));
        }, {passive:true});
        setInterval(function() { show(current + 1); }, 10000);
    });
}

function initBookingValidation() {
    var filterForm = document.getElementById('booking-filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            var ci = document.getElementById('checkin');
            var co = document.getElementById('checkout');
            if (ci && co && ci.value && co.value && ci.value >= co.value) {
                e.preventDefault();
                alert('Дата выезда должна быть позже даты заезда');
            }
        });
    }
    var detailForm = document.querySelector('.booking-form-detail');
    if (detailForm) {
        detailForm.addEventListener('submit', function(e) {
            var ci = document.getElementById('checkin');
            var co = document.getElementById('checkout');
            if (ci && co && ci.value && co.value && ci.value >= co.value) {
                e.preventDefault();
                alert('Дата выезда должна быть позже даты заезда');
            }
        });
    }
}

function initFlashMessages() {
    document.querySelectorAll('.flash').forEach(function(msg) {
        setTimeout(function() {
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(100px)';
            setTimeout(function() { msg.remove(); }, 300);
        }, 5000);
    });
}

function initImageUpload() {
    document.querySelectorAll('.image-upload-zone').forEach(function(zone) {
        zone.addEventListener('dragover', function(e) { e.preventDefault(); this.style.borderColor = '#667eea'; this.style.background = '#f0efff'; });
        zone.addEventListener('dragleave', function(e) { e.preventDefault(); this.style.borderColor = '#ddd'; this.style.background = 'transparent'; });
        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.borderColor = '#ddd';
            this.style.background = 'transparent';
            var files = e.dataTransfer.files;
            if (files.length > 0) handleImageUpload(files);
        });
        zone.addEventListener('click', function() {
            var input = document.createElement('input');
            input.type = 'file'; input.multiple = true; input.accept = 'image/*';
            input.addEventListener('change', function() { if (this.files.length > 0) handleImageUpload(this.files); });
            input.click();
        });
    });
}

function handleImageUpload(files) {
    console.log('Uploaded files:', files.length);
    Array.from(files).forEach(function(file) { if (file.type.startsWith('image/')) console.log('Image:', file.name); });
}

document.addEventListener('DOMContentLoaded', initImageUpload);

async function updateBookingStatusAjax(bookingId, status) {
    try {
        var r = await fetch('/admin/booking/' + bookingId + '/status', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({status: status}) });
        return r.ok;
    } catch(e) { console.error(e); return false; }
}

async function deleteImageAjax(houseId, imageUrl) {
    try {
        var r = await fetch('/admin/house/' + houseId + '/delete-image', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({image_url: imageUrl}) });
        return r.ok;
    } catch(e) { console.error(e); return false; }
}

async function reorderImagesAjax(houseId, newOrder) {
    try {
        var r = await fetch('/admin/house/' + houseId + '/reorder-images', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({order: newOrder}) });
        return r.ok;
    } catch(e) { console.error(e); return false; }
}

function formatPrice(price) { return new Intl.NumberFormat('ru-RU').format(price) + ' \u20BD'; }
function getDateString(date) { return date.toISOString().split('T')[0]; }
function isDatePast(dateStr) { var d = new Date(dateStr); var t = new Date(); t.setHours(0,0,0,0); return d < t; }
function debounce(func, wait) { var t; return function() { var ctx = this, args = arguments; clearTimeout(t); t = setTimeout(function() { func.apply(ctx, args); }, wait); }; }
function throttle(func, limit) { var inThrottle; return function() { if (!inThrottle) { func.apply(this, arguments); inThrottle = true; setTimeout(function() { inThrottle = false; }, limit); } }; }

var SotnurCalendarMonthNames = ['\u042F\u043D\u0432', '\u0424\u0435\u0432', '\u041C\u0430\u0440', '\u0410\u043F\u0440', '\u041C\u0430\u0439', '\u0418\u044E\u043D', '\u0418\u044E\u043B', '\u0410\u0432\u0433', '\u0421\u0435\u043D', '\u041E\u043A\u0442', '\u041D\u043E\u044F', '\u0414\u0435\u043A'];
var SotnurCalendarMonthFull = ['\u042F\u043D\u0432\u0430\u0440\u044C', '\u0424\u0435\u0432\u0440\u0430\u043B\u044C', '\u041C\u0430\u0440\u0442', '\u0410\u043F\u0440\u0435\u043B\u044C', '\u041C\u0430\u0439', '\u0418\u044E\u043D\u044C', '\u0418\u044E\u043B\u044C', '\u0410\u0432\u0433\u0443\u0441\u0442', '\u0421\u0435\u043D\u0442\u044F\u0431\u0440\u044C', '\u041E\u043A\u0442\u044F\u0431\u0440\u044C', '\u041D\u043E\u044F\u0431\u0440\u044C', '\u0414\u0435\u043A\u0430\u0431\u0440\u044C'];

window.SotnurCalendarUtils = {
    monthNames: SotnurCalendarMonthNames,
    monthNamesFull: SotnurCalendarMonthFull,
    weekDays: ['\u041F\u043D', '\u0412\u0442', '\u0421\u0440', '\u0427\u0442', '\u041F\u0442', '\u0421\u0431', '\u0412\u0441'],
    getStartDay: function(date) { var d = date.getDay(); return d === 0 ? 6 : d - 1; },
    buildMonthGrid: function(year, month) {
        var firstDay = new Date(year, month, 1);
        var lastDay = new Date(year, month + 1, 0);
        var startDay = this.getStartDay(firstDay);
        var totalDays = lastDay.getDate();
        var today = new Date(); today.setHours(0,0,0,0);
        var grid = [];
        for (var i = 0; i < startDay; i++) grid.push(null);
        for (var day = 1; day <= totalDays; day++) {
            var date = new Date(year, month, day);
            var dateStr = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
            grid.push({day: day, dateStr: dateStr, date: date, isPast: date < today});
        }
        return grid;
    },
    changeMonth: function(currentMonth, currentYear, delta) {
        currentMonth += delta;
        if (currentMonth > 11) { currentMonth = 0; currentYear++; }
        if (currentMonth < 0) { currentMonth = 11; currentYear--; }
        return {month: currentMonth, year: currentYear};
    }
};

window.Sotnur = {
    formatPrice: formatPrice,
    getDateString: getDateString,
    isDatePast: isDatePast,
    debounce: debounce,
    throttle: throttle,
    updateBookingStatusAjax: updateBookingStatusAjax,
    deleteImageAjax: deleteImageAjax,
    reorderImagesAjax: reorderImagesAjax,
    CalendarUtils: window.SotnurCalendarUtils
};