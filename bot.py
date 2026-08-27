# bot.py
import re
import asyncio
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    MessageEntity
)
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ============ تنظیمات ============
TOKEN = "8651125448:AAEjFhxzCmEcYgi7aTiv5s4LpgH6SWoosPQ"  # ⚠️ بعداً با توکن جدید عوض کن
ADMIN_ID = 5013016506
GROUP_LINK = "https://t.me/+ly7f-ue6IyQzY2Jk"

# ============ Custom Emoji IDها ============
# با دستور /emojiid می‌توانید ID واقعی هر ایموجی را بگیرید
CUSTOM_EMOJIS = {
    "mewo": "CUSTOM_EMOJI_ID_1",    # 🍏 میو
    "money": "CUSTOM_EMOJI_ID_2",   # 💰 پول
    "tick": "CUSTOM_EMOJI_ID_3",    # ✅ تیک
    "clock": "CUSTOM_EMOJI_ID_4",   # ⏳ ساعت
    "rocket": "CUSTOM_EMOJI_ID_5",  # 🚀 موشک
    "gift": "CUSTOM_EMOJI_ID_6",    # 🎁 هدیه
    "star": "CUSTOM_EMOJI_ID_7",    # ⭐ ستاره
    "bank": "CUSTOM_EMOJI_ID_8",    # 🏦 بانک
    "card": "CUSTOM_EMOJI_ID_9",    # 💳 کارت
    "warning": "CUSTOM_EMOJI_ID_10", # ⚠️ هشدار
    "success": "CUSTOM_EMOJI_ID_11", # 🎉 موفقیت
    "game": "CUSTOM_EMOJI_ID_12",   # 🎮 بازی
    "fire": "CUSTOM_EMOJI_ID_13",   # 🔥 آتش
}

# ============ توابع کمکی ============
def ce(name: str, fallback: str = "⭐") -> str:
    """
    تولید تگ HTML برای Custom Emoji
    مثال: ce("rocket", "🚀") => '<tg-emoji emoji-id="CUSTOM_EMOJI_ID_5">🚀</tg-emoji>'
    """
    emoji_id = CUSTOM_EMOJIS.get(name)
    if not emoji_id or emoji_id.startswith("CUSTOM_"):
        return fallback
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

def emoji_button(text: str, callback_data: str, emoji_name: str) -> InlineKeyboardButton:
    """ساخت دکمه با آیکون Custom Emoji"""
    emoji_id = CUSTOM_EMOJIS.get(emoji_name)
    if emoji_id and not emoji_id.startswith("CUSTOM_"):
        return InlineKeyboardButton(
            text,
            callback_data=callback_data,
            icon_custom_emoji_id=emoji_id
        )
    return InlineKeyboardButton(f"{text}", callback_data=callback_data)

# دیتابیس موقت
pending_orders = {}
user_ids = set()

# ============ توابع اصلی ============
def calculate_price(mewo_points):
    if mewo_points < 30_000_000:
        return (mewo_points // 1_000_000) * 4500
    elif mewo_points <= 200_000_000:
        return (mewo_points // 1_000_000) * 4000
    else:
        return (mewo_points // 1_000_000) * 3500

async def is_admin(user_id):
    return user_id == ADMIN_ID

# ============ دستورات ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_ids.add(user.id)
    
    keyboard = [
        [
            InlineKeyboardButton(
                "عضویت در گروه بازی میو",
                url=GROUP_LINK,
                icon_custom_emoji_id=CUSTOM_EMOJIS.get("game")
            )
        ],
        [
            InlineKeyboardButton(
                "شروع خرید میوپوینت",
                callback_data="start_shopping",
                icon_custom_emoji_id=CUSTOM_EMOJIS.get("mewo")
            )
        ]
    ]
    
    await update.message.reply_text(
        f'{ce("rocket", "🚀")} <b>به ربات فروش میوپوینت خوش آمدی {user.first_name}!</b>\n\n'
        f'{ce("fire", "🔥")} <b>با ما همراه شو!</b>\n'
        f'با عضویت در گروه بازی میو از تخفیف‌های ویژه و مسابقات هیجان‌انگیز باخبر شو.\n\n'
        f'<b>مزایای عضویت در گروه:</b>\n'
        f'{ce("tick", "✅")} تخفیف‌های ویژه برای اعضا\n'
        f'{ce("tick", "✅")} اطلاع از مسابقات و جوایز نقدی\n'
        f'{ce("tick", "✅")} ارتباط با سایر بازیکنان\n\n'
        f'{ce("fire", "🔥")} <b>همین حالا عضو شو و از مزایاش استفاده کن!</b>\n'
        f'(برای خرید نیازی به عضویت نیست)',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ============ پنل مدیریت ============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton(
                "آمار کاربران",
                callback_data="admin_stats",
                icon_custom_emoji_id=CUSTOM_EMOJIS.get("star")
            )
        ],
        [
            InlineKeyboardButton(
                "پیام همگانی",
                callback_data="admin_broadcast",
                icon_custom_emoji_id=CUSTOM_EMOJIS.get("gift")
            )
        ]
    ]
    await update.message.reply_text(
        f'{ce("star", "⭐")} <b>پنل مدیریت ربات</b>\n\n'
        f'از دکمه‌های زیر برای مدیریت استفاده کنید:',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("⛔ دسترسی غیرمجاز!")
        return
    
    total_users = len(user_ids)
    total_orders = len(pending_orders)
    
    await query.edit_message_text(
        f'{ce("star", "📊")} <b>آمار ربات</b>\n\n'
        f'👥 تعداد کل کاربران: <b>{total_users}</b>\n'
        f'📦 سفارشات در انتظار تایید: <b>{total_orders}</b>',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "بازگشت به پنل",
                    callback_data="admin_panel",
                    icon_custom_emoji_id=CUSTOM_EMOJIS.get("tick")
                )
            ]
        ]),
        parse_mode="HTML"
    )

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("⛔ دسترسی غیرمجاز!")
        return
    
    await query.edit_message_text(
        f'{ce("gift", "📢")} <b>ارسال پیام همگانی</b>\n\n'
        f'لطفاً پیام مورد نظر خود را به صورت <b>متن</b> ارسال کنید.\n'
        f'{ce("warning", "⚠️")} توجه: این پیام برای <b>همه کاربران</b> ارسال خواهد شد.',
        parse_mode="HTML"
    )
    context.user_data['state'] = 'waiting_broadcast_message'

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'waiting_broadcast_message':
        return
    
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی غیرمجاز!")
        return
    
    message_text = update.message.text
    total_users = len(user_ids)
    sent_count = 0
    failed_count = 0
    
    status_msg = await update.message.reply_text(
        f'🔄 در حال ارسال پیام به {total_users} کاربر...'
    )
    
    for user_id in user_ids:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f'{ce("gift", "📢")} <b>پیام همگانی از ادمین</b>\n\n{message_text}',
                parse_mode="HTML"
            )
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed_count += 1
            print(f"خطا در ارسال به {user_id}: {e}")
    
    await status_msg.edit_text(
        f'{ce("tick", "✅")} <b>پیام همگانی ارسال شد!</b>\n\n'
        f'📤 ارسال موفق: {sent_count}\n'
        f'❌ ارسال ناموفق: {failed_count}\n'
        f'👥 کل کاربران: {total_users}',
        parse_mode="HTML"
    )
    context.user_data['state'] = None

# ============ دریافت ID ایموجی ============
async def get_emoji_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /emojiid برای دریافت ID ایموجی‌های پریمیوم"""
    if not update.message or not update.message.entities:
        await update.message.reply_text(
            "❌ یک Custom Emoji برای من بفرست تا ID آن را استخراج کنم."
        )
        return

    for entity in update.message.entities:
        if entity.type == MessageEntity.CUSTOM_EMOJI:
            await update.message.reply_text(
                f'✅ Custom Emoji ID:\n\n<code>{entity.custom_emoji_id}</code>',
                parse_mode="HTML"
            )
            return

    await update.message.reply_text(
        "❌ این پیام Custom Emoji نداشت."
    )

# ============ مدیریت دکمه‌ها ============
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # ===== دکمه‌های پنل ادمین =====
    if query.data == 'admin_panel':
        await admin_panel(update, context)
    
    elif query.data == 'admin_stats':
        await admin_stats(update, context)
    
    elif query.data == 'admin_broadcast':
        await admin_broadcast_start(update, context)

    # ===== دکمه‌های خرید =====
    elif query.data == 'start_shopping':
        await query.edit_message_text(
            f'{ce("mewo", "🍏")} <b>تعداد میوپوینت مورد نظرت رو وارد کن (به میلیون):</b>\n'
            f'حداقل <b>۱ میلیون</b> - حداکثر <b>۱,۰۰۰ میلیون</b>\n\n'
            f'{ce("money", "💰")} <b>قیمت‌ها (به ازای هر ۱ میلیون میوپوینت):</b>\n'
            f'• زیر ۳۰ میلیون: ۴,۵۰۰ تومان\n'
            f'• ۳۰ تا ۲۰۰ میلیون: ۴,۰۰۰ تومان\n'
            f'• بالای ۲۰۰ میلیون: ۳,۵۰۰ تومان',
            parse_mode="HTML"
        )
        context.user_data['state'] = 'waiting_amount'

    elif query.data == 'confirm_amount':
        await query.edit_message_text(
            f'{ce("card", "💳")} <b>شماره کارت میویی خودت رو وارد کن:</b>\n'
            f'نمونه: <code>240368354326</code> (۱۲ رقم)',
            parse_mode="HTML"
        )
        context.user_data['state'] = 'waiting_mewo_card'

    elif query.data == 'cancel':
        await query.edit_message_text(
            f'{ce("warning", "⚠️")} عملیات لغو شد.',
            parse_mode="HTML"
        )
        context.user_data.clear()

    elif query.data == 'confirm_payment':
        if user_id in pending_orders:
            order = pending_orders[user_id]
            await context.bot.send_message(
                ADMIN_ID,
                f'{ce("gift", "🎁")} <b>درخواست جدید میوپوینت!</b>\n'
                f'{ce("star", "⭐")} کاربر: {query.from_user.first_name} (ایدی: {user_id})\n'
                f'{ce("mewo", "🍏")} میوپوینت: {order["mewo_points"]:,}\n'
                f'{ce("money", "💰")} مبلغ: {order["price"]:,} تومان\n'
                f'{ce("card", "💳")} شماره کارت میویی: {order["mewo_card"]}',
                parse_mode="HTML"
            )
            if 'receipt_photo' in order:
                await context.bot.send_photo(
                    ADMIN_ID,
                    order['receipt_photo'],
                    caption=f'{ce("bank", "🏦")} فیش واریزی'
                )

            await query.edit_message_text(
                f'{ce("tick", "✅")} <b>فیش ارسال شد!</b>\n'
                f'{ce("clock", "⏳")} منتظر تایید مدیر باشید...',
                parse_mode="HTML"
            )

            admin_keyboard = [
                [
                    InlineKeyboardButton(
                        "تایید و واریز",
                        callback_data=f'approve_{user_id}',
                        icon_custom_emoji_id=CUSTOM_EMOJIS.get("tick")
                    )
                ],
                [
                    InlineKeyboardButton(
                        "رد",
                        callback_data=f'reject_{user_id}',
                        icon_custom_emoji_id=CUSTOM_EMOJIS.get("warning")
                    )
                ]
            ]
            await context.bot.send_message(
                ADMIN_ID, 
                f'{ce("star", "⭐")} یکی از گزینه‌ها رو انتخاب کن:',
                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                parse_mode="HTML"
            )
            context.user_data.clear()

    elif query.data.startswith('approve_'):
        if user_id == ADMIN_ID:
            target_user = int(query.data.split('_')[1])
            if target_user in pending_orders:
                points = pending_orders[target_user]['mewo_points']
                mewo_card = pending_orders[target_user]['mewo_card']
                
                await context.bot.send_message(
                    target_user,
                    f'{ce("success", "🎉")} <b>خرید شما تایید شد!</b>\n'
                    f'{ce("gift", "🎁")} <b>{points:,}</b> میوپوینت به شماره کارت میویی شما واریز شد.\n'
                    f'{ce("card", "💳")} شماره کارت میویی: <code>{mewo_card}</code>\n'
                    f'{ce("star", "⭐")} از خرید شما متشکریم!',
                    parse_mode="HTML"
                )
                await query.edit_message_text(
                    f'{ce("tick", "✅")} {points:,} میوپوینت برای کاربر {target_user} واریز شد.',
                    parse_mode="HTML"
                )
                del pending_orders[target_user]
                context.user_data.clear()

    elif query.data.startswith('reject_'):
        if user_id == ADMIN_ID:
            target_user = int(query.data.split('_')[1])
            await context.bot.send_message(
                target_user,
                f'{ce("warning", "⚠️")} خرید شما رد شد. با پشتیبانی تماس بگیرید.',
                parse_mode="HTML"
            )
            await query.edit_message_text(
                f'{ce("warning", "⚠️")} رد شد.',
                parse_mode="HTML"
            )
            if target_user in pending_orders:
                del pending_orders[target_user]

# ============ هندلرهای متنی ============
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # بررسی دستور پنل ادمین
    if text == "پنل" and await is_admin(user_id):
        await admin_panel(update, context)
        return

    if state == 'waiting_amount':
        await handle_amount(update, context, text)
    elif state == 'waiting_mewo_card':
        await handle_mewo_card(update, context, text)
    elif state == 'waiting_broadcast_message':
        await handle_broadcast_message(update, context)
    else:
        await update.message.reply_text(
            f'{ce("warning", "⚠️")} لطفاً از دکمه‌های ربات استفاده کن.',
            parse_mode="HTML"
        )

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    text = text.replace(',', '').strip()
    if not text.isdigit():
        await update.message.reply_text(
            f'{ce("warning", "⚠️")} فقط عدد وارد کن.',
            parse_mode="HTML"
        )
        return

    mewo_points = int(text)
    if mewo_points < 1 or mewo_points > 1000:
        await update.message.reply_text(
            f'{ce("warning", "⚠️")} تعداد میوپوینت باید بین ۱ تا ۱,۰۰۰ میلیون باشه.',
            parse_mode="HTML"
        )
        return

    actual_points = mewo_points * 1_000_000
    price = calculate_price(actual_points)
    
    context.user_data['mewo_points'] = actual_points
    context.user_data['price'] = price

    keyboard = [
        [
            InlineKeyboardButton(
                "تایید و خرید",
                callback_data='confirm_amount',
                icon_custom_emoji_id=CUSTOM_EMOJIS.get("tick")
            )
        ],
        [
            InlineKeyboardButton(
                "انصراف",
                callback_data='cancel',
                icon_custom_emoji_id=CUSTOM_EMOJIS.get("warning")
            )
        ]
    ]
    await update.message.reply_text(
        f'{ce("mewo", "🍏")} شما <b>{mewo_points:,} میلیون</b> میوپوینت درخواست کردید.\n'
        f'{ce("money", "💰")} مبلغ قابل پرداخت: <b>{price:,} تومان</b>\n\n'
        f'آیا تایید میکنید؟',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    context.user_data['state'] = 'waiting_confirm'

async def handle_mewo_card(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    if len(text) != 12 or not text.isdigit():
        await update.message.reply_text(
            f'{ce("warning", "⚠️")} شماره کارت میویی باید <b>۱۲ رقم</b> باشه.\n'
            f'مثال: <code>240368354326</code>\n\n'
            f'لطفاً دوباره وارد کن:',
            parse_mode="HTML"
        )
        return

    context.user_data['mewo_card'] = text
    
    await update.message.reply_text(
        f'{ce("bank", "🏦")} مبلغ {context.user_data["price"]:,} تومان رو به شماره کارت زیر واریز کن:\n'
        f'<code>6219861448719251</code>\n'
        f'به نام <b>علیرضا کیانی</b>\n\n'
        f'{ce("clock", "⏳")} سپس عکس فیش واریزی رو بفرست.',
        parse_mode="HTML"
    )
    context.user_data['state'] = 'waiting_receipt'

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'waiting_receipt':
        await update.message.reply_text(
            f'{ce("warning", "⚠️")} لطفاً ابتدا شماره کارت میویی خودت رو وارد کن.',
            parse_mode="HTML"
        )
        return

    if not update.message.photo:
        await update.message.reply_text(
            f'{ce("warning", "⚠️")} لطفاً یک عکس از فیش واریزی ارسال کن.',
            parse_mode="HTML"
        )
        return

    user_id = update.effective_user.id
    pending_orders[user_id] = {
        'mewo_points': context.user_data.get('mewo_points'),
        'price': context.user_data.get('price'),
        'mewo_card': context.user_data.get('mewo_card'),
        'receipt_photo': update.message.photo[-1].file_id
    }

    keyboard = [
        [
            InlineKeyboardButton(
                "تایید نهایی",
                callback_data='confirm_payment',
                icon_custom_emoji_id=CUSTOM_EMOJIS.get("tick")
            )
        ]
    ]
    await update.message.reply_text(
        f'{ce("tick", "✅")} فیش دریافت شد.\n'
        f'{ce("clock", "⏳")} برای تایید نهایی دکمه زیر رو بزن:',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    context.user_data['state'] = 'waiting_final_confirm'

# ============ اجرا ============
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("emojiid", get_emoji_id))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 ربات فروش میوپوینت با Custom Emoji و پنل مدیریت روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
