# -*- coding: utf-8 -*-
"""
SOTNUR - сайт бронирования домов (Марий Эл)
Флейм-версия: 3.0.0
"""

import os
import json
import shutil
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from werkzeug.utils import secure_filename
from io import BytesIO

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# Telegram конфигурация (только через переменные окружения!)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Email конфигурация для уведомлений
EMAIL_HOST = 'smtp.yandex.ru'
EMAIL_PORT = 587
EMAIL_USER = 'sotnur-notify@yandex.ru'
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_TO = 's.evsin@my18.ru'

def send_telegram_notification(message, chat_id):
    """Отправка уведомления в Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram bot token не настроен")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': str(chat_id),
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        print(f"Telegram response: {result}")
        if result.get('ok'):
            return True
        else:
            print(f"Telegram error: {result.get('description')}")
            return False
    except Exception as e:
        print(f"Ошибка Telegram: {e}")
        return False

def send_email_notification(subject, body):
    """Отправка email уведомления"""
    if not EMAIL_PASSWORD:
        print("Email пароль не настроен")
        return False
    
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Email отправлен: {subject}")
        return True
    except Exception as e:
        print(f"Ошибка email: {e}")
        return False

# Конфигурация приложения
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max для загрузки фото


# Обработчик для передачи flash_message в шаблоны
@app.before_request
def before_request():
    pass


@app.after_request
def after_request(response):
    return response


# context_processor для передачи flash в шаблоны
@app.context_processor
def inject_flash():
    flash_msg = session.pop('flash_message', None)
    return {'flash_message': flash_msg}

# Пути к файлам
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')


# ==================== ФУНКЦИИ РАБОТЫ С ДАННЫМИ ====================

@app.template_filter('phone_link')
def phone_link(value):
    """Очищает номер телефона для tel: ссылки (с +)"""
    import re
    digits = re.sub(r'\D', '', value)
    if not digits.startswith('7') and not digits.startswith('8'):
        return digits
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    return '+' + digits


def load_data():
    """Загрузка данных из JSON-файла"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"houses": [], "reviews": [], "bookings": [], "users": []}


def save_data(data):
    """Сохранение данных в JSON-файл"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


DEFAULT_HOUSES = [
    {
        "id": 8,
        "name": "Дубовая роща",
        "short_desc": "Тихий дом в окружении дубов",
        "full_desc": "Дом расположен в живописной дубовой роще. Внутри — деревянная отделка, камин и большая терраса с видом на лес. Идеальное место для уединённого отдыха.",
        "price": 7000,
        "max_guests": 4,
        "images": ["https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=600"],
        "amenities": ["Баня", "Мангал", "Камин", "Wi-Fi"],
        "calendar": {}
    },
    {
        "id": 9,
        "name": "Сосновый бор",
        "short_desc": "Уютный дом в сосновом лесу",
        "full_desc": "Дом в тихом месте, окружённый соснами. Идеально для семейного отдыха. Рядом лесные тропы и озеро.",
        "price": 8000,
        "max_guests": 4,
        "images": ["https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600"],
        "amenities": ["Баня", "Мангал", "Купель", "Wi-Fi"],
        "calendar": {}
    },
    {
        "id": 10,
        "name": "Берёзовая заводь",
        "short_desc": "Дом с видом на озеро",
        "full_desc": "Просторный дом прямо у воды. Своя купель и баня. Летом можно рыбачить и кататься на лодке.",
        "price": 12000,
        "max_guests": 6,
        "images": ["https://images.unsplash.com/photo-1449157291145-7efd050a4d0e?w=600"],
        "amenities": ["Баня", "Мангал", "Купель", "Wi-Fi", "Лодка"],
        "calendar": {}
    },
    {
        "id": 11,
        "name": "Шале «На рассвете»",
        "short_desc": "Большой дом для компании",
        "full_desc": "Просторный дом с двумя спальнями, большой гостиной и верандой. Восходы над лесом — главное украшение этого места.",
        "price": 15000,
        "max_guests": 8,
        "images": ["https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=600"],
        "amenities": ["Баня", "Мангал", "Купель", "Wi-Fi", "Камин"],
        "calendar": {}
    },
    {
        "id": 12,
        "name": "Кленовый хутор",
        "short_desc": "Премиальный дом с панорамой",
        "full_desc": "Элитный дом с панорамными окнами, сауной и бассейном. Подходит для больших компаний и семейных праздников.",
        "price": 25000,
        "max_guests": 10,
        "images": ["https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=600"],
        "amenities": ["Баня", "Мангал", "Сауна", "Wi-Fi", "Бассейн", "Купель"],
        "calendar": {}
    },
    {
        "id": 13,
        "name": "Лесная поляна",
        "short_desc": "Уютный домик для двоих",
        "full_desc": "Небольшой романтичный домик на краю леса. Есть открытая купель под звёздами и мангальная зона.",
        "price": 6000,
        "max_guests": 2,
        "images": ["https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600"],
        "amenities": ["Купель", "Мангал", "Wi-Fi"],
        "calendar": {}
    },
    {
        "id": 14,
        "name": "Озерный причал",
        "short_desc": "Дом с собственной купелью",
        "full_desc": "Дом прямо у озера с собственным причалом и купелью на дровах. Лодка и рыболовные снасти входят в стоимость.",
        "price": 10000,
        "max_guests": 5,
        "images": ["https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=600"],
        "amenities": ["Баня", "Купель", "Лодка", "Мангал", "Wi-Fi"],
        "calendar": {}
    }
]

def seed_default_data():
    """Создаёт тестовые дома + админа при первом запуске (если база пуста)"""
    import os
    if os.path.exists(DATA_FILE):
        return
    data = {"houses": [], "reviews": [], "bookings": [], "users": []}
    data['houses'] = DEFAULT_HOUSES
    data['users'] = [{"login": "admin", "password": "sotnur2026"}]
    save_data(data)


def migrate_missing_houses():
    """Добавляет недостающие дома в существующую базу"""
    import os
    if not os.path.exists(DATA_FILE):
        return
    try:
        data = load_data()
        existing_ids = {h['id'] for h in data.get('houses', [])}
        new_houses = []
        for h in DEFAULT_HOUSES:
            if h['id'] not in existing_ids:
                new_houses.append(h)
        if new_houses:
            data.setdefault('houses', []).extend(new_houses)
            save_data(data)
    except Exception:
        pass


def get_house(house_id):
    """Получение дома по ID"""
    data = load_data()
    for house in data.get('houses', []):
        if house['id'] == house_id:
            return house
    return None


def get_available_dates(house_id):
    """Получение занятых дат для дома (календарь + подтверждённые брони)"""
    house = get_house(house_id)
    if not house:
        return {}
    dates = dict(house.get('calendar', {}))
    # Добавляем даты из подтверждённых броней
    try:
        data = load_data()
        for b in data.get('bookings', []):
            if b.get('house_id') == house_id and b.get('status') in ('confirmed', 'new'):
                cin = datetime.strptime(b['checkin'], '%Y-%m-%d')
                cout = datetime.strptime(b['checkout'], '%Y-%m-%d')
                cur = cin
                while cur < cout:
                    ds = cur.strftime('%Y-%m-%d')
                    if ds not in dates:
                        dates[ds] = 'booked'
                    cur += timedelta(days=1)
    except (ValueError, KeyError):
        pass
    return dates


def get_min_price(house):
    """Получение минимальной цены (с учетом кастомных цен)"""
    try:
        base_price = house.get('price', 0)
        if not isinstance(base_price, int):
            base_price = 0
        
        calendar = house.get('calendar', {})
        if not calendar:
            calendar = {}
        
        min_price = base_price
        for date_key, date_data in calendar.items():
            if isinstance(date_data, dict):
                custom_price = date_data.get('price')
                if custom_price and isinstance(custom_price, (int, float)) and custom_price < min_price:
                    min_price = custom_price
        
        return min_price
    except Exception as e:
        print(f"Error in get_min_price: {e}")
        return house.get('price', 0)


def is_date_booked(house_id, date_str):
    """Проверка, занята ли дата (календарь + брони)"""
    calendar = get_available_dates(house_id)
    if date_str in calendar:
        date_data = calendar[date_str]
        if isinstance(date_data, dict):
            return date_data.get('status') == 'booked'
        return date_data == 'booked'
    # Fallback: проверяем брони в data.json
    try:
        data = load_data()
        for b in data.get('bookings', []):
            if b.get('house_id') == house_id and b.get('status') in ('confirmed', 'new'):
                cin = datetime.strptime(b['checkin'], '%Y-%m-%d')
                cout = datetime.strptime(b['checkout'], '%Y-%m-%d')
                cur = cin
                while cur < cout:
                    if cur.strftime('%Y-%m-%d') == date_str:
                        return True
                    cur += timedelta(days=1)
    except (ValueError, KeyError):
        pass
    return False


# ==================== ROUTES - ГЛАВНЫЕ СТРАНИЦЫ ====================

@app.route('/')
def index():
    """Главная страница - список всех домов"""
    data = load_data()
    houses = data.get('houses', [])
    
    # Обработка фильтров из виджета бронирования
    checkin = request.args.get('checkin')
    checkout = request.args.get('checkout')
    guests = request.args.get('guests', type=int)
    promo = request.args.get('promo', '').strip().lower()
    
    filtered_houses = houses
    filter_applied = False
    
    # Фильтр по гостям
    if guests:
        filtered_houses = [h for h in filtered_houses if h.get('max_guests', 0) >= guests]
        filter_applied = True
    
    # Фильтр по датам (простой - проверяем есть ли доступные даты)
    if checkin and checkout:
        try:
            checkin_date = datetime.strptime(checkin, '%Y-%m-%d')
            checkout_date = datetime.strptime(checkout, '%Y-%m-%d')
            
            temp_houses = []
            for h in filtered_houses:
                # Проверяем каждую дату в диапазоне
                available = True
                current = checkin_date
                while current < checkout_date:
                    date_str = current.strftime('%Y-%m-%d')
                    if is_date_booked(h['id'], date_str):
                        available = False
                        break
                    current += timedelta(days=1)
                
                if available:
                    temp_houses.append(h)
            
            filtered_houses = temp_houses
            filter_applied = True
        except ValueError:
            pass
    
    # Применение промокода (пока просто заглушка)
    discount = 0
    if promo == 'sotnur10':
        discount = 10
    
    # Добавляем min_price для каждого дома
    for h in filtered_houses:
        if isinstance(h, dict):
            h['min_price'] = get_min_price(h)
    for h in houses:
        if isinstance(h, dict):
            h['min_price'] = get_min_price(h)
    
    # Даты, занятые хотя бы в одном доме (для красной подсветки в календаре)
    booked_set = set()
    for h in houses:
        cal = h.get('calendar', {})
        for date_str, status in cal.items():
            if isinstance(status, dict):
                is_b = status.get('status') == 'booked'
            else:
                is_b = status == 'booked'
            if is_b:
                booked_set.add(date_str)
    # Добавляем даты из подтверждённых броней (на случай, если календарь не синхронизирован)
    for b in data.get('bookings', []):
        if b.get('status') in ('confirmed', 'new'):
            try:
                cin = datetime.strptime(b['checkin'], '%Y-%m-%d')
                cout = datetime.strptime(b['checkout'], '%Y-%m-%d')
                cur = cin
                while cur < cout:
                    booked_set.add(cur.strftime('%Y-%m-%d'))
                    cur += timedelta(days=1)
            except (ValueError, KeyError):
                pass
    
    return render_template('index.html', 
                           houses=filtered_houses, 
                           all_houses=houses,
                           checkin=checkin,
                           checkout=checkout,
                           guests=guests,
                           promo=promo,
                           discount=discount,
                           filter_applied=filter_applied,
                           fully_booked_dates=list(booked_set))


@app.route('/house/<int:house_id>')
def house(house_id):
    """Страница конкретного дома"""
    house_data = get_house(house_id)
    if not house_data:
        session['flash_message'] = {'type': 'error', 'text': 'Дом не найден'}
        return redirect(url_for('index'))
    
    data = load_data()
    
    # Отзывы для этого дома
    reviews = [r for r in data.get('reviews', []) if r.get('house_id') == house_id]
    
    # Занятые даты для календаря
    booked_dates = get_available_dates(house_id)
    
    return render_template('house.html', 
                           house=house_data, 
                           reviews=reviews,
                           booked_dates=booked_dates)


# ==================== ROUTES - БРОНИРОВАНИЕ ====================

def check_date_overlap(house_id, checkin, checkout):
    """Проверка наложения дат - возвращает список занятых дат в диапазоне"""
    occupied_dates = []
    try:
        checkin_date = datetime.strptime(checkin, '%Y-%m-%d')
        checkout_date = datetime.strptime(checkout, '%Y-%m-%d')
        current = checkin_date
        while current < checkout_date:
            date_str = current.strftime('%Y-%m-%d')
            if is_date_booked(house_id, date_str):
                occupied_dates.append(date_str)
            current += timedelta(days=1)
    except (ValueError, TypeError):
        pass
    return occupied_dates


@app.route('/book', methods=['POST'])
def book():
    """Обработка формы бронирования с проверкой занятых дат"""
    house_id = request.form.get('house_id', type=int)
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    checkin = request.form.get('checkin', '').strip()
    checkout = request.form.get('checkout', '').strip()
    
    if not all([name, phone, checkin, checkout]):
        session['flash_message'] = {'type': 'error', 'text': 'Пожалуйста, заполните все поля'}
        return redirect(url_for('house', house_id=house_id))
    
    # Проверка что даты не в прошлом
    today = datetime.now().strftime('%Y-%m-%d')
    if checkin < today:
        session['flash_message'] = {'type': 'error', 'text': 'Дата заезда не может быть в прошлом'}
        return redirect(url_for('house', house_id=house_id))
    
    if checkout <= checkin:
        session['flash_message'] = {'type': 'error', 'text': 'Дата выезда должна быть позже даты заезда'}
        return redirect(url_for('house', house_id=house_id))
    
    # Проверка наложения дат
    occupied_dates = check_date_overlap(house_id, checkin, checkout)
    if occupied_dates:
        session['flash_message'] = {'type': 'error', 'text': f'На выбранные даты есть бронирования: {", ".join(occupied_dates[:3])}{"..." if len(occupied_dates) > 3 else ""}. Пожалуйста, выберите другие даты.'}
        return redirect(url_for('house', house_id=house_id))
    
    data = load_data()
    
    # Генерация ID для новой брони
    max_id = 0
    for b in data.get('bookings', []):
        if b['id'] > max_id:
            max_id = b['id']
    
    new_booking = {
        "id": max_id + 1,
        "house_id": house_id,
        "name": name,
        "phone": phone,
        "checkin": checkin,
        "checkout": checkout,
        "status": "new",
        "created_at": datetime.now().isoformat()
    }
    
    data.setdefault('bookings', []).append(new_booking)
    
    # Помечаем даты в календаре дома (только для confirmed статуса)
    # При создании брони автоматически помечаем, владелец может отменить
    house = next((h for h in data.get('houses', []) if h.get('id') == house_id), None)
    if house:
        cal = house.setdefault('calendar', {})
        try:
            cin = datetime.strptime(checkin, '%Y-%m-%d')
            cout = datetime.strptime(checkout, '%Y-%m-%d')
            cur = cin
            while cur < cout:
                ds = cur.strftime('%Y-%m-%d')
                if ds not in cal:
                    cal[ds] = 'booked'
                cur += timedelta(days=1)
        except ValueError:
            pass
    
    save_data(data)
    
    # Отправка уведомлений
    try:
        house = next((h for h in data.get('houses', []) if h.get('id') == house_id), None)
        house_name = house.get('name', 'Неизвестный дом') if house else 'Неизвестный дом'
        
        # Telegram
        telegram_message = (
            f"🔔 НОВАЯ ЗАЯВКА НА БРОНИРОВАНИЕ\n"
            f"\n🏠 Дом: {house_name}"
            f"\n👤 Имя: {name}"
            f"\n📱 Телефон: {phone}"
            f"\n📅 Заезд: {checkin}"
            f"\n📅 Выезд: {checkout}"
            f"\n\n🌐 {request.host_url}"
        )
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            send_telegram_notification(telegram_message, TELEGRAM_CHAT_ID)
        
        # Email
        email_subject = f"Новая заявка на бронирование - {house_name}"
        email_body = f"""Новая заявка на бронирование!

Дом: {house_name}
Имя: {name}
Телефон: {phone}
Заезд: {checkin}
Выезд: {checkout}

Дата заявки: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        send_email_notification(email_subject, email_body)
    except Exception as e:
        print(f"Ошибка отправки уведомлений: {e}")
    
    session['flash_message'] = {'type': 'success', 'text': 'Бронирование успешно создано! Мы свяжемся с вами в ближайшее время.'}
    return redirect(url_for('house', house_id=house_id))


# ==================== ROUTES - АДМИНКА ====================

@app.route('/login')
def login():
    """Страница входа в админку"""
    if session.get('logged_in'):
        return redirect(url_for('admin'))
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_post():
    """Обработка входа"""
    login = request.form.get('login', '').strip()
    password = request.form.get('password', '').strip()
    
    data = load_data()
    users = data.get('users', [])
    
    for user in users:
        if user.get('login') == login and user.get('password') == password:
            session['logged_in'] = True
            session['admin_login'] = login
            session['flash_message'] = {'type': 'success', 'text': 'Добро пожаловать в админку!'}
            return redirect(url_for('admin'))
    
    session['flash_message'] = {'type': 'error', 'text': 'Неверный логин или пароль'}
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    """Выход из админки"""
    session.clear()
    session['flash_message'] = {'type': 'info', 'text': 'Вы вышли из системы'}
    return redirect(url_for('index'))


@app.route('/admin')
def admin():
    """Панель администрирования - основная страница"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    # Приветствие в дашборде — только при первом входе
    show_welcome = not session.get('welcome_shown', False)
    if show_welcome:
        session['welcome_shown'] = True
    return render_template('admin.html',
                           page='dashboard',
                           show_welcome=show_welcome,
                           houses=data.get('houses', []),
                           bookings=data.get('bookings', []),
                           reviews=data.get('reviews', []))


@app.route('/admin/houses')
def admin_houses():
    """Управление домами - отдельная страница"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    return render_template('admin.html',
                           page='houses',
                           houses=data.get('houses', []),
                           bookings=data.get('bookings', []),
                           reviews=data.get('reviews', []))
    # FIXME: ниже был мёртвый код (дубль после return) — удалён при рефакторинге


@app.route('/admin/bookings')
def admin_bookings():
    """Управление бронированиями"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    houses = data.get('houses', [])
    bookings = data.get('bookings', [])
    
    # Добавляем название дома к каждой брони
    for b in bookings:
        house = next((h for h in houses if h['id'] == b.get('house_id')), None)
        b['house_name'] = house['name'] if house else 'Unknown'
    
    return render_template('admin.html',
                           page='bookings',
                           houses=houses,
                           bookings=bookings,
                           reviews=data.get('reviews', []))


@app.route('/admin/reviews')
def admin_reviews():
    """Управление отзывами"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    houses = data.get('houses', [])
    reviews = data.get('reviews', [])
    
    # Добавляем название дома к каждому отзыву
    for r in reviews:
        house = next((h for h in houses if h['id'] == r.get('house_id')), None)
        r['house_name'] = house['name'] if house else 'Unknown'
    
    return render_template('admin.html',
                           page='reviews',
                           houses=houses,
                           reviews=reviews,
                           bookings=data.get('bookings', []))


@app.route('/admin/settings')
def admin_settings():
    """Настройки системы"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    return render_template('admin.html',
                           page='settings',
                           houses=data.get('houses', []),
                           bookings=data.get('bookings', []),
                           reviews=data.get('reviews', []))


# ==================== ROUTES - УПРАВЛЕНИЕ ДОМАМИ ====================

@app.route('/admin/house/add', methods=['POST'])
def admin_house_add():
    """Добавление нового дома"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    
    # Генерация ID
    max_id = 0
    for h in data.get('houses', []):
        if h['id'] > max_id:
            max_id = h['id']
    
    new_house_id = max_id + 1
    
    # Обработка загруженных изображений
    images = []
    
    # Обработка URL-ссылок
    image_urls = request.form.get('image_urls', '').strip()
    if image_urls:
        for url in image_urls.split('\n'):
            url = url.strip()
            if url.startswith('http'):
                images.append(url)
    
    # Обработка файлов
    if 'image_files' in request.files:
        files = request.files.getlist('image_files')
        for file in files:
            if file and file.filename and not file.filename.startswith('http'):
                ext = os.path.splitext(file.filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    filename = f"house{new_house_id}_{datetime.now().timestamp()}{ext}"
                    filepath = os.path.join(UPLOADS_DIR, filename)
                    file.save(filepath)
                    images.append(f"uploads/{filename}")
    
    new_house = {
        "id": new_house_id,
        "name": request.form.get('name', '').strip(),
        "short_desc": request.form.get('short_desc', '').strip(),
        "full_desc": request.form.get('full_desc', '').strip(),
        "price": request.form.get('price', type=int, default=0),
        "max_guests": request.form.get('max_guests', type=int, default=2),
        "amenities": request.form.getlist('amenities'),
        "images": images,
        "calendar": {}
    }
    
    data.setdefault('houses', []).append(new_house)
    save_data(data)
    
    session['flash_message'] = {'type': 'success', 'text': 'Дом успешно добавлен'}
    return redirect(url_for('admin'))


@app.route('/admin/house/<int:house_id>/edit', methods=['POST'])
def admin_house_edit(house_id):
    """Редактирование дома с загрузкой фото"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    
    for house in data.get('houses', []):
        if house['id'] == house_id:
            house['name'] = request.form.get('name', '').strip()
            house['short_desc'] = request.form.get('short_desc', '').strip()
            house['full_desc'] = request.form.get('full_desc', '').strip()
            house['price'] = request.form.get('price', type=int, default=0)
            house['max_guests'] = request.form.get('max_guests', type=int, default=2)
            house['amenities'] = request.form.getlist('amenities')
            
            # Добавление новых URL-изображений
            new_image_urls = request.form.get('new_image_urls', '').strip()
            if new_image_urls:
                for url in new_image_urls.split('\n'):
                    url = url.strip()
                    if url.startswith('http') and url not in house['images']:
                        house['images'].append(url)
            
            # Загрузка новых файлов
            if 'new_image_files' in request.files:
                files = request.files.getlist('new_image_files')
                for file in files:
                    if file and file.filename and not file.filename.startswith('http'):
                        ext = os.path.splitext(file.filename)[1].lower()
                        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                            filename = f"house{house_id}_{datetime.now().timestamp()}{ext}"
                            filepath = os.path.join(UPLOADS_DIR, filename)
                            file.save(filepath)
                            house['images'].append(f"uploads/{filename}")
            
            break
    
    save_data(data)
    session['flash_message'] = {'type': 'success', 'text': 'Дом обновлён'}
    return redirect(url_for('admin'))


@app.route('/admin/house/<int:house_id>/delete', methods=['POST'])
def admin_house_delete(house_id):
    """Удаление дома"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    data['houses'] = [h for h in data.get('houses', []) if h['id'] != house_id]
    
    # Также удаляем отзывы и брони этого дома
    data['reviews'] = [r for r in data.get('reviews', []) if r.get('house_id') != house_id]
    data['bookings'] = [b for b in data.get('bookings', []) if b.get('house_id') != house_id]
    
    save_data(data)
    session['flash_message'] = {'type': 'success', 'text': 'Дом удалён'}
    return redirect(url_for('admin'))


@app.route('/admin/house/<int:house_id>/upload-images', methods=['POST'])
def admin_upload_images(house_id):
    """Загрузка изображений для дома"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'images' not in request.files:
        return jsonify({'error': 'No files provided'}, status=400)
    
    files = request.files.getlist('images')
    uploaded_urls = []
    
    for file in files:
        if file and file.filename:
            # Проверяем, что это URL (внешняя ссылка)
            if file.filename.startswith('http'):
                uploaded_urls.append(file.filename)
            else:
                # Локальная загрузка
                filename = secure_filename(f"house{house_id}_{datetime.now().timestamp()}_{file.filename}")
                filepath = os.path.join(UPLOADS_DIR, filename)
                file.save(filepath)
                uploaded_urls.append(f"uploads/{filename}")
    
    # Добавляем к дому
    data = load_data()
    for house in data.get('houses', []):
        if house['id'] == house_id:
            house['images'].extend(uploaded_urls)
            break
    
    save_data(data)
    return jsonify({'images': uploaded_urls})


@app.route('/admin/house/<int:house_id>/delete-image', methods=['POST'])
def admin_delete_image(house_id):
    """Удаление изображения дома"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    image_url = request.json.get('image_url', '')
    
    data = load_data()
    for house in data.get('houses', []):
        if house['id'] == house_id and image_url in house['images']:
            house['images'].remove(image_url)
            break
    
    save_data(data)
    return jsonify({'success': True})


@app.route('/admin/house/<int:house_id>/reorder-images', methods=['POST'])
def admin_reorder_images(house_id):
    """Изменение порядка изображений"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    new_order = request.json.get('order', [])
    
    data = load_data()
    for house in data.get('houses', []):
        if house['id'] == house_id:
            house['images'] = new_order
            break
    
    save_data(data)
    return jsonify({'success': True})


# ==================== ROUTES - УПРАВЛЕНИЕ КАЛЕНДАРЁМ ====================

@app.route('/admin/calendar/<int:house_id>')
def admin_calendar(house_id):
    """Страница управления календарём дома"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    house = get_house(house_id)
    if not house:
        session['flash_message'] = {'type': 'error', 'text': 'Дом не найден'}
        return redirect(url_for('admin'))
    
    return render_template('admin.html', 
                           page='calendar', 
                           house=house,
                           houses=load_data().get('houses', []))


@app.route('/admin/calendar/<int:house_id>/update', methods=['POST'])
def admin_calendar_update(house_id):
    """Обновление статуса даты в календаре"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    date_str = request.json.get('date', '')
    status = request.json.get('status', 'free')
    special_price = request.json.get('price')
    
    data = load_data()
    
    for house in data.get('houses', []):
        if house['id'] == house_id:
            if 'calendar' not in house:
                house['calendar'] = {}
            
            if status == 'free':
                if date_str in house['calendar']:
                    if special_price:
                        # Только цена, без брони
                        house['calendar'][date_str] = {'price': special_price}
                    else:
                        del house['calendar'][date_str]
                elif special_price:
                    house['calendar'][date_str] = {'price': special_price}
            else:
                if special_price:
                    house['calendar'][date_str] = {'status': status, 'price': special_price}
                else:
                    house['calendar'][date_str] = status
            break
    
    save_data(data)
    return jsonify({'success': True})


# ==================== ROUTES - УПРАВЛЕНИЕ БРОНЯМИ ====================

@app.route('/admin/booking/<int:booking_id>/status', methods=['POST'])
def admin_booking_status(booking_id):
    """Изменение статуса брони — синхронизирует календарь"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    new_status = request.json.get('status', 'new')
    
    data = load_data()
    booking = None
    for b in data.get('bookings', []):
        if b['id'] == booking_id:
            b['status'] = new_status
            booking = b
            break
    
    if booking:
        house_id = booking['house_id']
        house = next((h for h in data.get('houses', []) if h.get('id') == house_id), None)
        if house:
            cal = house.setdefault('calendar', {})
            try:
                cin = datetime.strptime(booking['checkin'], '%Y-%m-%d')
                cout = datetime.strptime(booking['checkout'], '%Y-%m-%d')
                cur = cin
                while cur < cout:
                    ds = cur.strftime('%Y-%m-%d')
                    if new_status == 'cancelled':
                        # Удаляем даты из календаря при отмене
                        cal.pop(ds, None)
                    elif new_status in ('confirmed', 'new'):
                        # Добавляем даты при подтверждении
                        if ds not in cal:
                            cal[ds] = 'booked'
                    cur += timedelta(days=1)
            except ValueError:
                pass
    
    save_data(data)
    return jsonify({'success': True})


@app.route('/admin/booking/<int:booking_id>/delete', methods=['POST'])
def admin_booking_delete(booking_id):
    """Удаление брони — очищает даты в календаре"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    
    # Находим бронь перед удалением, чтобы очистить календарь
    booking = next((b for b in data.get('bookings', []) if b['id'] == booking_id), None)
    if booking:
        house = next((h for h in data.get('houses', []) if h.get('id') == booking['house_id']), None)
        if house:
            cal = house.get('calendar', {})
            try:
                cin = datetime.strptime(booking['checkin'], '%Y-%m-%d')
                cout = datetime.strptime(booking['checkout'], '%Y-%m-%d')
                cur = cin
                while cur < cout:
                    ds = cur.strftime('%Y-%m-%d')
                    cal.pop(ds, None)
                    cur += timedelta(days=1)
            except ValueError:
                pass
    
    data['bookings'] = [b for b in data.get('bookings', []) if b['id'] != booking_id]
    save_data(data)
    
    session['flash_message'] = {'type': 'success', 'text': 'Бронирование удалено'}
    return redirect(url_for('admin'))


@app.route('/admin/booking/<int:booking_id>/pdf')
def admin_booking_pdf(booking_id):
    """Генерация PDF билета для бронирования"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if not FPDF_AVAILABLE:
        session['flash_message'] = {'type': 'error', 'text': 'Библиотека FPDF не установлена'}
        return redirect(url_for('admin_bookings'))
    
    data = load_data()
    booking = None
    for b in data.get('bookings', []):
        if b['id'] == booking_id:
            booking = b
            break
    
    if not booking:
        session['flash_message'] = {'type': 'error', 'text': 'Бронирование не найдено'}
        return redirect(url_for('admin_bookings'))
    
    house = None
    for h in data.get('houses', []):
        if h['id'] == booking.get('house_id'):
            house = h
            break
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 20)
            self.set_text_color(90, 138, 107)
            self.cell(0, 20, 'SOTNUR - Booking Voucher', align='C')
            self.ln(20)
    
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    
    # Use simple ASCII replacement for Russian
    def to_ascii(text):
        if not text:
            return ''
        # Map common Russian chars to transliteration
        replacements = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '',
            'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }
        result = ''
        for c in str(text):
            result += replacements.get(c, c)
        return result
    
    house_name = to_ascii(house.get('name', 'Unknown') if house else 'Unknown')
    guest_name = to_ascii(booking.get('name', 'Unknown'))
    phone = booking.get('phone', 'Unknown')
    checkin = booking.get('checkin', '')
    checkout = booking.get('checkout', '')
    status = booking.get('status', '').upper()
    created = booking.get('created_at', '')[:10] if booking.get('created_at') else ''
    
    # Booking info
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, f'Booking #{booking["id"]}')
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f'House: {house_name}')
    pdf.ln(8)
    pdf.cell(0, 8, f'Guest: {guest_name}')
    pdf.ln(8)
    pdf.cell(0, 8, f'Phone: {phone}')
    pdf.ln(8)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, f'Check-in: {checkin}')
    pdf.ln(8)
    pdf.cell(0, 8, f'Check-out: {checkout}')
    pdf.ln(12)
    
    pdf.set_font('Arial', 'I', 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8, f'Created: {created}')
    pdf.ln(8)
    pdf.cell(0, 8, f'Status: {status}')
    
    # Сохранение в буфер
    output = BytesIO()
    pdf_output = pdf.output(dest='S')
    # fpdf2 возвращает bytearray, fpdf (старый) возвращает строку
    if isinstance(pdf_output, str):
        pdf_output = pdf_output.encode('latin1')
    output.write(pdf_output)
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=voucher_{booking_id}.pdf'
    
    return response


# ==================== ROUTES - УПРАВЛЕНИЕ ОТЗЫВАМИ ====================

@app.route('/admin/review/add', methods=['POST'])
def admin_review_add():
    """Добавление отзыва"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    
    # Генерация ID
    max_id = 0
    for r in data.get('reviews', []):
        if r['id'] > max_id:
            max_id = r['id']
    
    new_review = {
        "id": max_id + 1,
        "house_id": request.form.get('house_id', type=int),
        "author": request.form.get('author', '').strip(),
        "avatar": request.form.get('avatar', '').strip(),
        "text": request.form.get('text', '').strip(),
        "rating": request.form.get('rating', type=int, default=5)
    }
    
    data.setdefault('reviews', []).append(new_review)
    save_data(data)
    
    session['flash_message'] = {'type': 'success', 'text': 'Отзыв добавлен'}
    return redirect(url_for('admin'))


@app.route('/admin/review/<int:review_id>/delete', methods=['POST'])
def admin_review_delete(review_id):
    """Удаление отзыва"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    data['reviews'] = [r for r in data.get('reviews', []) if r['id'] != review_id]
    save_data(data)
    
    session['flash_message'] = {'type': 'success', 'text': 'Отзыв удалён'}
    return redirect(url_for('admin'))


# ==================== ROUTES - АНАЛИТИКА ====================

@app.route('/admin/analytics')
def admin_analytics():
    """Страница аналитики"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    data = load_data()
    bookings = data.get('bookings', [])
    houses = data.get('houses', [])
    
    # Статистика за последние 30 дней
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    recent_bookings = []
    total_revenue = 0
    total_days_booked = 0
    
    for b in bookings:
        try:
            checkin_date = datetime.strptime(b.get('checkin', ''), '%Y-%m-%d')
            if checkin_date >= thirty_days_ago:
                recent_bookings.append(b)
                
                # Подсчёт выручки
                house = next((h for h in houses if h['id'] == b.get('house_id')), None)
                if house and b.get('status') == 'confirmed':
                    try:
                        checkout_date = datetime.strptime(b.get('checkout', ''), '%Y-%m-%d')
                        nights = (checkout_date - checkin_date).days
                        if nights > 0:
                            # Проверяем есть ли особые цены в календаре
                            special_prices = house.get('calendar', {})
                            total_price = 0
                            current = checkin_date
                            while current < checkout_date:
                                date_str = current.strftime('%Y-%m-%d')
                                if date_str in special_prices:
                                    price_data = special_prices[date_str]
                                    if isinstance(price_data, dict):
                                        total_price += price_data.get('price', house.get('price', 0))
                                    else:
                                        total_price += house.get('price', 0)
                                else:
                                    total_price += house.get('price', 0)
                                current += timedelta(days=1)
                            total_revenue += total_price
                            total_days_booked += nights
                    except (ValueError, TypeError):
                        pass
        except (ValueError, TypeError):
            pass
    
    # Загруженность по домам
    house_stats = []
    for house in houses:
        total_capacity = 30  # дней в месяце
        booked_days = 0
        
        for b in bookings:
            if b.get('house_id') == house['id'] and b.get('status') != 'cancelled':
                try:
                    checkin = datetime.strptime(b.get('checkin', ''), '%Y-%m-%d')
                    checkout = datetime.strptime(b.get('checkout', ''), '%Y-%m-%d')
                    booked_days += max(0, (checkout - checkin).days)
                except (ValueError, TypeError):
                    pass
        
        load_percent = min(100, int(booked_days / total_capacity * 100)) if total_capacity > 0 else 0
        house_stats.append({
            'name': house['name'],
            'booked_days': booked_days,
            'load_percent': load_percent
        })
    
    return render_template('admin.html',
                           page='analytics',
                           recent_bookings=recent_bookings,
                           total_bookings=len(recent_bookings),
                           total_revenue=total_revenue,
                           total_days_booked=total_days_booked,
                           house_stats=house_stats,
                           houses=houses)


# ==================== ROUTES - API ====================

@app.route('/api/calendar/<int:house_id>')
def api_calendar(house_id):
    """API для получения занятых дат дома"""
    booked_dates = get_available_dates(house_id)
    return jsonify(booked_dates)


@app.route('/api/check-dates', methods=['POST'])
def api_check_dates():
    """API для проверки доступности дат перед бронированием"""
    data = request.json
    house_id = data.get('house_id')
    checkin = data.get('checkin')
    checkout = data.get('checkout')
    
    if not all([house_id, checkin, checkout]):
        return jsonify({'available': False, 'error': 'Missing data'})
    
    # Проверка дат
    occupied_dates = check_date_overlap(house_id, checkin, checkout)
    
    if occupied_dates:
        return jsonify({
            'available': False,
            'occupied': occupied_dates
        })
    
    # Подсчёт стоимости
    house = get_house(house_id)
    if house:
        try:
            checkin_date = datetime.strptime(checkin, '%Y-%m-%d')
            checkout_date = datetime.strptime(checkout, '%Y-%m-%d')
            nights = (checkout_date - checkin_date).days
            
            # Подсчёт с учётом особых цен
            calendar = house.get('calendar', {})
            total_price = 0
            current = checkin_date
            while current < checkout_date:
                date_str = current.strftime('%Y-%m-%d')
                if date_str in calendar:
                    price_data = calendar[date_str]
                    if isinstance(price_data, dict):
                        total_price += price_data.get('price', house.get('price', 0))
                    else:
                        total_price += house.get('price', 0)
                else:
                    total_price += house.get('price', 0)
                current += timedelta(days=1)
            
            return jsonify({
                'available': True,
                'nights': nights,
                'price_per_night': house.get('price', 0),
                'total_price': total_price
            })
        except (ValueError, TypeError) as e:
            return jsonify({'available': False, 'error': str(e)})
    
    return jsonify({'available': False, 'error': 'House not found'})


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Отдача загруженных файлов"""
    from flask import send_from_directory
    return send_from_directory(UPLOADS_DIR, filename)


@app.route('/api/stats')
def api_stats():
    """API для получения общей статистики"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = load_data()
    houses = data.get('houses', [])
    bookings = data.get('bookings', [])
    
    # Подсчёт статистики
    total_bookings = len(bookings)
    confirmed_bookings = len([b for b in bookings if b.get('status') == 'confirmed'])
    new_bookings = len([b for b in bookings if b.get('status') == 'new'])
    
    # Выручка за текущий месяц
    current_month = datetime.now().strftime('%Y-%m')
    month_revenue = 0
    for b in bookings:
        if b.get('status') == 'confirmed' and b.get('checkin', '').startswith(current_month):
            house = next((h for h in houses if h['id'] == b.get('house_id')), None)
            if house:
                try:
                    checkin = datetime.strptime(b.get('checkin', ''), '%Y-%m-%d')
                    checkout = datetime.strptime(b.get('checkout', ''), '%Y-%m-%d')
                    nights = (checkout - checkin).days
                    month_revenue += nights * house.get('price', 0)
                except:
                    pass
    
    return jsonify({
        'total_houses': len(houses),
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'new_bookings': new_bookings,
        'month_revenue': month_revenue
    })


# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

# Seed database on first run + миграция новых домов
seed_default_data()
migrate_missing_houses()

# Создаём директорию для загрузок если нет
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

if __name__ == '__main__':
    print("=" * 50)
    print("SOTNUR - Server started!")
    print("Site: http://127.0.0.1:5000")
    print("Admin: http://127.0.0.1:5000/admin")
    print("Login: admin / sotnur2026")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)