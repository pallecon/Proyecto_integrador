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
                displa
