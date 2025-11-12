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
    template_engine = engines['django'].engine
    error = ''
    
    failed = request.session.get('failed_attempts', 0) 
    lockout_until = request.session.get('lockout_until', 0)
    now = time.time()

    if lockout_until and now < float(lockout_until):
        remaining = int(float(lockout_until) - now)
        error = f'Cuenta temporalmente bloqueada por seguridad. Intente en {remaining} segundos.'
        template = template_engine.from_string(LOGIN_TEMPLATE)
        context = Context({
            'error': error,
            'csrf_token': request.session.get('csrf_token', ''),
            'rand': random.random(),
            'is_locked': True
        })
        return HttpResponse(template.render(context))

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        captcha = request.POST.get('captcha', '').strip()

        if not username or not password:
            error = 'Usuario y contraseña son requeridos'
        elif len(password) < 6:
            error = 'La contraseña debe tener al menos 6 caracteres'
        else:
            captcha_valid, captcha_error = validate_captcha(request, captcha)
            if not captcha_valid:
                error = captcha_error
                failed += 1
            else:
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)
                    request.session['failed_attempts'] = 0
                    request.session['lockout_until'] = 0
                    return redirect('/menu')
                else:
                    error = 'Credenciales inválidas'
                    failed += 1
        request.session['failed_attempts'] = failed
        if failed >= MAX_ATTEMPTS:
            request.session['lockout_until'] = time.time() + LOCKOUT_SECONDS
            error = f'Demasiados intentos fallidos. Cuenta bloqueada por {LOCKOUT_SECONDS} segundos.'

        new_captcha(request)

    else:
        # GET: generar nuevo captcha y token CSRF
        new_captcha(request)
        csrf_token = base64.b64encode(os.urandom(18)).decode()
        request.session['csrf_token'] = csrf_token

    template = template_engine.from_string('''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Iniciar Sesión</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #00c3ff;
                --secondary: #3a7bd5;
                --dark: #1a1f36;
                --light: #ffffff;
                --error: #ff3b3b;
            }
            
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            
            body {
                font-family: 'Poppins', sans-serif;
                background: linear-gradient(180deg, rgba(2,8,16,0.7), rgba(2,8,16,0.8)), 
                            url('/static/seguridad.jpg') center/cover no-repeat fixed;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                margin: 0;
            }
            
            .login-container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                width: 100%;
                max-width: 480px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            }
            
            .login-header {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .login-header h1 {
                color: var(--light);
                font-size: 2em;
                margin-bottom: 10px;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                color: var(--light);
                margin-bottom: 8px;
                font-size: 0.9em;
            }
            
            .form-control {
                width: 100%;
                padding: 12px 15px;
                border: 2px solid rgba(255,255,255,0.1);
                background: rgba(255,255,255,0.07);
                border-radius: 10px;
                color: var(--light);
                font-size: 1em;
                transition: all 0.3s ease;
            }
            
            .form-control:focus {
                border-color: var(--primary);
                outline: none;
                background: rgba(255,255,255,0.1);
            }
            
            .captcha-container {
                display: flex;
                gap: 15px;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .captcha-image {
                border-radius: 10px;
                border: 2px solid rgba(255,255,255,0.1);
            }
            
            .btn {
                width: 100%;
                padding: 12px;
                border: none;
                border-radius: 10px;
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                color: var(--light);
                font-size: 1em;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,195,255,0.4);
            }
            
            .error-message {
                background: rgba(255,59,59,0.1);
                color: var(--error);
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                font-size: 0.9em;
                border: 1px solid rgba(255,59,59,0.3);
            }
            
            .reload-captcha {
                background: none;
                border: none;
                color: var(--primary);
                cursor: pointer;
                font-size: 0.9em;
                text-decoration: underline;
            }
            
            @media (max-width: 480px) {
                .login-container {
                    padding: 20px;
                }
                
                .captcha-container {
                    flex-direction: column;
                }
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>Iniciar Sesión</h1>
                <p style="color: var(--light); opacity: 0.7;">Ingrese sus credenciales para continuar</p>
            </div>
            
            <form method="post" novalidate>
                {% if error %}
                <div class="error-message">{{ error }}</div>
                {% endif %}
                
                <div class="form-group">
                    <label for="username">Usuario</label>
                    <input type="text" id="username" name="username" class="form-control" required 
                           autocomplete="username" {% if is_locked %}disabled{% endif %}>
                </div>
                
                <div class="form-group">
                    <label for="password">Contraseña</label>
                    <input type="password" id="password" name="password" class="form-control" required
                           autocomplete="current-password" {% if is_locked %}disabled{% endif %}>
                </div>
                
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                
                <div class="captcha-container">
                    <img id="captcha_img" class="captcha-image" src="/captcha_image?rand={{ rand }}" 
                         alt="Captcha" style="width: 200px; height: 60px;">
                    <div style="flex: 1">
                        <input type="text" name="captcha" class="form-control" 
                               placeholder="Ingrese el código" required {% if is_locked %}disabled{% endif %}>
                        <button type="button" class="reload-captcha" onclick="reloadCaptcha()"
                                {% if is_locked %}disabled{% endif %}>
                            Recargar código
                        </button>
                    </div>
                </div>
                
                <button type="submit" class="btn" {% if is_locked %}disabled{% endif %}>
                    Ingresar
                </button>
            </form>
        </div>
        
        <script>
            function reloadCaptcha() {
                document.getElementById('captcha_img').src = 
                    '/captcha_image?rand=' + Math.random();
            }
            
            // Auto-focus al campo de usuario
            document.addEventListener('DOMContentLoaded', () => {
                document.getElementById('username')?.focus();
            });
            
            // Prevenir múltiples envíos del form
            document.querySelector('form').addEventListener('submit', function(e) {
                let btn = this.querySelector('button[type="submit"]');
                if (btn) btn.disabled = true;
            });
        </script>
    </body>
    </html>
    ''')

    context = Context({
        'error': error,
        'csrf_token': request.session.get('csrf_token', ''),
        'rand': random.random(),
        'is_locked': bool(lockout_until and now < float(lockout_until))
    })
    
    return HttpResponse(template.render(context))

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
            --accent1:#00d4ff;
            --accent2:#3a7bd5;
            --card: rgba(6,12,20,0.72);
            --glass: rgba(255,255,255,0.04);
            --muted: #9fb7cc;
        }
        *{box-sizing:border-box;font-family:Inter, system-ui, -apple-system, "Segoe UI", Roboto, Arial;}
        html,body{height:100%;margin:0;color:#e6f7ff;}
        body{
            background: linear-gradient(180deg, rgba(2,8,16,0.7), rgba(2,8,16,0.8)), 
                        url('/static/seguridad.jpg') center/cover no-repeat fixed;
            display:flex;align-items:center;justify-content:center;padding:28px;
        }
        .card{
            width:420px; max-width:92vw; border-radius:14px; padding:28px; background:var(--card);
            box-shadow: 0 12px 40px rgba(0,0,0,0.6), 0 8px 40px rgba(0,195,255,0.06);
            border: 1px solid rgba(255,255,255,0.04); backdrop-filter: blur(6px);
        }
        .logo {display:flex;align-items:center;gap:12px;margin-bottom:18px}
        .logo img{width:48px;height:48px;border-radius:10px;object-fit:cover;box-shadow:0 6px 18px rgba(0,195,255,0.06)}
        h1{margin:0;font-size:1.25rem;color:var(--accent1);letter-spacing:0.4px}
        p.lead{margin:8px 0 18px 0;color:var(--muted);font-size:0.92rem}
        .field{margin-bottom:12px}
        input[type="text"], input[type="password"]{
            width:100%; padding:12px 14px; border-radius:10px; border:1px solid rgba(255,255,255,0.06);
            background:var(--glass); color:#e8fbff; outline:none; font-size:0.96rem;
        }
        .captcha-row{display:flex;gap:12px;align-items:center;margin-top:8px}
        .captcha-img{width:150px;height:64px;border-radius:8px;object-fit:cover;border:1px solid rgba(255,255,255,0.06);background:#071426}
        .btn-primary{width:100%;padding:12px;border-radius:10px;border:none;background:linear-gradient(90deg,var(--accent1),var(--accent2));color:#042033;font-weight:700;cursor:pointer;margin-top:10px}
        .meta{display:flex;justify-content:space-between;align-items:center;margin-top:12px;color:var(--muted);font-size:0.86rem}
        .error{background:#3a0008;color:#ffd2d2;padding:10px;border-radius:8px;margin-bottom:12px;font-weight:600}
        .smallbtn{background:none;border:none;color:var(--accent1);cursor:pointer;font-weight:600;padding:6px;border-radius:6px}
        .show-pass{background:none;border:none;color:var(--accent1);cursor:pointer;font-weight:700}
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
                        <span style="color:var(--muted);font-size:0.88rem">Captcha válido por 3 minutos</span>
                    </div>
                </div>
            </div>

            <button type="submit" class="btn-primary">Entrar</button>
        </form>

        <div class="meta" aria-hidden="false">
            <div>¿Olvidaste tu contraseña? <a style="color:var(--accent1);text-decoration:none" href="/registro">Contactar</a></div>
            <div>Máx {{ max_attempts }} intentos</div>
        </div>
    </main>
</body>
</html>
'''.replace('{{ max_attempts }}', str(MAX_ATTEMPTS))

def logout_view(request):
    logout(request)
    return redirect('/login')

def menu_view(request):
    if not request.user.is_authenticated:
        return redirect('/login')
    template_engine = engines['django'].engine
    bienvenido = request.session.pop('bienvenido', False)
    usuario = request.user.username

    if bienvenido:
        template = template_engine.from_string(''' 
        <!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Menú Principal</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: url('/static/images/sale.jpg') no-repeat center center/cover;
            color: #fff;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Contenedor del menú */
        .menu-container {
            position: fixed;
            top: 0;
            left: 0;
            height: 100%;
            width: 320px;
            background: rgba(30, 30, 40, 0.85);
            backdrop-filter: blur(12px);
            box-shadow: 6px 0 40px rgba(0, 195, 255, 0.3);
            display: flex;
            flex-direction: column;
            padding: 40px 20px;
            transition: transform 0.5s ease;
        }

        .menu-header {
            text-align: center;
            margin-bottom: 40px;
        }

        .menu-header h2 {
            font-size: 2.2em;
            font-weight: 700;
            color: #00c3ff;
            text-shadow: 0 2px 12px #00c3ff44;
            letter-spacing: 1px;
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
            top: 40px;
            right: 40px;
            width: 340px;
            height: auto;
            border-radius: 36px;
            box-shadow: 0 12px 40px rgba(0, 195, 255, 0.22);
            border: 3px solid rgba(255,255,255,0.18);
            background: rgba(255,255,255,0.10);
            backdrop-filter: blur(3px);
            transition: transform 0.4s, box-shadow 0.4s;
        }

        .top-right-image:hover {
            transform: scale(1.04) rotate(-2deg);
            box-shadow: 0 20px 60px #00c3ff55;
        }

        .submenu {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-in-out;
            padding-left: 12px;
            margin-top: -2px; /* Reducido */
        }

        .submenu.open {
            max-height: 500px;
            margin-bottom: 6px; /* Reducido de 10px a 6px */
        }

        /* Estilos para los botones del submenú */
        .submenu-button {
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.08);
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            cursor: pointer;
            text-decoration: none;
            font-size: 1em;
            font-weight: 500;
            text-align: left;
            margin: 3px 0; /* Reducido */
            width: 100%;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }

        .submenu-button:hover {
            background: rgba(255, 255, 255, 0.15);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 195, 255, 0.15);
        }

        @media (max-width: 900px) {
            .menu-container { width: 80vw; padding: 30px 16px; }
            .top-right-image { width: 200px; top: 16px; right: 16px; border-radius: 20px; }
        }

        @media (max-width: 600px) {
            .menu-container { width: 100vw; border-radius: 0; padding: 20px; }
            .top-right-image { display: none; }
        }
    </style>
    <script src="https://kit.fontawesome.com/a076d05399.js" crossorigin="anonymous"></script>
</head>
<body>
    <div class="menu-container">
        <div class="menu-header">
            <h2>Menú Principal</h2>
        </div>
        <a class="menu-button" href="/seguimiento"><i class="fas fa-chart-line"></i> Seguimiento</a>
        <a class="menu-button" href="/registro"><i class="fas fa-clipboard-list"></i> Registro</a>
        <!-- Botones eliminados:
        <a class="menu-button" href="/monitoreo_titulacion"><i class="fas fa-user-graduate"></i> Monitoreo Titulación</a>
        <a class="menu-button" href="/detalles_estudiante"><i class="fas fa-user"></i> Detalles Estudiante</a>
        <a class="menu-button" href="/logout"><i class="fas fa-sign-out-alt"></i> Cerrar Sesión</a>
        -->
    </div>
    <img src="/static/images/image.png" alt="Imagen" class="top-right-image">
</body>
</html>
''')
        context = Context({'usuario': usuario})
        return HttpResponse(template.render(context))

    template = template_engine.from_string('''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Menú con Imagen</title>
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
            .menu-container {
                position: absolute;
                top: 30px;
                left: 30px;
                z-index: 20;
            }
            .menu-toggle {
                background: rgba(255,255,255,0.18);
                border: none;
                cursor: pointer;
                display: flex;
                flex-direction: column;
                gap: 7px;
                justify-content: center;
                align-items: center;
                width: 60px;
                height: 60px;
                border-radius: 20px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.18);
                transition: background 0.3s, box-shadow 0.3s;
                backdrop-filter: blur(6px);
            }
            .menu-toggle:hover {
                background: rgba(255,255,255,0.28);
                box-shadow: 0 8px 32px #00c3ff44;
            }
            .menu-toggle span {
                display: block;
                width: 36px;
                height: 5px;
                background: linear-gradient(90deg, #fff 60%, #00c3ff 100%);
                border-radius: 3px;
                transition: all 0.4s cubic-bezier(.68,-0.55,.27,1.55);
            }
            .menu-toggle.open span:nth-child(1) {
                transform: translateY(12px) rotate(45deg);
            }
            .menu-toggle.open span:nth-child(2) {
                opacity: 0;
            }
            .menu-toggle.open span:nth-child(3) {
                transform: translateY(-12px) rotate(-45deg);
            }
            .menu-buttons {
                display: none;
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

            .submenu {
                max-height: 0;
                overflow: hidden;
                transition: max-height 0.3s ease-in-out;
                padding-left: 12px;
                margin-top: -2px; /* Reducido */
            }

            .submenu.open {
                max-height: 500px;
                margin-bottom: 6px; /* Reducido de 10px a 6px */
            }

            /* Estilos para los botones del submenú */
            .submenu-button {
                padding: 12px 16px;
                background: rgba(255, 255, 255, 0.08);
                color: #fff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                cursor: pointer;
                text-decoration: none;
                font-size: 1em;
                font-weight: 500;
                text-align: left;
                margin: 3px 0; /* Reducido */
                width: 100%;
                display: flex;
                align-items: center;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
            }

            .submenu-button:hover {
                background: rgba(255, 255, 255, 0.15);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 195, 255, 0.15);
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
        <script>
            // Abrir menú automáticamente al cargar la página
            document.addEventListener('DOMContentLoaded', function() {
                document.querySelector('.menu-buttons').classList.add('open');
                document.querySelector('.menu-toggle').classList.add('open');
            });

            let activeSubmenu = null;

            function toggleSubmenu(id) {
                const submenu = document.getElementById(id);
                const button = submenu.previousElementSibling;
                
                if (activeSubmenu && activeSubmenu !== submenu) {
                    // Cerrar el submenú activo anterior
                    activeSubmenu.classList.remove('open');
                    activeSubmenu.previousElementSibling.classList.remove('active');
                }

                if (submenu.classList.contains('open')) {
                    // Cerrar el submenú actual
                    submenu.classList.remove('open');
                    button.classList.remove('active');
                    activeSubmenu = null;
                } else {
                    // Abrir el nuevo submenú
                    submenu.classList.add('open');
                    button.classList.add('active');
                    activeSubmenu = submenu;
                }
            }

            function toggleMenu() {
                const menuButtons = document.querySelector('.menu-buttons');
                const menuToggle = document.querySelector('.menu-toggle');
                menuButtons.classList.toggle('open');
                menuToggle.classList.toggle('open');
            }

            // Evitar que los clics dentro del menú lo cierren
            document.querySelector('.menu-buttons').addEventListener('click', (event) => {
                event.stopPropagation();
            });
        </script>
    </head>
    <body>
        {% if bienvenido %}
        <div style="position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#00c3ff;color:#fff;padding:16px 32px;border-radius:16px;box-shadow:0 4px 24px #00c3ff44;font-size:1.3em;z-index:1000;">
            ¡Bienvenido!
        </div>
        {% endif %}
        <div class="menu-container">
            <button class="menu-toggle" onclick="toggleMenu()">
                <span></span>
                <span></span>
                <span></span>
            </button>
        </div>
        <img src="/static/images/image.png" alt="Imagen" class="top-right-image">
        <div class="menu-buttons">
            <h2>Menú Principal</h2>
            
            <!-- Botón Seguimiento -->
            <button class="menu-button" onclick="toggleSubmenu('seguimiento')">
                Seguimiento <span class="arrow">▼</span>
            </button>
            <div id="seguimiento" class="submenu">
                <button class="submenu-button" onclick="window.location.href='/monitoreo_titulacion'">
                    Monitoreo de Titulación
                </button>
                <button class="submenu-button" onclick="window.location.href='/detalles_estudiante'">
                    Detalles del Estudiante
                </button>
            </div>

            <!-- Botón Registro -->
            <button class="menu-button" onclick="toggleSubmenu('registro')">
                Registro <span class="arrow">▼</span>
            </button>
            <div id="registro" class="submenu">
                <button class="submenu-button" onclick="window.location.href='/estudiantes'">
                    Estudiante
                </button>
                <button class="submenu-button" onclick="window.location.href='/docentes'">
                    Docente
                </button>
                <button class="submenu-button" onclick="window.location.href='/modalidad'">
                    Modalidad
                </button>
                <button class="submenu-button" onclick="window.location.href='/etapas_titulacion'">
                    Etapas de Titulación
                </button>
            </div>

            <!-- Nuevo Botón Reportes -->
            <button class="menu-button" onclick="toggleSubmenu('reportes')">
                Reportes <span class="arrow">▼</span>
            </button>
            <div id="reportes" class="submenu">
                <button class="submenu-button" onclick="window.location.href='/reporte_estudiantes'">
                    Reporte de Estudiantes
                </button>
                <button class="submenu-button" onclick="window.location.href='/reporte_docentes'">
                    Reporte de Docentes
                </button>
                <button class="submenu-button" onclick="window.location.href='/reporte_titulacion'">
                    Reporte de Titulación
                </button>
            </div>
        </div>

        <script>
            // Abrir menú automáticamente al cargar la página
            document.addEventListener('DOMContentLoaded', function() {
                document.querySelector('.menu-buttons').classList.add('open');
                document.querySelector('.menu-toggle').classList.add('open');
            });

            let activeSubmenu = null;

            function toggleSubmenu(id) {
                const submenu = document.getElementById(id);
                const button = submenu.previousElementSibling;
                
                if (activeSubmenu && activeSubmenu !== submenu) {
                    // Cerrar el submenú activo anterior
                    activeSubmenu.classList.remove('open');
                    activeSubmenu.previousElementSibling.classList.remove('active');
                }

                if (submenu.classList.contains('open')) {
                    // Cerrar el submenú actual
                    submenu.classList.remove('open');
                    button.classList.remove('active');
                    activeSubmenu = null;
                } else {
                    // Abrir el nuevo submenú
                    submenu.classList.add('open');
                    button.classList.add('active');
                    activeSubmenu = submenu;
                }
            }

            function toggleMenu() {
                const menuButtons = document.querySelector('.menu-buttons');
                const menuToggle = document.querySelector('.menu-toggle');
                menuButtons.classList.toggle('open');
                menuToggle.classList.toggle('open');
            }

            // Evitar que los clics dentro del menú lo cierren
            document.querySelector('.menu-buttons').addEventListener('click', (event) => {
                event.stopPropagation();
            });
        </script>
    </body>
    </html>
    ''')
    context = Context({'bienvenido': bienvenido})
    return HttpResponse(template.render(context))

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
    path('', login_view),
    path('login', login_view),
    path('logout', logout_view),
    path('menu', menu_view),
    path('seguimiento', seguimiento_view),
    path('registro', registro_view),
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
    execute_from_command_line(['manage.py', 'runserver'])
