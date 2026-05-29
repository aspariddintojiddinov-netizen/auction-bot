"""
🏆 AUKSION TELEGRAM BOT
- Taymer tugaganda eng yuqori narx yutadi
- O'zbek va Rus tili
- Admin panel, to'lov tasdiqlash, g'olibga xabar, minimal stavka

ISHLATISH:
1. pip install python-telegram-bot==20.7
2. BOT_TOKEN ni o'zgartiring
3. ADMIN_ID ni o'zgartiring
4. python auction_bot.py
"""

import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"   # @BotFather dan oling
ADMIN_IDS = [123456789]              # Sizning Telegram ID ingiz

# ==================== TILLAR ====================
TEXTS = {
    "uz": {
        "start": "👋 Salom! Men Auksion Botman!\n\n🔨 /auctions - Faol auksionlar\n📋 /myorders - Mening buyurtmalarim",
        "no_auctions": "😔 Hozircha faol auksion yo'q",
        "bid_btn": "💰 Stavka berish",
        "item_info": "🏷 *{title}*\n\n📝 {description}\n\n💵 Boshlang'ich narx: *{start_price} so'm*\n📈 Minimal stavka: *+{min_step} so'm*\n⏰ Tugash vaqti: *{end_time}*\n\n🥇 Hozirgi eng yuqori: *{current_price} so'm*\n👤 Lider: {leader}",
        "enter_bid": "💰 Stavkangizni kiriting (so'mda):\nMinimal: {min_bid} so'm",
        "bid_low": "❌ Stavka juda past! Minimal: {min_bid} so'm",
        "bid_success": "✅ Stavkangiz qabul qilindi!\n💰 {amount} so'm\n⏰ {end_time} gacha kuting",
        "outbid": "⚠️ Siz ortda qoldingiz!\n🏷 *{title}*\nYangi lider: {amount} so'm\n👉 /auctions orqali qayta stavka bering",
        "winner": "🎉 Tabriklaymiz! Siz g'olib bo'ldingiz!\n\n🏷 *{title}*\n💰 Narx: *{amount} so'm*\n\nTo'lov uchun adminga murojaat qiling: @{admin}",
        "auction_ended": "🏁 Auksion yakunlandi!\n\n🏷 {title}\n🥇 G'olib: {winner}\n💰 Narx: {amount} so'm",
        "payment_confirm": "✅ To'lov tasdiqlandi!\n\n🏷 {title}\n💰 {amount} so'm\n📦 Tez orada yetkazib beriladi!",
        "no_winner": "😔 Auksion yakunlandi, lekin hech kim stavka bermadi.",
        "choose_lang": "🌐 Tilni tanlang / Выберите язык:",
        "lang_set": "✅ O'zbek tili tanlandi!",
    },
    "ru": {
        "start": "👋 Привет! Я Аукцион Бот!\n\n🔨 /auctions - Активные аукционы\n📋 /myorders - Мои заказы",
        "no_auctions": "😔 Активных аукционов пока нет",
        "bid_btn": "💰 Сделать ставку",
        "item_info": "🏷 *{title}*\n\n📝 {description}\n\n💵 Начальная цена: *{start_price} сум*\n📈 Минимальный шаг: *+{min_step} сум*\n⏰ Время окончания: *{end_time}*\n\n🥇 Текущая максимальная: *{current_price} сум*\n👤 Лидер: {leader}",
        "enter_bid": "💰 Введите вашу ставку (в сумах):\nМинимум: {min_bid} сум",
        "bid_low": "❌ Ставка слишком низкая! Минимум: {min_bid} сум",
        "bid_success": "✅ Ваша ставка принята!\n💰 {amount} сум\n⏰ Ждите до {end_time}",
        "outbid": "⚠️ Вас обогнали!\n🏷 *{title}*\nНовый лидер: {amount} сум\n👉 Зайдите через /auctions",
        "winner": "🎉 Поздравляем! Вы победили!\n\n🏷 *{title}*\n💰 Цена: *{amount} сум*\n\nДля оплаты обратитесь к администратору: @{admin}",
        "auction_ended": "🏁 Аукцион завершён!\n\n🏷 {title}\n🥇 Победитель: {winner}\n💰 Цена: {amount} сум",
        "payment_confirm": "✅ Оплата подтверждена!\n\n🏷 {title}\n💰 {amount} сум\n📦 Доставим в ближайшее время!",
        "no_winner": "😔 Аукцион завершён, но никто не сделал ставку.",
        "choose_lang": "🌐 Tilni tanlang / Выберите язык:",
        "lang_set": "✅ Выбран русский язык!",
    }
}

# ==================== MA'LUMOTLAR ====================
auctions = {}       # {auction_id: auction_data}
user_langs = {}     # {user_id: "uz"/"ru"}
user_states = {}    # {user_id: state}
auction_counter = 0

# ConversationHandler states
WAIT_TITLE, WAIT_DESC, WAIT_START_PRICE, WAIT_MIN_STEP, WAIT_DURATION, WAIT_BID = range(6)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== YORDAMCHI FUNKSIYALAR ====================

def get_lang(user_id):
    return user_langs.get(user_id, "uz")

def t(user_id, key, **kwargs):
    lang = get_lang(user_id)
    text = TEXTS[lang].get(key, TEXTS["uz"].get(key, key))
    return text.format(**kwargs) if kwargs else text

def is_admin(user_id):
    return user_id in ADMIN_IDS

def format_time(dt):
    return dt.strftime("%d.%m.%Y %H:%M")

# ==================== START ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")]
    ]
    await update.message.reply_text(
        "🌐 Tilni tanlang / Выберите язык:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.split("_")[1]
    user_langs[user_id] = lang

    welcome = t(user_id, "start")
    extra = ""
    if is_admin(user_id):
        extra = "\n\n🔧 *ADMIN PANEL:*\n/newauction - Yangi auksion\n/list - Barcha auksionlar\n/endauction - Auksionni tugatish"

    await query.edit_message_text(welcome + extra, parse_mode="Markdown")

# ==================== AUKSIONLAR RO'YXATI ====================

async def list_auctions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    active = {k: v for k, v in auctions.items() if v["active"]}

    if not active:
        await update.message.reply_text(t(user_id, "no_auctions"))
        return

    for aid, auction in active.items():
        await send_auction_card(update.message, user_id, aid, auction)

async def send_auction_card(message, user_id, aid, auction):
    leader_name = auction.get("leader_name", "—")
    current = auction.get("current_price", auction["start_price"])

    text = t(user_id, "item_info",
        title=auction["title"],
        description=auction["description"],
        start_price=f"{auction['start_price']:,}",
        min_step=f"{auction['min_step']:,}",
        end_time=format_time(auction["end_time"]),
        current_price=f"{current:,}",
        leader=leader_name
    )

    keyboard = [[InlineKeyboardButton(
        t(user_id, "bid_btn"),
        callback_data=f"bid_{aid}"
    )]]

    await message.reply_text(text, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== STAVKA BERISH ====================

async def bid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    aid = query.data.split("_")[1]

    if aid not in auctions or not auctions[aid]["active"]:
        await query.message.reply_text("❌ Auksion topilmadi yoki yakunlandi.")
        return

    auction = auctions[aid]
    current = auction.get("current_price", auction["start_price"])
    min_bid = current + auction["min_step"]

    user_states[user_id] = {"state": WAIT_BID, "auction_id": aid}

    await query.message.reply_text(
        t(user_id, "enter_bid", min_bid=f"{min_bid:,}")
    )

async def handle_bid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_states or user_states[user_id].get("state") != WAIT_BID:
        return

    try:
        amount = int(update.message.text.replace(" ", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("❌ Faqat raqam kiriting!")
        return

    aid = user_states[user_id]["auction_id"]
    auction = auctions.get(aid)

    if not auction or not auction["active"]:
        await update.message.reply_text("❌ Auksion topilmadi.")
        del user_states[user_id]
        return

    current = auction.get("current_price", auction["start_price"])
    min_bid = current + auction["min_step"]

    if amount < min_bid:
        await update.message.reply_text(
            t(user_id, "bid_low", min_bid=f"{min_bid:,}")
        )
        return

    # Oldingi liderni xabardor qilish
    prev_leader = auction.get("leader_id")
    if prev_leader and prev_leader != user_id:
        try:
            await context.bot.send_message(
                prev_leader,
                t(prev_leader, "outbid",
                  title=auction["title"],
                  amount=f"{amount:,}"),
                parse_mode="Markdown"
            )
        except:
            pass

    # Yangi stavkani saqlash
    auction["current_price"] = amount
    auction["leader_id"] = user_id
    auction["leader_name"] = update.effective_user.first_name
    auction.setdefault("bids", []).append({
        "user_id": user_id,
        "name": update.effective_user.first_name,
        "amount": amount,
        "time": datetime.now()
    })

    del user_states[user_id]

    await update.message.reply_text(
        t(user_id, "bid_success",
          amount=f"{amount:,}",
          end_time=format_time(auction["end_time"])),
    )

# ==================== ADMIN: YANGI AUKSION ====================

async def new_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Faqat adminlar uchun!")
        return

    user_states[user_id] = {"state": WAIT_TITLE, "auction_data": {}}
    await update.message.reply_text("📝 Tovar nomini kiriting:")

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states:
        return

    state_info = user_states[user_id]
    state = state_info.get("state")
    text = update.message.text

    if state == WAIT_TITLE:
        state_info["auction_data"]["title"] = text
        state_info["state"] = WAIT_DESC
        await update.message.reply_text("📝 Tavsif kiriting:")

    elif state == WAIT_DESC:
        state_info["auction_data"]["description"] = text
        state_info["state"] = WAIT_START_PRICE
        await update.message.reply_text("💰 Boshlang'ich narxni kiriting (so'mda):")

    elif state == WAIT_START_PRICE:
        try:
            price = int(text.replace(" ", "").replace(",", ""))
            state_info["auction_data"]["start_price"] = price
            state_info["state"] = WAIT_MIN_STEP
            await update.message.reply_text("📈 Minimal stavka miqdorini kiriting (so'mda):")
        except:
            await update.message.reply_text("❌ Faqat raqam!")

    elif state == WAIT_MIN_STEP:
        try:
            step = int(text.replace(" ", "").replace(",", ""))
            state_info["auction_data"]["min_step"] = step
            state_info["state"] = WAIT_DURATION
            await update.message.reply_text("⏰ Necha soat davom etsin? (masalan: 24):")
        except:
            await update.message.reply_text("❌ Faqat raqam!")

    elif state == WAIT_DURATION:
        try:
            hours = float(text)
            data = state_info["auction_data"]
            data["end_time"] = datetime.now() + timedelta(hours=hours)
            data["active"] = True
            data["current_price"] = data["start_price"]
            data["leader_id"] = None
            data["leader_name"] = "—"
            data["bids"] = []

            global auction_counter
            auction_counter += 1
            aid = str(auction_counter)
            auctions[aid] = data

            del user_states[user_id]

            await update.message.reply_text(
                f"✅ Auksion yaratildi!\n\n"
                f"🏷 *{data['title']}*\n"
                f"💰 Boshlang'ich: {data['start_price']:,} so'm\n"
                f"⏰ Tugaydi: {format_time(data['end_time'])}",
                parse_mode="Markdown"
            )

            # Taymerni ishga tushirish
            asyncio.create_task(auction_timer(context, aid))

        except:
            await update.message.reply_text("❌ Faqat raqam!")

    elif state == WAIT_BID:
        await handle_bid_input(update, context)

# ==================== TAYMER ====================

async def auction_timer(context: ContextTypes.DEFAULT_TYPE, aid: str):
    auction = auctions[aid]
    wait_seconds = (auction["end_time"] - datetime.now()).total_seconds()
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

    await end_auction(context, aid)

async def end_auction(context: ContextTypes.DEFAULT_TYPE, aid: str):
    if aid not in auctions:
        return
    auction = auctions[aid]
    if not auction["active"]:
        return

    auction["active"] = False

    # Adminlarga xabar
    for admin_id in ADMIN_IDS:
        lang = get_lang(admin_id)
        if auction["leader_id"]:
            msg = TEXTS[lang]["auction_ended"].format(
                title=auction["title"],
                winner=auction["leader_name"],
                amount=f"{auction['current_price']:,}"
            )
            # To'lovni tasdiqlash tugmasi
            keyboard = [[InlineKeyboardButton(
                "✅ To'lovni tasdiqlash",
                callback_data=f"confirm_{aid}"
            )]]
            try:
                await context.bot.send_message(admin_id, msg,
                    reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
        else:
            try:
                await context.bot.send_message(
                    admin_id,
                    TEXTS[lang]["no_winner"]
                )
            except:
                pass

    # G'olibga xabar
    if auction["leader_id"]:
        winner_id = auction["leader_id"]
        admin_username = "admin"  # O'zingizning username ingiz
        try:
            await context.bot.send_message(
                winner_id,
                t(winner_id, "winner",
                  title=auction["title"],
                  amount=f"{auction['current_price']:,}",
                  admin=admin_username),
                parse_mode="Markdown"
            )
        except:
            pass

# ==================== TO'LOV TASDIQLASH ====================

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not is_admin(user_id):
        return

    aid = query.data.split("_")[1]
    auction = auctions.get(aid)
    if not auction:
        return

    winner_id = auction.get("leader_id")
    if winner_id:
        try:
            await context.bot.send_message(
                winner_id,
                t(winner_id, "payment_confirm",
                  title=auction["title"],
                  amount=f"{auction['current_price']:,}")
            )
        except:
            pass

    await query.edit_message_text(
        f"✅ To'lov tasdiqlandi!\n🏷 {auction['title']}\n"
        f"👤 {auction['leader_name']}\n💰 {auction['current_price']:,} so'm"
    )

# ==================== ADMIN STATISTIKA ====================

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not auctions:
        await update.message.reply_text("📋 Hech qanday auksion yo'q")
        return

    text = "📋 *BARCHA AUKSIONLAR:*\n\n"
    for aid, a in auctions.items():
        status = "✅ Faol" if a["active"] else "🔴 Tugagan"
        text += (f"ID: {aid} | {status}\n"
                 f"🏷 {a['title']}\n"
                 f"💰 {a['current_price']:,} so'm\n"
                 f"👤 Lider: {a['leader_name']}\n"
                 f"⏰ {format_time(a['end_time'])}\n\n")

    await update.message.reply_text(text, parse_mode="Markdown")

# ==================== ISHGA TUSHIRISH ====================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auctions", list_auctions))
    app.add_handler(CommandHandler("newauction", new_auction))
    app.add_handler(CommandHandler("list", admin_list))

    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(bid_callback, pattern="^bid_"))
    app.add_handler(CallbackQueryHandler(confirm_payment, pattern="^confirm_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))

    print("🤖 Auksion bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
