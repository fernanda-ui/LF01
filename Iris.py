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

# ===================== CONFIG GOOGLE API (opcional) =====================
GOOGLE_API_KEY = "AIzaSyDsScOCMHpFi76-w100NMXzpe6taoQrQWc"
GOOGLE_CX = "6643044f0efe44c19"

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
    cur.execute("SELECT id, password FROM users WHERE username = ? OR email = ?", (username_or_email, username_or_email))
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    db_pass = str(row[1])
    if db_pass.lower() == hash_password(password).lower():
        return row[0]    # Devuelve el ID del usuario si coincide
    return None


def create_user(first_name, last_name, email, phone, username, password):
    """
    Crea un nuevo usuario con datos completos si cumple requisitos de seguridad
    """
    import re
    # Validación robusta de contraseña
    regex = re.compile(r'^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$')
    if not regex.match(password):
        return False

    con = get_connection()
    cur = con.cursor()
    try:
        cur.execute("""
            INSERT INTO users (first_name, last_name, email, phone, username, password)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, email, phone, username, hash_password(password)))
        con.commit()
    except Exception:
        con.rollback()
        con.close()
        return False
    con.close()
    return True


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

# ===================== FUNCIONES AUXILIARES DE TEXTO Y GOOGLE =====================
def limpiar_consulta(consulta):
    """Limpia un comando de voz para mejorar búsqueda en Google"""
    consulta = consulta.lower()
    reemplazos = {
        "qué es": "definición de",
        "que es": "definición de",
        "cuál es": "",
        "cual es": "",
        "dime": "",
        "explícame": "",
        "busca en google": "",
        "búscame en google": "",
        "busca": "",
        "búscame": ""
    }
    for k, v in reemplazos.items():
        consulta = consulta.replace(k, v)
    return consulta.strip()

def buscar_google(query):
    """Hace una búsqueda en Google usando Custom Search API"""
    query = f"{query} -site:wikipedia.org"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_API_KEY, "cx": GOOGLE_CX, "q": query, "num": 3, "hl": "es"}
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if "items" not in data:
            return "No encontré resultados en Google.", "No encontré resultados en Google."
        voz_respuesta, chat_respuesta = "", ""
        for item_google in data["items"]:
            titulo = item_google.get("title", "")
            snippet = item_google.get("snippet", "")
            link = item_google.get("link", "")
            voz_respuesta += f"{titulo}. {snippet} "
            chat_respuesta += f"{titulo}<br>{snippet}<br><a href='{link}' target='_blank'>{link}</a><br><br>"
        return voz_respuesta.strip(), chat_respuesta.strip()
    except Exception as e:
        return f"Error buscando en Google: {e}", f"Error buscando en Google: {e}"

# ===================== CONFIGURACIÓN DE VOZ =====================
voz = pyttsx3.init()
voces = voz.getProperty('voices')
for v in voces:
    if "Sabina" in v.name or "es" in str(v.languages).lower():
        voz.setProperty('voice', v.id)
        break
voz.setProperty('rate', 170)   # Velocidad
voz.setProperty('volume', 1.0) # Volumen máximo

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
    """El asistente habla y guarda mensaje en historial y BD"""
    chat_historial.append({"tipo": "alira", "mensaje": texto})
    with current_user_id_lock:
        uid = current_user_id
    if uid:
        try:
            insert_chat(uid, "alira", texto)
        except Exception as e:
            print("Error guardando chat (alira):", e)
    def run():
        with voz_lock:
            voz.say(texto)
            voz.runAndWait()
    threading.Thread(target=run, daemon=True).start()

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

            # Guardar mensaje en historial y BD
            chat_historial.append({"tipo": "usuario", "mensaje": comando})
            with current_user_id_lock:
                uid = current_user_id
            if uid:
                try:
                    insert_chat(uid, "usuario", comando)
                except Exception as e:
                    print("Error guardando chat (usuario):", e)

            # === Comandos posibles ===
            if "estoy cansado" in comando:
                hablar("Puedo ayudarte a organizar tu jornada con más calma.")
            elif "youtube" in comando:
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
            elif "busca en google" in comando or "búscame en google" in comando:
                consulta = comando.replace("busca en google", "").replace("búscame en google", "").strip()
                if consulta:
                    consulta_limpia = limpiar_consulta(consulta)
                    hablar(f"Buscando en Google: {consulta_limpia}")
                    voz_texto, chat_texto = buscar_google(consulta_limpia)
                    chat_historial.append({"tipo": "alira", "mensaje": chat_texto})
                    if uid:
                        try:
                            insert_chat(uid, "alira", chat_texto)
                        except Exception as e:
                            print("Error guardando chat (alira google):", e)
                    hablar(voz_texto)
                else:
                    hablar("¿Qué quieres que busque en Google?")
            elif PALABRA_FINAL in comando:
                hablar("Gracias a ti")
        except Exception:
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

@app.route("/login", methods=["GET","POST"])
def login():
    """Ruta de login"""
    error = None
    if request.method == "POST":
        user_input = request.form["username"]
        pwd = request.form["password"]
        user_id = check_user(user_input, pwd)
        if user_id:
            session["user_id"] = user_id
            session["username"] = user_input

            # ✅ Obtener info completa del usuario
            user_info = get_user_info(user_id)

            return render_template("lufe.html", user=user_info)
        else:
            error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Ruta de registro"""
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone_local = request.form["phone"]
        phone = "+57" + phone_local  # Se guarda con el prefijo
        user = request.form["username"]
        pwd = request.form["password"]

        # Validaciones básicas
        if not all([first_name, last_name, email, phone, user, pwd]):
            return "Todos los campos son obligatorios"

        # Llamada a la función que crea usuario en BD
        if create_user(first_name, last_name, email, phone, user, pwd):
            return redirect(url_for("login"))

        return "Usuario inválido o ya existe (mínimo 6 chars, letras+nums)"
    return render_template("register.html")

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

# ===================== EJECUCIÓN PRINCIPAL =====================
if __name__ == "__main__":
    app.run(debug=False)
