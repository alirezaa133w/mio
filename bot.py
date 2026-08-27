# bot.py
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ============ تنظیمات ============
TOKEN = "8651125448:AAEjFhxzCmEcYgi7aTiv5s4LpgH6SWoosPQ"  # بعداً عوض کن
ADMIN_ID = 5013016506

# دیتابیس موقت
pending_orders = {}

# ایموجی‌های پریمیوم
EMOJIS = {
    "apple": "🍎",
    "money": "💰",
    "tick": "✅",
    "clock": "⏳",
    "rocket": "🚀",
    "gift": "🎁",
    "star": "⭐",
    "point": "⭐",
    "bank": "🏦",
    "card": "💳",
    "warning": "⚠️",
    "success": "🎉"
}

# ============ توابع ============
def calculate_price(mewo_points):
    """محاسبه مبلغ تومانی بر اساس تعداد میوپوینت"""
    if mewo_points < 30_000_000:
        return (mewo_points // 1_000_000) * 4500
    elif mewo_points <= 200_000_000:
        return (mewo_points // 1_000_000) * 4000
    else:
        return (mewo_points // 1_000_000) * 3500

# ============ دستورات ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    await update.message.reply_text(
        f"{EMOJIS['rocket']} به ربات فروش میوپوینت خوش آمدی {user.first_name}!\n\n"
        f"{EMOJIS['apple']} تعداد میوپوینت مورد نظرت رو وارد کن (به میلیون):\n"
        f"(حداقل ۱ میلیون - حداکثر ۱,۰۰۰ میلیون)\n\n"
        f"{EMOJIS['star']} قیمت‌ها (به ازای هر ۱ میلیون میوپوینت):\n"
        f"• زیر ۳۰ میلیون: ۴,۵۰۰ تومان\n"
        f"• ۳۰ تا ۲۰۰ میلیون: ۴,۰۰۰ تومان\n"
        f"• بالای ۲۰۰ میلیون: ۳,۵۰۰ تومان"
    )
    context.user_data['state'] = 'waiting_amount'

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'waiting_amount':
        return

    text = update.message.text.replace(',', '').strip()
    if not text.isdigit():
        await update.message.reply_text(f"{EMOJIS['warning']} فقط عدد وارد کن (تعداد میوپوینت به میلیون).")
        return

    mewo_points = int(text)
    if mewo_points < 1 or mewo_points > 1000:
        await update.message.reply_text(f"{EMOJIS['warning']} تعداد میوپوینت باید بین ۱ تا ۱,۰۰۰ میلیون باشه.")
        return

    actual_points = mewo_points * 1_000_000
    price = calculate_price(actual_points)
    
    context.user_data['mewo_points'] = actual_points
    context.user_data['mewo_points_million'] = mewo_points
    context.user_data['price'] = price

    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['tick']} تایید و خرید", callback_data='confirm_amount')],
        [InlineKeyboardButton(f"{EMOJIS['warning']} انصراف", callback_data='cancel')]
    ]
    await update.message.reply_text(
        f"{EMOJIS['apple']} شما **{mewo_points:,} میلیون** میوپوینت درخواست کردید.\n"
        f"{EMOJIS['money']} مبلغ قابل پرداخت: **{price:,} تومان**\n\n"
        f"آیا تایید میکنید؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['state'] = 'waiting_confirm'

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'confirm_amount':
        await query.edit_message_text(f"{EMOJIS['clock']} شماره کارت ۱۶ رقمی خودت رو وارد کن:")
        context.user_data['state'] = 'waiting_card'

    elif query.data == 'cancel':
        await query.edit_message_text(f"{EMOJIS['warning']} لغو شد.")
        context.user_data.clear()

    elif query.data == 'confirm_payment':
        if user_id in pending_orders:
            order = pending_orders[user_id]
            await context.bot.send_message(
                ADMIN_ID,
                f"{EMOJIS['gift']} درخواست جدید میوپوینت!\n"
                f"{EMOJIS['star']} کاربر: {query.from_user.first_name} (ایدی: {user_id})\n"
                f"{EMOJIS['apple']} میوپوینت: {order['mewo_points']:,}\n"
                f"{EMOJIS['money']} مبلغ: {order['price']:,} تومان\n"
                f"{EMOJIS['card']} شماره کارت: {order['card_number']}"
            )
            if 'receipt_photo' in order:
                await context.bot.send_photo(ADMIN_ID, order['receipt_photo'], caption=f"{EMOJIS['bank']} فیش واریزی")

            await query.edit_message_text(f"{EMOJIS['tick']} فیش ارسال شد! منتظر تایید مدیر باشید {EMOJIS['clock']}")

            admin_keyboard = [
                [InlineKeyboardButton(f"{EMOJIS['tick']} تایید و واریز میوپوینت", callback_data=f'approve_{user_id}')],
                [InlineKeyboardButton(f"{EMOJIS['warning']} رد", callback_data=f'reject_{user_id}')]
            ]
            await context.bot.send_message(
                ADMIN_ID, 
                f"{EMOJIS['star']} یکی از گزینه‌ها رو انتخاب کن:",
                reply_markup=InlineKeyboardMarkup(admin_keyboard)
            )
            context.user_data.clear()

    elif query.data.startswith('approve_'):
        if user_id == ADMIN_ID:
            target_user = int(query.data.split('_')[1])
            if target_user in pending_orders:
                points = pending_orders[target_user]['mewo_points']
                
                await context.bot.send_message(
                    target_user,
                    f"{EMOJIS['success']} خرید شما تایید شد!\n"
                    f"{EMOJIS['gift']} **{points:,}** میوپوینت به شماره کارت میویی شما واریز شد.\n"
                    f"{EMOJIS['bank']} شماره کارت میویی: `240368354326`\n"
                    f"{EMOJIS['star']} از خرید شما متشکریم!"
                )
                await query.edit_message_text(f"{EMOJIS['tick']} {points:,} میوپوینت برای کاربر {target_user} واریز شد.")
                del pending_orders[target_user]
                context.user_data.clear()

    elif query.data.startswith('reject_'):
        if user_id == ADMIN_ID:
            target_user = int(query.data.split('_')[1])
            await context.bot.send_message(target_user, f"{EMOJIS['warning']} خرید شما رد شد. با پشتیبانی تماس بگیرید.")
            await query.edit_message_text(f"{EMOJIS['warning']} رد شد.")
            if target_user in pending_orders:
                del pending_orders[target_user]

async def handle_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'waiting_card':
        return

    card = update.message.text.strip()
    if not re.match(r'^\d{16}$', card):
        await update.message.reply_text(f"{EMOJIS['warning']} شماره کارت باید ۱۶ رقم باشه.")
        return

    context.user_data['card_number'] = card
    await update.message.reply_text(
        f"{EMOJIS['bank']} مبلغ {context.user_data['price']:,} تومان رو به شماره کارت زیر واریز کن:\n"
        f"`6219861448719251`\n"
        f"به نام **علیرضا کیانی**\n\n"
        f"{EMOJIS['clock']} سپس عکس فیش واریزی رو بفرست."
    )
    context.user_data['state'] = 'waiting_receipt'

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'waiting_receipt':
        return

    if not update.message.photo:
        await update.message.reply_text(f"{EMOJIS['warning']} لطفاً یک عکس از فیش واریزی ارسال کن.")
        return

    user_id = update.effective_user.id
    pending_orders[user_id] = {
        'mewo_points': context.user_data.get('mewo_points'),
        'price': context.user_data.get('price'),
        'card_number': context.user_data.get('card_number'),
        'receipt_photo': update.message.photo[-1].file_id
    }

    keyboard = [[InlineKeyboardButton(f"{EMOJIS['tick']} تایید نهایی", callback_data='confirm_payment')]]
    await update.message.reply_text(
        f"{EMOJIS['tick']} فیش دریافت شد.\n"
        f"{EMOJIS['clock']} برای تایید نهایی دکمه زیر رو بزن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['state'] = 'waiting_final_confirm'

# ============ اجرا ============
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Regex(r'^\d{16}$'), handle_card))
    
    print("🤖 ربات میوپوینت با ایموجی‌های پریمیوم روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
