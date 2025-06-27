import logging
import datetime
import requests
import json
import asyncio
import os
from aiohttp import web
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    filters,
)

# ========= CONFIG =========
BOT_TOKEN = "7644996926:AAFAqmY7nz8riytHLKfkUGKjp5t6RO96wGo"
OWNER = "@BLADEXDEVELOPER"  # example: "@NR_CODEX"
API_URL = "https://godtufan-like.vercel.app//like?uid={uid}&server_name={region}&key=BHUPALI×GAGAN"
WEBHOOK_URL = "https://fearless-kanhaapi.onrender.com"
PORT = int(os.environ.get("PORT", 5000))
ADMIN_IDS = [6232302167]  # example: [123456789]
ALLOWED_GROUPS = {-1002352923608}  # example: {-1001234567890}
vip_users = {6232302167}
DEFAULT_DAILY_LIMIT = 30

# ========= STATE =========
allowed_groups = set(ALLOWED_GROUPS)
group_usage = {}
group_limits = {}
last_reset_date = {}
user_data = {}
promotion_message = ""
command_enabled = True

# ========= LOGGING =========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Log initial state
logger.info(f"Initialized ADMIN_IDS: {ADMIN_IDS}")
logger.info(f"Initialized ALLOWED_GROUPS: {ALLOWED_GROUPS}")
logger.info(f"Initialized vip_users: {vip_users}")

# ========= HELPERS =========
async def get_user_name(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        user = await context.bot.get_chat(user_id)
        return user.full_name or f"User {user_id}"
    except Exception as e:
        logger.error(f"Error getting user name for {user_id}: {e}")
        return f"User {user_id}"

def is_group(update: Update):
    return update.message.chat.type in ["group", "supergroup"]

def get_today():
    return datetime.date.today().strftime("%Y-%m-%d")

def reset_if_needed(group_id: int):
    today = datetime.date.today()
    if last_reset_date.get(group_id) != today:
        group_usage[group_id] = 0
        last_reset_date[group_id] = today

def get_limit(group_id: int):
    return group_limits.get(group_id, DEFAULT_DAILY_LIMIT)

def check_command_enabled(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not command_enabled and update.message.text != "/on":
            await update.message.reply_text("🚫 Commands are currently disabled.")
            logger.info(f"Commands disabled for user {update.effective_user.id}")
            return
        return await func(update, context)
    return wrapper

async def check_group_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        return True
    group_id = update.effective_chat.id
    logger.info(f"Checking group access for group_id: {group_id}, allowed_groups: {allowed_groups}")
    if group_id not in allowed_groups:
        await update.message.reply_text(
            "🚫 This bot can only be used in this group: https://t.me/+kmjgWZwLAaM5NDU9\n📞 Please contact the owner @nilay_vii"
        )
        logger.warning(f"Unauthorized group access attempt: {group_id}")
        return False
    return True

# ========= CORE COMMANDS =========
@check_command_enabled
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    logger.info(f"Received /start from user {update.effective_user.id}")
    await update.message.reply_text("👋 Welcome! Use /like ind <uid> to get Free Fire likes.")

@check_command_enabled
async def gay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    await update.message.reply_text("I know you're gay 😁")

@check_command_enabled
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    help_text = """
📘 HELP MENU

🔹 Like Bot Commands:
/like <region> <uid> - Send likes
/check - Your usage today
/groupstatus - Group usage stats
/remain - Today's user count
/gay - Fun command

🔹 User Management:
/userinfo <user_id> - Get user details
/stats - Usage statistics
/feedback <msg> - Send feedback

🔹 System:
/status - Bot status
/on - Enable Bot (Admin)
/off - Disable Bot (Admin)

👑 Owner: {OWNER}
"""
    await update.message.reply_text(help_text)

@check_command_enabled
async def open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Received /open from user {user_id}, ADMIN_IDS: {ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        logger.warning(f"Unauthorized /open attempt by user {user_id}")
        return
    admin_menu = """
📘 ADMIN TOOLS

🔹 Admin Tools:
/allow <group_id> - Allow group
/remove <group_id> - Remove group
/setremain <number> - Set group limit
/groupreset - Reset group usage
/broadcast <msg> - Global broadcast
/send <msg> - Send to VIPs & groups
/setadmin [user_id] or reply to user
/removeadmin [user_id] or reply to user
/adminlist - Show admins with names

🔹 VIP Management:
/setvip <user_id> - Add VIP
/removevip <user_id> - Remove VIP
/viplist - Show VIP users
/setpromotion <text> - Set promo msg

🔹 System:
/on - Enable commands
/off - Disable Commands
"""
    await update.message.reply_text(admin_menu)

# ========= BROADCAST COMMANDS =========
@check_command_enabled
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /broadcast <message>")
        return
    text = " ".join(context.args)
    sent = 0
    failed = 0
    msg = await update.message.reply_text("📢 Broadcasting started...")
    for user_id in set(user_data.keys()):
        try:
            await context.bot.send_message(user_id, text)
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Error broadcasting to user {user_id}: {e}")
        await asyncio.sleep(0.1)
    for group_id in allowed_groups:
        try:
            await context.bot.send_message(group_id, text)
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Error broadcasting to group {group_id}: {e}")
        await asyncio.sleep(0.1)
    await msg.edit_text(f"📢 Broadcast Complete!\n\n✅ Sent: {sent}\n❌ Failed: {failed}")

@check_command_enabled
async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in vip_users:
        await update.message.reply_text("⛔ Unauthorized")
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Please provide a message to send.")
        return
    success_users = []
    success_groups = []
    failed_users = []
    failed_groups = []
    for user_id in set(vip_users):
        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else user.full_name
            await context.bot.send_message(user_id, text)
            success_users.append(f"{username} (ID: {user_id})")
        except Exception as e:
            failed_users.append(f"User {user_id}")
            logger.error(f"Error sending to VIP user {user_id}: {e}")
    for group_id in set(allowed_groups):
        try:
            chat = await context.bot.get_chat(group_id)
            group_name = chat.title or f"Group {group_id}"
            await context.bot.send_message(group_id, text)
            success_groups.append(f"{group_name} (ID: {group_id})")
        except Exception as e:
            failed_groups.append(f"Group {group_id}")
            logger.error(f"Error sending to group {group_id}: {e}")
    response = "📢 Message Delivery Report\n\n"
    if success_users:
        response += f"✅ Sent to {len(success_users)} users:\n" + "\n".join(success_users) + "\n\n"
    if success_groups:
        response += f"✅ Sent to {len(success_groups)} groups:\n" + "\n".join(success_groups) + "\n\n"
    if failed_users:
        response += f"❌ Failed to send to {len(failed_users)} users:\n" + "\n".join(failed_users) + "\n\n"
    if failed_groups:
        response += f"❌ Failed to send to {len(failed_groups)} groups:\n" + "\n".join(failed_groups)
    await update.message.reply_text(response[:4000])

# ========= ADMIN TOOLS =========
@check_command_enabled
async def userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    user_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else (
        int(context.args[0]) if context.args else None)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user or provide user_id")
        return
    try:
        user = await context.bot.get_chat(user_id)
        is_vip = "✅" if user_id in vip_users else "❌"
        is_admin = "✅" if user_id in ADMIN_IDS else "❌"
        await update.message.reply_text(
            f"👤 User Information\n\n"
            f"🆔 ID: {user.id}\n"
            f"📛 Name: {user.full_name}\n"
            f"🔗 Username: @{user.username if user.username else 'N/A'}\n"
            f"👑 VIP: {is_vip}\n"
            f"🛡️ Admin: {is_admin}\n"
            f"📅 Last Active: {user_data.get(user_id, {}).get('date', 'Never')}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

@check_command_enabled
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    today = get_today()
    active_users = sum(1 for data in user_data.values() if data.get('date') == today)
    await update.message.reply_text(
        f"📊 Bot Status\n\n"
        f"👥 Total Users: {len(user_data)}\n"
        f"📅 Active Today: {active_users}\n"
        f"👑 VIP Users: {len(vip_users)}\n"
        f"🛡️ Admins: {len(ADMIN_IDS)}\n"
        f"💬 Allowed Groups: {len(allowed_groups)}\n"
        f"⏰ Last Reset: {last_reset_date.get('last', 'Never')}"
    )

@check_command_enabled
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    today = datetime.date.today().strftime("%Y-%m-%d")
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    daily_users = {}
    for data in user_data.values():
        date = data.get('date')
        if date:
            daily_users[date] = daily_users.get(date, 0) + 1
    await update.message.reply_text(
        f"📈 Usage Statistics\n\n"
        f"📅 Today: {daily_users.get(today, 0)} users\n"
        f"📅 Last 7 Days: {sum(count for date, count in daily_users.items() if date >= week_ago)}\n"
        f"📅 All Time: {len(user_data)} users\n"
        f"👑 VIP Users: {len(vip_users)}\n"
        f"💬 Active Groups: {len(allowed_groups)}"
    )

# ========= USER COMMANDS =========
@check_command_enabled
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /feedback <your message>")
        return
    feedback_text = " ".join(context.args)
    user = update.effective_user
    feedback_msg = (
        f"📢 New Feedback\n\n"
        f"👤 From: {user.full_name}\n"
        f"🆔 ID: {user.id}\n"
        f"📝 Message: {feedback_text}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, feedback_msg)
        except Exception as e:
            logger.error(f"Error sending feedback to admin {admin_id}: {e}")
    await update.message.reply_text("✅ Thank you for your feedback!")

@check_command_enabled
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    user_id = update.effective_user.id
    today = get_today()
    user_info = user_data.get(user_id, {})
    user_date = user_info.get("date")
    count = user_info.get("count", 0)
    status = "UNLIMITED (VIP)" if user_id in vip_users else (
        f"{count}/1 ✅ Used" if user_date == today else "0/1 ❌ Not Used"
    )
    await update.message.reply_text(
        f"👤 DEAR {update.effective_user.first_name}, YOUR STATUS\n\n"
        f"🎯 FREE REQUEST: {status}\n"
        f"👑 OWNER: {OWNER}"
    )

@check_command_enabled
async def setpromotion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in vip_users:
        await update.message.reply_text("⛔ Unauthorized")
        return
    global promotion_message
    promotion_message = " ".join(context.args)
    await update.message.reply_text("✅ Promotion Updated!")

@check_command_enabled
async def like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    if not is_group(update):
        return
    group_id = update.effective_chat.id
    if group_id not in allowed_groups:
        return
    reset_if_needed(group_id)
    used = group_usage.get(group_id, 0)
    limit = get_limit(group_id)
    if used >= limit:
        await update.message.reply_text("❌ Group daily like limit reached!")
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("⚠️ Usage: /like ind <uid>")
        return
    processing_msg = await update.message.reply_text("⏳ Processing your request...")
    region, uid = args
    user_id = update.effective_user.id
    today = get_today()
    is_vip = user_id in vip_users
    if not is_vip:
        user_info = user_data.get(user_id, {})
        if user_info.get("date") == today and user_info.get("count", 0) >= 1:
            await processing_msg.edit_text("⛔ You have used your free like today 📞 Please contact @Nilay_OK.")
            return
        user_data[user_id] = {"date": today, "count": user_info.get("count", 0)}
    try:
        api_url = API_URL.format(uid=uid, region=region)
        logger.info(f"Calling API: {api_url}")
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"API response for UID {uid}: {data}")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            logger.error(f"API returned 404 for UID {uid}: Endpoint not found")
            await processing_msg.edit_text("🚨 Like service is currently unavailable (API not found). Please try again later or contact @NR_CODEX.")
            return
        logger.error(f"API HTTP error for UID {uid}: {e}")
        await processing_msg.edit_text("🚨 API Error! Try again later.")
        return
    except Exception as e:
        logger.error(f"API error for UID {uid}: {e}")
        await processing_msg.edit_text("🚨 API Error! Try again later.")
        return
    required_keys = ["PlayerNickname", "UID", "LikesbeforeCommand", "LikesafterCommand", "LikesGivenByAPI", "status"]
    if not all(key in data for key in required_keys):
        await processing_msg.edit_text("⚠️ Invalid UID or unable to fetch details. 🙁 Please check UID or try again later.")
        logger.warning(f"Incomplete API response for UID {uid}: {data}")
        return
    # Updated status check for status 1 or 2
    if data.get("status") not in [1, 2]:
        await processing_msg.edit_text(f"⚠️ Invalid response status: {data.get('status')}. Please try again or contact @NR_CODEX.")
        logger.warning(f"Invalid status {data.get('status')} for UID {uid}")
        return
    if data.get("LikesGivenByAPI") == 0 or data.get("LikesbeforeCommand") == data.get("LikesafterCommand"):
        await processing_msg.edit_text("⚠️ UID has already reached max likes today or no likes added.")
        logger.info(f"No likes added for UID {uid}: {data}")
        return
    if not is_vip:
        user_data[user_id]["count"] += 1
    group_usage[group_id] = group_usage.get(group_id, 0) + 1
    text = (
        f"✅ Like Sent Successfully! (Status: {data.get('status')})\n\n"
        f"👤 Name: {data['PlayerNickname']}\n"
        f"🆔 UID: {data['UID']}\n"
        f"🌍 Server: {region.upper()}\n"
        f"😭 Before: {data['LikesbeforeCommand']}\n"
        f"☠️ After: {data['LikesafterCommand']}\n"
        f"😊 Given: {data['LikesGivenByAPI']}\n"
        f"🔥 OWNER: @NR_CODEX"
    )
    if promotion_message:
        text += f"\n\n📢 {promotion_message}"
    try:
        user_photos = await context.bot.get_user_profile_photos(user_id, limit=1)
        if user_photos.total_count > 0:
            photo_file = await user_photos.photos[0][-1].get_file()
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo_file.file_id,
                caption=text,
                reply_to_message_id=update.message.message_id
            )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text(text)
    except Exception as e:
        logger.error(f"Error handling photo for user {user_id}: {e}")
        await processing_msg.edit_text(text)

@check_command_enabled
async def groupstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    if not is_group(update):
        return
    group_id = update.effective_chat.id
    count = group_usage.get(group_id, 0)
    await update.message.reply_text(
        f"📊 Group Usage Status\n\n"
        f"🆔 Group ID: {group_id}\n"
        f"✅ Likes used today: {count}/{get_limit(group_id)}\n"
        f"⏰ Reset: 4:30 AM daily"
    )

@check_command_enabled
async def remain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    today = get_today()
    used_users = [uid for uid, data in user_data.items() if data.get("date") == today]
    await update.message.reply_text(
        f"📊 Today's Usage\n\n"
        f"✅ Users used likes: {len(used_users)}\n"
        f"📅 Date: {today}"
    )

@check_command_enabled
async def allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized command usage.")
        return
    if not is_group(update):
        await update.message.reply_text("⚠️ This command can only be used in groups.")
        return
    try:
        gid = int(context.args[0]) if context.args else update.effective_chat.id
        allowed_groups.add(gid)
        logger.info(f"Added group {gid} to allowed_groups: {allowed_groups}")
        await update.message.reply_text(f"✅ Group {gid} allowed.")
    except Exception as e:
        logger.error(f"Error in allow command: {e}")
        await update.message.reply_text("⚠️ Invalid group ID or usage. Use /allow or /allow <group_id>.")

@check_command_enabled
async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized command usage.")
        return
    try:
        gid = int(context.args[0])
        allowed_groups.discard(gid)
        logger.info(f"Removed group {gid} from allowed_groups: {allowed_groups}")
        await update.message.reply_text(f"❌ Group {gid} removed.")
    except Exception as e:
        logger.error(f"Error in remove command: {e}")
        await update.message.reply_text("⚠️ Invalid group ID.")

@check_command_enabled
async def groupreset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    group_usage.clear()
    await update.message.reply_text("✅ Group usage reset!")

@check_command_enabled
async def setremain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized command usage.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Usage: /setremain <number>")
        return
    group_id = update.effective_chat.id
    group_limits[group_id] = int(context.args[0])
    await update.message.reply_text(f"✅ Daily group limit set to: {context.args[0]} likes.")

@check_command_enabled
async def autogroupreset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    await update.message.reply_text("✅ Group auto-resumes is active. Runs daily at 4:30 AM.")

@check_command_enabled
async def setvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    replied_user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    user_id = replied_user.id if replied_user else (int(context.args[0]) if context.args else None)
    if not user_id:
        await update.message.reply_text("⚠️ Usage: Reply to a user with `/setvip` OR use `/setvip <user_id>`")
        return
    if user_id in vip_users:
        name = await get_user_name(context, user_id)
        await update.message.reply_text(f"✅ {name} is already a VIP.")
    else:
        vip_users.add(user_id)
        name = await get_user_name(context, user_id)
        await update.message.reply_text(f"✅ {name} (ID: {user_id}) has been added to VIP list.")

@check_command_enabled
async def removevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    replied_user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    user_id = replied_user.id if replied_user else (int(context.args[0]) if context.args else None)
    if not user_id:
        await update.message.reply_text("⚠️ Usage: Reply to a user with `/removevip` OR use `/removevip <user_id>`")
        return
    if user_id in vip_users:
        vip_users.remove(user_id)
        name = await get_user_name(context, user_id)
        await update.message.reply_text(f"✅ {name} (ID: {user_id}) removed from VIP list.")
    else:
        await update.message.reply_text("❌ User is not in VIP list.")

@check_command_enabled
async def viplist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    if not vip_users:
        await update.message.reply_text("❌ No VIP users.")
        return
    vip_list = []
    for user_id in vip_users:
        name = await get_user_name(context, user_id)
        vip_list.append(f"👑 {name} (ID: {user_id})")
    await update.message.reply_text("🌟 VIP Users:\n" + "\n".join(vip_list))

@check_command_enabled
async def setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    replied_user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    user_id = update.message.reply_to_message.from_user.id if replied_user else (int(context.args[0]) if context.args else None)
    if not user_id:
        await update.message.reply_text("⚠️ Usage: Reply to a user with `/setadmin` OR use `/setadmin <user_id>`")
        return
    if user_id in ADMIN_IDS:
        name = await get_user_name(context, user_id)
        await update.message.reply_text(f"✅ {name} is already an admin.")
    else:
        ADMIN_IDS.append(user_id)
        name = await get_user_name(context, user_id)
        await update.message.reply_text(f"✅ {name} (ID: {user_id}) added to admin list.")

@check_command_enabled
async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    replied_user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    user_id = replied_user.id if replied_user else (int(context.args[0]) if context.args else None)
    if not user_id:
        await update.message.reply_text("⚠️ Usage: Reply to a user with `/removeadmin` OR use `/removeadmin <user_id>`")
        return
    if user_id in ADMIN_IDS:
        ADMIN_IDS.remove(user_id)
        name = await get_user_name(context, user_id)
        await update.message.reply_text(f"✅ {name} (ID: {user_id}) removed from admin list.")
    else:
        await update.message.reply_text("❌ User is not an admin.")

@check_command_enabled
async def adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group_access(update, context):
        return
    if not ADMIN_IDS:
        await update.message.reply_text("❌ No admins.")
        return
    admin_list = []
    for user_id in ADMIN_IDS:
        name = await get_user_name(context, user_id)
        admin_list.append(f"🦅 {name} (ID: {user_id})")
    await update.message.reply_text("🔐 Admins:\n" + "\n".join(admin_list))

@check_command_enabled
async def off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    global command_enabled
    command_enabled = False
    await update.message.reply_text("⛔ All commands disabled.")

@check_command_enabled
async def on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    global command_enabled
    command_enabled = True
    await update.message.reply_text("✅ Commands are now enabled.")

# ========= AUTO RESET TASK =========
async def reset_group_usage_task():
    while True:
        try:
            now = datetime.now()
            reset_time = now.replace(hour=4, minute=30, second=0, microsecond=0)
            if now >= reset_time:
                reset_time += datetime.timedelta(days=1)
            wait_seconds = (reset_time - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            group_usage.clear()
            logger.info("✅ Group like limits reset at 4:30 AM")
        except Exception as e:
            logger.error(f"Error in reset task: {e}")
            await asyncio.sleep(60)

# ========= WEBHOOK SETUP =========
async def webhook_handler(request: web.Request):
    try:
        app = request.app['telegram_app']
        update = Update.de_json(await request.json(), app.bot)
        await app.process_update(update)
        logger.info("Webhook update processed successfully")
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}")
        return web.Response(status=500)

async def health_check(request: web.Request):
    logger.info("Health check requested")
    return web.Response(text="Bot is running", status=200)

async def set_webhook():
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

def setup_application():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gay", gay))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("open", open))
    app.add_handler(CommandHandler("like", like))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("setpromotion", setpromotion))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("send", send))
    app.add_handler(CommandHandler("groupstatus", groupstatus))
    app.add_handler(CommandHandler("remain", remain))
    app.add_handler(CommandHandler("userinfo", userinfo))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("allow", allow))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("groupreset", groupreset))
    app.add_handler(CommandHandler("setremain", setremain))
    app.add_handler(CommandHandler("autogroupreset", autogroupreset))
    app.add_handler(CommandHandler("setvip", setvip))
    app.add_handler(CommandHandler("removevip", removevip))
    app.add_handler(CommandHandler("viplist", viplist))
    app.add_handler(CommandHandler("setadmin", setadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("adminlist", adminlist))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(CommandHandler("off", off))
    app.add_handler(CommandHandler("on", on))
    return app

async def main():
    logger.info("Starting bot...")
    telegram_app = setup_application()
    web_app = web.Application()
    web_app['telegram_app'] = telegram_app
    web_app.router.add_post('/', webhook_handler)
    web_app.router.add_get('/health', health_check)
    await set_webhook()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Webhook server running on port {PORT}")
    await telegram_app.initialize()
    telegram_app.create_task(reset_group_usage_task())
    await asyncio.Event().wait()

if __name__ == "__main__":
    if not all([BOT_TOKEN, WEBHOOK_URL]):
        logger.error("Missing required environment variables: BOT_TOKEN or WEBHOOK_URL")
        exit(1)
    asyncio.run(main())
