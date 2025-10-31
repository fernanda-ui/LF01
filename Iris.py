# ===================== IMPORTACIONES =====================
import tkinter as tk
from tkinter import Toplevel                             # Para crear interfaces gráficas (ventana flotante con GIF)
from PIL import Image, ImageTk, ImageSequence     # Para cargar, redimensionar y animar imágenes GIF
import speech_recognition as sr                   # Para reconocimiento de voz
import threading                                  # Para manejar hilos
import pystray                              # Para icono en bandeja del sistema
from pystray import MenuItem as item
import time
import webbrowser
import os
import subprocess
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import requests
import hashlib
import pyodbc
from gtts import gTTS
import pygame
import re
import tempfile
import google.generativeai as genai
import secrets
import smtplib
from email.mime.text import MIMEText
import ctypes

# ===================== CONFIGURACIÓN GENERAL =====================
PALABRA_FINAL = "gracias"
PALABRA_ACTIVADORA = "iris"
GIF_SALUDO = "static/permanente.gif"
GIF_PERMANENTE = "static/permanente.gif"
POSICION_VENTANA = (100, 100)
TAMANO_IMAGEN = (200, 200)

# ===================== CONFIGURACIÓN API Gemini =====================
genai.configure(api_key="AIzaSyDDc_si0A-u30KM7CkZaGKHYEEfwnkPriU")  # <-- Reemplaza aquí con tu API key

# ===================== INICIALIZAR REPRODUCTOR (gTTS + pygame) =====================
# Inicializa pygame mixer; si falla por headless, revisa entorno.
try:
    pygame.mixer.init()
except Exception as e:
    print("pygame.mixer.init() error:", e)

audio_actual = None
detener_voz_flag = False

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

# ===================== UTILIDADES TTS (gTTS + pygame) =====================
def limpiar_texto_para_voz(texto: str) -> str:
    """Elimina símbolos innecesarios para la voz."""
    if not texto:
        return ""
    return re.sub(r'[^A-Za-zÁÉÍÓÚáéíóúÑñ0-9,.!?: ]+', '', texto)

def dividir_en_frases(texto: str, max_len: int = 150):
    """Divide en fragmentos amigables para gTTS"""
    texto_limpio = limpiar_texto_para_voz(texto)
    frases = []
    inicio = 0
    while inicio < len(texto_limpio):
        corte = None
        delimitadores = ['.', '!', '?', ',', ':']
        for signo in delimitadores:
            idx = texto_limpio.find(signo, inicio)
            if idx != -1 and (corte is None or idx < corte):
                corte = idx
        if corte is None or corte - inicio > max_len:
            palabras = texto_limpio[inicio:].split()
            frag = ''
            for palabra in palabras:
                if len(frag) + len(palabra) + 1 > max_len:
                    break
                frag += (palabra + ' ')
            frag = frag.strip()
            if frag:
                frases.append(frag)
            inicio += len(frag)
            if not frag:
                break
        else:
            frag = texto_limpio[inicio:corte+1].strip()
            if frag:
                frases.append(frag)
            inicio = corte + 1
    return frases

def detener_voz():
    """Detiene la voz de Iris inmediatamente."""
    global detener_voz_flag, audio_actual
    detener_voz_flag = True
    try:
        if pygame.mixer.get_init():
            pygame.mixer.stop()
        if audio_actual:
            audio_actual.stop()
            audio_actual = None
    except Exception as e:
        print("Error al detener voz:", e)


def hablar_por_frases(texto: str):
    """Convierte texto a voz por fragmentos y reproduce (gTTS + pygame)."""
    global audio_actual, detener_voz_flag

    frases = dividir_en_frases(texto)
    if not frases:
        return

    detener_voz_flag = False

    for frag in frases:
        if detener_voz_flag:
            break
        frag = frag.strip()
        if not frag:
            continue

        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts = gTTS(text=frag, lang='es')
            tts.save(tmp.name)
            tmp.close()

            if not pygame.mixer.get_init():
                pygame.mixer.init()

            audio_actual = pygame.mixer.Sound(tmp.name)
            audio_actual.play()

            while pygame.mixer.get_busy():
                if detener_voz_flag:
                    pygame.mixer.stop()
                    break
                time.sleep(0.05)

        except Exception as e:
            print("Error reproduciendo audio:", e)

        finally:
            try:
                os.remove(tmp.name)
            except Exception:
                pass


# ===================== INTEGRACIÓN CON GEMINI =====================
def obtener_respuesta_ia(prompt: str) -> str:
    """Usa Gemini para generar la respuesta en texto."""
    try:
        modelo = genai.GenerativeModel("gemini-2.0-flash")
        respuesta = modelo.generate_content(prompt)
        # respuesta.text es la propiedad de texto devuelta
        return respuesta.text if hasattr(respuesta, "text") else str(respuesta)
    except Exception as e:
        print("Error al conectar con Gemini:", e)
        return "⚠️ No pude conectar con la IA. Revisa la API key o tu conexión."

# ===================== VARIABLES GLOBALES Y CONFIG. VOZ =====================
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
escuchando = True
# ===================== VARIABLES DE CONTROL DE VOZ =====================
detener_voz_flag = False   # Bandera para cortar voz al instante
audio_actual = None        # Último audio en reproducción
hablando = False           # Indica si Iris está reproduciendo voz
animando = False         # Indica si la burbuja está animando texto


# ===================== FUNCIÓN PARA HABLAR Y GUARDAR HISTORIAL (CENTRAL) =====================
def hablar_y_guardar(texto: str):
    """Habla por voz (thread) y guarda el mensaje en BD y en historial local."""
    # Lanzar hilo de TTS
    threading.Thread(target=hablar_por_frases, args=(texto,), daemon=True).start()

    # Guardar en historial local y BD si hay user actual
    chat_historial.append({"tipo": "alira", "mensaje": texto})
    with current_user_id_lock:
        uid = current_user_id
    if uid:
        try:
            insert_chat(uid, "alira", texto)
        except Exception as e:
            print("Error guardando chat (alira):", e)

# ===================== FUNCIÓN DE ESCUCHA (RECONOCIMIENTO DE VOZ) =====================
def escuchar_loop():
    """Loop continuo de escucha que procesa comandos de voz y envía a IA cuando aplica."""
    global escuchando
    r = recognizer
    with mic as source:
        r.adjust_for_ambient_noise(source)
    while escuchando:
        with mic as source:
            try:
                print("🎧 Escuchando...")
                audio = r.listen(source, timeout=5, phrase_time_limit=7)
            except Exception:
                continue
        try:
            texto = r.recognize_google(audio, language="es-ES").lower()
            print("Reconocido:", texto)
            if not texto.startswith(PALABRA_ACTIVADORA):
                continue
            comando = texto.replace(PALABRA_ACTIVADORA, "", 1).strip()

            # === COMANDOS DE APPS (NO se registran en chat) ===
            if "youtube" in comando:
                hablar_y_guardar("Abriendo YouTube")
                webbrowser.open("https://www.youtube.com")
            elif "google" in comando and "busca" not in comando:
                hablar_y_guardar("Abriendo Google")
                webbrowser.open("https://www.google.com")
            elif "netflix" in comando:
                hablar_y_guardar("Abriendo Netflix")
                webbrowser.open("https://www.netflix.com")
            elif "explorador" in comando or "archivos" in comando:
                hablar_y_guardar("Abriendo explorador de archivos")
                os.startfile("explorer")
            elif "configuración" in comando or "configuracion" in comando:
                hablar_y_guardar("Abriendo configuración")
                subprocess.run("start ms-settings:", shell=True)
            elif "word" in comando:
                hablar_y_guardar("Abriendo Word")
                try:
                    os.startfile("winword")
                except Exception:
                    hablar_y_guardar("Word no está instalado. Abriendo Word online.")
                    webbrowser.open("https://office.live.com/start/Word.aspx")
            elif "excel" in comando:
                hablar_y_guardar("Abriendo Excel")
                try:
                    os.startfile("excel")
                except Exception:
                    hablar_y_guardar("Excel no está instalado. Abriendo Excel online.")
                    webbrowser.open("https://office.live.com/start/Excel.aspx")
            elif "powerpoint" in comando:
                hablar_y_guardar("Abriendo PowerPoint")
                try:
                    os.startfile("powerpnt")
                except Exception:
                    hablar_y_guardar("PowerPoint no está instalado. Abriendo PowerPoint online.")
                    webbrowser.open("https://office.live.com/start/PowerPoint.aspx")
            elif "visual studio" in comando or "visual studio code" in comando or "vscode" in comando:
                hablar_y_guardar("Abriendo Visual Studio Code")
                try:
                    os.startfile("code")
                except Exception:
                    hablar_y_guardar("No se encontró Visual Studio Code. Abriendo VS Code web.")
                    webbrowser.open("https://vscode.dev")
            elif "zoom" in comando:
                hablar_y_guardar("Abriendo Zoom")
                try:
                    os.startfile("zoom")
                except Exception:
                    hablar_y_guardar("Zoom no está instalado. Abriendo Zoom web.")
                    webbrowser.open("https://zoom.us/signin")
            elif "chat gpt" in comando:
                hablar_y_guardar("Abriendo ChatGPT")
                webbrowser.open("https://chat.openai.com")
            elif "busca en google" in comando or "búscame en google" in comando or "buscame en google" in comando:
                consulta = comando
                consulta = consulta.replace("busca en google", "").replace("búscame en google", "").replace("buscame en google", "").strip()
                if consulta:
                    hablar_y_guardar(f"Buscando en google: {consulta}")
                    url_busqueda = f"https://www.google.com/search?q={consulta.replace(' ', '+')}"
                    webbrowser.open(url_busqueda)
                else:
                    hablar_y_guardar("¿Qué quieres que busque en Google?")
            elif PALABRA_FINAL in comando:
                hablar_y_guardar("Gracias a ti")
            else:
                # === Comandos que SÍ se registran en chat ===
                with current_user_id_lock:
                    uid = current_user_id
                # Guardar mensaje del usuario en BD
                if uid:
                    try:
                        insert_chat(uid, "usuario", comando)
                    except Exception as e:
                        print("Error guardando chat (usuario):", e)

                # Preguntar a la IA
                respuesta = obtener_respuesta_ia(comando)
                hablar_y_guardar_con_bubble_threadsafe(respuesta)



        except Exception as e:
            print("Error en reconocimiento de voz:", e)
            continue

# ===================== INTERFAZ GRÁFICA (TK + BANDEJA DEL SISTEMA) =====================
# ================== VENTANA PRINCIPAL (GIF) ==================
def crear_ventana():
    """Crea la ventana flotante tipo chat para mostrar y escribir mensajes"""
    global ventana, canvas, frames_saludo, duraciones_saludo, frames_permanente, duraciones_permanente
    global bubble_window, bubble_text, bubble_entry, escuchar_thread, icono

    # ----------------- VENTANA PRINCIPAL -----------------
    if 'ventana' in globals() and ventana and ventana.winfo_exists():
        ventana.deiconify()
        ventana.lift()
        return

    ventana = tk.Tk()
    ventana.overrideredirect(True)
    ventana.geometry(f"{TAMANO_IMAGEN[0]}x{TAMANO_IMAGEN[1]}+{POSICION_VENTANA[0]}+{POSICION_VENTANA[1]}")
    ventana.wm_attributes("-topmost", True)
    ventana.config(bg='white')
    ventana.wm_attributes('-transparentcolor', 'white')

    canvas = tk.Canvas(ventana, width=TAMANO_IMAGEN[0], height=TAMANO_IMAGEN[1],
                       bg="white", highlightthickness=0)
    canvas.pack()

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

    # Cargar GIFs
    try:
        frames_saludo, duraciones_saludo = cargar_gif(GIF_SALUDO)
        frames_permanente, duraciones_permanente = cargar_gif(GIF_PERMANENTE)
    except Exception as e:
        print("Error cargando GIFs:", e)

    frame_actual = 0
    usar_saludo = True

    def animar():
        nonlocal frame_actual
        frames = frames_saludo if usar_saludo else frames_permanente
        duraciones = duraciones_saludo if usar_saludo else duraciones_permanente
        if frames:
            canvas.delete("all")
            frame = frames[frame_actual % len(frames)]
            canvas.create_image(TAMANO_IMAGEN[0]//2, TAMANO_IMAGEN[1]//2, anchor=tk.CENTER, image=frame)
            delay = duraciones[frame_actual % len(duraciones)] if duraciones else 80
            frame_actual = (frame_actual + 1) % len(frames)
            ventana.after(delay, animar)
        else:
            ventana.after(200, animar)

    # ==================== FUNCIONES BANDEJA ====================
    def ocultar_ventana():
        try:
            ventana.withdraw()
            if icono:
                icono.visible = True
        except Exception:
            pass

    def restaurar_ventana(icon, item):
        try:
            ventana.deiconify()
            icon.visible = False
        except Exception:
            pass

    def salir_app(icon, item):
        global escuchando
        escuchando = False
        try:
            ventana.destroy()
        except Exception:
            pass
        try:
            icon.stop()
        except Exception:
            pass

    try:
        icono_img = Image.open(GIF_PERMANENTE).resize((32, 32))
    except Exception:
        icono_img = Image.new("RGBA", (32, 32), (255, 0, 0, 0))
    icono = pystray.Icon("Iris", icono_img, menu=pystray.Menu(
        item("Restaurar", restaurar_ventana),
        item("Salir", salir_app)
    ))
    threading.Thread(target=icono.run, daemon=True).start()

    # ==================== EVENTOS: MOVER ====================
    def guardar_pos(e):
        ventana.x = e.x
        ventana.y = e.y

    def mover_ventana(e):
        nueva_x = ventana.winfo_pointerx() - ventana.x
        nueva_y = ventana.winfo_pointery() - ventana.y
        ventana.geometry(f"+{nueva_x}+{nueva_y}")
        mover_burbuja_con_gif()  # mover la burbuja con el GIF

    canvas.bind("<Button-1>", guardar_pos)
    canvas.bind("<B1-Motion>", mover_ventana)
    canvas.bind("<Double-Button-1>", lambda e: ocultar_ventana())

    # Hilo de escucha (voz)
    escuchar_thread = threading.Thread(target=escuchar_loop, daemon=True)
    escuchar_thread.start()

    # Saludo inicial
    threading.Thread(target=hablar_y_guardar, args=("Hola, soy Iris. Estoy lista para ayudarte.",), daemon=True).start()

    animar()
    ventana.mainloop()

# ==================== BURBUJA (VIÑETA SOBRE EL GIF) ====================
bubble_win = None
bubble_label = None
bubble_entry = None
bubble_send_btn = None
bubble_close_btn = None
bubble_stop_btn = None
bubble_anim_id = None
bubble_visible = False

def bubble_position_relative():
    """Calcula la posición para que la burbuja quede justo encima del GIF."""
    if ventana:
        x = ventana.winfo_x()
        y = ventana.winfo_y()
        w = TAMANO_IMAGEN[0]
        h = TAMANO_IMAGEN[1]
        return (x + w//2 - 160, y - 160)
    return POSICION_VENTANA

def create_bubble_window():
    """Crea la burbuja del chat (viñeta) con scroll y botones fijos"""
    global bubble_win, bubble_label, bubble_entry, bubble_send_btn, bubble_close_btn, bubble_stop_btn, bubble_visible, bubble_text

    if bubble_win and bubble_win.winfo_exists():
        bubble_win.deiconify()
        bubble_win.lift()
        return

    pos = bubble_position_relative()
    bubble_win = tk.Toplevel()
    bubble_win.overrideredirect(True)
    bubble_win.wm_attributes("-topmost", True)
    bubble_win.config(bg="#f7f7f8")
    bubble_win.geometry(f"340x200+{pos[0]}+{pos[1]}")  # tamaño fijo

    # -------------------- GRID PRINCIPAL --------------------
    bubble_win.rowconfigure(0, weight=1)  # Text se expande
    bubble_win.rowconfigure(1, weight=0)  # fila de botones fija
    bubble_win.columnconfigure(0, weight=1)

    # -------------------- AREA DE TEXTO CON SCROLL --------------------
    text_frame = tk.Frame(bubble_win, bg="#f7f7f8")
    text_frame.grid(row=0, column=0, sticky="nsew")

    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    bubble_text = tk.Text(
        text_frame,
        wrap=tk.WORD,
        yscrollcommand=scrollbar.set,
        bg="#f7f7f8",
        fg="#111",
        font=("Arial", 10),
        padx=8,
        pady=8,
        state=tk.DISABLED
    )
    bubble_text.pack(fill=tk.BOTH, expand=True)
    scrollbar.config(command=bubble_text.yview)

    # -------------------- BARRA INFERIOR FIJA --------------------
    bottom = tk.Frame(bubble_win, bg="#f7f7f8")
    bottom.grid(row=1, column=0, sticky="ew", pady=(4,4))
    bottom.columnconfigure(0, weight=1)  # Entry se expande

    bubble_entry = tk.Entry(bottom, font=("Arial", 10))
    bubble_entry.grid(row=0, column=0, sticky="ew", padx=(4,4))

    bubble_send_btn = tk.Button(bottom, text="Enviar", command=bubble_send, bg="#00bfff", fg="white")
    bubble_send_btn.grid(row=0, column=1, padx=(0, 4))

    bubble_stop_btn = tk.Button(bottom, text="⏹", command=detener_voz, bg="#ff5555", fg="white")
    bubble_stop_btn.grid(row=0, column=2, padx=(0, 4))

    bubble_close_btn = tk.Button(bottom, text="❌", command=hide_bubble, bg="#dddddd")
    bubble_close_btn.grid(row=0, column=3, padx=(0,4))

    bubble_visible = True


def mover_burbuja_con_gif():
    if bubble_win and bubble_win.winfo_exists() and bubble_visible:
        pos = bubble_position_relative()
        bubble_win.geometry(f"+{pos[0]}+{pos[1]}")

def show_bubble_with_text(text, animate=True):
    if not (bubble_win and bubble_win.winfo_exists()):
        create_bubble_window()
    try:
        bubble_win.deiconify()
        bubble_win.lift()
    except Exception:
        pass

    if animate:
        _animate_text(0, text)
    else:
        bubble_text.config(state=tk.NORMAL)
        bubble_text.delete("1.0", tk.END)
        bubble_text.insert(tk.END, text)
        bubble_text.config(state=tk.DISABLED)

def _animate_text(idx, text):
    global bubble_anim_id
    if idx <= len(text):
        bubble_text.config(state=tk.NORMAL)
        bubble_text.delete("1.0", tk.END)
        bubble_text.insert(tk.END, text[:idx])
        bubble_text.config(state=tk.DISABLED)
        bubble_anim_id = ventana.after(18, _animate_text, idx + 1, text)
    else:
        bubble_anim_id = None

def hide_bubble():
    global bubble_visible
    if bubble_win and bubble_win.winfo_exists():
        bubble_win.withdraw()
    bubble_visible = False

def bubble_send():
    texto = bubble_entry.get().strip()
    if not texto:
        return
    bubble_entry.delete(0, tk.END)

    def enviar_y_responder(prompt):
        try:
            user_id = None
            with current_user_id_lock:
                user_id = current_user_id
            if not user_id:
                return

            # Mostrar el mensaje del usuario
            agregar_mensaje(f"Tú: {prompt}")

            # Enviar mensaje al backend
            import requests
            resp = requests.post("http://127.0.0.1:5000/send_message", json={"message": prompt})

            if resp.status_code == 200:
                data = resp.json()
                respuesta = data.get("bot_response", "Error: sin respuesta")
                hablar_y_guardar_con_bubble_threadsafe(respuesta)
            else:
                agregar_mensaje("⚠️ Error al conectar con el servidor")

        except Exception as e:
            print("Error en bubble_send:", e)
            agregar_mensaje(f"⚠️ Error: {e}")

    threading.Thread(target=enviar_y_responder, args=(texto,), daemon=True).start()


    # Respuesta IA
    def responder(prompt):
        show_bubble_with_text("Escribiendo...", animate=False)
        respuesta = obtener_respuesta_ia(prompt)
        hablar_y_guardar_con_bubble_threadsafe(respuesta)
        

    threading.Thread(target=responder, args=(texto,), daemon=True).start()

def hablar_y_guardar_con_bubble_threadsafe(texto):
    """Actualiza burbuja y habla, de forma segura para hilos."""
    def actualizar_burbuja():
        show_bubble_with_text(texto, animate=True)
    if ventana:
        ventana.after(0, actualizar_burbuja)  # Se ejecuta en el hilo principal de Tk
    # Luego la voz sigue en hilo separado
    threading.Thread(target=hablar_y_guardar, args=(texto,), daemon=True).start()


def limpiar_texto(widget):
    try:
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.config(state=tk.DISABLED)
    except Exception as e:
        print("Error en limpiar_texto:", e)

def agregar_mensaje(texto):
    global bubble_text, bubble_window
    try:
        if not (bubble_window and bubble_window.winfo_exists()):
            create_bubble_window()
    except Exception:
        pass

    try:
        if not bubble_text:
            return
        bubble_text.config(state=tk.NORMAL)
        bubble_text.insert(tk.END, texto + "\n\n")
        bubble_text.see(tk.END)
        bubble_text.config(state=tk.DISABLED)
    except Exception as e:
        print("Error en agregar_mensaje:", e)



# ===================== FLASK WEB APP ===================== #
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
        secret_key = "6LcWmeorAAAAANAU3YgXlw8X_9fveTarCRZIzoEv" 
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
    global ventana, escuchando, current_user_id, icono

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Si había quedado un icono viejo, eliminarlo
    try:
        if icono:
            icono.stop()
            icono = None
    except:
        pass

    # Si ya hay ventana visible, no crear otra
    if ventana and ventana.winfo_exists():
        return jsonify({"status": "Iris ya está activa"})

    escuchando = True

    # Asignar usuario actual
    with current_user_id_lock:
        current_user_id = session.get("user_id")

    threading.Thread(target=crear_ventana, daemon=True).start()

    return jsonify({"status": "Iris activada correctamente"})


@app.route("/desactivar")
def desactivar():
    """Desactiva Iris sin bloquear la respuesta del servidor"""
    global ventana, escuchando, icono, detener_voz_flag

    # Detener reconocimiento y voz inmediatamente
    escuchando = False
    detener_voz_flag = True
    try:
        detener_voz()  # 💥 Corta cualquier reproducción TTS activa
    except Exception as e:
        print("Error al detener voz:", e)

    def cerrar_todo():
        """Cerrar ventana e icono sin bloquear Flask"""
        global ventana, icono
        try:
            if ventana and ventana.winfo_exists():
                ventana.destroy()
                ventana = None
        except Exception as e:
            print("Error al cerrar ventana:", e)
            ventana = None

        try:
            if icono:
                icono.stop()
                icono = None
        except Exception as e:
            print("Error al detener icono:", e)

    # Cerrar en segundo plano para no bloquear la respuesta al navegador
    threading.Thread(target=cerrar_todo, daemon=True).start()

    # Responder inmediatamente al frontend
    return jsonify({"status": "Iris desactivada"})



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



# ===================== NUEVA RUTA: RECIBIR MENSAJES DESDE EL FRONT (WEB) =====================
@app.route('/send_message', methods=['POST'])
def send_message():
    """
    Endpoint que el frontend puede usar para enviar un mensaje escrito desde la web.
    Guarda en BD y dispara la IA + TTS para que la ventana flotante responda por voz.
    Body JSON: { "message": "texto" }
    """
    if "user_id" not in session:
        return jsonify({"error": "No autorizado"}), 401

    data = request.get_json() or {}
    mensaje = data.get("message", "").strip()
    if not mensaje:
        return jsonify({"error": "Mensaje vacío"}), 400

    user_id = session["user_id"]

    try:
        # Guardar mensaje del usuario
        insert_chat(user_id, "usuario", mensaje)
    except Exception as e:
        print("Error guardando mensaje web:", e)

    # Generar respuesta IA (sin bloquear el frontend)
    try:
        respuesta = obtener_respuesta_ia(mensaje)

        # Guardar respuesta y reproducirla (esta función también guarda en BD)
        hablar_y_guardar_con_bubble_threadsafe(respuesta)

        # ✅ Devolver ambos mensajes para actualizar el chat sin recargar
        return jsonify({
            "ok": True,
            "user_message": mensaje,
            "ia_message": respuesta
        })

    except Exception as e:
        print("Error en responder_y_hablar:", e)
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500
    



# ===================== EJECUCIÓN PRINCIPAL =====================
if __name__ == "__main__":
    # Nota: ejecuta la app Flask; la ventana flotante se lanza cuando el usuario pulsa activar desde la web (/activar).
    app.run(debug=True)
