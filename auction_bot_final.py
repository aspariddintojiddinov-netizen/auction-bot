import asyncio
import import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8986359963:AAFe1v3aNp6ASkcPKD5Qozi8FSyjWaCa5C4")

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = BOT_TOKEN = "8986359963:AAFe1v3aNp6ASkcPKD5Qozi8FSyjWaCa5C4"


ADMIN_IDS = [8575593397]

TEXTS = {
    "uz": {
        "start": "👋 Salom! Men Auksion Botman!\n\n🔨 /auctions - Faol auksionlar",
        "no_auctions": "😔 Hozircha faol auksion yo'q",
        "bid_btn": "💰 Stavka berish",
        "item_info": "🏷 *{title}*\n\n📝 {description}\n\n💵 Boshlang'ich: *{start_price} so'm*\n📈 Minimal stavka: *+{min_step} so'm*\n⏰ Tugash: *{end_time}*\n\n🥇 Eng yuqori: *{current_price} so'm*\n👤 Lider: {leader}",
        "enter_bid": "💰 Stavkangizni kiriting:\nMinimal: {min_bid} so'm",
        "bid_low": "❌ Kam! Minimal: {min_bid} so'm",
        "bid_success": "✅ Stavka qabul qilindi!\n💰 {amount} so'm",
        "outbid": "⚠️ Siz ortda qoldingiz!\n🏷 {title}\nYangi: {amount} so'm",
        "winner": "🎉 Siz g'olib bo'ldingiz!\n\n🏷 {title}\n💰 {amount} so'm\n\nAdmin: @{admin}",
        "auction_ended": "🏁 Auksion yakunlandi!\n🏷 {title}\n🥇 {winner}\n💰 {amount} so'm",
        "payment_confirm": "✅ To'lov tasdiqlandi!\n🏷 {title}\n💰 {amount} so'm",
        "no_winner": "😔 Hech kim stavka bermadi.",
        "lang_set": "✅ O'zbek tili!",
    },
    "ru": {
        "start": "👋 Привет! Я Аукцион Бот!\n\n🔨 /auctions - Активные аукционы",
        "no_auctions": "😔 Активных аукционов нет",
        "bid_btn": "💰 Сделать ставку",
        "item_info": "🏷 *{title}*\n\n📝 {description}\n\n💵 Начальная: *{start_price} сум*\n📈 Мин. шаг: *+{min_step} сум*\n⏰ Конец: *{end_time}*\n\n🥇 Максимум: *{current_price} сум*\n👤 Лидер: {leader}",
        "enter_bid": "💰 Введите ставку:\nМинимум: {min_bid} сум",
        "bid_low": "❌ Мало! Минимум: {min_bid} сум",
        "bid_success": "✅ Ставка принята!\n💰 {amount} сум",
        "outbid": "⚠️ Вас обогнали!\n🏷 {title}\nНовый: {amount} сум",
        "winner": "🎉 Вы победили!\n\n🏷 {title}\n💰 {amount} сум\n\nАдмин: @{admin}",
        "auction_ended": "🏁 Аукцион завершён!\n🏷 {title}\n🥇 {winner}\n💰 {amount} сум",
        "payment_confirm": "✅ Оплата подтверждена!\n🏷 {title}\n💰 {amount} сум",
        "no_winner": "😔 Никто не сделал ставку.",
        "lang_set": "✅ Русский язык!",
    }
}

auctions = {}
user_langs = {}
user_states = {}
auction_counter = 0
WAIT_TITLE, WAIT_DESC, WAIT_START_PRICE, WAIT_MIN_STEP, WAIT_DURATION, WAIT_BID = range(6)
logging.basicConfig(level=logging.INFO)

def get_lang(user_id):
    return user_langs.get(user_id, "uz")

def t(user_id, key, **kwargs):
    lang = get_lang(user_id)
    text = TEXTS[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text

def is_admin(user_id):
    return user_id in ADMIN_IDS

def format_time(dt):
    return dt.strftime("%d.%m.%Y %H:%M")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"), InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")]]
    await update.message.reply_text("🌐 Tilni tanlang / Выберите язык:", reply_markup=InlineKeyboardMarkup(keyboard))

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.split("_")[1]
    user_langs[user_id] = lang
    extra = "\n\n🔧 Admin: /newauction | /list" if is_admin(user_id) else ""
    await query.edit_message_text(t(user_id, "start") + extra, parse_mode="Markdown")

async def list_auctions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    active = {k: v for k, v in auctions.items() if v["active"]}
    if not active:
        await update.message.reply_text(t(user_id, "no_auctions"))
        return
    for aid, auction in active.items():
        current = auction.get("current_price", auction["start_price"])
        text = t(user_id, "item_info", title=auction["title"], description=auction["description"], start_price=f"{auction['start_price']:,}", min_step=f"{auction['min_step']:,}", end_time=format_time(auction["end_time"]), current_price=f"{current:,}", leader=auction.get("leader_name", "—"))
        keyboard = [[InlineKeyboardButton(t(user_id, "bid_btn"), callback_data=f"bid_{aid}")]]
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def bid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    aid = query.data.split("_")[1]
    if aid not in auctions or not auctions[aid]["active"]:
        await query.message.reply_text("❌ Auksion topilmadi.")
        return
    auction = auctions[aid]
    current = auction.get("current_price", auction["start_price"])
    min_bid = current + auction["min_step"]
    user_states[user_id] = {"state": WAIT_BID, "auction_id": aid}
    await query.message.reply_text(t(user_id, "enter_bid", min_bid=f"{min_bid:,}"))

async def new_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Faqat adminlar!")
        return
    user_states[user_id] = {"state": WAIT_TITLE, "auction_data": {}}
    await update.message.reply_text("📝 Tovar nomini kiriting:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states:
        return
    state_info = user_states[user_id]
    state = state_info.get("state")
    text = update.message.text
    if state == WAIT_BID:
        try:
            amount = int(text.replace(" ", "").replace(",", ""))
        except:
            await update.message.reply_text("❌ Faqat raqam!")
            return
        aid = state_info["auction_id"]
        auction = auctions.get(aid)
        if not auction or not auction["active"]:
            await update.message.reply_text("❌ Auksion topilmadi.")
            del user_states[user_id]
            return
        current = auction.get("current_price", auction["start_price"])
        min_bid = current + auction["min_step"]
        if amount < min_bid:
            await update.message.reply_text(t(user_id, "bid_low", min_bid=f"{min_bid:,}"))
            return
        prev = auction.get("leader_id")
        if prev and prev != user_id:
            try:
                await context.bot.send_message(prev, t(prev, "outbid", title=auction["title"], amount=f"{amount:,}"), parse_mode="Markdown")
            except:
                pass
        auction["current_price"] = amount
        auction["leader_id"] = user_id
        auction["leader_name"] = update.effective_user.first_name
        del user_states[user_id]
        await update.message.reply_text(t(user_id, "bid_success", amount=f"{amount:,}"))
    elif state == WAIT_TITLE:
        state_info["auction_data"]["title"] = text
        state_info["state"] = WAIT_DESC
        await update.message.reply_text("📝 Tavsif kiriting:")
    elif state == WAIT_DESC:
        state_info["auction_data"]["description"] = text
        state_info["state"] = WAIT_START_PRICE
        await update.message.reply_text("💰 Boshlang'ich narx (so'mda):")
    elif state == WAIT_START_PRICE:
        try:
            state_info["auction_data"]["start_price"] = int(text.replace(" ","").replace(",",""))
            state_info["state"] = WAIT_MIN_STEP
            await update.message.reply_text("📈 Minimal stavka miqdori:")
        except:
            await update.message.reply_text("❌ Faqat raqam!")
    elif state == WAIT_MIN_STEP:
        try:
            state_info["auction_data"]["min_step"] = int(text.replace(" ","").replace(",",""))
            state_info["state"] = WAIT_DURATION
            await update.message.reply_text("⏰ Necha soat? (masalan: 24):")
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
            global auction_counter
            auction_counter += 1
            aid = str(auction_counter)
            auctions[aid] = data
            del user_states[user_id]
            await update.message.reply_text(f"✅ Auksion yaratildi!\n🏷 *{data['title']}*\n⏰ {format_time(data['end_time'])}", parse_mode="Markdown")
            asyncio.create_task(auction_timer(context, aid))
        except:
            await update.message.reply_text("❌ Faqat raqam!")

async def auction_timer(context, aid):
    auction = auctions[aid]
    wait = (auction["end_time"] - datetime.now()).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)
    auction["active"] = False
    for admin_id in ADMIN_IDS:
        if auction["leader_id"]:
            kb = [[InlineKeyboardButton("✅ To'lovni tasdiqlash", callback_data=f"confirm_{aid}")]]
            try:
                await context.bot.send_message(admin_id, t(admin_id, "auction_ended", title=auction["title"], winner=auction["leader_name"], amount=f"{auction['current_price']:,}"), reply_markup=InlineKeyboardMarkup(kb))
            except:
                pass
    if auction["leader_id"]:
        try:
            await context.bot.send_message(auction["leader_id"], t(auction["leader_id"], "winner", title=auction["title"], amount=f"{auction['current_price']:,}", admin="admin"), parse_mode="Markdown")
        except:
            pass

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    aid = query.data.split("_")[1]
    auction = auctions.get(aid)
    if not auction:
        return
    if auction.get("leader_id"):
        try:
            await context.bot.send_message(auction["leader_id"], t(auction["leader_id"], "payment_confirm", title=auction["title"], amount=f"{auction['current_price']:,}"))
        except:
            pass
    await query.edit_message_text(f"✅ Tasdiqlandi!\n🏷 {auction['title']}\n💰 {auction['current_price']:,} so'm")

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    if not auctions:
        await update.message.reply_text("📋 Auksionlar yo'q")
        return
    text = "📋 *AUKSIONLAR:*\n\n"
    for aid, a in auctions.items():
        status = "✅" if a["active"] else "🔴"
        text += f"{status} {a['title']} | {a['current_price']:,} so'm | {a['leader_name']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auctions", list_auctions))
    app.add_handler(CommandHandler("newauction", new_auction))
    app.add_handler(CommandHandler("list", admin_list))
    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(bid_callback, pattern="^bid_"))
    app.add_handler(CallbackQueryHandler(confirm_payment, pattern="^confirm_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
