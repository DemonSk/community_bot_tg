import logging
import html
import json
import traceback
import os
from time import sleep

from telegram import Update
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ChatMemberHandler
from dotenv import load_dotenv
from datetime import date

load_dotenv()


# Introduction checks
INTRODUCTION_TIMEOUT = 20
INTRODUCTION_TRIES = 3

# Introduction handlers
LEFT, INTRODUCE, WRONG_INTRODUCE, INTRODUCED = range(4)

# Users intro object
# key - user_id, [intro_tries, job_name, messages to delete...]
USERS_INTRO = {}

# Files name for information store
FILE_NAME = 'user_info.json'
LINKS_FILE = 'links.json'


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


                                                ### ERROR HANDLER ###
# Send errors to console
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    await context.bot.send_message(
        chat_id=os.getenv("DEVELOPER_CHAT_ID"), text=message, parse_mode=ParseMode.HTML
    )


                                                ### COMMANDS ###
# Basic start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello!, this bot only useful to greed "
                                                                          "users in group")


# Command to get messages from group
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    try:
        data = get_users_data()
        user_data = data[str(user_id)]
    except KeyError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Sorry, I don't have information about [{first_name}](tg://user?id={user_id}). For now, I can only share stats only for the newcomers joined from 11.08.2023", parse_mode=ParseMode.MARKDOWN)
        return
    today = date.today()
    date_formatted_today = today.strftime("%d-%m-%Y")
    user_messages = user_data['messages']
    user_social_rating = user_data['social_rating']
    user_joined = user_data['joined']
    # joined_in_days = date_formatted_today - datetime(user_joined)
    # print(joined_in_days)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"[{first_name}](tg://user?id={user_id}), your stats in this group:\n\nMessages: {user_messages}\nSocial rating: {user_social_rating} (feature in progress)\nJoined group: {user_joined}", parse_mode=ParseMode.MARKDOWN)


                                                ### MAIN FUNCTIONS ###
# Main function to greet new members
async def greet_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status = update.chat_member.new_chat_member.status
    # If user is left or banned or bot -> do nothing
    if status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
        return
    if update.chat_member.new_chat_member.user.is_bot:
        return

    # get user info for greet message
    first_name = update.chat_member.new_chat_member.user.first_name
    user_id = update.chat_member.new_chat_member.user.id

    try:
        data = get_users_data()
        data[str(user_id)]
        print("old user")
        return
    except Exception:
        print("new user")

    # wait 2 seconds before send greet message
    sleep(2)

    # send greet message
    message = await update.effective_chat.send_message(f"Hi [{first_name}](tg://user?id={user_id})\\, \n\nWelcome to "
                                                       f"the KyivEthereum community 🤗 \n\nPlease send an "
                                                       f"introduction *__within next 1 hour__* with the following "
                                                       f"information, otherwise we will be forced to remove you from "
                                                       f"the chat 😔: \n\n1\\. *_Name_* \n2\\. *_Company_* \n3\\. "
                                                       f"*_Who invited you to the group OR how you find it_* \n4\\. "
                                                       f"*_Expectations from the community_* \n5\\. *_How can you "
                                                       f"help, contribute to the community_* \n6\\. *_Put the hashtag "
                                                       f"\\#kyiv\\_ethereum\\_community\\_intro_*",
                                                       parse_mode=ParseMode.MARKDOWN_V2,
                                                       )

    # remove job if user left
    _remove_job_if_exists(str(user_id), context)
    context.job_queue.run_once(_timeout, INTRODUCTION_TIMEOUT, chat_id=update.chat_member.chat.id, name=str(
        user_id), data=user_id)
    USERS_INTRO[user_id] = [0, user_id, message.id]
    print(USERS_INTRO)


# Checks message for proper user introduction
# Sends message about problems in introduction
# User have 3 tries before kick from group
# @Dev: Also listens to all messages
async def user_intro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"\n\n{update}\n\n")
    user_id = update.effective_user.id
    if user_id not in list(USERS_INTRO.keys()):
        data = get_users_data()
        if update.message.chat_id == os.getenv("CHAT_ID"):
            try:
                user_data = data[str(user_id)]
                user_data["messages"] += 1
                with open(FILE_NAME, 'w') as file:
                    json.dump(data, file, indent=4)
                print("message added")
            except Exception:
                print("User is not in user_info file")
            return
        else:
            print("User sends message not in main channel")
            return
    if update.message.new_chat_members:
        print("User joined the channel")
        return
    if update.effective_user.is_bot:
        print("New User is a bot")
        return
    if update.message.left_chat_member:
        print("User left the channel")
        return
    introduction_text = update.message.text
    print(len(introduction_text))
    if "#kyiv_ethereum_community_intro" in introduction_text.lower():
        if len(introduction_text) > 50:
            _remove_job_if_exists(str(user_id), context)
            await _save_user_info(update, context)
            return
        else:
            await context.bot.delete_message(update.message.chat_id, update.message.message_id)
            message = await update.effective_chat.send_message("It seems introduction is not full. Please write as "
                                                               "shown in the example.")
            user_intro = USERS_INTRO[user_id]
            user_intro.append(message.id)
            user_tries = user_intro[0]
            user_intro[0] = user_tries + 1
            USERS_INTRO[user_id] = user_intro
            if USERS_INTRO[user_id][0] == INTRODUCTION_TRIES:
                await context.bot.delete_message(update.message.chat_id, update.message.message_id)
                await _remove_user(update, context)
                return
    else:
        await context.bot.delete_message(update.message.chat_id, update.message.message_id)
        message = await update.effective_chat.send_message("Hashtag #kyiv_ethereum_community_intro is absent, please "
                                                           "add one.")
        user_intro = USERS_INTRO[user_id]
        user_intro.append(message.id)
        user_tries = user_intro[0]
        user_intro[0] = user_tries + 1
        USERS_INTRO[user_id] = user_intro
        if USERS_INTRO[user_id][0] == INTRODUCTION_TRIES:
            await context.bot.delete_message(update.message.chat_id, update.message.message_id)
            await _remove_user(update, context)
            return
        return


                                                ### INTERNAL FUNCTIONS ####
# Remove user in case of 3 tries
async def _remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    messages = USERS_INTRO[user_id][2:]
    for message in messages:
        await context.bot.delete_message(update.effective_chat.id, message)
    USERS_INTRO.pop(user_id)
    try:
        _remove_job_if_exists(str(user_id), context)
        await context.bot.ban_chat_member(update.effective_chat.id, user_id)
        await context.bot.unban_chat_member(update.effective_chat.id, user_id)
    except Exception:
        print("user could left chat")
    print(f"({user_id}) removed due 3 tries")
    print(USERS_INTRO)
    return True


# Remove user in case of inactivity to send introduction message
async def _timeout(context: ContextTypes.DEFAULT_TYPE) -> bool:
    job = context.job
    user_id = job.data
    messages = USERS_INTRO[user_id][2:]
    for message in messages:
        await context.bot.delete_message(job.chat_id, message)
    USERS_INTRO.pop(user_id)
    try:
        _remove_job_if_exists(str(user_id), context)
        await context.bot.ban_chat_member(job.chat_id, user_id)
        await context.bot.unban_chat_member(job.chat_id, user_id)
    except Exception:
        print("user could left chat")
    print(f"({user_id}) removed due timeout")
    print(USERS_INTRO)
    return True


# Save user introduction message to json file (TODO: make it work with Data Base)
async def _save_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    messages = USERS_INTRO[user_id][2:]
    for message in messages:
        await context.bot.delete_message(update.effective_chat.id, message)
    USERS_INTRO.pop(user_id)

    _add_user_info(update.effective_user.first_name,
                  user_id, update.message.text)

    return True


# Remove job with given name. Returns whether job was removed.
def _remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


# Add user info to json file
def _add_user_info(username, user_id, introduction_message, filename='user_info.json'):
    try:
        # Load existing data from the JSON file
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}

    # get date and format it to day-month-year like 22-11-2024
    today = date.today()
    date_formatted = today.strftime("%d-%m-%Y")
    joined_date = str(date_formatted)
    # Add the new user information to the data
    new_user = {'username': username, 'user_id': user_id,
                'introduction': introduction_message, 'joined': joined_date, 'social_rating': 0, "messages": 0}

    # Write user info with id as key
    data[str(user_id)] = new_user

    # Write the updated data back to the JSON file
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

    print(f"User '{username}' with ID '{user_id}' added successfully.")


                                                ### GETTERS ###
# Get user info from json file
def get_users_data(filename='user_info.json') -> object:
    try:
        # Load existing data from the JSON file
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}

    return data


if __name__ == '__main__':
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).read_timeout(7).get_updates_read_timeout(42).build()

    start_handler = CommandHandler('start', start)
    stats_command_handler = CommandHandler('stats', stats)
    new_member_handler = ChatMemberHandler(
        greet_chat_members, ChatMemberHandler.CHAT_MEMBER)
    user_intro_handler = MessageHandler(filters.ALL, user_intro)

    application.add_handler(start_handler)
    application.add_handler(stats_command_handler)
    application.add_handler(new_member_handler)
    application.add_handler(user_intro_handler)

    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)
