# ===================== IMPORTACIONES =====================
import tkinter as tk                              # Para crear interfaces gráficas (ventana flotante con GIF)
from PIL import Image, ImageTk, ImageSequence     # Para cargar, redimensionar y animar imágenes GIF
import speech_recognition as sr                   # Para reconocimiento de voz (captura de audio y convierte a texto)
import pyttsx3                                    # Para síntesis de voz (el asistente responde hablando)
import threading                                  # Para manejar hilos (paralelismo: escuchar, hablar, ventana, etc.)
import pystray                                    # Para icono en bandeja del sistema
from pystray import MenuItem as item              # Para ítems de menú en el icono de la bandeja
import time
import webbrowser                                 # Para abrir páginas web en el navegador
import os
import subprocess                                 # Para ejecutar comandos del sistema
from flask import Flask, render_template, jsonify, request, redirect, url_for, session   # Framework web Flask
import requests                                   # Para realizar peticiones HTTP (ej: Google API)
import hashlib                                    # Para cifrar contraseñas con SHA256
import pyodbc                                     # Para conexión con base de datos SQL Server

# ===================== CONFIGURACIÓN GENERAL =====================
PALABRA_FINAL = "gracias"             # Palabra para finalizar interacciones
PALABRA_ACTIVADORA = "iris"           # El asistente solo escucha comandos si inician con esta palabra
GIF_SALUDO = "static/permanente.gif"  # GIF de saludo (se carga al inicio)
GIF_PERMANENTE = "static/permanente.gif"  # GIF de animación permanente
POSICION_VENTANA = (100, 100)         # Posición de la ventana flotante
TAMANO_IMAGEN = (200, 200)            # Tamaño de la animación

# ===================== CONEXIÓN A BASE DE DATOS (SQL Server) =====================
MSSQL_DRIVER = "ODBC Driver 17 for SQL Server"
MSSQL_SERVER = "FER\\FERNANDA"
MSSQL_DATABASE = "LF01"
MSSQL_UID = "sa"
MSSQL_PWD = "Luisa3022679731"
USE_TRUSTED_CONNECTION = False       


# ===================== FUNCIONES AUXILIARES BASE DE DATOS =====================

def get_user_info(user_id):
    """Obtiene información del usuario desde la base de datos."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT first_name, last_name, email, phone, username FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    con.close()
    if row:
        return {
            "first_name": row[0],
            "last_name": row[1],
            "email": row[2],
            "phone": row[3],
            "username": row[4]
        }
    return None
def get_connection():
    """Crea y devuelve una conexión a SQL Server"""
    if USE_TRUSTED_CONNECTION:
        conn_str = f"DRIVER={{{MSSQL_DRIVER}}};SERVER={MSSQL_SERVER};DATABASE={MSSQL_DATABASE};Trusted_Connection=yes;"
    else:
        conn_str = f"DRIVER={{{MSSQL_DRIVER}}};SERVER={MSSQL_SERVER};DATABASE={MSSQL_DATABASE};UID={MSSQL_UID};PWD={MSSQL_PWD};"
    return pyodbc.connect(conn_str, autocommit=False)


def hash_password(password: str) -> str:
    """Devuelve un hash SHA256 de la contraseña"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def check_user(username_or_email, password):
    """
    Verifica usuario y contraseña en la BD.
    Acepta tanto username como email para el login.
    """
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT id, username, password FROM users WHERE username = ? OR email = ?", (username_or_email, username_or_email))
    user = cur.fetchone()
    con.close()
    if user:
        db_id, db_username, db_password = user
        if db_password.lower() == hash_password(password).lower():
            return db_id    # Devuelve el ID del usuario si coincide
    return None


def create_user(first_name, last_name, email, phone, username, password):
    """
    Crea un nuevo usuario con datos completos si cumple requisitos de seguridad.
    Retorna (True, None) si todo bien, o (False, mensaje_error) si hay problema.
    """
    import re
    regex = re.compile(r'^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$')
    if not regex.match(password):
        return False, "La contraseña no cumple los requisitos."

    con = get_connection()
    cur = con.cursor()
    # Verifica si el usuario o correo ya existen
    cur.execute("SELECT 1 FROM users WHERE username = ? OR email = ?", (username, email))
    if cur.fetchone():
        con.close()
        return False, "El usuario o correo ya están registrados."
    try:
        cur.execute("""
            INSERT INTO users (first_name, last_name, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, email, phone, username, hash_password(password)))
        con.commit()
    except Exception:
        con.rollback()
        con.close()
        return False, "Error al crear el usuario."
    con.close()
    return True, None


def insert_chat(user_id, sender, mensaje):
    """Guarda un mensaje en la tabla de chats"""
    con = get_connection()
    cur = con.cursor()
    cur.execute("INSERT INTO chats (user_id, sender, mensaje) VALUES (?, ?, ?)", (user_id, sender, mensaje))
    con.commit()
    con.close()


def fetch_chats_for_user(user_id):
    """Obtiene historial de chats de un usuario"""
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT sender, mensaje, timestamp FROM chats WHERE user_id = ? ORDER BY timestamp", (user_id,))
    rows = cur.fetchall()
    con.close()
    result = []
    for r in rows:
        result.append({
            "tipo": "usuario" if r[0] == "usuario" else "alira",
            "mensaje": r[1],
            "timestamp": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2])
        })
    return result


# ===================== CONFIGURACIÓN DE VOZ =====================
voz = pyttsx3.init()
voces = voz.getProperty('voices')
for v in voces:
    if "Sabina" in v.name or "es" in str(v.languages).lower():
        voz.setProperty('voice', v.id)
        break
voz.setProperty('rate', 170)   # Velocidad
voz.setProperty('volume', 1.0) # Volumen máximo
print("Voz seleccionada:", voz.getProperty('voice'))

# ===================== VARIABLES GLOBALES =====================
recognizer = sr.Recognizer()
mic = sr.Microphone()
icono = None
usar_saludo = True
frame_actual = 0
ventana, canvas = None, None
frames_saludo, duraciones_saludo = [], []
frames_permanente, duraciones_permanente = [], []
current_user_id_lock = threading.Lock()
current_user_id = None
chat_historial = []
voz_lock = threading.Lock()
escuchando = True  # Control de escucha activa

# ===================== FUNCIÓN PARA HABLAR =====================
def hablar(texto):
    """El asistente habla SIEMPRE y después guarda mensaje en historial y BD"""

    # === Primero hablar ===
    def run():
        try:
            with voz_lock:
                voz.say(texto)
                voz.runAndWait()
        except Exception as e:
            print("⚠️ Error en síntesis de voz:", e)
    threading.Thread(target=run, daemon=True).start()

    # === Después guardar en historial y BD ===
    try:
        chat_historial.append({"tipo": "alira", "mensaje": texto})
        with current_user_id_lock:
            uid = current_user_id
        if uid:
            insert_chat(uid, "alira", texto)
    except Exception as e:
        print(" Error guardando chat (alira):", e)


# ===================== FUNCIÓN DE ESCUCHA (RECONOCIMIENTO DE VOZ) =====================
def escuchar():
    """Escucha comandos de voz y ejecuta acciones"""
    global escuchando
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
    while escuchando:
        with mic as source:
            print("🎧 Escuchando...")
            audio = recognizer.listen(source)
        try:
            texto = recognizer.recognize_google(audio, language="es-ES").lower()
            if not texto.startswith(PALABRA_ACTIVADORA):
                continue
            comando = texto.replace(PALABRA_ACTIVADORA, "", 1).strip()

            # === COMANDOS DE APPS (NO se registran en chat) ===
            if "youtube" in comando:
                hablar("Abriendo YouTube")
                webbrowser.open("https://www.youtube.com")
            elif "google" in comando and "busca" not in comando:
                hablar("Abriendo Google")
                webbrowser.open("https://www.google.com")
            elif "netflix" in comando:
                hablar("Abriendo Netflix")
                webbrowser.open("https://www.netflix.com")
            elif "explorador" in comando or "archivos" in comando:
                hablar("Abriendo explorador de archivos")
                os.startfile("explorer")
            elif "configuración" in comando or "configuracion" in comando:
                hablar("Abriendo configuración")
                subprocess.run("start ms-settings:", shell=True)
            elif "word" in comando:
                hablar("Abriendo Word")
                try:
                    os.startfile("winword")
                except Exception:
                    hablar("Word no está instalado. Abriendo Word online.")
                    webbrowser.open("https://office.live.com/start/Word.aspx")
            elif "excel" in comando:
                hablar("Abriendo Excel")
                try:
                    os.startfile("excel")
                except Exception:
                    hablar("Excel no está instalado. Abriendo Excel online.")
                    webbrowser.open("https://office.live.com/start/Excel.aspx")
            elif "powerpoint" in comando:
                hablar("Abriendo PowerPoint")
                try:
                    os.startfile("powerpnt")
                except Exception:
                    hablar("PowerPoint no está instalado. Abriendo PowerPoint online.")
                    webbrowser.open("https://office.live.com/start/PowerPoint.aspx")
            elif "visual studio" in comando or "visual studio code" in comando or "vscode" in comando:
                hablar("Abriendo Visual Studio Code")
                try:
                    os.startfile("code")
                except Exception:
                    hablar("No se encontró Visual Studio Code. Abriendo VS Code web.")
                    webbrowser.open("https://vscode.dev")
            elif "zoom" in comando:
                hablar("Abriendo Zoom")
                try:
                    os.startfile("zoom")
                except Exception:
                    hablar("Zoom no está instalado. Abriendo Zoom web.")
                    webbrowser.open("https://zoom.us/signin")
            elif "chat gpt" in comando:
                hablar("Abriendo ChatGPT")
                webbrowser.open("https://chat.openai.com")

            elif "busca en google" in comando or "búscame en google" in comando:
                consulta = comando.replace("busca en google", "").replace("búscame en google", "").strip()
                if consulta:
                    hablar(f"Abriendo Google para: {consulta}")
                    url_busqueda = f"https://www.google.com/search?q={consulta.replace(' ', '+')}"
                    webbrowser.open(url_busqueda)
                else:
                    hablar("¿Qué quieres que busque en Google?")

            elif PALABRA_FINAL in comando:
                hablar("Gracias a ti")

            else:
                # === Comandos que SÍ se registran en chat ===
                chat_historial.append({"tipo": "usuario", "mensaje": comando})
                with current_user_id_lock:
                    uid = current_user_id
                if uid:
                    try:
                        insert_chat(uid, "usuario", comando)
                    except Exception as e:
                        print("Error guardando chat (usuario):", e)

        except Exception as e:
            print("Error en reconocimiento de voz:", e)
            continue

# ===================== INTERFAZ GRÁFICA (TK + BANDEJA DEL SISTEMA) =====================
def crear_ventana():
    """Crea la ventana flotante animada con GIF y el icono de bandeja"""
    global ventana, canvas, frames_saludo, duraciones_saludo, frames_permanente, duraciones_permanente, icono, escuchando
    ventana = tk.Tk()
    ventana.overrideredirect(True)  # Sin bordes
    ventana.geometry(f"{TAMANO_IMAGEN[0]}x{TAMANO_IMAGEN[1]}+{POSICION_VENTANA[0]}+{POSICION_VENTANA[1]}")
    ventana.wm_attributes("-topmost", True)
    ventana.config(bg='white')
    ventana.wm_attributes('-transparentcolor', 'white')
    canvas = tk.Canvas(ventana, width=TAMANO_IMAGEN[0], height=TAMANO_IMAGEN[1], bg="white", highlightthickness=0)
    canvas.pack()

    # Cargar GIFs (saludo y permanente)
    def cargar_gif(path):
        img = Image.open(path)
        frames, duraciones = [], []
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGBA")
            w, h = frame.size
            ratio = min(TAMANO_IMAGEN[0]/w, TAMANO_IMAGEN[1]/h)
            frame = frame.resize((int(w*ratio), int(h*ratio)), Image.Resampling.LANCZOS)
            frames.append(ImageTk.PhotoImage(frame))
            duraciones.append(frame.info.get('duration', 80))
        return frames, duraciones

    frames_saludo, duraciones_saludo = cargar_gif(GIF_SALUDO)
    frames_permanente, duraciones_permanente = cargar_gif(GIF_PERMANENTE)

    # Animar GIF en bucle
    def animar():
        global frame_actual
        frames = frames_saludo if usar_saludo else frames_permanente
        duraciones = duraciones_saludo if usar_saludo else duraciones_permanente
        canvas.delete("all")
        canvas.create_image(TAMANO_IMAGEN[0]//2, TAMANO_IMAGEN[1]//2, anchor=tk.CENTER, image=frames[frame_actual])
        delay = duraciones[frame_actual]
        frame_actual = (frame_actual + 1) % len(frames)
        ventana.after(delay, animar)

    # Funciones bandeja
    def ocultar_ventana():
        ventana.withdraw()
        if icono:
            icono.visible = True

    def restaurar_ventana(icon, item):
        ventana.deiconify()
        icon.visible = False

    def salir_app(icon, item):
        global escuchando
        escuchando = False
        ventana.destroy()
        icon.stop()

    # Crear icono en bandeja
    icono_img = Image.open(GIF_PERMANENTE).resize((32,32))
    icono = pystray.Icon("Lucy", icono_img, menu=pystray.Menu(
        item("Restaurar", restaurar_ventana),
        item("Salir", salir_app)
    ))
    threading.Thread(target=icono.run, daemon=True).start()

    # Eventos de la ventana
    canvas.bind("<Button-1>", lambda e: setattr(ventana, 'x', e.x) or setattr(ventana, 'y', e.y))
    canvas.bind("<B1-Motion>", lambda e: ventana.geometry(f"+{ventana.winfo_pointerx()-ventana.x}+{ventana.winfo_pointery()-ventana.y}"))
    canvas.bind("<Double-Button-1>", lambda e: ocultar_ventana())

    # Hilos de escucha y saludo inicial
    threading.Thread(target=escuchar, daemon=True).start()
    threading.Thread(target=lambda: hablar("Hola soy Iris, estoy lista para ayudarte"), daemon=True).start()
    animar()
    ventana.mainloop()

# ===================== FLASK WEB APP =====================
app = Flask(__name__)
app.secret_key = "clave_secreta_segura"

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username_or_email = request.form['username']
        password = request.form['password']

        # ===  VALIDAR reCAPTCHA ===
        recaptcha_response = request.form.get('g-recaptcha-response')
        secret_key = "6LcWmeorAAAAANAU3YgXlw8X_9fveTarCRZIzoEv"  # 🔑 Reemplázala con tu clave secreta (de Google)
        verify_url = "https://www.google.com/recaptcha/api/siteverify"
        data = {"secret": secret_key, "response": recaptcha_response}

        import requests  # por si no lo tienes arriba
        response = requests.post(verify_url, data=data)
        result = response.json()

        if not result.get("success"):
            error = "Por favor, verifica el reCAPTCHA antes de continuar."
            return render_template('login.html', error=error)

        # === Si el CAPTCHA fue validado, sigue con el login normal ===
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT id, username, password FROM users WHERE username = ? OR email = ?", (username_or_email, username_or_email))
        user = cur.fetchone()
        con.close()

        if not user:
            error = "El usuario es incorrecto."
            return render_template('login.html', error=error)
        else:
            db_id, db_username, db_password = user
            if hash_password(password) != db_password:
                error = "La contraseña es incorrecta."
                return render_template('login.html', error=error)
            session['user_id'] = db_id  # <-- Guarda el id numérico
            return redirect(url_for('home'))

    return render_template('login.html', error=error)



@app.route('/register', methods=['POST'])
def register():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    phone = request.form['phone']
    username = request.form['username']
    password = request.form['password']
    password_repeat = request.form['password_repeat']

    import re
    regex = r'^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$'
    if password != password_repeat:
        error = "Las contraseñas no coinciden."
        return render_template('login.html', error=error, suggested=username)
    if not re.match(regex, password):
        error = "La contraseña no cumple los requisitos."
        return render_template('login.html', error=error, suggested=username)

    # Verifica si el correo ya está registrado
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    if cur.fetchone():
        con.close()
        error = "El correo ya está registrado."
        return render_template('login.html', error=error, suggested=username)

    # Verifica si el usuario ya está registrado
    cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    if cur.fetchone():
        con.close()
        error = "El usuario ya está registrado."
        return render_template('login.html', error=error, suggested=username)

    # Si todo está bien, crea el usuario
    try:
        cur.execute("""
            INSERT INTO users (first_name, last_name, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, email, phone, username, hash_password(password)))
        con.commit()
    except Exception:
        con.rollback()
        con.close()
        error = "Error al crear el usuario."
        return render_template('login.html', error=error, suggested=username)
    con.close()
    return redirect(url_for('login', suggested=username))

    user_info = get_user_info(session["user_id"]) if "user_id" in session else None

@app.route("/logout")
def logout():
    """Cerrar sesión"""
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def landing():
    """Página inicial (landing page)"""
    return render_template("landing.html") 

@app.route("/home")
def home():
    """Pantalla principal (después del login)"""
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_info = get_user_info(session["user_id"])
    return render_template("lufe.html", user=user_info)


@app.route("/activar")
def activar():
    """Activa la ventana de Iris"""
    if "user_id" not in session:
        return redirect(url_for("login"))
    with current_user_id_lock:
        global current_user_id
        current_user_id = session.get("user_id")
    threading.Thread(target=crear_ventana, daemon=True).start()
    return jsonify({"status": "Iris activada"})

@app.route("/get_chat")
def get_chat():
    """Devuelve historial de chat del usuario logueado"""
    if "user_id" not in session:
        return jsonify({"error":"No autorizado"}), 401
    try:
        chats = fetch_chats_for_user(session["user_id"])
        return jsonify(chats)
    except Exception as e:
        print("Error fetch chats:", e)
        return jsonify([])

from flask import jsonify
import secrets
import smtplib
from email.mime.text import MIMEText

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT username FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    if not user:
        con.close()
        return jsonify({'success': False, 'message': 'El correo no está registrado.'})
    # Generar token seguro
    import secrets
    token = secrets.token_urlsafe(32)
    # Guarda el token en la tabla password_resets
    cur.execute("INSERT INTO password_resets (email, token) VALUES (?, ?)", (email, token))
    con.commit()
    con.close()
    # Enviar correo con el enlace de restablecimiento
    reset_link = f"http://localhost:5000/reset_password/{token}"
    send_reset_email(email, reset_link)
    return jsonify({'success': True, 'message': 'Se ha enviado un correo para restablecer tu contraseña.'})

def send_reset_email(email, link):
    # Configura tu servidor SMTP aquí
    remitente = "luciacar1303@gmail.com"
    password = "qdfe gqix rvqk yday"
    msg = MIMEText(f"Para restablecer tu contraseña haz clic en el siguiente enlace:\n{link}")
    msg['Subject'] = "Restablece tu contraseña"
    msg['From'] = remitente
    msg['To'] = email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(remitente, password)
        server.sendmail(remitente, [email], msg.as_string())

@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    exists = cur.fetchone() is not None
    con.close()
    return jsonify({'exists': exists})

@app.route('/check_username', methods=['POST'])
def check_username():
    username = request.json.get('username')
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    exists = cur.fetchone() is not None
    # Sugerencias si existe
    suggestions = []
    if exists:
        base = username
        for i in range(1, 6):
            cur.execute("SELECT 1 FROM users WHERE username = ?", (f"{base}{i}",))
            if not cur.fetchone():
                suggestions.append(f"{base}{i}")
    con.close()
    return jsonify({'exists': exists, 'suggestions': suggestions})

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT email FROM password_resets WHERE token = ?", (token,))
    row = cur.fetchone()
    if not row:
        con.close()
        return render_template('reset_password.html', error="Token inválido o expirado.", token=token)
    email = row[0]
    if request.method == 'POST':
        new_password = request.form['new_password']
        import re
        regex = r'^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$'
        if not re.match(regex, new_password):
            con.close()
            return render_template('reset_password.html', error="La contraseña no cumple los requisitos.", token=token)
        # Cambia la contraseña del usuario
        cur.execute("UPDATE users SET password = ? WHERE email = ?", (hash_password(new_password), email))
        # Elimina el token usado
        cur.execute("DELETE FROM password_resets WHERE token = ?", (token,))
        con.commit()
        con.close()
        return redirect(url_for('login', mensaje="Contraseña restablecida correctamente."))
    con.close()
    return render_template('reset_password.html', token=token)

# ===================== EJECUCIÓN PRINCIPAL =====================
if __name__ == "__main__":
    app.run(debug=True)

