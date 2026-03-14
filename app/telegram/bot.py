import logging
from threading import Thread
from functools import wraps

from openai import OpenAI
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

logger = logging.getLogger(__name__)

sys_msg = (
    "You are a chatbot that reluctantly answers with a sarcastic responses, "
    "helping users with the correct use of chat commands. "
    "You do not ask if they need any further assistance."
)


def openai_api(flask_app, prompt, system_message=sys_msg, temp=1.0):
    client = OpenAI(api_key=flask_app.config["OPENAI_TOKEN"])
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=temp,
        max_tokens=512,
    )
    return response.choices[0].message.content


def admin_only(view_function):
    @wraps(view_function)
    async def decorated_function(*args, **kwargs):
        update = args[0]
        context = args[1]
        flask_app = context.bot_data["flask_app"]
        if update.message.from_user.id != flask_app.config["TELEGRAM_ADMIN_ID"]:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
            )
            content = (
                f"Forklar brukeren {update.message.from_user.first_name} at "
                f"vedkommende ikke har tilstrekkelige rettigheter til å utføre handlingen."
            )
            response = openai_api(flask_app, content)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
            return
        return await view_function(*args, **kwargs)

    return decorated_function


def message_from_command(context):
    return " ".join(context.args)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flask_app = context.bot_data["flask_app"]
    if context.args:
        from app.telegram.controllers import svc_connect_user
        with flask_app.app_context():
            result = svc_connect_user(
                chat_user_id=update.message.from_user.id,
                chat_username=update.message.from_user.username,
                identifier=context.args[0],
            )
        if result["ok"]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"Hei {update.message.from_user.first_name}! Du har blitt koblet til "
                    f"Gavmild-brukeren {result['username']}, og kan motta meldinger fra meg "
                    f"om aktivitet for denne brukeren."
                ),
            )
        elif result.get("not_found"):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Lenken er allerede brukt eller utløpt. Gå til Gavmild og hent en ny lenke.",
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="Noe gikk dessverre galt."
            )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Greetings! 🌟 Welcome to our virtual space."
        )


async def suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flask_app = context.bot_data["flask_app"]
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    req_message = message_from_command(context)
    if not req_message:
        content = (
            f"Brukeren {update.message.from_user.first_name} har brukt kommandoen /forslag feil. "
            f"Forklar brukeren i korthet at riktig bruk er /forslag Dette er mitt forslag."
        )
        response = openai_api(flask_app, content)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return

    from app.telegram.controllers import svc_add_suggestion
    with flask_app.app_context():
        ok = svc_add_suggestion(
            username=update.message.from_user.username,
            user_id=update.message.from_user.id,
            suggestion_text=req_message,
        )
    if ok:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Takk {update.message.from_user.first_name}, forslaget har blitt lagt til!",
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Noe gikk dessverre galt."
        )


@admin_only
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flask_app = context.bot_data["flask_app"]
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="/slett <id>")
        return

    from app.telegram.controllers import svc_delete_suggestion
    with flask_app.app_context():
        result = svc_delete_suggestion(context.args[0])

    if result["ok"]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Forslaget "{result["message"]}" har blitt utført og fjernet fra listen.',
        )
    elif result.get("not_found"):
        content = "Skriv en kort feilmelding om at ønsket med det id-nummeret brukeren sendte inn ikke eksisterer."
        msg = openai_api(flask_app, content, "You are a friendly chat bot")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    else:
        content = "Skriv en kort feilmelding om at du ikke fikk kontakt med tjenesten, Gavmild, og handlingen derfor ikke kunne utføres."
        msg = openai_api(flask_app, content, "You are a friendly chat bot")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


@admin_only
async def solve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flask_app = context.bot_data["flask_app"]
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="/solve <id>")
        return

    from app.telegram.controllers import svc_solve_suggestion
    with flask_app.app_context():
        result = svc_solve_suggestion(context.args[0])

    if result["ok"]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Forslaget "{result["message"]}" har blitt utført og fjernet fra listen.',
        )
    elif result.get("not_found"):
        content = "Skriv en kort feilmelding om at ønsket med det id-nummeret brukeren sendte inn ikke eksisterer."
        msg = openai_api(flask_app, content, "You are a friendly chat bot")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    else:
        content = "Skriv en kort feilmelding om at du ikke fikk kontakt med tjenesten, Gavmild, og handlingen derfor ikke kunne utføres."
        msg = openai_api(flask_app, content, "You are a friendly chat bot")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


@admin_only
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flask_app = context.bot_data["flask_app"]
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    from app.telegram.controllers import svc_get_users
    with flask_app.app_context():
        users = svc_get_users()

    if users is not None:
        message = "Users:\n" + "".join(f"{u['id']}: {u['first_name']}\n" for u in users)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Noe gikk dessverre galt."
        )


async def get_reset_password_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flask_app = context.bot_data["flask_app"]
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    if update.message.chat.type != "private":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Denne kommandoen kan bare utføres i en privat chat med meg. "
                "Du kan enkelt starte en privat chat ved å klikke på navnet mitt."
            ),
        )
        return

    from app.telegram.controllers import svc_get_reset_token
    with flask_app.app_context():
        result = svc_get_reset_token(update.effective_chat.id)

    if result["ok"]:
        token = result["token"]
        name = result["name"]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"Følg denne lenken for å bytte passord: "
                f"https://gavmild.dfiko.no/bytt-passord/{token}?name={name}\n\n"
                f"Lenken utløper om 15 minutter."
            ),
        )
    elif result.get("not_found"):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Fant ingen bruker koblet til denne kontoen.",
        )
    elif result.get("rate_limited"):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Hei! Jeg har allerede har sendt deg en lenke for å nullstille passordet ditt. "
                "Klikk på den og følg instruksjonene der for å fullføre prosessen."
            ),
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Noe gikk dessverre galt. Prøv på nytt senere.",
        )


async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flask_app = context.bot_data["flask_app"]
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    response = openai_api(flask_app, message_from_command(context), "Du er en vennlig chatbot")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)


@admin_only
async def gpt_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flask_app = context.bot_data["flask_app"]
    response = openai_api(flask_app, message_from_command(context), "Du er en vennlig chatbot")
    await context.bot.send_message(
        chat_id=flask_app.config["CHAT_GROUP_ID"], text=response
    )


@admin_only
async def message_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flask_app = context.bot_data["flask_app"]
    await context.bot.send_message(
        chat_id=flask_app.config["CHAT_GROUP_ID"],
        text=message_from_command(context),
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def start_bot(flask_app):
    token = flask_app.config.get("TELEGRAM_TOKEN")
    if not token:
        logger.warning("TELEGRAM_TOKEN not set — bot will not start.")
        return

    application = ApplicationBuilder().token(token).build()
    application.bot_data["flask_app"] = flask_app

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("forslag", suggestion))
    application.add_handler(CommandHandler("slett", delete))
    application.add_handler(CommandHandler("solve", solve))
    application.add_handler(CommandHandler("gpt", gpt))
    application.add_handler(CommandHandler("gpt_group", gpt_to_group))
    application.add_handler(CommandHandler("msg_group", message_to_group))
    application.add_handler(CommandHandler("users", list_users))
    application.add_handler(CommandHandler("glemtpassord", get_reset_password_token))

    def run():
        import asyncio

        async def _run():
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            await asyncio.Event().wait()  # run until the daemon thread is killed

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())

    thread = Thread(target=run, daemon=True, name="telegram-bot")
    thread.start()
    logger.info("Telegram bot started in background thread.")
