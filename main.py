import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes
import json
from datetime import datetime

# कॉन्फिगरेशन
BOT_TOKEN = "8672499858:AAGPtzFcwe8kF72Ge7lzRuDXZFDWiXfMXCA"
GAME_WEBAPP_URL = "https://lcrscan.com/winiGame/"
API_KEY = "699c31f616cf06eec2a4d053"

# लॉगिंग
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# यूजर डेटा
users_data = {}

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
    
    if args and args[0].isdigit():
        referred_by = int(args[0])
        # रेफरर को बोनस दें अगर नया यूजर है
        if referred_by != user_id and referred_by in users_data and user_id not in users_data:
            users_data[referred_by].balance += 0.1
            users_data[referred_by].referral_count += 1
            users_data[referred_by].referral_earnings += 0.1
    
    if user_id not in users_data:
        users_data[user_id] = UserData(user_id, user.username or user.first_name, referred_by)
    
    keyboard = [
        [InlineKeyboardButton("🎰 Open WINI Game", web_app=WebAppInfo(url=f"{GAME_WEBAPP_URL}?user_id={user_id}"))],
        [InlineKeyboardButton("👥 Referral", callback_data="referral"),
         InlineKeyboardButton("💳 Withdraw", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎮 Hello {user.first_name}! Play Game With WINI Game\n💰 Balance: ${users_data[user_id].balance}",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "withdraw":
        await query.edit_message_text(
            "🚧 **Withdraw Feature Coming Soon!**\n\n"
            "We're working hard to bring you withdrawal options.\n"
            "Stay tuned for updates! 🎮",
            parse_mode='Markdown'
        )
        # Add a small delay and then go back to main menu
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    
    elif query.data == "referral":
        if user_id in users_data:
            user = users_data[user_id]
            referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user_id}"
            
            message = (
                f"👥 **Referral Program**\n\n"
                f"🔗 **Your Referral Link:**\n`{referral_link}`\n\n"
                f"📊 **Your Stats:**\n"
                f"• Total Referrals: {user.referral_count}\n"
                f"• Referral Earnings: ${user.referral_earnings}\n"
                f"• Current Balance: ${user.balance}\n\n"
                f"🎁 **Rewards:**\n"
                f"• Get $0.1 for each friend who joins!\n"
                f"• Share your link and earn more!"
            )
            
            # Share button added here
            keyboard = [
                [InlineKeyboardButton("📤 Share Referral Link", switch_inline_query=f"Join WINI Game and get bonus! {referral_link}")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    elif query.data == "back":
        user = users_data[user_id]
        keyboard = [
            [InlineKeyboardButton("🎰 Open WINI Game", web_app=WebAppInfo(url=f"{GAME_WEBAPP_URL}?user_id={user_id}"))],
            [InlineKeyboardButton("👥 Referral", callback_data="referral"),
             InlineKeyboardButton("💳 Withdraw", callback_data="withdraw")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎮 Hello {update.effective_user.first_name}! Play Game With WINI Game\n💰 Balance: ${user.balance}",
            reply_markup=reply_markup
        )

# ✅ सिंपल तरीका - सभी मैसेज हैंडल करें
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # चेक करें कि वेब ऐप डेटा है या नहीं
    if update.effective_message and update.effective_message.web_app_data:
        try:
            data = json.loads(update.effective_message.web_app_data.data)
            user_id = update.effective_user.id
            
            if user_id in users_data:
                user = users_data[user_id]
                
                if data.get('action') == 'update_balance':
                    user.balance = data.get('balance', user.balance)
                    await update.effective_message.reply_text(f"💰 Balance: ${user.balance}")
                
                elif data.get('action') == 'game_played':
                    user.games_played += 1
                    await update.effective_message.reply_text(f"🎮 Played Game : {data.get('game_name')}")
        
        except Exception as e:
            logger.error(f"Error: {e}")

def main():
    print("🤖 बॉट शुरू...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(None, handle_messages))  # सभी मैसेज हैंडल करें
    
    print("✅ बॉट चल रहा है!")
    app.run_polling()

if __name__ == '__main__':
    main()