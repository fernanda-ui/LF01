# LF01 - Iris Voice Assistant

Iris es un asistente de voz inteligente con interfaz web y de escritorio que utiliza inteligencia artificial para responder preguntas y realizar tareas.

## Características

- 🎤 Reconocimiento de voz en español
- 🤖 Integración con Google Gemini AI
- 💬 Interfaz web moderna con chat en tiempo real
- 🗣️ Síntesis de voz (Text-to-Speech) con gTTS
- 👤 Sistema de autenticación de usuarios
- 💾 Almacenamiento de historial de conversaciones
- 🎨 Tema claro/oscuro en interfaz de chat

## Requisitos Previos

- Python 3.8 o superior
- SQL Server (LocalDB, Express, o completo)
- Cuenta de Google Cloud para Gemini API
- Cuenta de Gmail para envío de correos (opcional)

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/fernanda-ui/LF01.git
cd LF01
```

### 2. Crear entorno virtual

```bash
python -m venv venv
```

Activar el entorno virtual:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

1. Copia el archivo `.env.example` como `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edita el archivo `.env` y completa todas las variables necesarias:

   - **GENAI_API_KEY**: Obtén tu clave en [Google AI Studio](https://makersuite.google.com/app/apikey)
   - **MSSQL_***: Configura la conexión a tu base de datos SQL Server
   - **FLASK_SECRET_KEY**: Genera una clave segura:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - **RECAPTCHA_SECRET_KEY**: Obtén tus claves en [Google reCAPTCHA](https://www.google.com/recaptcha/admin)
   - **SMTP_EMAIL** y **SMTP_PASSWORD**: Para envío de correos de recuperación de contraseña

### 5. Configurar la base de datos

Crea una base de datos SQL Server llamada `LF01` (o el nombre que configuraste en `.env`) con las siguientes tablas:

```sql
-- Tabla de usuarios
CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    first_name NVARCHAR(100) NOT NULL,
    last_name NVARCHAR(100) NOT NULL,
    email NVARCHAR(255) NOT NULL UNIQUE,
    phone NVARCHAR(20),
    username NVARCHAR(50) NOT NULL UNIQUE,
    password NVARCHAR(255) NOT NULL
);

-- Tabla de chats
CREATE TABLE chats (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    sender NVARCHAR(20) NOT NULL,
    mensaje NVARCHAR(MAX) NOT NULL,
    timestamp DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tabla de restablecimiento de contraseñas
CREATE TABLE password_resets (
    id INT IDENTITY(1,1) PRIMARY KEY,
    email NVARCHAR(255) NOT NULL,
    token NVARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT GETDATE()
);
```

## Uso

### Ejecutar la aplicación

```bash
python Iris.py
```

La aplicación estará disponible en `http://localhost:5000`

### Funcionalidades principales

1. **Registro e inicio de sesión**: Accede desde la página principal
2. **Activar Iris**: Una vez autenticado, activa el asistente de voz
3. **Comandos de voz**: Di "Iris" seguido de tu comando
4. **Chat web**: Escribe mensajes directamente en la interfaz

### Comandos de voz disponibles

- "Iris, abre YouTube"
- "Iris, abre Google"
- "Iris, busca en Google [consulta]"
- "Iris, abre Netflix"
- "Iris, abre Word/Excel/PowerPoint"
- "Iris, abre Visual Studio Code"
- O cualquier pregunta que será respondida por la IA

## Estructura del Proyecto

```
LF01/
├── Iris.py              # Aplicación principal
├── requirements.txt     # Dependencias Python
├── .env.example        # Plantilla de variables de entorno
├── static/             # Archivos estáticos (CSS, JS, imágenes)
├── templates/          # Plantillas HTML
├── flask_session/      # Sesiones de Flask
└── README.md          # Este archivo
```

## Seguridad

- Las contraseñas se almacenan hasheadas con SHA256
- Se requiere reCAPTCHA en el inicio de sesión
- Las variables sensibles se manejan mediante archivo `.env`
- El archivo `.env` está excluido del control de versiones

## Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu característica (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -m 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abre un Pull Request

## Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## Contacto

Para preguntas o soporte, por favor abre un issue en el repositorio de GitHub.