import os
import django
import random
import io
import time
import hmac
import hashlib
import base64
import string
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import path
from django.conf.urls.static import static
from django.core.management import execute_from_command_line
from django.template import engines, Context
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.views.generic import RedirectView
import json
import reportes


try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

from modalidad_titulacion import monitoreo_titulacion_view
from Detalles_estudiante import detalles_estudiantes_view
from estudiante import estudiante_view
from docente import docente_view
from modalidad import modalidad_view
from etapas_titulacion import etapas_titulacion_view

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='secret-key',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        MIDDLEWARE=[
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ],
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
            }
        },
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
        }],
        STATIC_URL='/static/',
        STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')],
    )

django.setup()

from django.contrib.auth.models import User

def crear_usuario_default():
    try:
        User.objects.get(username='Adams')
    except User.DoesNotExist:
        User.objects.create_superuser('Adams', 'adams@gmail.com', '73588144')

crear_usuario_default()

image_path = os.path.join(BASE_DIR, 'static', 'images', 'salesiana.jpg')
os.makedirs(os.path.dirname(image_path), exist_ok=True)
if not os.path.exists(image_path):
    try:
        with open(image_path, 'wb') as f:
            f.write(
                b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
                b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09\x08'
                b'\x0a\x0c\x14\x0d\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e'
                b'\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xda'
            )
    except Exception as e:
        print(f"Error creando imagen: {e}")

digits_dir = os.path.join(BASE_DIR, 'static', 'images', 'captcha_digits')
os.makedirs(digits_dir, exist_ok=True)

def ensure_digit_images():
  
    if not PIL_AVAILABLE:
        print("Pillow no disponible: no se generan imágenes de dígitos.")
        return

    from PIL import Image, ImageDraw, ImageFont

    missing = [d for d in '0123456789' if not os.path.exists(os.path.join(digits_dir, f"{d}.png"))]
    if not missing:
        return


    try:
        font_path = os.path.join(BASE_DIR, 'static', 'fonts', 'DejaVuSans-Bold.ttf')
        font = ImageFont.truetype(font_path, 100)  
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 72)
        except Exception:
            font = ImageFont.load_default()

    for ch in missing:
        width, height = 80, 100
        img = Image.new('RGBA', (width, height), (30, 30, 36, 255))
        draw = ImageDraw.Draw(img)

        w, h = draw.textsize(ch, font=font)
        tx = (width - w) // 2
        ty = (height - h) // 2
        draw.text((tx, ty), ch, font=font, fill=(240, 240, 240))

        for _ in range(6):
            x1, y1 = random.randint(0, width), random.randint(0, height)
            x2, y2 = random.randint(0, width), random.randint(0, height)
            draw.line((x1, y1, x2, y2), fill=(random.randint(60, 160), random.randint(60,160), random.randint(60,160)), width=2)
        for _ in range(120):
            px, py = random.randint(0, width-1), random.randint(0, height-1)
            draw.point((px, py), fill=(random.randint(40,200), random.randint(40,200), random.randint(40,200)))

        out_path = os.path.join(digits_dir, f"{ch}.png")
        try:
            img.convert('RGB').save(out_path, format='PNG')
        except Exception as e:
            print(f"Error guardando {out_path}: {e}")

    print(f"Generadas/actualizadas imágenes de dígitos: {', '.join(missing)}")

ensure_digit_images()

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 5 
CAPTCHA_TTL = 180     

def _rand_string(length=6):  
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits  
    return ''.join(random.choice(chars) for _ in range(length))

def generate_captcha_image(code):
    width, height = 240, 80 
    if not PIL_AVAILABLE:
        return None

    digits_dir = os.path.join(BASE_DIR, 'static', 'images', 'captcha_digits')
    use_digit_images = os.path.isdir(digits_dir) and all(os.path.exists(os.path.join(digits_dir, f"{d}.png")) for d in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')


    if use_digit_images:
        digit_imgs = []
        for ch in code:
            path = os.path.join(digits_dir, f"{ch}.png")
            try:
                img = Image.open(path)
                digit_imgs.append(img)
            except Exception:
                continue  

    if use_digit_images:
        total_w = sum(img.width for img in digit_imgs) + (len(digit_imgs) - 1) * 6
        img_h = max(img.height for img in digit_imgs)
        canvas = Image.new('RGBA', (max(width, total_w + 60), max(height, img_h + 40)), (255, 255, 255, 255))
        x = 20
        for img in digit_imgs:
            canvas.paste(img, (x, 10))
            x += img.width + 6

        draw = ImageDraw.Draw(canvas)
        for _ in range(300):
            x = random.randint(0, canvas.width - 1)
            y = random.randint(0, canvas.height - 1)
            draw.point((x, y), fill=(random.randint(60, 200), random.randint(60, 200), random.randint(60, 200)))

        out = io.BytesIO()
        canvas.convert("RGB").save(out, format='PNG')
        out.seek(0)
        return out

    image = Image.new('RGB', (width, height), (255, 255, 255))  
    draw = ImageDraw.Draw(image)

    for _ in range(800):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point((x, y), fill=(random.randint(60, 200), random.randint(60, 200), random.randint(60, 200)))

    try:
        font_path = os.path.join(BASE_DIR, 'static', 'fonts', 'DejaVuSans-Bold.ttf')
        font = ImageFont.truetype(font_path, 40)
    except Exception:
        font = ImageFont.load_default()

    start_x = 20
    for ch in code:
        char_img = Image.new('RGBA', (60, 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(char_img)
        color = (0, 0, 0)  
        d.text((0, 0), ch, font=font, fill=color)
        char_img = char_img.rotate(random.uniform(-30, 30), resample=Image.BILINEAR, expand=1)
        offset_y = random.randint(-6, 10)
        image.paste(char_img, (start_x, 10 + offset_y), char_img)
        start_x += random.randint(34, 46)

    image = image.filter(ImageFilter.SMOOTH_MORE)
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    return buf

def new_captcha(request):
    digits_dir = os.path.join(BASE_DIR, 'static', 'images', 'captcha_digits')
    use_digit_images = os.path.isdir(digits_dir) and all(os.path.exists(os.path.join(digits_dir, f"{d}.png")) for d in "0123456789")

    if use_digit_images:
        length = 4  
        code = ''.join(random.choice('0123456789') for _ in range(length)) 
    else:
        code = _rand_string(4) 

    request.session['captcha_code'] = code
    request.session['captcha_expiry'] = time.time() + CAPTCHA_TTL
    hm = hmac.new(settings.SECRET_KEY.encode(), (code + str(request.session['captcha_expiry'])).encode(), hashlib.sha256).hexdigest()
    request.session['captcha_hmac'] = hm
    return code

def validate_captcha(request, provided):
    now = time.time()
    expiry = request.session.get('captcha_expiry')
    code = request.session.get('captcha_code')
    if not code or not expiry or now > float(expiry):
        return False, 'Captcha expirado. Genera uno nuevo.'
    expected_hm = request.session.get('captcha_hmac')
    calc_hm = hmac.new(settings.SECRET_KEY.encode(), (code + str(expiry)).encode(), hashlib.sha256).hexdigest()
    if expected_hm and calc_hm != expected_hm:
        return False, 'Integridad del captcha fallida.'
    if not provided:
        return False, 'Captcha vacío.'
    if provided.strip().upper() != code.upper():
        return False, 'Captcha incorrecto.'
    return True, ''

def captcha_image_view(request):
    code = request.session.get('captcha_code')
    if not code:
        code = new_captcha(request)
    buf = generate_captcha_image(code) if PIL_AVAILABLE else None
    if buf is None:
        img = Image.new('RGB', (220, 80), color=(50, 50, 60)) if PIL_AVAILABLE else None
        if img:
            d = ImageDraw.Draw(img)
            d.text((20, 20), code, fill=(220, 220, 220))
            out = io.BytesIO()
            img.save(out, 'PNG')
            out.seek(0)
            return HttpResponse(out.read(), content_type='image/png')
        return HttpResponseForbidden('Pillow no está disponible en el servidor.')
    return HttpResponse(buf.read(), content_type='image/png')

# Login 
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        captcha = request.POST.get('captcha')
        
        is_valid, error_msg = validate_captcha(request, captcha)
        if not is_valid:
            new_captcha(request)
            return HttpResponse(json.dumps({
                'success': False,
                'error': error_msg,
                'captcha_url': f'/captcha_image?rand={random.random()}'
            }), content_type='application/json')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponse(json.dumps({
                'success': True,
                'redirect': '/dashboard'
            }), content_type='application/json')
        else:
            new_captcha(request)
            return HttpResponse(json.dumps({
                'success': False,
                'error': 'Usuario o contraseña incorrectos',
                'captcha_url': f'/captcha_image?rand={random.random()}'
            }), content_type='application/json')
    
    return redirect('/menu')

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Iniciar sesión</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root{
            --primary:#0f3460;
            --primary-light:#1e5a96;
            --accent:#4fb3d9;
            --card: rgba(255,255,255,0.95);
            --glass: rgba(255,255,255,0.08);
            --muted: #546e7a;
            --success: #43a047;
        }
        *{box-sizing:border-box;font-family:Inter, system-ui, -apple-system, "Segoe UI", Roboto, Arial;}
        html,body{height:100%;margin:0;color:#0a1929;}
        body{
            background: linear-gradient(135deg, #0f3460 0%, #1e5a96 50%, #0a1929 100%);
            display:flex;align-items:center;justify-content:center;padding:28px;
            min-height: 100vh;
        }
        .card{
            width:420px; max-width:92vw; border-radius:14px; padding:28px; background:var(--card);
            box-shadow: 0 12px 40px rgba(0,0,0,0.3), 0 8px 40px rgba(79, 179, 217, 0.2);
            border: 2px solid var(--accent); backdrop-filter: blur(6px);
        }
        .logo {display:flex;align-items:center;gap:12px;margin-bottom:18px}
        .logo img{width:48px;height:48px;border-radius:10px;object-fit:cover;box-shadow:0 6px 18px rgba(79, 179, 217, 0.3)}
        h1{margin:0;font-size:1.25rem;color:var(--primary);letter-spacing:0.4px;font-weight:700}
        p.lead{margin:8px 0 18px 0;color:var(--muted);font-size:0.92rem}
        .field{margin-bottom:12px}
        input[type="text"], input[type="password"]{
            width:100%; padding:12px 14px; border-radius:10px; border:2px solid var(--accent);
            background:rgba(79, 179, 217, 0.05); color:var(--primary); outline:none; font-size:0.96rem;
            transition: all 0.3s;
        }
        input[type="text"]::placeholder, input[type="password"]::placeholder{
            color:var(--muted);
        }
        input[type="text"]:focus, input[type="password"]:focus{
            border-color:var(--primary-light);
            background:rgba(79, 179, 217, 0.1);
            box-shadow: 0 0 0 3px rgba(79, 179, 217, 0.2);
        }
        .captcha-row{display:flex;gap:12px;align-items:center;margin-top:8px}
        .captcha-img{width:150px;height:64px;border-radius:8px;object-fit:cover;border:2px solid var(--accent);background:#f5f7fa}
        .btn-primary{width:100%;padding:12px;border-radius:10px;border:none;background:linear-gradient(90deg,var(--primary),var(--primary-light));color:white;font-weight:700;cursor:pointer;margin-top:10px;transition:all 0.3s}
        .btn-primary:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(79, 179, 217, 0.4)}
        .meta{display:flex;justify-content:space-between;align-items:center;margin-top:12px;color:var(--muted);font-size:0.86rem}
        .error{background:#ffebee;color:#c62828;padding:10px;border-radius:8px;margin-bottom:12px;font-weight:600;border-left:4px solid #d32f2f}
        .smallbtn{background:none;border:none;color:var(--primary);cursor:pointer;font-weight:600;padding:6px;border-radius:6px;transition:all 0.3s}
        .smallbtn:hover{background:rgba(79, 179, 217, 0.1)}
        .show-pass{background:none;border:none;color:var(--primary);cursor:pointer;font-weight:700;transition:all 0.3s}
        .show-pass:hover{color:var(--accent)}
        @media (max-width:520px){ .card{padding:18px} .captcha-img{width:130px;height:58px} }
    </style>
    <script>
        function reloadCaptcha(){ document.getElementById('captcha_img').src = '/captcha_image?rand=' + Math.random(); }
        function togglePassword(){ var p=document.getElementById('password'); var b=document.getElementById('showbtn'); if(p.type==='password'){p.type='text'; b.textContent='Ocultar'}else{p.type='password'; b.textContent='Mostrar'} }
        document.addEventListener('DOMContentLoaded', function(){ document.getElementById('username')?.focus(); });
    </script>
</head>
<body>
    <main class="card" role="main" aria-labelledby="login-title">
        <div class="logo" aria-hidden="false">
            <img src="/static/logo.png" alt="Logo">
            <div>
                <h1 id="login-title">Iniciar sesión</h1>
                <p class="lead">Introduce tus credenciales y resuelve el captcha.</p>
            </div>
        </div>

        <form method="post" novalidate>
            {% if error %}<div class="error">{{ error }}</div>{% endif %}
            <div class="field">
                <label class="sr-only">Usuario</label>
                <input id="username" type="text" name="username" placeholder="Usuario" required autocomplete="username">
            </div>

            <div class="field" style="position:relative;display:flex;gap:8px;">
                <input id="password" type="password" name="password" placeholder="Contraseña" required autocomplete="current-password">
                <button type="button" id="showbtn" class="show-pass" onclick="togglePassword()">Mostrar</button>
            </div>

            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <div class="captcha-row" aria-live="polite">
                <img id="captcha_img" class="captcha-img" src="/captcha_image?rand={{ rand }}" alt="Captcha">
                <div style="flex:1;display:flex;flex-direction:column;">
                    <input type="text" name="captcha" placeholder="Escribe los caracteres" required>
                    <div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
                        <button type="button" class="smallbtn" onclick="reloadCaptcha()">Recargar</button>
                        <span style="color:var(--muted);font-size:0.88rem">Válido 3 min</span>
                    </div>
                </div>
            </div>

            <button type="submit" class="btn-primary">Entrar</button>
        </form>

        <div class="meta" aria-hidden="false">
            <div>¿Olvidaste tu contraseña? <a style="color:var(--primary);text-decoration:none;font-weight:600" href="/registro">Contactar</a></div>
            <div>Máx {{ max_attempts }} intentos</div>
        </div>
    </main>
</body>
</html>
'''.replace('{{ max_attempts }}', str(MAX_ATTEMPTS))

def logout_view(request):
    logout(request)
    return redirect('/menu')

def menu_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard')

    usuario = "Iniciar sesión"
    is_authenticated = False

    template_engine = engines['django'].engine

    template = template_engine.from_string(''' 
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Salesiana - Sistema de Gestión de Titulación</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            :root {
                --primary: #0f3460;
                --primary-dark: #051e3e;
                --primary-light: #1e5a96;
                --accent: #4fb3d9;
                --white: #ffffff;
                --light: #f5f7fa;
                --dark: #0a1929;
                --muted: #546e7a;
            }

            html, body {
                height: 100%;
                font-family: 'Inter', sans-serif;
                color: var(--dark);
                background: var(--light);
            }

            /* Top Bar */
            .top-bar {
                background: linear-gradient(90deg, var(--primary), var(--primary-light));
                color: var(--white);
                padding: 12px 0;
                font-size: 0.9em;
                border-bottom: 2px solid var(--accent);
            }

            .top-bar-content {
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 20px;
                display: flex;
                justify-content: flex-end;
                align-items: center;
            }

            .top-bar-right {
                display: flex;
                gap: 20px;
                align-items: center;
            }

            .user-section {
                display: flex;
                gap: 15px;
                align-items: center;
            }

            .user-info {
                color: var(--white);
                font-size: 0.95em;
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 15px;
                background: rgba(255,255,255,0.15);
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.3s ease;
                border: 1px solid rgba(255,255,255,0.2);
            }

            .user-info:hover {
                background: rgba(255,255,255,0.25);
                transform: translateY(-2px);
            }

            .logout-btn {
                background: var(--accent);
                color: var(--primary);
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s ease;
                text-decoration: none;
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 0.9em;
            }

            .logout-btn:hover {
                background: var(--white);
                transform: translateY(-2px);
            }

            /* Modal Login */
            .modal {
                display: none;
                position: fixed;
                z-index: 2000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
                backdrop-filter: blur(4px);
            }

            .modal.show {
                display: flex;
                align-items: center;
                justify-content: center;
                animation: fadeIn 0.3s ease;
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            .modal-content {
                background: var(--white);
                padding: 40px;
                border-radius: 12px;
                max-width: 420px;
                width: 90%;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                animation: slideUp 0.3s ease;
                border: 2px solid var(--accent);
            }

            @keyframes slideUp {
                from { 
                    transform: translateY(50px);
                    opacity: 0;
                }
                to { 
                    transform: translateY(0);
                    opacity: 1;
                }
            }

            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 25px;
            }

            .modal-header h2 {
                color: var(--primary);
                font-size: 1.5em;
                margin: 0;
            }

            .close-btn {
                background: none;
                border: none;
                font-size: 1.5em;
                color: var(--muted);
                cursor: pointer;
                transition: color 0.3s;
            }

            .close-btn:hover {
                color: var(--primary);
            }

            .form-group {
                margin-bottom: 15px;
            }

            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: var(--primary);
                font-weight: 600;
                font-size: 0.95em;
            }

            .form-group input {
                width: 100%;
                padding: 10px 12px;
                border: 2px solid var(--accent);
                border-radius: 6px;
                font-size: 0.95em;
                transition: border-color 0.3s;
                background: rgba(79, 179, 217, 0.05);
                color: var(--primary);
            }

            .form-group input::placeholder {
                color: var(--muted);
            }

            .form-group input:focus {
                outline: none;
                border-color: var(--primary);
                box-shadow: 0 0 0 3px rgba(79, 179, 217, 0.2);
                background: rgba(79, 179, 217, 0.1);
            }

            .captcha-row {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
                align-items: center;
            }

            .captcha-img {
                width: 120px;
                height: 50px;
                border-radius: 6px;
                border: 2px solid var(--accent);
                object-fit: cover;
                cursor: pointer;
                background: var(--light);
            }

            .captcha-input-group {
                flex: 1;
            }

            .captcha-input-group input {
                width: 100%;
            }

            .reload-captcha {
                background: linear-gradient(90deg, var(--primary), var(--primary-light));
                color: var(--white);
                border: none;
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.85em;
                margin-top: 6px;
                width: 100%;
                font-weight: 600;
                transition: all 0.3s;
            }

            .reload-captcha:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(79, 179, 217, 0.3);
            }

            .error {
                background: #ffebee;
                color: #c62828;
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 15px;
                font-size: 0.9em;
                border-left: 4px solid #d32f2f;
            }

            .btn-login {
                width: 100%;
                padding: 12px;
                background: linear-gradient(90deg, var(--primary), var(--primary-light));
                color: var(--white);
                border: none;
                border-radius: 6px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 10px;
            }

            .btn-login:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(79, 179, 217, 0.4);
            }

            /* Header/Navbar */
            nav {
                background: var(--white);
                padding: 15px 0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                position: sticky;
                top: 0;
                z-index: 1000;
                border-bottom: 2px solid var(--accent);
            }

            .navbar-container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                height: 80px;
            }

            .logo-section {
                display: flex;
                align-items: center;
                gap: 15px;
            }

            .logo-img {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, var(--primary), var(--primary-light));
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--white);
                font-weight: bold;
                font-size: 1.5em;
                box-shadow: 0 4px 12px rgba(79, 179, 217, 0.3);
            }

            .logo-img-file {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                object-fit: cover;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }

            .logo-text h1 {
                color: var(--primary);
                font-size: 1.5em;
                font-weight: 700;
                margin: 0;
            }

            .logo-text p {
                color: var(--accent);
                font-size: 0.85em;
                margin: 2px 0 0 0;
                font-weight: 600;
            }

            /* Botón Hamburguesa */
            .hamburger-btn {
                display: none;
                background: none;
                border: none;
                color: var(--primary);
                font-size: 1.5em;
                cursor: pointer;
                padding: 8px;
                margin-left: 20px;
            }

            .hamburger-btn:hover {
                color: var(--accent);
            }

            .sidebar-menu {
                position: fixed;
                left: -300px;
                top: 0;
                width: 300px;
                height: 100vh;
                background: linear-gradient(180deg, var(--primary), var(--primary-light));
                box-shadow: 2px 0 8px rgba(0,0,0,0.2);
                transition: left 0.3s ease;
                z-index: 999;
                padding-top: 20px;
                overflow-y: auto;
            }

            .sidebar-menu.active {
                left: 0;
            }

            .sidebar-header {
                padding: 20px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .sidebar-header h3 {
                color: var(--white);
                margin: 0;
                font-size: 1.3em;
            }

            .sidebar-close {
                background: none;
                border: none;
                color: var(--white);
                font-size: 1.5em;
                cursor: pointer;
            }

            .sidebar-menu-items {
                padding: 20px 0;
            }

            .sidebar-menu-items a {
                display: block;
                padding: 15px 20px;
                color: var(--white);
                text-decoration: none;
                transition: all 0.3s ease;
                border-left: 4px solid transparent;
            }

            .sidebar-menu-items a:hover {
                background: rgba(255, 255, 255, 0.1);
                border-left-color: var(--accent);
                padding-left: 24px;
            }

            .overlay {
                display: none;
                position: fixed;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 998;
            }

            .overlay.active {
                display: block;
            }

            .nav-links {
                display: flex;
                gap: 0;
                list-style: none;
                flex: 1;
                justify-content: center;
            }

            .nav-links li {
                flex: 1;
                text-align: center;
            }

            .nav-links li a {
                color: var(--dark);
                text-decoration: none;
                padding: 8px 12px;
                display: block;
                font-weight: 500;
                font-size: 0.85em;
                transition: all 0.3s ease;
                border-bottom: 3px solid transparent;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .nav-links li a:hover {
                color: var(--primary);
                border-bottom-color: var(--accent);
            }

            .nav-right {
                display: flex;
                gap: 15px;
                align-items: center;
            }

            .hero-banner {
                background: linear-gradient(rgba(15, 52, 96, 0.7), rgba(15, 52, 96, 0.7)), 
                            url('/static/images/salesiana.jpg') center/cover;
                color: var(--white);
                padding: 120px 20px;
                text-align: center;
                position: relative;
            }

            .hero-content {
                max-width: 900px;
                margin: 0 auto;
            }

            .hero-banner h2 {
                font-size: 3.5em;
                font-weight: 700;
                margin-bottom: 15px;
                font-family: 'Playfair Display', serif;
            }

            .hero-banner p {
                font-size: 1.3em;
                color: #f0f0f0;
                margin-bottom: 30px;
            }

            /* Main Content */
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 80px 20px;
            }

            .section-header {
                text-align: center;
                margin-bottom: 60px;
            }

            .section-header h3 {
                font-size: 2.5em;
                color: var(--primary);
                margin-bottom: 15px;
                font-weight: 700;
            }

            .section-header p {
                color: var(--muted);
                font-size: 1.1em;
                margin-bottom: 20px;
            }

            .divider {
                width: 100px;
                height: 4px;
                background: linear-gradient(90deg, var(--primary), var(--accent));
                margin: 0 auto;
                border-radius: 2px;
            }

            .cards-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 40px;
                margin-top: 50px;
            }

            .card {
                background: var(--white);
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                transition: all 0.4s ease;
                border-top: 5px solid var(--accent);
                cursor: pointer;
            }

            .card:hover {
                transform: translateY(-12px);
                box-shadow: 0 12px 30px rgba(79, 179, 217, 0.2);
            }

            .card-icon {
                background: linear-gradient(135deg, var(--primary), var(--primary-light));
                padding: 40px;
                text-align: center;
                font-size: 3.5em;
                color: var(--white);
                height: 180px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .card-content {
                padding: 30px;
            }

            .card-content h4 {
                color: var(--primary);
                font-size: 1.4em;
                margin-bottom: 15px;
                font-weight: 700;
            }

            .card-content p {
                color: var(--muted);
                font-size: 1em;
                margin-bottom: 25px;
                line-height: 1.6;
            }

            .card-btn {
                background: linear-gradient(90deg, var(--primary), var(--primary-light));
                color: var(--white);
                border: none;
                padding: 12px 28px;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 10px;
                font-weight: 600;
                transition: all 0.3s ease;
                font-size: 0.95em;
            }

            .card-btn:hover {
                transform: translateX(5px);
                box-shadow: 0 6px 20px rgba(79, 179, 217, 0.3);
            }

            .modules-hidden {
                display: none;
            }

            .info-section {
                background: var(--light);
                padding: 80px 20px;
            }

            .info-grid {
                max-width: 1400px;
                margin: 0 auto;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 40px;
            }

            .info-item {
                text-align: center;
            }

            .info-icon {
                font-size: 3em;
                color: var(--accent);
                margin-bottom: 15px;
            }

            .info-item h5 {
                color: var(--primary);
                margin-bottom: 10px;
                font-weight: 700;
            }

            .info-item p {
                color: var(--muted);
                font-size: 0.95em;
            }

            footer {
                background: linear-gradient(90deg, var(--primary), var(--primary-light));
                color: var(--white);
                padding: 50px 20px;
                margin-top: 80px;
            }

            .footer-content {
                max-width: 1400px;
                margin: 0 auto;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 40px;
                margin-bottom: 30px;
            }

            .footer-section h6 {
                color: var(--accent);
                margin-bottom: 15px;
                font-weight: 700;
            }

            .footer-section ul {
                list-style: none;
            }

            .footer-section ul li {
                margin-bottom: 8px;
            }

            .footer-section a {
                color: rgba(255,255,255,0.8);
                text-decoration: none;
                transition: color 0.3s;
                font-size: 0.9em;
            }

            .footer-section a:hover {
                color: var(--accent);
            }

            .footer-bottom {
                text-align: center;
                padding-top: 30px;
                border-top: 1px solid rgba(255,255,255,0.1);
                color: rgba(255,255,255,0.7);
                font-size: 0.9em;
            }

            @media (max-width: 768px) {
                .hamburger-btn {
                    display: block;
                }

                .navbar-container {
                    height: auto;
                    flex-direction: column;
                    padding: 15px 20px;
                }

                .nav-links {
                    flex-direction: column;
                    width: 100%;
                    margin-top: 15px;
                    gap: 5px;
                    display: none;
                }

                .nav-links li a {
                    padding: 10px 0;
                }

                .hero-banner h2 {
                    font-size: 2em;
                }

                .section-header h3 {
                    font-size: 1.8em;
                }

                .cards-grid {
                    grid-template-columns: 1fr;
                }
            }

            @media (max-width: 600px) {
                .top-bar {
                    padding: 8px 0;
                }

                .hero-banner {
                    padding: 60px 20px;
                }

                .hero-banner h2 {
                    font-size: 1.5em;
                }

                .container {
                    padding: 40px 20px;
                }
            }
        </style>
    </head>
    <body>
        <!-- Top Bar -->
        <div class="top-bar">
            <div class="top-bar-content">
                <div class="top-bar-right">
                    <div class="user-section">
                        <div class="user-info" onclick="openLoginModal()">
                            <i class="fas fa-user-circle"></i>
                            <span>{{ usuario }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Modal de Login -->
        <div id="loginModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Iniciar sesión</h2>
                    <button class="close-btn" onclick="closeLoginModal()">&times;</button>
                </div>

                <div id="loginError" class="error" style="display: none;"></div>

                <form id="loginForm" novalidate>
                    <div class="form-group">
                        <label>Usuario</label>
                        <input type="text" id="username" name="username" placeholder="Introduce tu usuario" required autofocus>
                    </div>

                    <div class="form-group">
                        <label>Contraseña</label>
                        <input type="password" name="password" id="password" placeholder="Introduce tu contraseña" required>
                    </div>

                    <div class="captcha-row">
                        <img id="captcha_img" class="captcha-img" src="/captcha_image?rand={{ rand }}" alt="Captcha" onclick="reloadCaptcha()">
                        <div class="captcha-input-group">
                            <input type="text" name="captcha" id="captchaInput" placeholder="Captcha" required>
                            <button type="button" class="reload-captcha" onclick="reloadCaptcha()">Recargar</button>
                        </div>
                    </div>

                    <button type="submit" class="btn-login">Entrar</button>
                </form>
            </div>
        </div>

        <!-- Overlay para el menú -->
        <div class="overlay" id="overlay"></div>

        <!-- Menú Lateral -->
        <div class="sidebar-menu" id="sidebarMenu">
            <div class="sidebar-header">
                <h3>Menú</h3>
                <button class="sidebar-close" onclick="closeSidebar()">&times;</button>
            </div>
            <div class="sidebar-menu-items">
                <a href="/seguimiento"><i class="fas fa-chart-line"></i> Seguimiento</a>
                <a href="/registro"><i class="fas fa-clipboard-list"></i> Registro</a>
                <a href="/reportes"><i class="fas fa-file-pdf"></i> Reportes</a>
            </div>
        </div>

        <!-- Navbar -->
        <nav>
            <div class="navbar-container">
                <div class="logo-section">
                    <img src="/static/logo.png" alt="Logo Salesiana" class="logo-img-file">
                    <div class="logo-text">
                        <h1>Salesiana</h1>
                        <p>Siempre a tu lado</p>
                    </div>
                </div>
                <ul class="nav-links">
                    <li><a href="#">Ciencias de la Educación</a></li>
                    <li><a href="#">Ingeniería de Sistemas</a></li>
                    <li><a href="#">Contaduría Pública</a></li>
                    <li><a href="#">Derecho</a></li>
                    <li><a href="#">Psicomotricidad</a></li>
                    <li><a href="#">Educación Parvularia</a></li>
                    <li><a href="#">Educación Especial</a></li>
                    <li><a href="#">Pedagogía Adulto Mayor</a></li>
                    <li><a href="#">Ingeniería Comercial</a></li>
                    <li><a href="#">Gastronomía</a></li>
                </ul>
                <div class="nav-right">
                </div>
            </div>
        </nav>

        <!-- Hero Banner -->
        <div class="hero-banner">
            <div class="hero-content">
                <h2>Salesiana</h2>
                <p>Siempre te ayudaremos</p>
            </div>
        </div>

        <!-- Main Content -->
        <div class="container">
        </div>

        <script>
            function openLoginModal() {
                document.getElementById('loginModal').classList.add('show');
                document.getElementById('username').focus();
            }

            function closeLoginModal() {
                document.getElementById('loginModal').classList.remove('show');
                document.getElementById('loginError').style.display = 'none';
                document.getElementById('loginForm').reset();
            }

            function reloadCaptcha() {
                const rand = Math.random();
                document.getElementById('captcha_img').src = '/captcha_image?rand=' + rand;
            }

            function openSidebar() {
                document.getElementById('sidebarMenu').classList.add('active');
                document.getElementById('overlay').classList.add('active');
            }

            function closeSidebar() {
                document.getElementById('sidebarMenu').classList.remove('active');
                document.getElementById('overlay').classList.remove('active');
            }

            document.getElementById('loginForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const captcha = document.getElementById('captchaInput').value;
                const errorDiv = document.getElementById('loginError');
                
                const formData = new FormData();
                formData.append('username', username);
                formData.append('password', password);
                formData.append('captcha', captcha);
                
                fetch('/login', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = data.redirect;
                    } else {
                        errorDiv.textContent = data.error;
                        errorDiv.style.display = 'block';
                        
                        if (data.captcha_url) {
                            document.getElementById('captcha_img').src = data.captcha_url;
                            document.getElementById('captchaInput').value = '';
                            document.getElementById('captchaInput').focus();
                        }
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    errorDiv.textContent = 'Error al procesar el login. Intenta nuevamente.';
                    errorDiv.style.display = 'block';
                });
            });

            document.getElementById('overlay').addEventListener('click', closeSidebar);

            window.onclick = function(event) {
                var modal = document.getElementById('loginModal');
                if (event.target == modal) {
                    closeLoginModal();
                }
            }
        </script>
    </body>
    </html>
    ''')
    context = Context({
        'usuario': usuario,
        'is_authenticated': is_authenticated,
        'rand': random.random()
    })
    return HttpResponse(template.render(context))

def dashboard_view(request):
    usuario = request.user.username if request.user.is_authenticated else "Usuario"
    template_engine = engines['django'].engine
    template = template_engine.from_string('''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Panel Administrativo - Salesiana</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
        <style>
            :root{
                --brand:#0f3460; /* color institucional azul */
                --brand-light:#1e5a96;
                --dark:#142028;
                --muted:#6b7b86;
                --card:#ffffff;
            }
            *{box-sizing:border-box}
            body{font-family:Inter, system-ui, -apple-system, "Segoe UI", Roboto, Arial;background:#f3f6f8;margin:0;color:var(--dark)}
            header{
                background: linear-gradient(90deg,var(--brand),var(--brand-light));
                color:white;padding:18px 28px;display:flex;align-items:center;gap:20px;
                box-shadow:0 4px 18px rgba(0,0,0,0.12)
            }
            .logo{display:flex;align-items:center;gap:14px}
            .logo img{width:54px;height:54px;border-radius:8px;object-fit:cover;border:2px solid rgba(255,255,255,0.08)}
            .logo h1{font-size:1.15rem;margin:0;font-weight:700}
            .header-right{margin-left:auto;display:flex;align-items:center;gap:12px;font-weight:600}
            .container{max-width:1200px;margin:28px auto;padding:0 20px}
            .grid{display:grid;grid-template-columns:260px 1fr;gap:22px;align-items:start}
            /* Sidebar */
            .sidebar{background:linear-gradient(180deg,rgba(255,255,255,0.98),rgba(255,255,255,0.96));padding:18px;border-radius:10px;box-shadow:0 6px 20px rgba(20,32,40,0.05)}
            .profile{display:flex;align-items:center;gap:12px;margin-bottom:12px}
            .avatar{width:48px;height:48px;border-radius:8px;background:var(--brand);display:flex;align-items:center;justify-content:center;color:white;font-weight:700}
            .nav a{display:block;padding:10px 12px;border-radius:8px;color:var(--dark);text-decoration:none;margin-bottom:6px;font-weight:600}
            .nav a:hover{background:#f2f6f8}
            .nav .active{background:linear-gradient(90deg,var(--brand),var(--brand-light));color:white}
            .toggle-btn{display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border-radius:8px;background:transparent;border:1px solid transparent;color:var(--dark);cursor:pointer;font-weight:700;margin-bottom:6px;width:100%}
            .toggle-btn:hover{background:#f8fafb}
            .submenu{display:none;padding-left:8px;margin-bottom:8px}
            .submenu a{display:block;padding:8px 12px;border-radius:6px;color:var(--dark);text-decoration:none;background:transparent;font-weight:600}
            .submenu a:hover{background:#f2f6f8;padding-left:14px}
            .submenu.show{display:block}
            /* Main */
            .main-card{background:var(--card);padding:18px;border-radius:10px;box-shadow:0 6px 24px rgba(20,32,40,0.06)}
            .row{display:flex;gap:16px;margin-bottom:18px;flex-wrap:wrap}
            .stat{flex:1;min-width:160px;background:linear-gradient(180deg,#fff,#fbfdff);padding:18px;border-radius:10px;border-left:6px solid var(--brand);box-shadow:0 6px 18px rgba(10,20,30,0.04)}
            .stat h3{margin:0;font-size:1.25rem}
            .stat p{margin:8px 0 0;color:var(--muted);font-size:0.95rem}
            .actions{display:flex;gap:12px;flex-wrap:wrap}
            .btn{padding:10px 14px;border-radius:8px;border:none;cursor:pointer;font-weight:700}
            .btn-primary{background:var(--brand);color:white}
            .btn-outline{background:white;border:1px solid #e6eef2;color:var(--dark)}
            table{width:100%;border-collapse:collapse}
            th,td{padding:12px 10px;text-align:left;border-bottom:1px solid #eef4f6;font-size:0.95rem}
            th{background:#fbfcfd;color:var(--muted);font-weight:700}
            .small{font-size:0.85rem;color:var(--muted)}
            footer{max-width:1200px;margin:28px auto;padding:20px;color:var(--muted);text-align:center}
            @media (max-width:900px){.grid{grid-template-columns:1fr;}.sidebar{order:2}.main-card{order:1}}
        </style>
    </head>
    <body>
        <header role="banner">
            <div class="logo" aria-hidden="false">
                <img src="/static/logo.png" alt="Logo">
                <div>
                    <h1>Salesiana - Administracion </h1>
                    <div class="small">Gestión de Titulación</div>
                </div>
            </div>
            <div class="header-right" aria-hidden="false">
                <div class="small">Bienvenido, {{ usuario }}</div>
                <a href="/logout" style="color:white;text-decoration:none;padding:8px 12px;background:rgba(0,0,0,0.12);border-radius:8px">Salir</a>
            </div>
        </header>

        <main class="container" role="main">
            <div class="grid">
                <!-- Sidebar -->
                <aside class="sidebar" aria-label="Navegación principal">
                    <div class="profile">
                        <div class="avatar">{{ usuario|slice:":1"|upper }}</div>
                        <div>
                            <div style="font-weight:700">{{ usuario }}</div>
                            <div class="small">Administrador</div>
                        </div>
                    </div>

                    <nav class="nav" aria-label="Menú">
                        <!-- Seguimiento: botón que despliega submenu -->
                        <button class="toggle-btn" type="button" onclick="toggleSubmenu('seguimientoSub')">
                            Seguimiento
                            <span id="icon-seguimiento">▸</span>
                        </button>
                        <div id="seguimientoSub" class="submenu" aria-hidden="true">
                            <a href="/monitoreo_titulacion">Monitoreo de Titulación</a>
                            <a href="/detalles_estudiante">Detalles del Estudiante</a>
                        </div>

                        <!-- Registro: botón que despliega submenu -->
                        <button class="toggle-btn" type="button" onclick="toggleSubmenu('registroSub')">
                            Registro
                            <span id="icon-registro">▸</span>
                        </button>
                        <div id="registroSub" class="submenu" aria-hidden="true">
                            <a href="/estudiantes">Estudiante</a>
                            <a href="/docentes">Docente</a>
                            <a href="/modalidad">Modalidad</a>
                            <a href="/etapas_titulacion">Etapas de Titulación</a>
                        </div>

                        <a href="/reportes">Reportes</a>
                    </nav>

                </aside>

                <!-- Main content -->
                <section>
                    <div class="main-card" role="region" aria-label="Resumen panel">
                        <!-- Área vacía como se solicitó -->
                    </div>
                </section>
            </div>
        </main>

        <footer>
            Salesiana - Sistema de Gestión de Titulación • Diseño administrativo
        </footer>

        <script>
            function toggleSubmenu(id) {
                const el = document.getElementById(id);
                const isShown = el.classList.toggle('show');
                el.setAttribute('aria-hidden', !isShown);
                // cambiar icono
                const iconId = id === 'seguimientoSub' ? 'icon-seguimiento' : 'icon-registro';
                const icon = document.getElementById(iconId);
                if (icon) icon.textContent = isShown ? '▾' : '▸';
            }
            // opcional: cerrar submenus al cargar en pantallas pequeñas
            document.addEventListener('DOMContentLoaded', function() {
                // mantener cerrados por defecto; si desea abrir alguno por defecto, reemplazar aquí
            });
        </script>
    </body>
    </html>
    ''')
    ctx = Context({
        'usuario': usuario,
        'now': datetime.now().strftime('%d-%m-%Y %H:%M')
    })
    return HttpResponse(template.render(ctx))

def seguimiento_view(request):
    template_engine = engines['django'].engine
    template = template_engine.from_string('''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Seguimiento</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
            body {
                font-family: 'Poppins', Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-image: url('/static/images/sale.jpg');
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                min-height: 100vh;
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }
            .menu-buttons {
                display: flex;
                flex-direction: column;
                gap: 32px;
                position: fixed;
                top: 0;
                left: 0;
                height: 100%;
                width: 370px;
                background: rgba(30, 30, 40, 0.82);
                box-shadow: 6px 0 40px 0 #00c3ff33;
                padding: 60px 40px 40px 40px;
                z-index: 30;
                backdrop-filter: blur(14px);
                border-top-right-radius: 40px;
                border-bottom-right-radius: 40px;
                border-left: 2px solid rgba(255,255,255,0.10);
                animation: slideIn 0.5s cubic-bezier(.68,-0.55,.27,1.55);
            }
            @keyframes slideIn {
                from { transform: translateX(-100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            .menu-buttons.open {
                display: flex;
            }
            .menu-buttons h2 {
                color: #fff;
                font-size: 2.3em;
                margin-bottom: 36px;
                text-align: center;
                letter-spacing: 2px;
                font-weight: 700;
                text-shadow: 0 2px 18px #00c3ff55;
            }
            /* Estilos para los botones principales del menú */
            .menu-button {
                padding: 15px 20px;
                background: linear-gradient(135deg, #00c3ff, #3a7bd5);
                color: #fff;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                text-decoration: none;
                font-size: 1.1em;
                font-weight: 600;
                text-align: left;
                margin: 4px 0; /* Reducido de 8px a 4px */
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 4px 12px rgba(0, 195, 255, 0.2);
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }

            .menu-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 195, 255, 0.4);
            }

            .menu-button.active {
                background: linear-gradient(135deg, #3a7bd5, #00c3ff);
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 195, 255, 0.4);
            }

            .top-right-image {
                position: absolute;
                top: 36px;
                right: 36px;
                width: 340px;
                height: auto;
                border-radius: 36px;
                box-shadow: 0 12px 40px rgba(0, 195, 255, 0.22);
                border: 3px solid rgba(255,255,255,0.18);
                background: rgba(255,255,255,0.10);
                backdrop-filter: blur(3px);
                z-index: 10;
                transition: transform 0.4s cubic-bezier(.68,-0.55,.27,1.55), box-shadow 0.4s;
            }
            .top-right-image:hover {
                transform: scale(1.04) rotate(-2deg);
                box-shadow: 0 20px 60px #00c3ff55;
            }
            @media (max-width: 900px) {
                .top-right-image { width: 200px; top: 16px; right: 16px; border-radius: 20px;}
                .menu-buttons { width: 90vw; padding: 40px 10vw 30px 10vw;}
            }
            @media (max-width: 600px) {
                .top-right-image { display: none; }
                .menu-buttons { width: 100vw; border-radius: 0; left: 0; padding: 30px 10px 20px 10px;}
            }
        </style>
    </head>
    <body>
        <img src="/static/images/image.png" alt="Imagen" class="top-right-image">
        <div class="menu-buttons">
            <h2>Seguimiento</h2>
            <button class="menu-button" onclick="window.location.href='/monitoreo_titulacion'">Monitoreo de Titulación</button>
            <button class="menu-button" onclick="window.location.href='/detalles_estudiante'">Detalles del Estudiante</button>
            <button class="menu-button" onclick="window.history.back()">Atrás</button>
        </div>
    </body>
    </html>
    ''')
    context = Context({})
    return HttpResponse(template.render(context))

def registro_view(request):
    template_engine = engines['django'].engine
    template = template_engine.from_string('''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Registro</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
            body {
                font-family: 'Poppins', Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-image: url('/static/images/Sale.jpg');
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                min-height: 100vh;
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }
            .menu-buttons {
                display: flex;
                flex-direction: column;
                gap: 32px;
                position: fixed;
                top: 0;
                left: 0;
                height: 100%;
                width: 370px;
                background: rgba(30, 30, 40, 0.82);
                box-shadow: 6px 0 40px 0 #00c3ff33;
                padding: 60px 40px 40px 40px;
                z-index: 30;
                backdrop-filter: blur(14px);
                border-top-right-radius: 40px;
                border-bottom-right-radius: 40px;
                border-left: 2px solid rgba(255,255,255,0.10);
                animation: slideIn 0.5s cubic-bezier(.68,-0.55,.27,1.55);
            }
            @keyframes slideIn {
                from { transform: translateX(-100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            .menu-buttons.open {
                display: flex;
            }
            .menu-buttons h2 {
                color: #fff;
                font-size: 2.3em;
                margin-bottom: 36px;
                text-align: center;
                letter-spacing: 2px;
                font-weight: 700;
                text-shadow: 0 2px 18px #00c3ff55;
            }
            /* Estilos para los botones principales del menú */
            .menu-button {
                padding: 15px 20px;
                background: linear-gradient(135deg, #00c3ff, #3a7bd5);
                color: #fff;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                text-decoration: none;
                font-size: 1.1em;
                font-weight: 600;
                text-align: left;
                margin: 4px 0; /* Reducido de 8px a 4px */
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 4px 12px rgba(0, 195, 255, 0.2);
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }

            .menu-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 195, 255, 0.4);
            }

            .menu-button.active {
                background: linear-gradient(135deg, #3a7bd5, #00c3ff);
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 195, 255, 0.4);
            }

            .top-right-image {
                position: absolute;
                top: 36px;
                right: 36px;
                width: 340px;
                height: auto;
                border-radius: 36px;
                box-shadow: 0 12px 40px rgba(0, 195, 255, 0.22);
                border: 3px solid rgba(255,255,255,0.18);
                background: rgba(255,255,255,0.10);
                backdrop-filter: blur(3px);
                z-index: 10;
                transition: transform 0.4s cubic-bezier(.68,-0.55,.27,1.55), box-shadow 0.4s;
            }
            .top-right-image:hover {
                transform: scale(1.04) rotate(-2deg);
                box-shadow: 0 20px 60px #00c3ff55;
            }
            @media (max-width: 900px) {
                .top-right-image { width: 200px; top: 16px; right: 16px; border-radius: 20px;}
                .menu-buttons { width: 90vw; padding: 40px 10vw 30px 10vw;}
            }
            @media (max-width: 600px) {
                .top-right-image { display: none; }
                .menu-buttons { width: 100vw; border-radius: 0; left: 0; padding: 30px 10px 20px 10px;}
            }
        </style>
    </head>
    <body>
        <img src="/static/images/image.png" alt="Imagen" class="top-right-image">
        <div class="menu-buttons">
            <h2>Registro</h2>
            <button class="menu-button" onclick="window.location.href='/estudiantes'">Estudiante</button>
            <button class="menu-button" onclick="window.location.href='/docentes'">Docente</button>
            <button class="menu-button" onclick="window.location.href='/modalidad'">Modalidad</button>
            <button class="menu-button" onclick="window.location.href='/etapas_titulacion'">Etapas de Titulación</button>
            <button class="menu-button" onclick="window.history.back()">Atrás</button>
        </div>
    </body>
    </html>
    ''')
    context = Context({})
    return HttpResponse(template.render(context))

urlpatterns = [
    path('', menu_view),  
    path('login', login_view),
    path('logout', logout_view),
    path('menu', menu_view),
    path('seguimiento', seguimiento_view),
    path('registro', registro_view),
    path('dashboard', dashboard_view),
    path('reportes', reportes.reportes_view, name='reportes'),
    path('monitoreo_titulacion', monitoreo_titulacion_view),
    path('detalles_estudiante', detalles_estudiantes_view),
    path('nueva_gestion', lambda request: HttpResponse('<h1>Página de Nueva Gestión</h1>')),
    path('gestion_actual', lambda request: HttpResponse('<h1>Página de Gestión Actual</h1>')),
    path('anteriores_gestiones', lambda request: HttpResponse('<h1>Página de Anteriores Gestiones</h1>')),
    path('docentes', docente_view),
    path('estudiantes', estudiante_view),
    path('modalidad', modalidad_view),
    path('etapas_titulacion', etapas_titulacion_view),
    path('captcha_image', captcha_image_view),
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico')),  
] + static(settings.STATIC_URL, document_root=os.path.join(BASE_DIR, 'static'))

def main():
    print("¡Bienvenido al menú principal!")

if __name__ == "__main__":
    from django.core.wsgi import get_wsgi_application
    from wsgiref.simple_server import make_server
    
    application = get_wsgi_application()
    server = make_server('0.0.0.0', 8000, application)
    
    print("Servidor iniciado en http://localhost:8000")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
