/* ============================================
   SOTNUR - Основной JavaScript
   Карусели, календарь, фильтры, модалки, AJAX
   ============================================ */

document.addEventListener('DOMContentLoaded', function() {
    
    /* ---------- Шапка при скролле ---------- */
    const header = document.getElementById('header');
    if (header) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        });
    }
    
    /* ---------- Мобильное меню ---------- */
    var menuToggle = document.getElementById('menu-toggle');
    var nav = document.getElementById('nav');
    
    if (menuToggle && nav) {
        menuToggle.addEventListener('click', function() {
            nav.classList.toggle('active');
            menuToggle.classList.toggle('active');
        });
        nav.querySelectorAll('.nav-link').forEach(function(link) {
            link.addEventListener('click', function() {
                nav.classList.remove('active');
                menuToggle.classList.remove('active');
            });
        });
    }
    
    /* ---------- Карусели на карточках домов ---------- */
    initCarousels();
    
    /* ---------- Модальное окно быстрого бронирования ---------- */
    initQuickBookModal();
    
    /* ---------- Галерея на странице дома ---------- */
    initGallery();
    
    /* ---------- Валидация формы бронирования ---------- */
    initBookingValidation();
    
    /* ---------- Уведомления ---------- */
    initFlashMessages();
});

/* ============================================
   Карусели для карточек домов
   ============================================ */
function initCarousels() {
    const carousels = document.querySelectorAll('.house-carousel');
    
    carousels.forEach(function(carousel) {
        const images = carousel.querySelectorAll('.carousel-img');
        const prevBtn = carousel.querySelector('.carousel-prev');
        const nextBtn = carousel.querySelector('.carousel-next');
        const dots = carousel.querySelectorAll('.carousel-dot');
        const container = carousel.querySelector('.carousel-images');
        
        if (!container || images.length === 0) {
            return;
        }
        
        if (images.length === 1) {
            if (prevBtn) prevBtn.style.display = 'none';
            if (nextBtn) nextBtn.style.display = 'none';
            if (carousel.querySelector('.carousel-dots')) {
                carousel.querySelector('.carousel-dots').style.display = 'none';
            }
            return;
        }
        
        let currentIndex = 0;
        
        function showImage(index) {
            if (index >= images.length) index = 0;
            if (index < 0) index = images.length - 1;
            currentIndex = index;
            
            if (container) {
                container.style.transform = 'translateX(-' + (currentIndex * 100) + '%)';
            }
            
            dots.forEach(function(dot, i) {
                if (dot) {
                    dot.classList.toggle('active', i === currentIndex);
                }
            });
        }
        
        if (prevBtn) {
            prevBtn.addEventListener('click', function(e) {
                e.preventDefault();
                showImage(currentIndex - 1);
            });
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', function(e) {
                e.preventDefault();
                showImage(currentIndex + 1);
            });
        }
        
        dots.forEach(function(dot, index) {
            if (dot) {
                dot.addEventListener('click', function(e) {
                    e.preventDefault();
                    showImage(index);
                });
            }
        });
        
        // Touch свайп для мобильных
        let touchStartX = 0;
        let touchEndX = 0;
        
        carousel.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, {passive: true});
        
        carousel.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, {passive: true});
        
        function handleSwipe() {
            if (touchEndX < touchStartX - 50) {
                showImage(currentIndex + 1);
            }
            if (touchEndX > touchStartX + 50) {
                showImage(currentIndex - 1);
            }
        }
        
        setInterval(function() {
            showImage(currentIndex + 1);
        }, 10000);
    });
}

/* ============================================
   Модальное окно быстрого бронирования
   ============================================ */
function initQuickBookModal() {
    const modal = document.getElementById('booking-modal');
    if (!modal) return;
    
    const closeBtn = document.getElementById('modal-close');
    const quickBookBtns = document.querySelectorAll('.quick-book-btn');
    const houseIdInput = document.getElementById('modal-house-id');
    const houseNameSpan = document.getElementById('modal-house-name');
    const form = document.getElementById('quick-book-form');
    const successDiv = document.getElementById('modal-success');
    
    // Открытие модалки
    quickBookBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const houseId = this.dataset.houseId;
            const houseName = this.dataset.houseName;
            
            houseIdInput.value = houseId;
            houseNameSpan.textContent = houseName;
            
            // Кастомный календарь сам блокирует прошлые даты, .min не нужен
            
            modal.classList.add('show');
        });
    });
    
    // Закрытие модалки
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('show');
            form.style.display = 'block';
            successDiv.style.display = 'none';
        });
    }
    
    // Закрытие по клику вне модалки
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.remove('show');
            form.style.display = 'block';
            successDiv.style.display = 'none';
        }
    });
    
    // Обработка формы
    if (form) {
        form.addEventListener('submit', function(e) {
            const loading = document.getElementById('modal-loading');
            if (loading) {
                form.style.display = 'none';
                loading.style.display = 'flex';
                startLoadingDots();
            }
        });
    }
}

function startLoadingDots() {
    const dotsEl = document.querySelector('.loading-dots');
    if (!dotsEl) return;
    
    let dotCount = 0;
    const dots = ['.', '..', '...'];
    
    setInterval(function() {
        dotCount = (dotCount + 1) % 3;
        dotsEl.textContent = dots[dotCount];
    }, 500);
}

/* ============================================
   Календарь на странице дома
   ============================================ */
function initHouseCalendar() {
    const calendarDays = document.getElementById('calendar-days');
    if (!calendarDays) return;
    
    const houseCalendarDates = typeof bookedDates !== 'undefined' ? bookedDates : {};
    const houseIdGlobal = typeof houseId !== 'undefined' ? houseId : null;
    
    let currentMonth = new Date().getMonth();
    let currentYear = new Date().getFullYear();
    
    const monthNames = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ];
    
    function renderCalendar() {
        const monthYearEl = document.getElementById('calendar-month-year');
        if (monthYearEl) {
            monthYearEl.textContent = `${monthNames[currentMonth]} ${currentYear}`;
        }
        
        const firstDay = new Date(currentYear, currentMonth, 1).getDay();
        const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
        
        let html = '';
        
        // Пустые ячейки (сдвиг для понедельника)
        const emptyDays = firstDay === 0 ? 6 : firstDay - 1;
        for (let i = 0; i < emptyDays; i++) {
            html += '<div class="calendar-day-page disabled"></div>';
        }
        
        // Дни месяца
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(currentYear, currentMonth, day);
            const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            
            let classes = 'calendar-day-page';
            let isDisabled = date < today;
            
            if (isDisabled) {
                classes += ' disabled';
            }
            
            if (houseCalendarDates[dateStr] === 'booked' || (houseCalendarDates[dateStr] && houseCalendarDates[dateStr].status === 'booked')) {
                classes += ' booked';
            }
            
            html += `<div class="${classes}" data-date="${dateStr}">${day}</div>`;
        }
        
        calendarDays.innerHTML = html;
        
        // Клик по дню - выбор даты
        calendarDays.querySelectorAll('.calendar-day-page:not(.disabled):not(.booked)').forEach(dayEl => {
            dayEl.addEventListener('click', function() {
                const checkinInput = document.getElementById('checkin');
                const checkoutInput = document.getElementById('checkout');
                const date = this.dataset.date;
                
                if (!checkinInput.value || (checkinInput.value && checkoutInput.value)) {
                    // Начало нового бронирования
                    checkinInput.value = date;
                    checkoutInput.value = '';
                    
                    // Визуальное выделение
                    calendarDays.querySelectorAll('.calendar-day-page').forEach(el => el.classList.remove('selected'));
                    this.classList.add('selected');
                } else {
                    // Конец бронирования
                    if (date > checkinInput.value) {
                        checkoutInput.value = date;
                        
                        // Выделение диапазона
                        const startDate = new Date(checkinInput.value);
                        const endDate = new Date(date);
                        
                        calendarDays.querySelectorAll('.calendar-day-page').forEach(el => {
                            const elDate = new Date(el.dataset.date);
                            if (elDate >= startDate && elDate <= endDate) {
                                el.classList.add('selected');
                            }
                        });
                    }
                }
            });
        });
    }
    
    // Навигация по месяцам
    const prevBtn = document.getElementById('prev-month');
    const nextBtn = document.getElementById('next-month');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            currentMonth--;
            if (currentMonth < 0) {
                currentMonth = 11;
                currentYear--;
            }
            renderCalendar();
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            currentMonth++;
            if (currentMonth > 11) {
                currentMonth = 0;
                currentYear++;
            }
            renderCalendar();
        });
    }
    
    renderCalendar();
}

/* ============================================
   Галерея на странице дома
   ============================================ */
function initGallery() {
    const mainImage = document.getElementById('main-image');
    const thumbs = document.querySelectorAll('.gallery-thumb');
    
    // Защита: если нет основного изображения (галерея на странице дома использует свою логику), выходим
    if (!mainImage || thumbs.length === 0) return;
    
    thumbs.forEach(thumb => {
        thumb.addEventListener('click', function() {
            const imgSrc = this.dataset.img;
            mainImage.src = imgSrc;
            
            thumbs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

/* ============================================
   Галерея на странице дома (глобальные функции)
   ============================================ */
let galleryCurrentIndex = 0;

function gallerySlide(direction) {
    const images = document.querySelectorAll('.gallery-img');
    const dots = document.querySelectorAll('.gallery-dot');
    if (images.length === 0) return;
    
    images[galleryCurrentIndex].classList.remove('active');
    dots[galleryCurrentIndex].classList.remove('active');
    
    galleryCurrentIndex += direction;
    if (galleryCurrentIndex >= images.length) galleryCurrentIndex = 0;
    if (galleryCurrentIndex < 0) galleryCurrentIndex = images.length - 1;
    
    images[galleryCurrentIndex].classList.add('active');
    dots[galleryCurrentIndex].classList.add('active');
}

function galleryGoTo(index) {
    const images = document.querySelectorAll('.gallery-img');
    const dots = document.querySelectorAll('.gallery-dot');
    if (images.length === 0 || index >= images.length) return;
    
    images[galleryCurrentIndex].classList.remove('active');
    dots[galleryCurrentIndex].classList.remove('active');
    
    galleryCurrentIndex = index;
    
    images[galleryCurrentIndex].classList.add('active');
    dots[galleryCurrentIndex].classList.add('active');
}

window.gallerySlide = gallerySlide;
window.galleryGoTo = galleryGoTo;

/* ============================================
   Валидация формы бронирования
   ============================================ */
function initBookingValidation() {
    // Проверка дат в виджете на главной
    const widgetForm = document.getElementById('booking-form');
    if (widgetForm) {
        widgetForm.addEventListener('submit', function(e) {
            const checkin = document.getElementById('checkin');
            const checkout = document.getElementById('checkout');
            
            if (checkin && checkout && checkin.value && checkout.value) {
                if (checkin.value >= checkout.value) {
                    e.preventDefault();
                    alert('Дата выезда должна быть позже даты заезда');
                }
            }
        });
    }
    
    // Проверка формы на странице дома
    const detailForm = document.querySelector('.booking-form-detail');
    if (detailForm) {
        detailForm.addEventListener('submit', function(e) {
            const checkin = document.getElementById('checkin');
            const checkout = document.getElementById('checkout');
            
            if (checkin && checkout && checkin.value && checkout.value) {
                if (checkin.value >= checkout.value) {
                    e.preventDefault();
                    alert('Дата выезда должна быть позже даты заезда');
                }
            }
        });
    }
}

/* ============================================
   Уведомления (flash messages)
   ============================================ */
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash');
    
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(100px)';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });
}

/* ============================================
   Drag-and-drop для загрузки изображений (админка)
   ============================================ */
function initImageUpload() {
    const dropZones = document.querySelectorAll('.image-upload-zone');
    
    dropZones.forEach(zone => {
        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.style.borderColor = '#667eea';
            this.style.background = '#f0efff';
        });
        
        zone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.style.borderColor = '#ddd';
            this.style.background = 'transparent';
        });
        
        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.borderColor = '#ddd';
            this.style.background = 'transparent';
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                // Здесь можно добавить логику загрузки
                handleImageUpload(files);
            }
        });
        
        // Клик для выбора файлов
        zone.addEventListener('click', function() {
            const input = document.createElement('input');
            input.type = 'file';
            input.multiple = true;
            input.accept = 'image/*';
            
            input.addEventListener('change', function() {
                if (this.files.length > 0) {
                    handleImageUpload(this.files);
                }
            });
            
            input.click();
        });
    });
}

function handleImageUpload(files) {
    // Базовая логика - в реальном проекте здесь был бы AJAX
    console.log('Загружено файлов:', files.length);
    
    // Для демонстрации - просто выводим информацию
    Array.from(files).forEach(file => {
        if (file.type.startsWith('image/')) {
            console.log('Изображение:', file.name);
        }
    });
}

// Инициализация drag-and-drop при загрузке страницы
document.addEventListener('DOMContentLoaded', initImageUpload);

/* ============================================
   AJAX функции для админки
   ============================================ */

// Обновление статуса бронирования
async function updateBookingStatusAjax(bookingId, status) {
    try {
        const response = await fetch(`/admin/booking/${bookingId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: status })
        });
        
        if (response.ok) {
            console.log('Статус обновлён');
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

// Удаление изображения
async function deleteImageAjax(houseId, imageUrl) {
    try {
        const response = await fetch(`/admin/house/${houseId}/delete-image`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ image_url: imageUrl })
        });
        
        if (response.ok) {
            return true;
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
    return false;
}

// Переупорядочивание изображений
async function reorderImagesAjax(houseId, newOrder) {
    try {
        const response = await fetch(`/admin/house/${houseId}/reorder-images`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ order: newOrder })
        });
        
        if (response.ok) {
            console.log('Порядок сохранён');
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

/* ============================================
   Утилиты
   ============================================ */

// Форматирование цены
function formatPrice(price) {
    return new Intl.NumberFormat('ru-RU').format(price) + ' ₽';
}

// Получение даты в формате YYYY-MM-DD
function getDateString(date) {
    return date.toISOString().split('T')[0];
}

// Проверка, является ли дата прошедшей
function isDatePast(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return date < today;
}

// Debounce функция
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle функция
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ============================================
//    CalendarUtils - общие утилиты для календарей
//    Добавлено при рефакторинге для устранения дублирования
// ============================================
var SotnurCalendarMonthNames = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
var SotnurCalendarMonthFull = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];

window.SotnurCalendarUtils = {
    monthNames: SotnurCalendarMonthNames,
    monthNamesFull: SotnurCalendarMonthFull,
    weekDays: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],

    // Получить день недели (пн=0 .. вс=6)
    getStartDay: function(date) {
        var d = date.getDay();
        return d === 0 ? 6 : d - 1;
    },

    // Отрисовать сетку дней месяца. Возвращает массив объектов {day, dateStr, isPast}
    buildMonthGrid: function(year, month) {
        var firstDay = new Date(year, month, 1);
        var lastDay = new Date(year, month + 1, 0);
        var startDay = this.getStartDay(firstDay);
        var totalDays = lastDay.getDate();
        var today = new Date();
        today.setHours(0, 0, 0, 0);

        var grid = [];
        for (var i = 0; i < startDay; i++) {
            grid.push(null); // пустая ячейка
        }
        for (var day = 1; day <= totalDays; day++) {
            var date = new Date(year, month, day);
            var dateStr = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
            grid.push({
                day: day,
                dateStr: dateStr,
                date: date,
                isPast: date < today
            });
        }
        return grid;
    },

    // Рендер сетки HTML для календаря
    renderGrid: function(grid, cellRenderer) {
        var html = '';
        for (var i = 0; i < grid.length; i++) {
            html += cellRenderer(grid[i], i);
        }
        return html;
    },

    // Переключение месяца
    changeMonth: function(currentMonth, currentYear, delta) {
        currentMonth += delta;
        if (currentMonth > 11) { currentMonth = 0; currentYear++; }
        if (currentMonth < 0) { currentMonth = 11; currentYear--; }
        return { month: currentMonth, year: currentYear };
    }
};

// Экспорт для использования в других скриптах
window.Sotnur = {
    formatPrice,
    getDateString,
    isDatePast,
    debounce,
    throttle,
    updateBookingStatusAjax,
    deleteImageAjax,
    reorderImagesAjax,
    CalendarUtils: window.SotnurCalendarUtils
};