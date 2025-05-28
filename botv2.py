import os
import sqlite3
import logging
import datetime

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
            telefono TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


init_db()

# Diccionario de barberos y sus citas disponibles
barberos = {
    "Juan": ["2025-05-28 11:54", "2025-04-10 14:25"],
    "Pedro": ["2025-04-11 11:00", "2025-04-11 15:00"],
    "Luis": ["2025-04-12 12:00", "2025-04-12 16:00"]
}

# Diccionario para almacenar la información de nombre y teléfono de los usuarios
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
        cursor.execute('SELECT barbero, fecha FROM citas WHERE user_id = ?', (user_id,))
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


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id not in usuarios_info:
        bot.send_message(user_id, "¡Hola! Antes de agendar una cita, por favor dime tu nombre completo.")
        bot.register_next_step_handler(message, save_name)
    else:
        markup = types.InlineKeyboardMarkup()
        btn_agendar = types.InlineKeyboardButton("Agendar cita", callback_data="agendar_cita")
        btn_ver = types.InlineKeyboardButton("Ver cita programada", callback_data="ver_cita")
        btn_cancelar = types.InlineKeyboardButton("Cancelar cita", callback_data="cancelar_cita")
        markup.row(btn_agendar, btn_ver, btn_cancelar)
        bot.send_message(
            message.chat.id,
            "¡Hola! Soy el bot para gestionar tus citas. ¿Qué te gustaría hacer?",
            reply_markup=markup
        )


def save_name(message):
    user_id = message.from_user.id
    usuarios_info[user_id] = {"name": message.text}
    bot.send_message(user_id,
                     "Gracias. Ahora, ¿puedes proporcionarnos tu número de teléfono?")
    bot.register_next_step_handler(message, save_phone)


def save_phone(message):
    user_id = message.from_user.id
    usuarios_info[user_id]["phone"] = message.text
    bot.send_message(user_id, "Gracias por tu información. Ahora puedes agendar una cita.")

    # Mostrar el menú para agendar la cita
    markup = types.InlineKeyboardMarkup()
    btn_agendar = types.InlineKeyboardButton("Agendar cita", callback_data="agendar_cita")
    btn_ver = types.InlineKeyboardButton("Ver cita programada", callback_data="ver_cita")
    btn_cancelar = types.InlineKeyboardButton("Cancelar cita", callback_data="cancelar_cita")
    markup.row(btn_agendar, btn_ver, btn_cancelar)
    bot.send_message(
        message.chat.id,
        "¡Información registrada! ¿Qué te gustaría hacer ahora?",
        reply_markup=markup
    )


# Callback para volver al menú
@bot.callback_query_handler(func=lambda call: call.data == "volver_menu")
def volver_al_menu(call):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup()
    btn_agendar = types.InlineKeyboardButton("Agendar cita", callback_data="agendar_cita")
    btn_ver = types.InlineKeyboardButton("Ver cita programada", callback_data="ver_cita")
    btn_cancelar = types.InlineKeyboardButton("Cancelar cita", callback_data="cancelar_cita")
    markup.row(btn_agendar, btn_ver, btn_cancelar)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="¡Hola! Soy el bot para gestionar tus citas. ¿Qué te gustaría hacer?",
        reply_markup=markup
    )


# Manejo de las interacciones
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
        cancelar_cita(call)
    elif call.data == "volver_menu":
        volver_al_menu(call)


def mostrar_barberos(call):
    markup = types.InlineKeyboardMarkup()
    for barber in barberos:
        btn = types.InlineKeyboardButton(f"Barbero {barber}", callback_data=f"barbero:{barber}")
        markup.row(btn)
    markup.row(types.InlineKeyboardButton("Volver al menú", callback_data="volver_menu"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Selecciona un barbero para agendar tu cita:",
        reply_markup=markup
    )


def seleccionar_horario(call):
    barber = call.data.split(":", 1)[1]
    horarios = barberos.get(barber, [])
    if not horarios:
        bot.answer_callback_query(call.id, text="No hay citas disponibles para este barbero.")
        return
    markup = types.InlineKeyboardMarkup()
    for horario in horarios:
        btn = types.InlineKeyboardButton(
            horario, callback_data=f"cita:{barber}:{horario}"
        )
        markup.row(btn)
    markup.row(types.InlineKeyboardButton("Volver al menú", callback_data="volver_menu"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Selecciona el horario para tu cita con el barbero {barber}:",
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
            bot.answer_callback_query(call.id, text="¡Esta cita ya ha sido tomada por otro usuario!")
            return

        # Guardar la cita
        user_id = call.from_user.id
        telefono = usuarios_info.get(user_id, {}).get("phone", "No proporcionado")
        save_cita(user_id, barber, fecha_cita_str, telefono)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ Cita agendada con el barbero {barber} para el {fecha_cita_str}. ¡Nos vemos pronto!"
        )

        # Programar el recordatorio 1 día antes solo si es en el futuro
        reminder_time = fecha_cita - datetime.timedelta(days=1)
        if reminder_time > datetime.datetime.now():
            job_id = f"{user_id}_{barber}_{fecha_cita_str}"
            job = scheduler.add_job(
                recordatorio,
                DateTrigger(run_date=reminder_time),
                args=[user_id, barber, fecha_cita_str],
                id=job_id
            )
            scheduled_jobs[job_id] = job
        else:
            bot.send_message(
                user_id,
                f"ℹ️ Nota: No se programó recordatorio porque tu cita con {barber} es muy pronto ({fecha_cita_str})"
            )
    except Exception as e:
        logger.error("Error al confirmar la cita: %s", e)
        bot.answer_callback_query(call.id, text="Error al procesar la cita.")


def ver_cita(call):
    user_id = call.from_user.id
    cita = get_cita(user_id)
    if cita:
        texto = f"📅 Tienes una cita programada con el barbero {cita[0]} para el {cita[1]}."
    else:
        texto = "ℹ️ No tienes citas programadas."
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Volver al menú", callback_data="volver_menu"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=texto,
        reply_markup=markup
    )


def cancelar_cita(call):
    user_id = call.from_user.id
    try:
        # Obtener todas las citas programadas del usuario
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, barbero, fecha FROM citas WHERE user_id = ?", (user_id,))
        citas = cursor.fetchall()
        conn.close()

        if not citas:
            texto = "ℹ️ No tienes citas programadas para cancelar."
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=texto
            )
            return

        # Mostrar confirmación antes de cancelar
        markup = types.InlineKeyboardMarkup()
        btn_confirmar = types.InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_cancelar")
        btn_cancelar = types.InlineKeyboardButton("❌ Volver", callback_data="volver_menu")
        markup.row(btn_confirmar, btn_cancelar)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="⚠️ ¿Estás seguro que quieres cancelar TODAS tus citas programadas?",
            reply_markup=markup
        )

        # Registrar el siguiente paso para manejar la confirmación
        bot.register_next_step_handler(call.message, lambda m: handle_confirmar_cancelar(m, user_id))

    except Exception as e:
        logger.error("Error al cancelar las citas: %s", e)
        texto = "❌ Hubo un error al cancelar tus citas."
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=texto
        )


def handle_confirmar_cancelar(message, user_id):
    try:
        # Eliminar todas las citas del usuario
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM citas WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        # Cancelar todos los recordatorios programados para este usuario
        for job_id in list(scheduled_jobs.keys()):
            if job_id.startswith(f"{user_id}_"):
                try:
                    scheduled_jobs[job_id].remove()
                    del scheduled_jobs[job_id]
                except Exception as e:
                    logger.error(f"Error al cancelar el trabajo {job_id}: {e}")

        texto = "✅ Todas tus citas han sido canceladas exitosamente."
        bot.send_message(
            message.chat.id,
            texto
        )

        # Volver al menú principal
        volver_al_menu(message)

    except Exception as e:
        logger.error("Error al confirmar cancelación: %s", e)
        texto = "❌ Hubo un error al cancelar tus citas."
        bot.send_message(
            message.chat.id,
            texto
        )


def recordatorio(user_id, barber, fecha_cita_str):
    try:
        # Verificar si la cita aún existe antes de enviar el recordatorio
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM citas WHERE user_id = ? AND barbero = ? AND fecha = ?",
                       (user_id, barber, fecha_cita_str))
        cita_existe = cursor.fetchone()
        conn.close()

        if cita_existe:
            # Formatear la fecha para mostrarla más amigable
            fecha_obj = datetime.datetime.strptime(fecha_cita_str, '%Y-%m-%d %H:%M')
            fecha_formateada = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

            bot.send_message(
                user_id,
                f"⏰ RECORDATORIO:\n\nTu cita con el barbero {barber} es mañana a las {fecha_formateada}.\n\n¡Te esperamos!"
            )

            # Eliminar el trabajo programado después de ejecutarse
            job_id = f"{user_id}_{barber}_{fecha_cita_str}"
            if job_id in scheduled_jobs:
                del scheduled_jobs[job_id]
    except Exception as e:
        logger.error("Error al enviar el recordatorio: %s", e)


if __name__ == "__main__":
    try:
        # Eliminar el webhook si está configurado
        bot.remove_webhook()

        # Iniciar el polling después de eliminar el webhook
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error("Error en polling del bot: %s", e)