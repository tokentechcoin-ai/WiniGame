import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes
import json
from datetime import datetime
import os

# कॉन्फिगरेशन
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your actual token
GAME_WEBAPP_URL = "https://lcrscan.com/winiGame/"
API_KEY = "699c31f616cf06eec2a4d053"

# लॉगिंग
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# डेटा फ़ाइल
DATA_FILE = "user_data.json"

def load_data():
    """लोड यूजर डेटा फ़ाइल से"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                
                # कन्वर्ट करें dict से UserData ऑब्जेक्ट में
                users = {}
                for user_id, user_info in data.items():
                    user = UserData(
                        user_id=int(user_id),
                        username=user_info['username'],
                        referred_by=user_info.get('referred_by')
                    )
                    user.balance = user_info.get('balance', 1)
                    user.games_played = user_info.get('games_played', 0)
                    user.joined_date = user_info.get('joined_date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    user.referral_count = user_info.get('referral_count', 0)
                    user.referral_earnings = user_info.get('referral_earnings', 0)
                    users[int(user_id)] = user
                return users
    except Exception as e:
        logger.error(f"Error loading data: {e}")
    return {}

def save_data(users):
    """सेव यूजर डेटा फ़ाइल में"""
    try:
        data = {}
        for user_id, user in users.items():
            data[str(user_id)] = {
                'username': user.username,
                'balance': user.balance,
                'games_played': user.games_played,
                'joined_date': user.joined_date,
                'referred_by': user.referred_by,
                'referral_count': user.referral_count,
                'referral_earnings': user.referral_earnings
            }
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return False

# यूजर डेटा लोड करें
users_data = load_data()

class UserData:
    def __init__(self, user_id, username, referred_by=None):
        self.user_id = user_id
        self.username = username
        self.balance = 1
        self.games_played = 0
        self.joined_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.referred_by = referred_by
        self.referral_count = 0
        self.referral_earnings = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # चेक करें कि रेफरल कोड के साथ शुरू किया है या नहीं
    args = context.args
    referred_by = None
    
    # Check if this is a new user
    is_new_user = user_id not in users_data
    
    # Process referral if this is a new user and has referral in args
    if args and args[0].isdigit() and is_new_user:
        referred_by = int(args[0])
        logger.info(f"New user {user_id} referred by {referred_by}")
        
        # Don't allow self-referral
        if referred_by == user_id:
            referred_by = None
            logger.info(f"User {user_id} tried to self-refer")
    
    # Create or get user
    if is_new_user:
        users_data[user_id] = UserData(user_id, user.username or user.first_name, referred_by)
        
        # Give referral bonus if referred
        if referred_by and referred_by in users_data:
            # Bonus for referrer
            users_data[referred_by].balance += 0.1
            users_data[referred_by].referral_count += 1
            users_data[referred_by].referral_earnings += 0.1
            
            # Bonus for new user
            users_data[user_id].balance += 0.05
            
            # Save data immediately
            save_data(users_data)
            
            # Notify referrer
            try:
                await context.bot.send_message(
                    referred_by,
                    f"🎉 **New Referral!** 🎉\n\n"
                    f"👤 **{user.first_name}** joined using your referral link!\n"
                    f"💰 You earned: **$0.1**\n"
                    f"📊 Total Referrals: **{users_data[referred_by].referral_count}**\n"
                    f"💎 Total Earnings: **${users_data[referred_by].referral_earnings}**"
                )
            except Exception as e:
                logger.error(f"Failed to notify referrer {referred_by}: {e}")
            
            # Welcome message for referred user
            welcome_msg = (
                f"🎉 **Welcome {user.first_name}!** 🎉\n\n"
                f"🎁 You received **$0.05 bonus** for joining via referral!\n"
                f"💰 Your Balance: **${users_data[user_id].balance}**\n\n"
                f"🎮 Start playing now!"
            )
        else:
            welcome_msg = f"🎮 Hello {user.first_name}! Play Game With WINI Game"
        
        # Save data
        save_data(users_data)
    else:
        welcome_msg = f"🎮 Welcome back {user.first_name}!"
    
    # Create main menu
    keyboard = [
        [InlineKeyboardButton("🎰 Open WINI Game", web_app=WebAppInfo(url=f"{GAME_WEBAPP_URL}?user_id={user_id}"))],
        [InlineKeyboardButton("👥 Referral", callback_data="referral"),
         InlineKeyboardButton("💰 Balance", callback_data="balance"),
         InlineKeyboardButton("💳 Withdraw", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{welcome_msg}\n💰 Balance: ${users_data[user_id].balance}",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Ensure user exists
    if user_id not in users_data:
        users_data[user_id] = UserData(user_id, update.effective_user.username or update.effective_user.first_name)
        save_data(users_data)
    
    user = users_data[user_id]
    
    if query.data == "withdraw":
        keyboard = [
            [InlineKeyboardButton("💰 Check Balance", callback_data="balance")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🚧 **Withdraw Feature Coming Soon!** 🚧\n\n"
            "We're working hard to bring you withdrawal options.\n"
            f"Your current balance: **${user.balance}**\n\n"
            "Minimum withdrawal: **$10** (coming soon)\n"
            "Stay tuned for updates! 🎮",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == "balance":
        keyboard = [
            [InlineKeyboardButton("👥 Check Referrals", callback_data="referral")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💰 **Your Balance** 💰\n\n"
            f"• Game Balance: **${user.balance}**\n"
            f"• Games Played: **{user.games_played}**\n"
            f"• Referral Earnings: **${user.referral_earnings}**\n"
            f"• Joined: **{user.joined_date}**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == "referral":
        # Get bot username
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        message = (
            f"👥 **Referral Program** 👥\n\n"
            f"🔗 **Your Referral Link:**\n`{referral_link}`\n\n"
            f"📊 **Your Stats:**\n"
            f"• Total Referrals: **{user.referral_count}**\n"
            f"• Referral Earnings: **${user.referral_earnings}**\n"
            f"• Current Balance: **${user.balance}**\n\n"
            f"🎁 **Rewards:**\n"
            f"• **You get:** $0.1 per referral\n"
            f"• **Friend gets:** $0.05 bonus\n"
            f"• No limit - invite more, earn more!\n\n"
            f"📱 **How to refer:**\n"
            f"1. Share your link with friends\n"
            f"2. They start the bot with your link\n"
            f"3. Both get bonus instantly!"
        )
        
        keyboard = [
            [InlineKeyboardButton("📤 Share Link", switch_inline_query=f"Join WINI Game and get $0.05 bonus! {referral_link}")],
            [InlineKeyboardButton("📋 Copy Link", callback_data="copy_link")],
            [InlineKeyboardButton("👥 My Referrals List", callback_data="referral_list")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == "copy_link":
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        # Show alert with link
        await query.answer(f"📋 Link copied!\n{referral_link}", show_alert=True)
    
    elif query.data == "referral_list":
        # Find all users referred by this user
        referred_users = []
        for uid, u in users_data.items():
            if u.referred_by == user_id:
                referred_users.append((u.username, u.joined_date, u.balance))
        
        if not referred_users:
            text = "👥 **Your Referrals**\n\nYou haven't referred anyone yet! Share your referral link to earn bonuses."
        else:
            text = "👥 **Your Referrals List**\n\n"
            for i, (name, date, balance) in enumerate(referred_users, 1):
                text += f"{i}. **{name}**\n   📅 Joined: {date[:10]}\n   💰 Balance: ${balance}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Referral", callback_data="referral")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🎰 Open WINI Game", web_app=WebAppInfo(url=f"{GAME_WEBAPP_URL}?user_id={user_id}"))],
            [InlineKeyboardButton("👥 Referral", callback_data="referral"),
             InlineKeyboardButton("💰 Balance", callback_data="balance"),
             InlineKeyboardButton("💳 Withdraw", callback_data="withdraw")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎮 Hello {update.effective_user.first_name}!\n💰 Balance: ${user.balance}",
            reply_markup=reply_markup
        )

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle web app data
    if update.effective_message and update.effective_message.web_app_data:
        try:
            data = json.loads(update.effective_message.web_app_data.data)
            user_id = update.effective_user.id
            
            if user_id in users_data:
                user = users_data[user_id]
                
                if data.get('action') == 'update_balance':
                    user.balance = data.get('balance', user.balance)
                    save_data(users_data)
                    await update.effective_message.reply_text(f"💰 Balance updated: ${user.balance}")
                
                elif data.get('action') == 'game_played':
                    user.games_played += 1
                    save_data(users_data)
                    await update.effective_message.reply_text(f"🎮 Game played: {data.get('game_name', 'Unknown')}")
        
        except Exception as e:
            logger.error(f"Error handling web app data: {e}")

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to check data (remove in production)"""
    user_id = update.effective_user.id
    
    if user_id in users_data:
        user = users_data[user_id]
        
        # Find who referred this user
        referred_by_name = "None"
        if user.referred_by and user.referred_by in users_data:
            referred_by_name = users_data[user.referred_by].username
        
        # Find users this user referred
        referrals = []
        for uid, u in users_data.items():
            if u.referred_by == user_id:
                referrals.append(u.username)
        
        debug_text = (
            f"🔍 **Debug Info**\n\n"
            f"User ID: {user_id}\n"
            f"Username: {user.username}\n"
            f"Balance: ${user.balance}\n"
            f"Referred By: {referred_by_name}\n"
            f"Referral Count: {user.referral_count}\n"
            f"Referral Earnings: ${user.referral_earnings}\n"
            f"Referrals: {', '.join(referrals) if referrals else 'None'}\n"
            f"Total Users: {len(users_data)}"
        )
        
        await update.message.reply_text(debug_text, parse_mode='Markdown')

def main():
    print("🤖 बॉट शुरू हो रहा है...")
    print(f"📊 लोड किए गए यूजर: {len(users_data)}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # कमांड हैंडलर
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("debug", debug_command))  # Debug command - remove in production
    
    # कॉलबैक हैंडलर
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # मैसेज हैंडलर (वेब ऐप डेटा के लिए)
    app.add_handler(MessageHandler(None, handle_messages))
    
    print("✅ बॉट चल रहा है!")
    print("📢 रेफरल सिस्टम फिक्स हो गया है!")
    print("💾 डेटा अब परमानेंट सेव होगा!")
    
    app.run_polling()

if __name__ == '__main__':
    main()