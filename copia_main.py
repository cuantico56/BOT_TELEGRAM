import json
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import telegram.error
import datetime
import logging # <-- Importamos el módulo de logging
import sys     # <-- Importamos sys para poder dirigir el log

# --- Configuración ---
# ¡IMPORTANTE! El token ahora se toma de la variable de entorno BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Archivo para guardar los chat_ids de los usuarios
# Cerca de tus configuraciones iniciales
# Define el ID del usuario al que deseas notificar
NOTIFICATION_USER_ID = 1434885751
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Directorio donde está el script
USUARIOS_FILE = os.path.join(BASE_DIR, "usuarios_bot.json")
# Define la ruta del archivo de log. Se creará en el mismo directorio del script.
LOG_FILE = os.path.join(BASE_DIR, "bot_telegram_moneda.log")
# --- AÑADE ESTAS LÍNEAS PARA SILENCIAR LOS LOGS DE HTTPX ---
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout) # Opcional: para ver logs en consola mientras desarrollas
    ]
)

# --- Almacenamiento de IDs de chat ---
usuarios_registrados = set()

def cargar_usuarios_registrados():
    """Carga los IDs de chat guardados desde un archivo."""
    global usuarios_registrados
    if os.path.exists(USUARIOS_FILE):
        try:
            with open(USUARIOS_FILE, 'r', encoding='utf-8') as f:
                usuarios_registrados = set(json.load(f))
                logging.info(f"Usuarios cargados: {len(usuarios_registrados)}")
                print(f"[{os.path.basename(__file__)}] Usuarios cargados: {len(usuarios_registrados)}")
        except Exception as e:
            print(f"Error al cargar usuarios: {e}")
            usuarios_registrados = set()
    else:
        print(f"[{os.path.basename(__file__)}] No se encontró el archivo de usuarios. Iniciando con lista vacía.")
        logging.info(f"No se encontró el archivo de usuarios '{USUARIOS_FILE}'. Iniciando con lista vacía.")

def guardar_usuarios_registrados():
    """Guarda los IDs de chat en un archivo."""
    try:
        with open(USUARIOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(usuarios_registrados), f, indent=4)
            print(f"Usuarios guardados: {len(usuarios_registrados)}")
            logging.info(f"Usuarios guardados: {len(usuarios_registrados)}")
    except Exception as e:
        print(f"Error al guardar usuarios: {e}")
        logging.error(f"Error al guardar usuarios en '{USUARIOS_FILE}': {e}")

# --- Funciones del Bot ---

async def registrar_usuario(update: Update,context: ContextTypes.DEFAULT_TYPE):
    """Registra el chat_id del usuario si no está ya en la lista."""
    chat_id = update.message.chat_id
    sender_user = update.message.from_user # Obtiene el objeto del usuario que envió el mensaje
    if chat_id not in usuarios_registrados:
        usuarios_registrados.add(chat_id)
        guardar_usuarios_registrados()
        print(f"Nuevo usuario registrado: {chat_id}")
        logging.info(f"Nuevo usuario registrado: {chat_id}"+" usuario: "+str(update.message.from_user))
        notification_message = (
        f"🚨 *¡Nuevo Usuario Registrado!* 🚨\n\n"
        f"**Nombre:** {update.get('full_name', 'N/A')}\n"
        f"**Username:** @{update.get('username', 'N/A')}\n"
        f"**ID:** `{update.get('id', 'N/A')}`"
        )
        try:
            await context.bot.send_message(chat_id=NOTIFICATION_USER_ID, text=notification_message)
            logging.info(f"Notificación enviada a {NOTIFICATION_USER_ID} sobre el mensaje de {sender_user.id}")
        except Exception as e:
            logging.error(f"Error al enviar notificación a {NOTIFICATION_USER_ID}: {e}")
        # --- Fin de la lógica de notificación ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para el comando /start."""
    print(f">>> PROCESANDO: Comando /start de {update.message.chat_id}"+"Ususario: "+str(update.message.from_user)) # Nuevo print
    logging.info(f"Comando /start recibido de {update.message.chat_id}"+ " usuario: "+str(update.message.from_user))
    await registrar_usuario(update,context)
    await update.message.reply_text("¡Hola! Soy tu bot de noticias de moneda del BCV. Te enviaré actualizaciones periódicas")

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para cualquier mensaje de texto (no comando)."""
    await registrar_usuario(update,context)
    user_message = update.message.text
    sender_user = update.message.from_user # Obtiene el objeto del usuario que envió el mensaje
    sender_chat_id = update.message.chat_id # Obtiene el ID del chat de donde proviene el mensaje
    print(f">>> PROCESANDO: Mensaje de eco de {update.message.chat_id}: {user_message}") # Nuevo print
    # Define las palabras clave que activarán el envío del audio
    keywords = ["vendieron", "venden", "vemdem", "vender", "vemder", "venderan", "vendiendo","vende"]

    # Convierte el mensaje del usuario a minúsculas una sola vez para optimizar
    message_lower = user_message.lower()

    # Verifica si alguna de las palabras clave está en el mensaje del usuario
    found_keyword = False
    for keyword in keywords:
        if keyword in message_lower:
            found_keyword = True
            break # Si encuentra una, no necesita seguir buscando

    # Verifica si el mensaje contiene la palabra "vendieron" (insensible a mayúsculas/minúsculas)
    if found_keyword:
        audio_path = os.path.join(BASE_DIR, "audios", "Ya_los_vendieron.mp3")
        if os.path.exists(audio_path):
            await update.message.reply_audio(audio=open(audio_path, 'rb'))
            logging.info(f"Audio 'Ya_los_vendieron.mp3' enviado a {update.message.chat_id} por mensaje '{user_message}'")
        else:
            await update.message.reply_text("Lo siento, no pude encontrar el archivo de audio 'Ya_los_vendieron.mp3'.")
            logging.warning(f"No se encontró el archivo de audio: {audio_path}")
    else:
        await update.message.reply_text(f"Recibí tu mensaje: {user_message}")

    # Solo notifica si el remitente NO es el usuario al que se va a notificar
    if sender_chat_id != NOTIFICATION_USER_ID:
        notification_message = (
            f"Nuevo mensaje de {sender_user.full_name} (@{sender_user.username if sender_user.username else 'N/A'}) "
            f"(ID: {sender_user.id}):\n\n"
            f"'{user_message}'"
        )
        try:
            await context.bot.send_message(chat_id=NOTIFICATION_USER_ID, text=notification_message)
            logging.info(f"Notificación enviada a {NOTIFICATION_USER_ID} sobre el mensaje de {sender_user.id}")
        except Exception as e:
            logging.error(f"Error al enviar notificación a {NOTIFICATION_USER_ID}: {e}")
    # --- Fin de la lógica de notificación ---
    logging.info(f"Mensaje de eco de {update.message.chat_id}: '{user_message}' usuario: {update.message.from_user}")


# --- Función para leer y enviar el archivo de texto a TODOS los usuarios ---
async def enviar_contenido_txt_a_todos(context: ContextTypes.DEFAULT_TYPE):
    print(f"DEBUG: Iniciando enviar_contenido_txt_a_todos.") # Nuevo print
    logging.info("Iniciando tarea de envío de contenido TXT a todos los usuarios.")
    fecha_actual_task = datetime.date.today()
    fechahoy_task = fecha_actual_task.strftime("%d-%m-%Y")   
    ARCHIVO_MONEDA_PATH_ACTUAL = r"C:\Users\scastillo\output\TAREA_BACK\MONEDAS\Archivos\Moneda_" + fechahoy_task + ".txt"
    logging.info(f"Ruta del archivo de moneda esperada: {ARCHIVO_MONEDA_PATH_ACTUAL}")

    print(f"DEBUG: Ruta del archivo esperada: {ARCHIVO_MONEDA_PATH_ACTUAL}") # Nuevo print

    if not usuarios_registrados:
        print(f"No hay usuarios registrados para enviar el contenido del TXT.")
        logging.warning("No hay usuarios registrados para enviar el contenido del TXT.")
        return

    if not os.path.exists(ARCHIVO_MONEDA_PATH_ACTUAL):
        print(f"Error: El archivo TXT no se encontró en la ruta: {ARCHIVO_MONEDA_PATH_ACTUAL}")
        error_msg = f"Error: El archivo TXT no se encontró en la ruta: {ARCHIVO_MONEDA_PATH_ACTUAL}"
        logging.error(error_msg)
        if context.job is None:
            if context.effective_chat:
                await context.effective_chat.send_message(f"Error: No se encontró el archivo de moneda para hoy: {fechahoy_task}. Por favor, verifica la ruta o la existencia del archivo.")
            else:
                if usuarios_registrados:
                    await context.bot.send_message(chat_id=list(usuarios_registrados)[0], text=f"Error: No se encontró el archivo de moneda para hoy: {fechahoy_task}. Por favor, verifica la ruta o la existencia del archivo.")
        return

    try:
        with open(ARCHIVO_MONEDA_PATH_ACTUAL, 'r', encoding='utf-8') as f:
            contenido_txt = f.read()
                
        print(f"DEBUG: Contenido del archivo TXT leído (primeros 50 chars): {contenido_txt[:50]}...") # Nuevo print
        logging.info(f"Contenido del archivo TXT leído (primeros 50 chars): '{contenido_txt[:50]}'...")

        for chat_id in list(usuarios_registrados):
            print(f"DEBUG: Intentando enviar a chat_id: {chat_id}") # Nuevo print
            try:
                if len(contenido_txt) > 4000:
                    with open(ARCHIVO_MONEDA_PATH_ACTUAL, 'rb') as doc_file:
                        await context.bot.send_document(chat_id=chat_id, document=doc_file, caption=f"Contenido del archivo {os.path.basename(ARCHIVO_MONEDA_PATH_ACTUAL)}")
                    print(f"Enviado TXT como documento a {chat_id}")
                    logging.info(f"Enviado TXT como documento a {chat_id}")
                else:
                    await context.bot.send_message(chat_id=chat_id, text=f"Precio dolar BCV es:\n```{contenido_txt}```", parse_mode='MarkdownV2')
                    print(f"Enviado TXT como texto a {chat_id}")
                    logging.info(f"Enviado TXT como texto a {chat_id}")
                await asyncio.sleep(0.1)

            except telegram.error.Forbidden:
                print(f"El bot fue bloqueado por el usuario {chat_id}. Removiendo de la lista.")
                usuarios_registrados.remove(chat_id)
                logging.warning(f"El bot fue bloqueado por el usuario {chat_id}. Removiendo de la lista.")
                guardar_usuarios_registrados()
            except Exception as e:
                print(f"Error al enviar a {chat_id}: {e}")
                logging.error(f"Error al enviar mensaje a {chat_id}: {e}")
        notification_message = (
            f"Se ha enviado notificacion a todos!"
        )
        await context.bot.send_message(chat_id=NOTIFICATION_USER_ID, text=notification_message)
                


    except Exception as e:
        print(f"Ocurrió un error general al leer/enviar el archivo TXT: {e}")
        logging.error(f"Ocurrió un error general al leer/enviar el archivo TXT: {e}")

# --- Manejador para el comando /publicarbcv ---
async def publicarbcv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f">>> MENSAJE RECIBIDO: de {update.message.chat_id} - Texto: '{update.message.text}'") # Nuevo print
    logging.info(f"Comando "+update.message.text+" recibido de "+str(update.message.chat_id)+" Usuario: "+str(update.message.from_user)+". Texto: '{update.message.text}'")
    print("Vamos a publicar")
    # Verificamos si el mensaje viene del propio bot
    # El ID de tu propio bot lo puedes obtener del token (parte antes de ':') o de context.bot.id
    # Necesitas el ID de tu bot para esto. Por ahora, solo verificaremos el texto.

    if update.message.text == "/publicarbcv":
        print(f"DEBUG: El texto es exactamente /publicarbcv. Procesando comando.") # Nuevo print
        await registrar_usuario(update,context)
        await enviar_contenido_txt_a_todos(context)
        logging.info("El texto es exactamente '/publicarbcv'. Procesando comando.")
    else:
        print(f" DEBUG: Mensaje no es exactamente /publicarbcv. No se ejecuta el envío.") # Nuevo print
        logging.warning(f"Mensaje no es exactamente '/publicarbcv'. No se ejecuta el envío.")


# --- Configuración y Ejecución del Bot ---

# --- Configuración y Ejecución Principal del Bot ---
logging.info("***********SE INICIA PROGRAMA MAIN**********")
if __name__ == '__main__':
    # Cargar usuarios al inicio
    cargar_usuarios_registrados()
    logging.info("***********CARGADOS USUARIOS REGISTRADOS**********")

    # Construir la aplicación del bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    logging.info("***********CARGADO TOKEN BOT**********")

    # Añadir manejadores de comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("publicarbcv", publicarbcv_command))
    logging.info("***********AÑADIDOS MANEJADOSRES DE COMANDOS**********")
    
    # Manejador para mensajes de texto que NO son comandos (descomentar si lo necesitas)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))
    logging.info("***********MANEJADOR DE MENSAJE**********")

    logging.info("Bot de Telegram iniciado. Esperando mensajes...")
    
    # Iniciar el polling para recibir actualizaciones de Telegram
    application.run_polling(allowed_updates=Update.ALL_TYPES)
