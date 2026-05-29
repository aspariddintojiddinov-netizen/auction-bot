import asyncio
import logging
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8986359963:AAFe1v3aNp6ASkcPKD5Qozi8FSyjWaCa5C4")
ADMIN_IDS = [8575593397]

logging.basicConfig(level=logging.INFO)

TEXTS = {
    "uz": {
        "start": "Salom! Men Auksion Botman!\n\n/auctions - Faol auksionlar",
        "no_auctions": "Hozircha faol auksion yoq",
        "bid_btn": "Stavka berish",
        "item_info": "{title}\n\n{description}\n\nBoshlanich: {start_price} som\nMinimal stavka: +{min_step} som\nTugash: {end_time}\n\nEng yuqori: {current_price} som\nLider: {leader}",
        "enter_bid": "Stavkangizni kiriting (somda):\nMinimal: {min_bid} som",
        "bid_low": "Kam! Minimal: {min_bid} som",
        "bid_success": "Stavka qabul qilindi! {amount} som",
        "outbid": "Siz ortda qoldingiz!\n{title}\nYangi lider: {amount} som",
        "winner": "Siz golib boldingiz!\n\n{title}\n{amount} som\n\nAdmin bilan boglanin",
        "auction_ended": "Auksion yakunlandi!\n{title}\nGolib: {winner}\n{amount} som",
        "payment_confirm": "Tolov tasdiqlandi!\n{title}\n{amount} som",
        "no_winner": "Hech kim stavka bermadi.",
    },
    "ru": {
        "start": "Привет! Я Аукцион Бот!\n\n/auctions - Активные аукционы",
        "no_auctions": "Активных аукционов нет",
        "bid_btn": "Сделать ставку",
        "item_info": "{title}\n\n{description}\n\nНачальная: {start_price} сум\nМин. шаг: +{min_step} сум\nКонец: {end_time}\n\nМаксимум: {current_price} сум\nЛидер: {leader}",
        "enter_bid": "Введите ставку (в сумах):\nМинимум: {min_bid} сум",
        "bid_low": "Мало! Минимум: {min_bid} сум",
        "bid_success": "Ставка принята! {amount} сум",
        "outbid": "Вас обогнали!\n{title}\nНовый лидер: {amount} сум",
        "winner": "Вы победили!\n\n{title}\n{amount} сум\n\nСвяжитесь с администратором",
        "auction_ended": "Аукцион завершён!\n{title}\nПобедитель: {winner}\n{amount} сум",
        "payment_confirm": "Оплата подтверждена!\n{title}\n{amount} сум",
        "no_winner": "Никто не сделал ставку.",
    }
}

auctions = {}
user_langs = {}
user_states = {}
auction_counter = 0
WAIT_TITLE, WAIT_DESC, WAIT_PRICE, WAIT_STEP, WAIT_DURATION, WAIT_BID = range(6)

def lang(uid): return user_langs.get(uid, "uz")
def t(uid, key, **kw):
    txt = TEXTS[lang(uid)].get(key, key)
    return txt.format(**kw) if kw else txt
def is_admin(uid): return uid in ADMIN_IDS
def ftime(dt): return dt.strftime("%d.%m.%Y %H:%M")

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("O'zbek", callback_data="lang_uz"),
           InlineKeyboardButton("Русский", callback_data="lang_ru")]]
    await update.message.reply_text("Tilni tanlang / Выберите язык:",
                                     reply_markup=InlineKeyboardMarkup(kb))

async def set_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    user_langs[uid] = q.data.split("_")[1]
    extra = "\n\nAdmin: /newauction | /list" if is_admin(uid) else ""
    await q.edit_message_text(t(uid, "start") + extra)

async def auctions_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    active = {k: v for k, v in auctions.items() if v["active"]}
    if not active:
        await update.message.reply_text(t(uid, "no_auctions"))
        return
    for aid, a in active.items():
        cur = a.get("current_price", a["start_price"])
        text = t(uid, "item_info",
                 title=a["title"], description=a["description"],
                 start_price=f"{a['start_price']:,}", min_step=f"{a['min_step']:,}",
                 end_time=ftime(a["end_time"]), current_price=f"{cur:,}",
                 leader=a.get("leader_name", "---"))
        kb = [[InlineKeyboardButton(t(uid, "bid_btn"), callback_data=f"bid_{aid}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def bid_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    aid = q.data.split("_")[1]
    if aid not in auctions or not auctions[aid]["active"]:
        await q.message.reply_text("Auksion topilmadi.")
        return
    a = auctions[aid]
    min_bid = a.get("current_price", a["start_price"]) + a["min_step"]
    user_states[uid] = {"state": WAIT_BID, "auction_id": aid}
    await q.message.reply_text(t(uid, "enter_bid", min_bid=f"{min_bid:,}"))

async def new_auction(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("Faqat adminlar!")
        return
    user_states[uid] = {"state": WAIT_TITLE, "data": {}}
    await update.message.reply_text("Tovar nomini kiriting:")

async def admin_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    if not auctions:
        await update.message.reply_text("Auksionlar yoq")
        return
    text = "AUKSIONLAR:\n\n"
    for aid, a in auctions.items():
        s = "Faol" if a["active"] else "Tugagan"
        text += f"{s} | {a['title']} | {a['current_price']:,} som | {a['leader_name']}\n"
    await update.message.reply_text(text)

async def handle_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_states:
        return
    si = user_states[uid]
    state = si.get("state")
    text = update.message.text

    if state == WAIT_BID:
        try:
            amount = int(text.replace(" ", "").replace(",", ""))
        except:
            await update.message.reply_text("Faqat raqam!")
            return
        aid = si["auction_id"]
        a = auctions.get(aid)
        if not a or not a["active"]:
            await update.message.reply_text("Auksion topilmadi.")
            del user_states[uid]
            return
        min_bid = a.get("current_price", a["start_price"]) + a["min_step"]
        if amount < min_bid:
            await update.message.reply_text(t(uid, "bid_low", min_bid=f"{min_bid:,}"))
            return
        prev = a.get("leader_id")
        if prev and prev != uid:
            try:
                await ctx.bot.send_message(prev, t(prev, "outbid", title=a["title"], amount=f"{amount:,}"))
            except:
                pass
        a["current_price"] = amount
        a["leader_id"] = uid
        a["leader_name"] = update.effective_user.first_name
        del user_states[uid]
        await update.message.reply_text(t(uid, "bid_success", amount=f"{amount:,}"))

    elif state == WAIT_TITLE:
        si["data"]["title"] = text
        si["state"] = WAIT_DESC
        await update.message.reply_text("Tavsif kiriting:")

    elif state == WAIT_DESC:
        si["data"]["description"] = text
        si["state"] = WAIT_PRICE
        await update.message.reply_text("Boshlangich narx (somda):")

    elif state == WAIT_PRICE:
        try:
            si["data"]["start_price"] = int(text.replace(" ", "").replace(",", ""))
            si["state"] = WAIT_STEP
            await update.message.reply_text("Minimal stavka miqdori (somda):")
        except:
            await update.message.reply_text("Faqat raqam!")

    elif state == WAIT_STEP:
        try:
            si["data"]["min_step"] = int(text.replace(" ", "").replace(",", ""))
            si["state"] = WAIT_DURATION
            await update.message.reply_text("Necha soat davom etsin? (masalan: 24)")
        except:
            await update.message.reply_text("Faqat raqam!")

    elif state == WAIT_DURATION:
        try:
            hours = float(text)
            d = si["data"]
            d["end_time"] = datetime.now() + timedelta(hours=hours)
            d["active"] = True
            d["current_price"] = d["start_price"]
            d["leader_id"] = None
            d["leader_name"] = "---"
            global auction_counter
            auction_counter += 1
            aid = str(auction_counter)
            auctions[aid] = d
            del user_states[uid]
            await update.message.reply_text(
                f"Auksion yaratildi!\n{d['title']}\nTugaydi: {ftime(d['end_time'])}")
            asyncio.create_task(auction_timer(ctx, aid))
        except:
            await update.message.reply_text("Faqat raqam!")

async def auction_timer(ctx, aid):
    a = auctions[aid]
    wait = (a["end_time"] - datetime.now()).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)
    a["active"] = False
    for admin_id in ADMIN_IDS:
        if a["leader_id"]:
            kb = [[InlineKeyboardButton("Tolovni tasdiqlash", callback_data=f"confirm_{aid}")]]
            try:
                await ctx.bot.send_message(
                    admin_id,
                    t(admin_id, "auction_ended", title=a["title"],
                      winner=a["leader_name"], amount=f"{a['current_price']:,}"),
                    reply_markup=InlineKeyboardMarkup(kb))
            except:
                pass
        else:
            try:
                await ctx.bot.send_message(admin_id, t(admin_id, "no_winner"))
            except:
                pass
    if a["leader_id"]:
        try:
            await ctx.bot.send_message(
                a["leader_id"],
                t(a["leader_id"], "winner", title=a["title"], amount=f"{a['current_price']:,}"))
        except:
            pass

async def confirm_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        return
    aid = q.data.split("_")[1]
    a = auctions.get(aid)
    if not a:
        return
    if a.get("leader_id"):
        try:
            await ctx.bot.send_message(
                a["leader_id"],
                t(a["leader_id"], "payment_confirm",
                  title=a["title"], amount=f"{a['current_price']:,}"))
        except:
            pass
    await q.edit_message_text(f"Tasdiqlandi! {a['title']} | {a['current_price']:,} som")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auctions", auctions_cmd))
    app.add_handler(CommandHandler("newauction", new_auction))
    app.add_handler(CommandHandler("list", admin_list))
    app.add_handler(CallbackQueryHandler(set_lang, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(bid_cb, pattern="^bid_"))
    app.add_handler(CallbackQueryHandler(confirm_payment, pattern="^confirm_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    print("Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
