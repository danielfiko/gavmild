import logging
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, StringCommandHandler
from chat_api import read_secret, openai_api
import httpx
import json
from functools import wraps
import re


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def admin_only(view_function):
    @wraps(view_function)
    async def decorated_function( *args, **kwargs):
        update = args[0]
        context = args[1]
        if update.message.from_user.id != 79156661:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
            content = f"Forklar brukeren {update.message.from_user.first_name} at vedkommende ikke har tilstrekkelige rettigheter til å utføre handlingen."
            response = openai_api(content)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
            return
        return await view_function(*args, **kwargs)
    return decorated_function


def message_from_command(update):
    return re.split(r"\/\S+ ", update.message.text)[1]


async def make_request(method, endpoint, data=None):
    url = f'http://gavmild_backend:5005/telegram/{endpoint}'
    headers = {
        "Content-Type": "application/json",
        'X-Api-Key': read_secret("bot-api-token")
        }

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, data=json.dumps(data))
        print(response.text)

    return response


async def make_response_message(method, endpoint, data, message):
        response = await make_request(method, endpoint, data)

        if response.status_code == 200:
            data = response.json()
            return message.format(data["message"])
        elif response.status_code == 404:
            content = f"Skriv en kort feilmelding om at ønsket med det id-nummeret brukeren sendte inn ikke eksisterer."
            message = openai_api(content, "You are a friendly chat bot")
            return message
        else:
            content = f"Skriv en kort feilmelding om at du ikke fikk kontakt med tjenesten, Gavmild, og handlingen derfor ikke kunne utføres."
            message = openai_api(content, "You are a friendly chat bot")
            return message


async def request_prisjakt(url):
    pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args):
        data = {
        "chat_user_id": update.message.from_user.id,
        "chat_username": update.message.from_user.username,
        "identifier": context.args[0]
        }

        response = await make_request("POST", "connect-user", data)
        response_data = response.json()

        if response.status_code == 200:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Hei {update.message.from_user.first_name}! Du har blitt koblet til Gavmild-brukeren {response_data['username']}, og kan motta meldinger fra meg om aktivitet for denne brukeren.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Noe gikk dessverre galt.")  # Invalid API Key or the server encountered an error
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Greetings! 🌟 Welcome to our virtual space.")


async def suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    req_message = message_from_command(update)
    if not req_message:
        content = f"Brukeren {update.message.from_user.first_name} har brukt kommandoen /forslag feil. Forklar brukeren i korthet at riktig bruk er /forslag Dette er mitt forslag."
        response = openai_api(content)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return "ok"

    data = {
        "username": update.message.from_user.username,
        "id": update.message.from_user.id,
        "suggestion": req_message
    }

    response = await make_request("POST", "suggestion", data)

    if response.status_code == 200:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Takk {update.message.from_user.first_name}, forslaget har blitt lagt til!")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Noe gikk dessverre galt.")  # Invalid API Key or the server encountered an error


# async def show_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
#     response = await make_request("GET", "suggestions")
#     for item in response.json()["items"]:



@admin_only
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text='/slett <id>')
        return
    data = {
        "suggestion_id": context.args[0]
    }

    message = await make_response_message("DELETE", "suggestion", data, 'Forslaget "{}" har blitt utført og fjernet fra listen.')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


@admin_only
async def solve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text='/solve <id>')
        return
    data = {
        "suggestion_id": context.args[0]
    }
    
    message = await make_response_message("POST", "solve", data, 'Forslaget "{}" har blitt utført og fjernet fra listen.')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


@admin_only
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    response = await make_request("GET", "users")

    if response.status_code == 200:
        message = "Users:\n"
        for user in response.json().items():
            message += f"{user['id']}: {user['first_name']}\n"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Noe gikk dessverre galt.")  # Invalid API Key or the server encountered an error


async def get_reset_password_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    if update.message.chat.type != "private":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Denne kommandoen kan bare utføres i en privat chat med meg. Du kan enkelt starte en privat chat ved å klikke på navnet mitt.")
        return

    response = await make_request("GET", f"reset-token/{update.effective_chat.id}")

    if response.status_code == 200:
        data = response.json()
        message = f"Følg denne lenken for å bytte passord: https://gavmild.dfiko.no/bytt-passord/{data['token']}?name={data['name']}\n\nLenken utløper om 15 minutter."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    
    elif response.status_code ==  404:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Fant ingen bruker koblet til denne kontoen.")

    elif response.status_code == 429:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Hei! Jeg har allerede har sendt deg en lenke for å nullstille passordet ditt. Klikk på den og følg instruksjonene der for å fullføre prosessen.")
    
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Noe gikk dessverre galt. Prøv på nytt senere.")  # Invalid API Key or the server encountered an error
    
    return


async def hello_api(update: Update, context: ContextTypes.DEFAULT_TYPE):  
    response = await make_request("GET", "api/data")
    
    if response.status_code == 200:
        data = response.json()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=data["message"] + " " + str(update.effective_chat.id))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Noe gikk dessverre galt.")  # Invalid API Key or the server encountered an error


async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    response = openai_api(message_from_command(update), f"Du er en vennlig chatbot")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)


@admin_only
async def gpt_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = openai_api(message_from_command(update), f"Du er en vennlig chatbot")
    await context.bot.send_message(chat_id=read_secret("chat-group-id"), text=response)


@admin_only
async def message_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_message = message_from_command(update)
    await context.bot.send_message(chat_id=read_secret("chat-group-id"), text=input_message)


if __name__ == '__main__':
    application = ApplicationBuilder().token(read_secret("telegram-token")).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler("hello_api", hello_api))
    application.add_handler(CommandHandler("forslag", suggestion))
    application.add_handler(CommandHandler("slett", delete))
    application.add_handler(CommandHandler("solve", solve))
    application.add_handler(CommandHandler("gpt", gpt))
    application.add_handler(CommandHandler("gpt_group", gpt_to_group))
    application.add_handler(CommandHandler("msg_group", message_to_group))
    application.add_handler(CommandHandler("users", list_users))
    application.add_handler(CommandHandler("glemtpassord", get_reset_password_token))
    #application.add_handler(CommandHandler("vis_forslag", show_suggestions))

    application.run_polling()

