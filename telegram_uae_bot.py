#!/usr/bin/env python3
"""
Apartment Accountant Bot - Arabic fixed + partner text formatting

- Egyptian Arabic fully applied in Arabic mode
- Partner distribution as clean bullet text (no pipes)
- Numeric choices flow retained (1/2 etc.)
- Token embedded (replace if you want)
"""

import logging
from typing import Dict

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ---------------- CONFIG ----------------
BOT_TOKEN = "8577252107:AAE6JEds5EA9QfqCmSU6ZzpoQ607OAjbUzE"

# Conversation states
LANG, LOC, YR, BED, MAN = range(5)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# ---------------- TEXT (EN + Egyptian AR) ----------------
TEXT = {
    "en": {
        "choose_lang": "🌐 Choose language:\n1 = English\n2 = Egyptian Arabic\n\nClick 1 or 2 (or type).",
        "choose_lang_buttons": [["1", "2"]],
        "ask_location": "📍 Choose location:\n1 = Dubai\n2 = Sharjah\n\nClick 1 or 2.",
        "loc_buttons": [["1", "2"]],
        "ask_yearly": "💰 Enter yearly rent (AED). Example: 85000",
        "ask_bed": "🛏️ Enter monthly bed price (AED) (per bed).",
        "ask_manager": "🧾 Choose manager:\n1 - 50% Partner\n2 - Normal Partner (12.5%)\n\nClick the button or type 1/2.",
        "manager_buttons": [["1 - 50% Partner", "2 - Normal Partner"], ["1", "2"]],
        "invalid_choice": "⚠️ Invalid choice — press a button or type the number.",
        "invalid_number": "⚠️ Invalid number — send digits only (e.g. 85000).",
        "processing": "🔎 Calculating...",
        "result_title": "📊 Apartment Investment Report",
        "done_prompt": "✅ Done — to calculate another apartment, click /start.",
        "guide": "Quick guide:\n/start — restart\nAnswer step-by-step by clicking buttons or typing numbers.",
    },
    "eg": {  # Egyptian Arabic (colloquial)
        "choose_lang": "🌐 اختار اللغة:\n1 = English\n2 = عربي (مصر)\n\nاضغط 1 أو 2 أو اكتبهم.",
        "choose_lang_buttons": [["1", "2"]],
        "ask_location": "📍 اختار المكان:\n1 = دبي\n2 = الشارقة\n\nاضغط 1 أو 2.",
        "loc_buttons": [["1", "2"]],
        "ask_yearly": "💰 اكتب الإيجار السنوي بالدرهم (مثال: 85000)",
        "ask_bed": "🛏️ اكتب سعر السرير الشهري بالدرهم (لكل سرير).",
        "ask_manager": "🧾 اختار المدير:\n1 - شريك 50%\n2 - شريك عادي (12.5%)\n\nاضغط الزر أو اكتب 1/2.",
        "manager_buttons": [["1 - شريك 50%", "2 - شريك عادي (12.5%)"], ["1", "2"]],
        "invalid_choice": "⚠️ اختيار غلط — اضغط الزر أو اكتب الرقم.",
        "invalid_number": "⚠️ رقم مش صالح — ابعت أرقام بس (مثال: 85000).",
        "processing": "🔎 بحسب... لحظة.",
        "result_title": "📊 تقرير استثمار الشقة",
        "done_prompt": "✅ تمام — لو عايز تحسب تاني، اضغط /start.",
        "guide": "دليل سريع:\n/start — ابدأ من الأول\nجاوب بالضغط أو بكتابة الأرقام.",
    },
}


# ---------------- CALCULATION ----------------
def calculate_financials(location: str, yearly_rent: float, bed_price: float, manager_type: int) -> Dict:
    loc = location.strip().lower()
    loc_key = "dubai" if loc in ("1", "dubai", "دبي") else "sharjah"

    monthly_rent = yearly_rent / 12.0
    upfront_months = 4 if loc_key == "dubai" else 3
    upfront_payment = monthly_rent * upfront_months

    commission_deposit = 0.10 * yearly_rent
    legal = 8000.0
    furniture = 8000.0
    total_initial = upfront_payment + commission_deposit + legal + furniture

    total_beds = 12
    monthly_income = bed_price * total_beds

    operating_expenses = 2000.0
    total_monthly_expenses = operating_expenses + monthly_rent

    net_monthly_profit = monthly_income - total_monthly_expenses
    net_profit_10_months = net_monthly_profit * 10.0
    true_net_profit = net_profit_10_months - total_initial

    manager_fee = 0.15 * true_net_profit if true_net_profit > 0 else 0.0
    remaining_after_manager = true_net_profit - manager_fee

    ownership = {"P1": 0.50, "P2": 0.125, "P3": 0.125, "P4": 0.125, "P5": 0.125}

    manager_partner = "P1" if manager_type == 1 else "P2"

    # distribute remaining and add manager fee to manager partner
    partner_distribution = {}
    for p, pct in ownership.items():
        partner_distribution[p] = remaining_after_manager * pct
    partner_distribution[manager_partner] += manager_fee

    partners = []
    for p in ["P1", "P2", "P3", "P4", "P5"]:
        pct = ownership[p]
        init_contrib = total_initial * pct
        yearly_profit = partner_distribution[p]
        monthly_profit = yearly_profit / 12.0
        roi_pct = (yearly_profit / init_contrib * 100.0) if init_contrib != 0 else 0.0
        partners.append(
            {
                "partner": p,
                "ownership_pct": pct * 100.0,
                "initial_investment": init_contrib,
                "yearly_profit": yearly_profit,
                "monthly_profit": monthly_profit,
                "roi_pct": roi_pct,
                "is_manager": (p == manager_partner),
            }
        )

    return {
        "location": loc_key.title(),
        "yearly_rent": yearly_rent,
        "monthly_rent": monthly_rent,
        "upfront_months": upfront_months,
        "upfront_payment": upfront_payment,
        "commission_deposit": commission_deposit,
        "legal": legal,
        "furniture": furniture,
        "total_initial": total_initial,
        "total_beds": total_beds,
        "monthly_income": monthly_income,
        "operating_expenses": operating_expenses,
        "total_monthly_expenses": total_monthly_expenses,
        "net_monthly_profit": net_monthly_profit,
        "net_profit_10_months": net_profit_10_months,
        "true_net_profit": true_net_profit,
        "manager_fee": manager_fee,
        "remaining_after_manager": remaining_after_manager,
        "manager_type": manager_type,
        "manager_partner": manager_partner,
        "partners": partners,
    }


# ---------------- FORMATTING (partner text clean) ----------------
def money(a: float) -> str:
    return f"AED {a:,.2f}"


def build_partner_text(res: Dict, lang: str) -> str:
    lines = []
    if lang == "eg":
        lines.append("🔸 توزيع الأرباح:")
    else:
        lines.append("🔸 Partners distribution:")

    # Build lines with emojis and consistent spacing
    for p in res["partners"]:
        mgr = " 👑 (المدير)" if p["is_manager"] else ""
        if lang == "eg":
            lines.append(
                f"• {p['partner']}{mgr}\n  - نسبة: {p['ownership_pct']:.2f}%\n  - الاستثمار الابتدائي: {money(p['initial_investment'])}\n  - الربح السنوي: {money(p['yearly_profit'])}\n  - شهريًا: {money(p['monthly_profit'])}\n  - عائد: {p['roi_pct']:.2f}%\n"
            )
        else:
            mgr_en = " 👑 (Manager)" if p["is_manager"] else ""
            lines.append(
                f"• {p['partner']}{mgr_en}\n  - Own%: {p['ownership_pct']:.2f}%\n  - Initial: {money(p['initial_investment'])}\n  - Yearly: {money(p['yearly_profit'])}\n  - Monthly: {money(p['monthly_profit'])}\n  - ROI: {p['roi_pct']:.2f}%\n"
            )

    return "\n".join(lines)


def format_report(res: Dict, lang: str) -> str:
    parts = []
    if lang == "eg":
        parts.append("📊 تقرير استثماري للشقة\n")
        parts.append("──────── تفاصيل المصاريف ────────")
    else:
        parts.append("📊 Apartment Investment Report\n")
        parts.append("──────── Initial Cost Breakdown ────────")

    # Initial costs (Arabic labels when eg)
    parts.append("```")
    if lang == "eg":
        parts.append(f"الإيجار الشهري:           {money(res['monthly_rent'])}")
        parts.append(f"الدفع المسبق ({res['upfront_months']} شهر): {money(res['upfront_payment'])}")
        parts.append(f"العمولة + الضمان:         {money(res['commission_deposit'])}")
        parts.append(f"المستندات القانونية:     {money(res['legal'])}")
        parts.append(f"الأثاث:                  {money(res['furniture'])}")
        parts.append(f"إجمالي التكلفة الأولية:   {money(res['total_initial'])}")
    else:
        parts.append(f"Monthly rent:           {money(res['monthly_rent'])}")
        parts.append(f"Upfront payment ({res['upfront_months']} mo): {money(res['upfront_payment'])}")
        parts.append(f"Commission + Deposit:   {money(res['commission_deposit'])}")
        parts.append(f"Legal:                  {money(res['legal'])}")
        parts.append(f"Furniture:              {money(res['furniture'])}")
        parts.append(f"Total initial cost:     {money(res['total_initial'])}")
    parts.append("```")

    # Income & expenses
    if lang == "eg":
        parts.append("──────── الدخل والمصروفات ────────")
    else:
        parts.append("──────── Income & Expenses ────────")
    parts.append("```")
    parts.append(f"Total monthly income:   {money(res['monthly_income'])}")
    parts.append(f"Total monthly expenses: {money(res['total_monthly_expenses'])}")
    parts.append(f"Net monthly profit:     {money(res['net_monthly_profit'])}")
    parts.append(f"Net profit (10 months): {money(res['net_profit_10_months'])}")
    parts.append(f"True Net Profit (Y1):   {money(res['true_net_profit'])}")
    parts.append("```")

    # Manager fee block (Arabic labels if eg)
    if lang == "eg":
        parts.append("──────── رسوم المدير ────────")
    else:
        parts.append("──────── Manager Fee ────────")
    parts.append("```")
    if lang == "eg":
        parts.append(f"المدير:                 {res['manager_partner']}")
        parts.append(f"مكافأة المدير 15%:      {money(res['manager_fee'])}")
        parts.append(f"المتبقي للشركاء:         {money(res['remaining_after_manager'])}")
    else:
        parts.append(f"Manager:                {res['manager_partner']}")
        parts.append(f"Manager 15% amount:     {money(res['manager_fee'])}")
        parts.append(f"Remaining for partners: {money(res['remaining_after_manager'])}")
    parts.append("```")

    # Partner distribution as clean text (no pipes)
    parts.append(build_partner_text(res, lang))

    # Profitability summary
    if lang == "eg":
        parts.append("──────── ملخص الربحية ────────")
        p1 = next(x for x in res["partners"] if x["partner"] == "P1")
        avg12 = sum(x["roi_pct"] for x in res["partners"] if x["partner"] != "P1") / 4.0
        parts.append(f"صافي الربح الحقيقي (سنة1): {money(res['true_net_profit'])}")
        parts.append(f"عائد شريك 50%: {p1['roi_pct']:.2f}%")
        parts.append(f"عائد الشركاء 12.5% (متوسط): {avg12:.2f}%")
        parts.append(f"مكافأة المدير: {money(res['manager_fee'])}")
        parts.append("\n✅ تمام — لو عايز تحسب تاني، اضغط /start.")
    else:
        parts.append("──────── Profitability Summary ────────")
        p1 = next(x for x in res["partners"] if x["partner"] == "P1")
        avg12 = sum(x["roi_pct"] for x in res["partners"] if x["partner"] != "P1") / 4.0
        parts.append(f"Total true net profit (Y1): {money(res['true_net_profit'])}")
        parts.append(f"ROI - 50% partner: {p1['roi_pct']:.2f}%")
        parts.append(f"ROI - 12.5% partners (avg): {avg12:.2f}%")
        parts.append(f"Manager fee: {money(res['manager_fee'])}")
        parts.append("\n✅ Done — to calculate another apartment, click /start.")

    return "\n".join(parts)


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup(TEXT["en"]["choose_lang_buttons"], one_time_keyboard=False, resize_keyboard=True)
    await update.message.reply_text(TEXT["en"]["choose_lang"], reply_markup=kb)
    return LANG


async def lang_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt == "1":
        context.user_data["lang"] = "en"
    elif txt == "2":
        context.user_data["lang"] = "eg"
    else:
        await update.message.reply_text(TEXT["en"]["invalid_choice"])
        return LANG

    lang = context.user_data["lang"]
    kb = ReplyKeyboardMarkup(TEXT[lang]["loc_buttons"], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(TEXT[lang]["ask_location"], reply_markup=kb)
    return LOC


async def location_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip()
    if txt not in ("1", "2"):
        await update.message.reply_text(TEXT[lang]["invalid_choice"])
        return LOC

    context.user_data["location"] = "dubai" if txt == "1" else "sharjah"
    await update.message.reply_text(TEXT[lang]["ask_yearly"], reply_markup=ReplyKeyboardRemove())
    return YR


async def yearly_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip().replace(",", "")
    try:
        val = float(txt)
    except:
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return YR
    context.user_data["yearly_rent"] = val
    await update.message.reply_text(TEXT[lang]["ask_bed"])
    return BED


async def bed_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip().replace(",", "")
    try:
        val = float(txt)
    except:
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return BED

    context.user_data["bed_price"] = val
    kb = ReplyKeyboardMarkup(TEXT[lang]["manager_buttons"], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(TEXT[lang]["ask_manager"], reply_markup=kb)
    return MAN


async def manager_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip()
    if txt.startswith("1"):
        mgr = 1
    elif txt.startswith("2"):
        mgr = 2
    else:
        await update.message.reply_text(TEXT[lang]["invalid_choice"])
        return MAN

    await update.message.reply_text(TEXT[lang]["processing"])

    res = calculate_financials(
        context.user_data["location"],
        context.user_data["yearly_rent"],
        context.user_data["bed_price"],
        mgr,
    )

    report_text = format_report(res, context.user_data.get("lang", "en"))

    # send report and remove keyboard
    await update.message.reply_text(report_text, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

    # send short done prompt (also in report)
    if context.user_data.get("lang", "en") == "eg":
        await update.message.reply_text(TEXT["eg"]["done_prompt"])
    else:
        await update.message.reply_text(TEXT["en"]["done_prompt"])

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_selected)],
            LOC: [MessageHandler(filters.TEXT & ~filters.COMMAND, location_received)],
            YR: [MessageHandler(filters.TEXT & ~filters.COMMAND, yearly_received)],
            BED: [MessageHandler(filters.TEXT & ~filters.COMMAND, bed_received)],
            MAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, manager_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("guide", lambda u, c: u.message.reply_text(TEXT.get(c.user_data.get("lang","en"), TEXT["en"])["choose_lang"])))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text(TEXT.get(c.user_data.get("lang","en"), TEXT["en"])["choose_lang"])))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
