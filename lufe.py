import tkinter as tk
from PIL import Image, ImageTk, ImageSequence
import speech_recognition as sr
import pyttsx3
import threading
import pystray
from pystray import MenuItem as item
import time
import webbrowser
import os
import subprocess
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import requests
import hashlib
import pyodbc

# === CONFIGURACION (AJUSTA ESTOS VALORES) ===
PALABRA_FINAL = "gracias"
GIF_SALUDO = "static/permanente.gif"
GIF_PERMANENTE = "static/permanente.gif"
POSICION_VENTANA = (100, 100)
TAMANO_IMAGEN = (200, 200)  # ancho x alto máximo

# SQL Server connection info -> cambia estos por los tuyos
MSSQL_DRIVER = "ODBC Driver 17 for SQL Server"   # o "ODBC Driver 18 for SQL Server"
MSSQL_SERVER = "FER\FERNANDA"       # o "localhost\\SQLEXPRESS" u "IP\\INSTANCE"
MSSQL_DATABASE = "LF01"
MSSQL_UID = "sa"          # si usas autenticación SQL Server
MSSQL_PWD = "Luisa3022679731"   # si usas autenticación SQL Server
USE_TRUSTED_CONNECTION = False   # True si quieres usar Windows Authentication

# === GOOGLE SEARCH (opcional) ===
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")


# === Helpers DB ===
def get_connection():
    """Devuelve una conexión pyodbc a SQL Server."""
    if USE_TRUSTED_CONNECTION:
        conn_str = (
            f"DRIVER={{{MSSQL_DRIVER}}};"
            f"SERVER={MSSQL_SERVER};"
            f"DATABASE={MSSQL_DATABASE};"
            "Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{{MSSQL_DRIVER}}};"
            f"SERVER={MSSQL_SERVER};"
            f"DATABASE={MSSQL_DATABASE};"
            f"UID={MSSQL_UID};PWD={MSSQL_PWD};"
        )
    return pyodbc.connect(conn_str, autocommit=False)

def hash_password(password: str) -> str:
    """Hash SHA256 en hex string (compatible entre Python y SQL si guardas como NVARCHAR(64))."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def check_user(username, password):
    """Devuelve user_id si coincide, o None."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    db_pass = row[1]
    # db_pass puede venir como bytes (si alguien usó HASHBYTES) o como texto hex.
    if isinstance(db_pass, (bytes, bytearray)):
        # convertir hash binario a hex para comparar
        db_hex = db_pass.hex()
    else:
        db_hex = str(db_pass)
    if db_hex.lower() == hash_password(password).lower():
        return row[0]
    return None

def create_user(username, password):
    """Crea usuario con contraseña hasheada en formato hex (NVARCHAR)."""
    con = get_connection()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, hash_password(password)))
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        # si existe, IntegrityError o similar
        return False
    con.close()
    return True

def insert_chat(user_id, sender, mensaje):
    """Inserta un registro en chats."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("INSERT INTO chats (user_id, sender, mensaje) VALUES (?, ?, ?)",
                (user_id, sender, mensaje))
    con.commit()
    con.close()

def fetch_chats_for_user(user_id):
    """Devuelve lista de dicts con los chats del usuario ordenados por timestamp asc."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT sender, mensaje, timestamp FROM chats WHERE user_id = ? ORDER BY timestamp", (user_id,))
    rows = cur.fetchall()
    con.close()
    result = []
    for r in rows:
        result.append({"tipo": "usuario" if r[0] == "usuario" else "alira", "mensaje": r[1], "timestamp": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2])})
    return result

# === VOZ / UI / LÓGICA (tu código original, con pequeños ajustes) ===
voz = pyttsx3.init()
voces = voz.getProperty('voices')
for v in voces:
    if "Sabina" in v.name or "es" in str(v.languages).lower():
        voz.setProperty('voice', v.id)
        break
voz.setProperty('rate', 170)
voz.setProperty('volume', 1.0)

recognizer = sr.Recognizer()
mic = sr.Microphone()
icono = None
usar_saludo = True
frame_actual = 0

ventana, canvas = None, None
frames_saludo, duraciones_saludo = [], []
frames_permanente, duraciones_permanente = [], []

# Guardamos el id del usuario que activó la ventana (se setea en /activar)
current_user_id_lock = threading.Lock()
current_user_id = None

# Mantener histórico en memoria (opcional, seguimos usando DB como fuente de verdad)
chat_historial = []

voz_lock = threading.Lock()
def hablar(texto):
    print(f"🗣️ Alira: {texto}")
    # Guardar en memoria
    chat_historial.append({"tipo": "alira", "mensaje": texto})
    # Guardar en DB (si hay usuario activo)
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

def ocultar_ventana():
    ventana.withdraw()
    if icono:
        icono.visible = True

def restaurar_ventana(icon, item):
    ventana.deiconify()
    icon.visible = False

def salir(icon, item):
    ventana.quit()
    icono.stop()

def escuchar():
    # ajusta ruido
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
    while True:
        with mic as source:
            print("🎧 Escuchando...")
            audio = recognizer.listen(source)
        try:
            texto = recognizer.recognize_google(audio, language="es-ES").lower()
            print(f"👂 Tú dijiste: {texto}")
            chat_historial.append({"tipo": "usuario", "mensaje": texto})
            # Guardar en DB
            with current_user_id_lock:
                uid = current_user_id
            if uid:
                try:
                    insert_chat(uid, "usuario", texto)
                except Exception as e:
                    print("Error guardando chat (usuario):", e)
            # ==== comandos ====
            if "estoy cansado" in texto:
                hablar("Puedo ayudarte a organizar tu jornada con más calma.")
            elif "youtube" in texto:
                hablar("Abriendo YouTube")
                webbrowser.open("https://www.youtube.com")
            elif "google" in texto and "busca" not in texto and "búscame" not in texto:
                hablar("Abriendo Google")
                webbrowser.open("https://www.google.com")
            elif "netflix" in texto:
                hablar("Abriendo Netflix")
                webbrowser.open("https://www.netflix.com")
            elif "explorador" in texto or "archivos" in texto:
                hablar("Abriendo explorador de archivos")
                os.startfile("explorer")
            elif "configuración" in texto or "configuracion" in texto:
                hablar("Abriendo configuración")
                subprocess.run("start ms-settings:", shell=True)
            elif "busca en google" in texto or "búscame en google" in texto:
                consulta = texto.replace("busca en google", "").replace("búscame en google", "").strip()
                if consulta:
                    consulta_limpia = limpiar_consulta(consulta)
                    hablar(f"Buscando en Google: {consulta_limpia}")
                    voz_texto, chat_texto = buscar_google(consulta_limpia)
                    chat_historial.append({"tipo": "alira", "mensaje": chat_texto})
                    # guardar respuestas tipo 'alira' en DB
                    if uid:
                        try:
                            insert_chat(uid, "alira", chat_texto)
                        except Exception as e:
                            print("Error guardando chat (alira google):", e)
                    hablar(voz_texto)
                else:
                    hablar("¿Qué quieres que busque en Google?")
            elif PALABRA_FINAL in texto:
                hablar("Gracias a ti")
        except Exception:
            continue

def crear_icono_bandeja():
    icono_img = Image.open(GIF_PERMANENTE).resize((32, 32))
    global icono
    icono = pystray.Icon("Alira", icono_img, menu=pystray.Menu(
        item("Restaurar", restaurar_ventana),
        item("Salir", salir)
    ))
    icono.run()

def cargar_gif_con_duracion(path):
    img = Image.open(path)
    frames, duraciones = [], []
    for frame in ImageSequence.Iterator(img):
        frame = frame.convert("RGBA")
        w, h = frame.size
        max_w, max_h = TAMANO_IMAGEN
        ratio = min(max_w / w, max_h / h)
        frame = frame.resize((int(w*ratio), int(h*ratio)), Image.Resampling.LANCZOS)
        frames.append(ImageTk.PhotoImage(frame))
        duraciones.append(frame.info.get('duration', 80))
    return frames, duraciones

def animar():
    global frame_actual, usar_saludo
    frames = frames_saludo if usar_saludo else frames_permanente
    duraciones = duraciones_saludo if usar_saludo else duraciones_permanente
    canvas.delete("all")
    canvas.create_image(TAMANO_IMAGEN[0]//2, TAMANO_IMAGEN[1]//2,
                        anchor=tk.CENTER, image=frames[frame_actual])
    delay = duraciones[frame_actual]
    frame_actual = (frame_actual + 1) % len(frames)
    ventana.after(delay, animar)

def iniciar_movimiento(e):
    ventana.x, ventana.y = e.x, e.y

def mover_ventana(e):
    x = ventana.winfo_pointerx() - ventana.x
    y = ventana.winfo_pointery() - ventana.y
    ventana.geometry(f"+{x}+{y}")

def saludo():
    global usar_saludo
    hablar("Hola soy Sara, estoy lista para ayudarte")
    time.sleep(4)
    usar_saludo = False

def crear_ventana():
    global ventana, canvas, frames_saludo, duraciones_saludo, frames_permanente, duraciones_permanente
    ventana = tk.Tk()
    ventana.overrideredirect(True)
    ventana.geometry(f"{TAMANO_IMAGEN[0]}x{TAMANO_IMAGEN[1]}+{POSICION_VENTANA[0]}+{POSICION_VENTANA[1]}")
    ventana.wm_attributes("-topmost", True)
    ventana.config(bg='white')
    ventana.wm_attributes('-transparentcolor', 'white')
    canvas = tk.Canvas(ventana, width=TAMANO_IMAGEN[0], height=TAMANO_IMAGEN[1],
                       bg="white", highlightthickness=0)
    canvas.pack()
    frames_saludo, duraciones_saludo = cargar_gif_con_duracion(GIF_SALUDO)
    frames_permanente, duraciones_permanente = cargar_gif_con_duracion(GIF_PERMANENTE)
    canvas.bind("<Button-1>", iniciar_movimiento)
    canvas.bind("<B1-Motion>", mover_ventana)
    canvas.bind("<Double-Button-1>", lambda e: ocultar_ventana())
    threading.Thread(target=crear_icono_bandeja, daemon=True).start()
    threading.Thread(target=escuchar, daemon=True).start()
    threading.Thread(target=saludo, daemon=True).start()
    animar()
    ventana.mainloop()

# === FLASK WEB ===
app = Flask(__name__)
app.secret_key = "clave_secreta_segura"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]
        user_id = check_user(user, pwd)
        if user_id:
            session["user_id"] = user_id
            session["username"] = user
            return redirect(url_for("home"))
        else:
            return "❌ Usuario o contraseña incorrectos"
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]
        if not user or not pwd:
            return "❌ Todos los campos son obligatorios"
        if create_user(user, pwd):
            return redirect(url_for("login"))
        else:
            return "❌ Ese usuario ya existe"
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("lufe.html", username=session["username"])

@app.route("/activar")
def activar():
    if "user_id" not in session:
        return redirect(url_for("login"))
    # asignar current_user_id para que la instancia de escritorio guarde chats correctamente
    with current_user_id_lock:
        global current_user_id
        current_user_id = session.get("user_id")
    threading.Thread(target=crear_ventana, daemon=True).start()
    return jsonify({"status": "Alira activada"})

@app.route("/get_chat")
def get_chat():
    if "user_id" not in session:
        return jsonify({"error": "No autorizado"}), 401
    # Traer chats directamente desde SQL Server
    try:
        chats = fetch_chats_for_user(session["user_id"])
        return jsonify(chats)
    except Exception as e:
        print("Error fetch chats:", e)
        return jsonify([])

if __name__ == "__main__":
    app.run(debug=False)
