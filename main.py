import telebot
from telebot import types
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

# Token del bot (reemplaza por el tuyo si es necesario)
TOKEN = '7692955688:AAFgaDOdvrVOQIHyG8vHZdkZtENKw_pEHOg'
bot = telebot.TeleBot(TOKEN)

# Diccionario para almacenar las citas agendadas por usuario
# Se almacenará una cadena con la información del barbero y la fecha
citas_agendadas = {}

# Diccionario de barberos y sus citas disponibles (puedes modificar o ampliar estas opciones)
barberos = {
    "Juan": ["2025-04-10 10:00", "2025-04-10 14:00"],
    "Pedro": ["2025-04-11 11:00", "2025-04-11 15:00"],
    "Luis": ["2025-04-12 12:00", "2025-04-12 16:00"]
}

# Inicializar el scheduler para los recordatorios
scheduler = BackgroundScheduler()
scheduler.start()


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn_agendar = types.InlineKeyboardButton("Agendar cita", callback_data="agendar_cita")
    btn_ver = types.InlineKeyboardButton("Ver citas programadas", callback_data="ver_citas")
    markup.row(btn_agendar, btn_ver)
    bot.send_message(
        message.chat.id,
        "¡Hola! Soy el bot para gestionar tus citas. Selecciona una opción:",
        reply_markup=markup
    )


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(
        message,
        'Usa el menú que aparece al iniciar (/start) para agendar o ver tus citas.'
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "agendar_cita":
        # Mostrar opciones de barberos
        markup = types.InlineKeyboardMarkup()
        for barber in barberos:
            btn = types.InlineKeyboardButton(f"Barbero {barber}", callback_data=f"barbero:{barber}")
            markup.row(btn)
        btn_volver = types.InlineKeyboardButton("Volver al menú", callback_data="volver_menu")
        markup.row(btn_volver)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Selecciona un barbero para agendar tu cita:",
            reply_markup=markup
        )
    elif call.data.startswith("barbero:"):
        # El usuario ha seleccionado un barbero: mostrar sus citas disponibles
        barber = call.data.split(":", 1)[1]
        horarios = barberos.get(barber, [])
        if not horarios:
            bot.answer_callback_query(call.id, text="No hay citas disponibles para este barbero.")
            return
        markup = types.InlineKeyboardMarkup()
        for horario in horarios:
            # El callback data incluirá tanto el barbero como el horario seleccionado.
            btn = types.InlineKeyboardButton(
                horario, callback_data=f"cita:{barber}:{horario}"
            )
            markup.row(btn)
        btn_volver = types.InlineKeyboardButton("Volver al menú", callback_data="volver_menu")
        markup.row(btn_volver)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Selecciona el horario para tu cita con el barbero {barber}:",
            reply_markup=markup
        )
    elif call.data.startswith("cita:"):
        # Procesar la cita seleccionada (formato: "cita:Barbero:FechaHora")
        try:
            # Realizamos el split máximo de 2 para preservar la parte de fecha que contiene ':'
            parts = call.data.split(":", 2)
            # parts[0] = "cita", parts[1] = barbero y parts[2] = fecha/hora
            barber = parts[1]
            fecha_cita_str = parts[2]
            # Convertir la fecha a objeto datetime para validación
            fecha_cita = datetime.datetime.strptime(fecha_cita_str, '%Y-%m-%d %H:%M')
            user_id = call.from_user.id

            # Guardar la cita en el diccionario con información del barbero y la fecha
            citas_agendadas[user_id] = f"Barbero {barber} - Fecha: {fecha_cita_str}"
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Cita agendada con el barbero {barber} para el {fecha_cita_str}. ¡Nos vemos pronto!"
            )

            # Calcular el momento del recordatorio (1 día antes de la cita)
            reminder_time = fecha_cita - datetime.timedelta(days=1)
            # Si el recordatorio ya habría pasado, lo ajustamos para enviarlo en 10 segundos
            if reminder_time < datetime.datetime.now():
                reminder_time = datetime.datetime.now() + datetime.timedelta(seconds=10)

            trigger = DateTrigger(run_date=reminder_time)
            scheduler.add_job(recordatorio, trigger, args=[user_id, barber, fecha_cita_str])
        except Exception as e:
            bot.answer_callback_query(call.id, text="Error al procesar la cita.")
    elif call.data == "ver_citas":
        # Mostrar la cita agendada del usuario (si existe)
        user_id = call.from_user.id
        cita = citas_agendadas.get(user_id, "No tienes citas programadas.")
        markup = types.InlineKeyboardMarkup()
        btn_volver = types.InlineKeyboardButton("Volver al menú", callback_data="volver_menu")
        markup.row(btn_volver)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Tus citas programadas: {cita}",
            reply_markup=markup
        )
    elif call.data == "volver_menu":
        # Volver al menú principal
        send_welcome(call.message)


def recordatorio(user_id, barber, fecha_cita_str):
    try:
        bot.send_message(
            user_id,
            f"Recordatorio: Tu cita con el barbero {barber} es mañana, {fecha_cita_str}. ¡No faltes!"
        )
    except Exception as e:
        print("Error al enviar el recordatorio:", e)


if __name__ == "__main__":
    bot.polling(none_stop=True)
