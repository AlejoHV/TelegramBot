"""
import telebot

#Conexion con nuestro BOT
TOKEN = '7692955688:AAFgaDOdvrVOQIHyG8vHZdkZtENKw_pEHOg' 
bot = telebot.TeleBot(TOKEN)


#Creacion de comandos simples como /start y /help
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 'Hola! Soy tu primer bot creado con Telebot')

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, 'Puedes interactuar conmigo usando comandos. Por ahora, solo respondo a /start y /help') 


@bot.message_handler(func=lambda m: True)
def echo_all(message):
    bot.reply_to(message, message.text)


if __name__ == "__main__":
    bot.polling(none_stop=True)  
"""

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup  # type: ignore
##from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
from telegram.ext import filters as Filters
from telegram.ext import CallbackContext, ApplicationBuilder 

from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
##from apscheduler.triggers.simple import SimpleTrigger  # type: ignore

from apscheduler.triggers.interval import IntervalTrigger
import datetime

# Token del bot proporcionado por BotFather
TOKEN = '7692955688:AAFgaDOdvrVOQIHyG8vHZdkZtENKw_pEHOg'

# Lista simple de citas (esto se puede mejorar con una base de datos)
citas_agendadas = {}

# Crear el scheduler para los recordatorios
scheduler = BackgroundScheduler()


def start(update: Update, context: CallbackContext) -> None:
    """Función de inicio, bienvenida y menú principal."""
    update.message.reply_text(
        "¡Hola! Soy el bot para gestionar tus citas. Selecciona una opción:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Agendar cita", callback_data='agendar_cita'),
            InlineKeyboardButton("Ver citas programadas", callback_data='ver_citas')
        ]])
    )


def agendar_cita(update: Update, context: CallbackContext) -> None:
    """Función para iniciar el proceso de agendar una cita."""
    query = update.callback_query
    query.answer()

    # Pide al usuario seleccionar la fecha
    query.edit_message_text(
        "Selecciona el día y la hora para tu cita.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Lunes 10:00 AM", callback_data='2025-04-10 10:00'),
            InlineKeyboardButton("Martes 2:00 PM", callback_data='2025-04-11 14:00')
        ]])
    )


def guardar_cita(update: Update, context: CallbackContext) -> None:
    """Guardar la cita y enviar confirmación."""
    query = update.callback_query
    fecha_cita = query.data
    user_id = query.from_user.id

    # Guardar cita en el diccionario
    citas_agendadas[user_id] = fecha_cita

    # Enviar mensaje de confirmación
    query.edit_message_text(f"Cita agendada para el {fecha_cita}. ¡Nos vemos pronto!")

    # Agendar recordatorio
    scheduler.add_job(recordatorio, SimpleTrigger(
        when=datetime.datetime.strptime(fecha_cita, '%Y-%m-%d %H:%M') - datetime.timedelta(days=1)),
                      args=[user_id, fecha_cita])


def recordatorio(user_id, fecha_cita):
    """Enviar un recordatorio un día antes de la cita."""
    bot = Bot(TOKEN)
    bot.send_message(
        chat_id=user_id,
        text=f"Recordatorio: Tu cita es mañana, {fecha_cita}. ¡No faltes!"
    )


def ver_citas(update: Update, context: CallbackContext) -> None:
    """Ver citas programadas."""
    user_id = update.callback_query.from_user.id
    cita = citas_agendadas.get(user_id, "No tienes citas programadas.")

    update.callback_query.edit_message_text(f"Tus citas programadas: {cita}")


def main():
    """Iniciar el bot y configurar los manejadores."""
    #updater = Updater(TOKEN)

    #dp = updater.dispatcher

    application = ApplicationBuilder().token(TOKEN).build()
    
    # Comandos básicos
    application.add_handler(CommandHandler("start", start))

    # Comandos básicos
    #dp.add_handler(CommandHandler("start", start))

    # Manejo de los botones de las opciones
    application.add_handler(CallbackQueryHandler(agendar_cita, pattern='^agendar_cita$'))
    application.add_handler(CallbackQueryHandler(guardar_cita, pattern=r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$'))
    application.add_handler(CallbackQueryHandler(ver_citas, pattern='^ver_citas$'))

    # Iniciar el bot
    application.run_polling()
    #updater.idle()


if __name__ == '__main__':
    main()    
