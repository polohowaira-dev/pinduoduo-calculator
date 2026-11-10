
import os
import math
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

PRICE, WEIGHT, CNY_RATE, USD_RATE, JP_EXTRA, FREE_EXTRA = range(6)

TAX_RATE = 0.19

keyboard = ReplyKeyboardMarkup(
    [["/calc", "/cancel"]],
    resize_keyboard=True
)


def money(value):
    return f"{round(value):,}".replace(",", " ") + " ₸"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🛍️ Я калькулятор доставки Pinduoduo.\n\n"
        "Сравню Jańa Post и вариант с бесплатной доставкой.\n\n"
        "Jańa Post: $4,29/кг, вес округляется вверх.\n"
        "Автоматический сбор: 19% от стоимости товара.\n"
        "Все результаты — в тенге.\n\n"
        "Нажми /calc, чтобы начать расчёт.",
        reply_markup=keyboard
    )


async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Шаг 1 из 6\n\n"
        "Введи цену товара в юанях (¥).\n"
        "Например: 100"
    )
    return PRICE


async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.replace(",", "."))
        if not math.isfinite(value) or value < 0:
            raise ValueError
        context.user_data["price"] = value
    except ValueError:
        await update.message.reply_text("Введи число, например 100.")
        return PRICE

    await update.message.reply_text(
        "Шаг 2 из 6\n\nВведи вес посылки в кг.\nНапример: 1.2"
    )
    return WEIGHT


async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.replace(",", "."))
        if not math.isfinite(value) or value <= 0:
            raise ValueError
        context.user_data["weight"] = value
    except ValueError:
        await update.message.reply_text(
            "Вес должен быть больше нуля. Например: 1.2"
        )
        return WEIGHT

    await update.message.reply_text(
        "Шаг 3 из 6\n\n"
        "Сколько тенге стоит 1 юань?\n"
        "Введи свой курс, например: 70"
    )
    return CNY_RATE


async def get_cny(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.replace(",", "."))
        if not math.isfinite(value) or value <= 0:
            raise ValueError
        context.user_data["cny"] = value
    except ValueError:
        await update.message.reply_text("Введи курс числом больше нуля.")
        return CNY_RATE

    await update.message.reply_text(
        "Шаг 4 из 6\n\n"
        "Сколько тенге стоит 1 доллар США?\n"
        "Введи свой курс, например: 500"
    )
    return USD_RATE


async def get_usd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.replace(",", "."))
        if not math.isfinite(value) or value <= 0:
            raise ValueError
        context.user_data["usd"] = value
    except ValueError:
        await update.message.reply_text("Введи курс числом больше нуля.")
        return USD_RATE

    await update.message.reply_text(
        "Шаг 5 из 6\n\n"
        "Дополнительные расходы Jańa Post в тенге.\n"
        "Если их нет, введи 0."
    )
    return JP_EXTRA


async def get_jp_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.replace(",", "."))
        if not math.isfinite(value) or value < 0:
            raise ValueError
        context.user_data["jp_extra"] = value
    except ValueError:
        await update.message.reply_text("Введи число от 0 и выше.")
        return JP_EXTRA

    await update.message.reply_text(
        "Шаг 6 из 6\n\n"
        "Дополнительные расходы при бесплатной доставке "
        "Pinduoduo в тенге.\n"
        "Укажи другие комиссии и расходы, если они есть. "
        "Сбор 19% уже будет добавлен автоматически. "
        "Если других расходов нет, введи 0."
    )
    return FREE_EXTRA


async def get_free_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.replace(",", "."))
        if not math.isfinite(value) or value < 0:
            raise ValueError
        context.user_data["free_extra"] = value
    except ValueError:
        await update.message.reply_text("Введи число от 0 и выше.")
        return FREE_EXTRA

    d = context.user_data

    product = d["price"] * d["cny"]
    tax = product * TAX_RATE

    billed_weight = math.ceil(d["weight"])
    shipping = billed_weight * 4.29 * d["usd"]

    jp_total = product + tax + shipping + d["jp_extra"]
    free_total = product + tax + d["free_extra"]

    difference = abs(jp_total - free_total)

    if jp_total < free_total:
        verdict = "✅ Выгоднее Jańa Post"
    elif free_total < jp_total:
        verdict = "✅ Выгоднее бесплатная доставка"
    else:
        verdict = "🤝 Стоимость одинаковая"

    result = (
        "📊 СРАВНЕНИЕ ДОСТАВКИ\n\n"
        f"Цена товара: {d['price']:g} ¥ = {money(product)}\n"
        f"Сбор 19% от товара: {money(tax)}\n"
        f"Товар + сбор: {money(product + tax)}\n"
        f"Фактический вес: {d['weight']:g} кг\n"
        f"Оплачиваемый вес Jańa Post: {billed_weight} кг\n\n"
        "🚚 JAŃA POST\n"
        f"Доставка: {billed_weight} × $4,29 × "
        f"{d['usd']:g} ₸ = {money(shipping)}\n"
        f"Другие дополнительные расходы: {money(d['jp_extra'])}\n"
        f"ИТОГО: {money(jp_total)}\n\n"
        "📦 БЕСПЛАТНАЯ ДОСТАВКА PINDUODUO\n"
        "Доставка: 0 ₸\n"
        f"Другие дополнительные расходы: {money(d['free_extra'])}\n"
        f"ИТОГО: {money(free_total)}\n\n"
        f"{verdict}\n"
        f"Разница: {money(difference)}\n\n"
        "Важно: сбор 19% рассчитан от стоимости товара "
        "в тенге и включён в оба варианта. "
        "Убедись, что это именно тот сбор, который тебе нужен."
    )

    await update.message.reply_text(result, reply_markup=keyboard)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Расчёт отменён. Для нового расчёта нажми /calc.",
        reply_markup=keyboard
    )
    return ConversationHandler.END


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")

    app = Application.builder().token(token).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("calc", calc)],
        states={
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            CNY_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cny)],
            USD_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_usd)],
            JP_EXTRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_jp_extra)],
            FREE_EXTRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_free_extra)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conversation)
    app.run_polling()


if __name__ == "__main__":
    main()
