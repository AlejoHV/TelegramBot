import os
import sqlite3
import logging
import datetime
import re

import telebot
from telebot import TeleBot, types
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv

# Token del bot
TOKEN = '7692955688:AAFgaDOdvrVOQIHyG8vHZdkZtENKw_pEHOg'
bot = telebot.TeleBot(TOKEN)

# Cargar variables de entorno (si es necesario)
load_dotenv()
if not TOKEN:
    raise ValueError("No se ha definido el token del bot en las variables de entorno.")

scheduler = BackgroundScheduler()
scheduler.start()
scheduled_jobs = {}  # Diccionario para almacenar los trabajos programados

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la base de datos
DB_NAME = 'appointments.db'


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            barbero TEXT NOT NULL,
            fecha TEXT NOT NULL,
            telefono TEXT NOT NULL,
            completada INTEGER DEFAULT 0,
            calificacion INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            user_id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL,
            cumpleanos TEXT,
            ultima_cita TEXT
        )
    ''')
    conn.commit()
    conn.close()


init_db()

# Diccionario de barberos y sus citas disponibles
barberos = {
    "Juan": [
        "2025-05-28 1:28", "2025-06-01 11:00", "2025-06-01 14:00", "2025-06-01 16:00",
        "2025-06-02 10:00", "2025-06-02 12:00", "2025-06-02 15:00", "2025-06-02 17:00",
        "2025-06-03 09:30", "2025-06-03 11:30", "2025-06-03 14:30", "2025-06-03 16:30"
    ],
    "Pedro": [
        "2025-06-01 08:00", "2025-06-01 10:30", "2025-06-01 13:00", "2025-06-01 15:30",
        "2025-06-02 09:00", "2025-06-02 11:30", "2025-06-02 14:00", "2025-06-02 16:30",
        "2025-06-04 08:30", "2025-06-04 11:00", "2025-06-04 13:30", "2025-06-04 16:00"
    ],
    "Luis": [
        "2025-06-01 08:30", "2025-06-01 11:00", "2025-06-01 13:30", "2025-06-01 16:00",
        "2025-06-03 08:00", "2025-06-03 10:30", "2025-06-03 13:00", "2025-06-03 15:30",
        "2025-06-05 09:00", "2025-06-05 11:30", "2025-06-05 14:00", "2025-06-05 16:30"
    ],
    "Carlos": [
        "2025-06-02 08:00", "2025-06-02 10:30", "2025-06-02 13:00", "2025-06-02 15:30",
        "2025-06-04 09:00", "2025-06-04 11:30", "2025-06-04 14:00", "2025-06-04 16:30",
        "2025-06-06 08:30", "2025-06-06 11:00", "2025-06-06 13:30", "2025-06-06 16:00"
    ],
    "Miguel": [
        "2025-06-03 09:00", "2025-06-03 11:30", "2025-06-03 14:00", "2025-06-03 16:30",
        "2025-06-05 08:00", "2025-06-05 10:30", "2025-06-05 13:00", "2025-06-05 15:30",
        "2025-06-07 09:30", "2025-06-07 12:00", "2025-06-07 14:30", "2025-06-07 17:00"
    ],
    "Andrés": [
        "2025-06-01 08:00", "2025-06-01 10:30", "2025-06-01 13:00", "2025-06-01 15:30",
        "2025-06-04 09:00", "2025-06-04 11:30", "2025-06-04 14:00", "2025-06-04 16:30",
        "2025-06-07 08:30", "2025-06-07 11:00", "2025-06-07 13:30", "2025-06-07 16:00"
    ],
    "Javier": [
        "2025-06-02 09:00", "2025-06-02 11:30", "2025-06-02 14:00", "2025-06-02 16:30",
        "2025-06-05 08:30", "2025-06-05 11:00", "2025-06-05 13:30", "2025-06-05 16:00",
        "2025-06-06 09:30", "2025-06-06 12:00", "2025-06-06 14:30", "2025-06-06 17:00"
    ]
}
# Diccionario para almacenar temporalmente la información de los usuarios
usuarios_info = {}


def save_cita(user_id, barbero, fecha, telefono):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO citas (user_id, barbero, fecha, telefono) VALUES (?, ?, ?, ?)',
                       (user_id, barbero, fecha, telefono))
        conn.commit()
    except Exception as e:
        logger.error("Error al guardar cita: %s", e)
    finally:
        conn.close()


def get_cita(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT id, barbero, fecha FROM citas WHERE user_id = ? AND completada = 0', (user_id,))
        result = cursor.fetchone()
        return result if result else None
    except Exception as e:
        logger.error("Error al obtener cita: %s", e)
        return None
    finally:
        conn.close()


def get_citas_by_barbero_and_fecha(barbero, fecha):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM citas WHERE barbero = ? AND fecha = ?', (barbero, fecha))
        result = cursor.fetchone()
        return result if result else None
    except Exception as e:
        logger.error("Error al obtener citas por barbero y fecha: %s", e)
        return None
    finally:
        conn.close()


def save_user_info(user_id, nombre, telefono, cumpleanos=None):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO usuarios (user_id, nombre, telefono, cumpleanos) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, nombre, telefono, cumpleanos))
        conn.commit()
    except Exception as e:
        logger.error("Error al guardar información del usuario: %s", e)
    finally:
        conn.close()


def get_user_info(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT nombre, telefono, cumpleanos FROM usuarios WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        if result:
            return {
                "name": result[0],
                "phone": result[1],
                "birthday": result[2]
            }
        return None
    except Exception as e:
        logger.error("Error al obtener información del usuario: %s", e)
        return None
    finally:
        conn.close()


def marcar_cita_como_completada(cita_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE citas SET completada = 1 WHERE id = ?', (cita_id,))
        conn.commit()
    except Exception as e:
        logger.error("Error al marcar cita como completada: %s", e)
    finally:
        conn.close()


def agregar_calificacion(cita_id, calificacion):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE citas SET calificacion = ? WHERE id = ?', (calificacion, cita_id))
        conn.commit()
    except Exception as e:
        logger.error("Error al agregar calificación: %s", e)
    finally:
        conn.close()


def verificar_cumpleanos():
    try:
        hoy = datetime.datetime.now().strftime("%m-%d")
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, nombre FROM usuarios WHERE substr(cumpleanos, 6) = ?', (hoy,))
        usuarios = cursor.fetchall()

        for user_id, nombre in usuarios:
            bot.send_message(
                user_id,
                f"🎉🎂 ¡Feliz cumpleaños, {nombre}! 🎂🎉\n\n"
                "Por ser tu día especial, tenemos un regalo para ti:\n"
                "✅ 20% de descuento en tu próxima cita este mes.\n\n"
                "¡Ven a celebrar con nosotros y luce genial en tu día especial!"
            )
    except Exception as e:
        logger.error("Error al verificar cumpleaños: %s", e)
    finally:
        conn.close()


# Programar verificación diaria de cumpleaños
scheduler.add_job(
    verificar_cumpleanos,
    'cron',
    hour=9,
    minute=0,
    id='verificar_cumpleanos'
)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_info = get_user_info(user_id)

    if not user_info:
        bot.send_message(user_id, "👋 ¡Hola! Bienvenido al sistema de citas de la barbería.\n\n"
                                  "Antes de agendar una cita, por favor dime tu nombre completo.")
        bot.register_next_step_handler(message, save_name)
    else:
        usuarios_info[user_id] = user_info
        mostrar_menu_principal(message)


def save_name(message):
    user_id = message.from_user.id
    usuarios_info[user_id] = {"name": message.text}
    bot.send_message(user_id,
                     "📝 Gracias. Ahora, ¿puedes proporcionarnos tu número de teléfono?")
    bot.register_next_step_handler(message, save_phone)


def save_phone(message):
    user_id = message.from_user.id
    phone = message.text

    # Validación básica de número de teléfono
    if not re.match(r'^[0-9\s\+\-\(\)]{7,15}$', phone):
        bot.send_message(user_id, "⚠️ El número de teléfono no parece válido. Por favor, inténtalo de nuevo.")
        bot.register_next_step_handler(message, save_phone)
        return

    usuarios_info[user_id]["phone"] = phone

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(types.KeyboardButton("Sí"), types.KeyboardButton("No"))

    bot.send_message(user_id,
                     "📅 ¿Te gustaría registrarnos tu fecha de cumpleaños para recibir descuentos especiales? (Sí/No)",
                     reply_markup=markup)
    bot.register_next_step_handler(message, preguntar_cumpleanos)


def preguntar_cumpleanos(message):
    user_id = message.from_user.id
    respuesta = message.text.lower()

    if respuesta == 'sí' or respuesta == 'si' or respuesta == 's':
        bot.send_message(user_id, "🎂 Por favor, ingresa tu fecha de cumpleaños en formato AAAA-MM-DD (ej: 1990-05-15)")
        bot.register_next_step_handler(message, save_birthday)
    else:
        save_user_info(user_id, usuarios_info[user_id]["name"], usuarios_info[user_id]["phone"])
        bot.send_message(user_id, "✅ Información registrada correctamente.")
        mostrar_menu_principal(message)


def save_birthday(message):
    user_id = message.from_user.id
    try:
        # Validar formato de fecha
        datetime.datetime.strptime(message.text, '%Y-%m-%d')
        usuarios_info[user_id]["birthday"] = message.text
        save_user_info(user_id, usuarios_info[user_id]["name"], usuarios_info[user_id]["phone"], message.text)
        bot.send_message(user_id, "✅ Información registrada correctamente. ¡Te avisaremos en tu cumpleaños!")
        mostrar_menu_principal(message)
    except ValueError:
        bot.send_message(user_id, "⚠️ Formato de fecha incorrecto. Por favor, usa AAAA-MM-DD (ej: 1990-05-15)")
        bot.register_next_step_handler(message, save_birthday)


def mostrar_menu_principal(message):
    markup = types.InlineKeyboardMarkup()
    btn_agendar = types.InlineKeyboardButton("📅 Agendar cita", callback_data="agendar_cita")
    btn_ver = types.InlineKeyboardButton("👀 Ver cita programada", callback_data="ver_cita")
    btn_cancelar = types.InlineKeyboardButton("❌ Cancelar cita", callback_data="cancelar_cita")
    markup.row(btn_agendar, btn_ver, btn_cancelar)

    if isinstance(message, types.Message):
        bot.send_message(
            message.chat.id,
            "📌 Menú Principal:\n\n¿Qué te gustaría hacer?",
            reply_markup=markup
        )
    else:  # Es un CallbackQuery
        bot.edit_message_text(
            chat_id=message.message.chat.id,
            message_id=message.message.message_id,
            text="📌 Menú Principal:\n\n¿Qué te gustaría hacer?",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data == "volver_menu")
def volver_al_menu(call):
    mostrar_menu_principal(call)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "agendar_cita":
        mostrar_barberos(call)
    elif call.data.startswith("barbero:"):
        seleccionar_horario(call)
    elif call.data.startswith("cita:"):
        confirmar_cita(call)
    elif call.data == "ver_cita":
        ver_cita(call)
    elif call.data == "cancelar_cita":
        confirmar_cancelacion(call)
    elif call.data == "confirmar_cancelar":
        cancelar_cita(call)
    elif call.data.startswith("calificar:"):
        procesar_calificacion(call)
    elif call.data == "volver_menu":
        volver_al_menu(call)


def mostrar_barberos(call):
    markup = types.InlineKeyboardMarkup()
    for barber in barberos:
        btn = types.InlineKeyboardButton(f"✂️ Barbero {barber}", callback_data=f"barbero:{barber}")
        markup.row(btn)
    markup.row(types.InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👨‍✂️ Selecciona un barbero para agendar tu cita:",
        reply_markup=markup
    )


def seleccionar_horario(call):
    barber = call.data.split(":", 1)[1]
    horarios = barberos.get(barber, [])
    if not horarios:
        bot.answer_callback_query(call.id, text="⚠️ No hay citas disponibles para este barbero.")
        return
    markup = types.InlineKeyboardMarkup()
    for horario in horarios:
        btn = types.InlineKeyboardButton(
            f"⏰ {horario}", callback_data=f"cita:{barber}:{horario}"
        )
        markup.row(btn)
    markup.row(types.InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🕒 Selecciona el horario para tu cita con el barbero {barber}:",
        reply_markup=markup
    )


def confirmar_cita(call):
    try:
        parts = call.data.split(":", 2)
        barber = parts[1]
        fecha_cita_str = parts[2]
        fecha_cita = datetime.datetime.strptime(fecha_cita_str, '%Y-%m-%d %H:%M')

        # Verificar si ya hay una cita para ese barbero y fecha
        cita_existente = get_citas_by_barbero_and_fecha(barber, fecha_cita_str)
        if cita_existente:
            bot.answer_callback_query(call.id, text="⚠️ ¡Esta cita ya ha sido tomada por otro usuario!")
            return

        # Guardar la cita
        user_id = call.from_user.id
        telefono = usuarios_info.get(user_id, {}).get("phone", "No proporcionado")
        save_cita(user_id, barber, fecha_cita_str, telefono)

        # Formatear fecha para mostrar
        fecha_formateada = fecha_cita.strftime('%d/%m/%Y a las %H:%M')

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ Cita agendada con éxito!\n\n"
                 f"✂️ Barbero: {barber}\n"
                 f"📅 Fecha: {fecha_formateada}\n\n"
                 f"¡Te esperamos! 🎉"
        )

        # Programar recordatorios
        programar_recordatorios(user_id, barber, fecha_cita_str, fecha_cita)

    except Exception as e:
        logger.error("Error al confirmar la cita: %s", e)
        bot.answer_callback_query(call.id, text="❌ Error al procesar la cita.")


def programar_recordatorios(user_id, barber, fecha_cita_str, fecha_cita):
    # Recordatorio 1 día antes
    reminder_time = fecha_cita - datetime.timedelta(days=1)
    if reminder_time > datetime.datetime.now():
        job_id = f"reminder_{user_id}_{barber}_{fecha_cita_str}"
        job = scheduler.add_job(
            recordatorio,
            DateTrigger(run_date=reminder_time),
            args=[user_id, barber, fecha_cita_str],
            id=job_id
        )
        scheduled_jobs[job_id] = job

    # Recordatorio 1 hora antes
    reminder_time = fecha_cita - datetime.timedelta(hours=1)
    if reminder_time > datetime.datetime.now():
        job_id = f"reminder_1h_{user_id}_{barber}_{fecha_cita_str}"
        job = scheduler.add_job(
            recordatorio_1h,
            DateTrigger(run_date=reminder_time),
            args=[user_id, barber, fecha_cita_str],
            id=job_id
        )
        scheduled_jobs[job_id] = job

    # Programar solicitud de calificación después de la cita
    calificacion_time = fecha_cita + datetime.timedelta(hours=2)
    if calificacion_time > datetime.datetime.now():
        job_id = f"calificacion_{user_id}_{barber}_{fecha_cita_str}"
        job = scheduler.add_job(
            solicitar_calificacion,
            DateTrigger(run_date=calificacion_time),
            args=[user_id, barber, fecha_cita_str],
            id=job_id
        )
        scheduled_jobs[job_id] = job


def ver_cita(call):
    user_id = call.from_user.id
    cita = get_cita(user_id)
    if cita:
        cita_id, barbero, fecha = cita
        fecha_obj = datetime.datetime.strptime(fecha, '%Y-%m-%d %H:%M')
        fecha_formateada = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

        texto = (f"📅 Cita programada:\n\n"
                 f"✂️ Barbero: {barbero}\n"
                 f"⏰ Fecha: {fecha_formateada}\n\n"
                 f"¿Necesitas hacer algún cambio?")
    else:
        texto = "ℹ️ No tienes citas programadas actualmente."

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔙 Volver al menú", callback_data="volver_menu"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=texto,
        reply_markup=markup
    )


def confirmar_cancelacion(call):
    user_id = call.from_user.id
    cita = get_cita(user_id)

    if not cita:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="ℹ️ No tienes citas programadas para cancelar."
        )
        return

    cita_id, barbero, fecha = cita
    fecha_obj = datetime.datetime.strptime(fecha, '%Y-%m-%d %H:%M')
    fecha_formateada = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

    markup = types.InlineKeyboardMarkup()
    btn_confirmar = types.InlineKeyboardButton("✅ Confirmar cancelación", callback_data="confirmar_cancelar")
    btn_cancelar = types.InlineKeyboardButton("🔙 Volver", callback_data="volver_menu")
    markup.row(btn_confirmar, btn_cancelar)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"⚠️ ¿Estás seguro que deseas cancelar tu cita con {barbero} programada para el {fecha_formateada}?",
        reply_markup=markup
    )


def cancelar_cita(call):
    user_id = call.from_user.id
    try:
        # Obtener la cita del usuario
        cita = get_cita(user_id)
        if not cita:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="ℹ️ No tienes citas programadas para cancelar."
            )
            return

        cita_id, barbero, fecha = cita

        # Eliminar la cita de la base de datos
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM citas WHERE id = ?", (cita_id,))
        conn.commit()
        conn.close()

        # Cancelar los recordatorios programados
        job_prefixes = [
            f"reminder_{user_id}_{barbero}_{fecha}",
            f"reminder_1h_{user_id}_{barbero}_{fecha}",
            f"calificacion_{user_id}_{barbero}_{fecha}"
        ]

        for prefix in job_prefixes:
            for job_id in list(scheduled_jobs.keys()):
                if job_id.startswith(prefix):
                    try:
                        scheduled_jobs[job_id].remove()
                        del scheduled_jobs[job_id]
                    except Exception as e:
                        logger.error(f"Error al cancelar el trabajo {job_id}: {e}")

        # Formatear fecha para el mensaje
        fecha_obj = datetime.datetime.strptime(fecha, '%Y-%m-%d %H:%M')
        fecha_formateada = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ Tu cita con {barbero} para el {fecha_formateada} ha sido cancelada exitosamente."
        )

    except Exception as e:
        logger.error("Error al cancelar la cita: %s", e)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❌ Hubo un error al cancelar tu cita. Por favor, inténtalo de nuevo."
        )


def recordatorio(user_id, barbero, fecha_cita_str):
    try:
        # Verificar si la cita aún existe
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM citas WHERE user_id = ? AND barbero = ? AND fecha = ?",
                       (user_id, barbero, fecha_cita_str))
        cita_existe = cursor.fetchone()
        conn.close()

        if cita_existe:
            # Formatear la fecha para mostrarla
            fecha_obj = datetime.datetime.strptime(fecha_cita_str, '%Y-%m-%d %H:%M')
            fecha_formateada = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

            bot.send_message(
                user_id,
                f"⏰ RECORDATORIO IMPORTANTE:\n\n"
                f"Tu cita con el barbero {barbero} es mañana a las {fecha_formateada}.\n\n"
                f"📍 Dirección: Calle Principal 123\n"
                f"📞 Teléfono: +123456789\n\n"
                f"¡Te esperamos! ✂️"
            )

    except Exception as e:
        logger.error("Error al enviar el recordatorio: %s", e)


def recordatorio_1h(user_id, barbero, fecha_cita_str):
    try:
        # Verificar si la cita aún existe
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM citas WHERE user_id = ? AND barbero = ? AND fecha = ?",
                       (user_id, barbero, fecha_cita_str))
        cita_existe = cursor.fetchone()
        conn.close()

        if cita_existe:
            bot.send_message(
                user_id,
                f"⏰ RECORDATORIO: ¡Tu cita con {barbero} es en 1 hora!\n\n"
                f"Por favor, asegúrate de llegar a tiempo. 😊"
            )

    except Exception as e:
        logger.error("Error al enviar el recordatorio de 1 hora: %s", e)


def solicitar_calificacion(user_id, barbero, fecha_cita_str):
    try:
        # Verificar si la cita existe y no ha sido calificada
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM citas WHERE user_id = ? AND barbero = ? AND fecha = ? AND calificacion = 0",
                       (user_id, barbero, fecha_cita_str))
        cita = cursor.fetchone()
        conn.close()

        if cita:
            cita_id = cita[0]
            markup = types.InlineKeyboardMarkup()
            for i in range(1, 6):
                markup.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"calificar:{cita_id}:{i}"))

            bot.send_message(
                user_id,
                f"✂️ ¿Cómo calificarías tu experiencia con el barbero {barbero}?\n\n"
                "Por favor, selecciona una calificación de 1 a 5 estrellas:",
                reply_markup=markup
            )

            # Marcar la cita como completada
            marcar_cita_como_completada(cita_id)

    except Exception as e:
        logger.error("Error al solicitar calificación: %s", e)


def procesar_calificacion(call):
    try:
        _, cita_id, calificacion = call.data.split(":")
        cita_id = int(cita_id)
        calificacion = int(calificacion)

        # Guardar la calificación
        agregar_calificacion(cita_id, calificacion)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🌟 ¡Gracias por tu calificación de {calificacion} estrellas!\n\n"
                 "Tu opinión nos ayuda a mejorar nuestro servicio. ¡Esperamos verte pronto de nuevo! 😊"
        )

    except Exception as e:
        logger.error("Error al procesar calificación: %s", e)
        bot.answer_callback_query(call.id, text="❌ Error al procesar tu calificación.")


if __name__ == "__main__":
    try:
        # Eliminar el webhook si está configurado
        bot.remove_webhook()

        # Iniciar el polling después de eliminar el webhook
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error("Error en polling del bot: %s", e)