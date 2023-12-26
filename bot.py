import os
import requests
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Retrieve bot token and client list from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_LIST_STRING = os.getenv("CLIENT_LIST")
CHANNEL_ID = os.getenv("CHANNEL_ID")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 6))

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not CLIENT_LIST_STRING:
    raise ValueError("BOT_TOKEN and CLIENT_LIST environment variables must be set.")

# Parse client list from environment variable string
CLIENT_LIST = eval(CLIENT_LIST_STRING)

# Log each request
def log_request(func):
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        user_name = update.effective_user.username
        command = context.args[0] if context.args else update.message.text.split()[0][1:]
        logger.info(f"Received command '{command}' from user {user_name} (ID: {user_id})")
        return func(update, context, *args, **kwargs)

    return wrapper

def get_revision_info(url, client):
    endpoint = f"{url}/ibc/core/client/v1/client_states/{client}"
    response = requests.get(endpoint)
    
    if response.status_code == 200:
        data = response.json()
        revision_number = data['client_state']['latest_height']['revision_number']
        revision_height = data['client_state']['latest_height']['revision_height']
        trusting_period = data['client_state']['trusting_period']
        trusting_period = int(trusting_period.rstrip('s'))
        chain_id = data['client_state']['chain_id']

        return revision_number, revision_height, trusting_period, chain_id
    else:
        raise Exception(f"Failed to get revision information. Status code: {response.status_code}")

def get_timestamp(url, client, revision_number, revision_height):
    endpoint = f"{url}/ibc/core/client/v1/consensus_states/{client}/revision/{revision_number}/height/{revision_height}"
    response = requests.get(endpoint)
    
    if response.status_code == 200:
        data = response.json()
        timestamp = data['consensus_state']['timestamp']
        return timestamp
    else:
        raise Exception(f"Failed to get timestamp information. Status code: {response.status_code}")

def calculate_time_left(url, client):
    try:
        revision_number, revision_height, trusting_period, _ = get_revision_info(url, client)
        timestamp_str = get_timestamp(url, client, revision_number, revision_height)
        timestamp_str = timestamp_str.split('.')[0] + "Z"
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        expiration_time = timestamp + timedelta(seconds=trusting_period)
        time_left = expiration_time - datetime.utcnow()

        return time_left
    except Exception as e:
        return f"Error: {e}"
    
def days_hours_minutes(td):
    return td.days, td.seconds//3600, (td.seconds//60)%60

@log_request
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Bot has started! Use the /client_status command to check the status of clients.")

@log_request
def status(update: Update, context: CallbackContext) -> None:
    response_message = ""
    for client, url in CLIENT_LIST:
        _, _, _, chain_id = get_revision_info(url, client)
        time_left = calculate_time_left(url, client)
        days, hours, minutes = days_hours_minutes(time_left)
        if isinstance(time_left, timedelta):
            response_message += f"- Source: {url}, Client: *{client}*, Counterparty: *{chain_id}*, Time left until expiration: *{days}* days + *{hours}* hours + *{minutes}* minutes.\n"
        else:
            response_message += f"Client: {client}, {time_left}\n"

    update.message.reply_markdown(response_message)

@log_request
def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Welcome to the Bot!\n\n"
        "Available commands:\n"
        "/start - Start the bot and get a welcome message.\n"
        "/client_status - Check the status of clients.\n"
        "/help - Get help with available commands."
    )
    update.message.reply_text(help_text)

def alert(context: CallbackContext) -> None:
    for client, url in CLIENT_LIST:
        _, _, _, chain_id = get_revision_info(url, client)
        time_left = calculate_time_left(url, client)
        
        if isinstance(time_left, timedelta) and time_left < timedelta(days=2):
            alert_message = f"- Alert! Client: {client}, Chain ID: {chain_id}, will be expired after {time_left}"
            context.bot.send_message(chat_id=CHANNEL_ID, text=alert_message)


def main():
    updater = Updater(BOT_TOKEN, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("client_status", status))
    dp.add_handler(CommandHandler("help", help_command))

    updater.start_polling(poll_interval=POLL_INTERVAL)

     # Run the alert function every 12 hours
    updater.job_queue.run_repeating(alert, interval=43200, first=0, context=None)

    updater.idle()

if __name__ == '__main__':
    main()