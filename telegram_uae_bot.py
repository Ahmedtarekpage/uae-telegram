#!/usr/bin/env python3
"""
Apartment Accountant Bot - Rooms & Beds flow

Flow:
 /start -> language -> location -> number of rooms ->
   for each room: ask "how many beds?" -> "how many of these are double?"
 -> ask "beds in hall?" -> "how many of hall beds are double?" ->
 -> monthly bed price -> manager selection -> report

Assumptions:
 - double bed counts as 2 bed-units (i.e. adds +1 unit compared to single)
 - monthly income = total_bed_units * monthly_bed_price
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
LANG, LOC, ROOMS_NUM, ROOM_BEDS, ROOM_DOUBLES, HALL_BEDS, HALL_DOUBLES, BED_PRICE, MAN = range(9)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# ---------------- TEXT (EN + Egyptian AR) ----------------
TEXT = {
    "en": {
        "choose_lang": "🌐 Choose language:\n1 = English\n2 = Egyptian Arabic\n\nClick 1 or 2 (or type it).",
        "choose_lang_buttons": [["1", "2"]],
        "ask_location": "📍 Choose location:\n1 = Dubai\n2 = Sharjah\n\nClick 1 or 2.",
        "loc_buttons": [["1", "2"]],
        "ask_rooms": "🏘️ How many rooms are in the apartment? (send a number, e.g. 2)",
        "ask_beds_room": "🛏️ Room {i}: How many beds in this room? (send a number)",
        "ask_doubles_room": "🔁 Of those {beds} beds in room {i}, how many are double beds? (send 0 if none)",
        "ask_hall_beds": "🛋️ Are there beds in the hall/common area? How many beds? (send 0 if none)",
        "ask_hall_doubles": "🔁 Of those hall beds ({beds}), how many are double beds?",
        "ask_bed_price": "💵 Enter the *monthly bed price* (AED) — the bot will multiply price × total bed-units.\nExample: 1300",
        "ask_manager": "🧾 Choose manager:\n1 - 50% Partner\n2 - Normal Partner (12.5%)\n\nClick the button or type 1/2.",
        "manager_buttons": [["1 - 50% Partner", "2 - Normal Partner"], ["1", "2"]],
        "invalid_choice": "⚠️ Invalid choice — please press the button or type the number shown.",
        "invalid_number": "⚠️ Please send a valid integer number (digits only).",
        "processing": "🔎 Calculating results...",
        "result_title": "📊 Apartment Investment Report",
        "done_prompt": "✅ Done — to calculate another apartment, click /start.",
    },
    "eg": {  # Egyptian Arabic
        "choose_lang": "🌐 اختار اللغة:\n1 = English\n2 = عربي (مصر)\n\nاضغط 1 أو 2 أو اكتبهم.",
        "choose_lang_buttons": [["1", "2"]],
        "ask_location": "📍 اختار المكان:\n1 = دبي\n2 = الشارقة\n\nاضغط 1 أو 2.",
        "loc_buttons": [["1", "2"]],
        "ask_rooms": "🏘️ كام أوضة في الشقة؟ (اكتب رقم، مثال: 2)",
        "ask_beds_room": "🛏️ أوضة {i}: كام سرير في الأوضة دي؟ (اكتب رقم)",
        "ask_doubles_room": "🔁 من {beds} سرير في الأوضة {i} كام منهم مزدوج (double)؟ (اكتب 0 لو مفيش)",
        "ask_hall_beds": "🛋️ في سرير في الصالة/الهول؟ كام سرير في الهول؟ (اكتب 0 لو مفيش)",
        "ask_hall_doubles": "🔁 من سرر الهول ({beds}) كام منهم مزدوج؟",
        "ask_bed_price": "💵 اكتب سعر السرير الشهري (بالدرهم). البرنامج هيضرب السعر × عدد وحدات السرير (مثال: 1300)",
        "ask_manager": "🧾 اختار المدير:\n1 - شريك 50%\n2 - شريك عادي (12.5%)\n\nاضغط أو اكتب 1/2.",
        "manager_buttons": [["1 - شريك 50%", "2 - شريك عادي (12.5%)"], ["1", "2"]],
        "invalid_choice": "⚠️ اختيار غلط — اضغط الزر أو اكتب الرقم.",
        "invalid_number": "⚠️ رجاءً ابعت رقم صحيح (أرقام بس).",
        "processing": "🔎 بحسب... لحظة.",
        "result_title": "📊 تقرير استثمار الشقة",
        "done_prompt": "✅ تمام — لو عايز تحسب تاني، اضغط /start.",
    },
}


# ---------------- CALCULATION LOGIC ----------------
def calculate_financials_from_inputs(data: Dict) -> Dict:
    """
    Inputs in `data`:
      - location ('dubai' or 'sharjah')
      - rooms: list of dicts per room: {'beds': int, 'doubles': int}
      - hall_beds: int
      - hall_doubles: int
      - bed_price: float (monthly bed price)
      - manager_type: int (1 or 2)
    """
    location = data["location"]
    rooms = data["rooms"]
    hall_beds = data["hall_beds"]
    hall_doubles = data["hall_doubles"]
    bed_price = data["bed_price"]
    manager_type = data["manager_type"]

    # total counts
    total_reported_beds = sum(r["beds"] for r in rooms) + hall_beds
    total_double_counts = sum(r["doubles"] for r in rooms) + hall_doubles

    # total bed-units: each bed counted + +1 for each double (double counts as 2 units)
    total_bed_units = total_reported_beds + total_double_counts

    # monthly income based on bed units
    monthly_income = bed_price * total_bed_units

    # previous rules:
    yearly_rent = data.get("yearly_rent", 0.0)  # user may still provide yearly rent? but we keep previous rules expecting yearly_rent for rent calculation
    # If yearly_rent is not provided, we compute monthly_rent from bed price? However original rules used yearly_rent to calculate landlord rent to be paid monthly.
    # We'll require yearly_rent to be 0 in data -> monthly_rent = 0 (no monthly rent expense). But to remain consistent with earlier flow, check if user provided yearly elsewhere.
    monthly_rent = data.get("monthly_rent_from_yearly") or (data.get("yearly_rent", 0.0) / 12.0)

    # Choose locale to detect upfront months
    loc_key = "dubai" if location.lower().startswith("d") or location == "dubai" else "sharjah"
    upfront_months = 4 if loc_key == "dubai" else 3
    upfront_payment = monthly_rent * upfront_months

    commission_deposit = 0.10 * data.get("yearly_rent", 0.0)
    legal = 8000.0
    furniture = 8000.0
    total_initial = upfront_payment + commission_deposit + legal + furniture

    operating_expenses = 2000.0
    total_monthly_expenses = operating_expenses + monthly_rent

    net_monthly_profit = monthly_income - total_monthly_expenses
    net_profit_10_months = net_monthly_profit * 10.0
    true_net_profit = net_profit_10_months - total_initial

    manager_fee = 0.15 * true_net_profit if true_net_profit > 0 else 0.0
    remaining_after_manager = true_net_profit - manager_fee

    ownership = {"P1": 0.50, "P2": 0.125, "P3": 0.125, "P4": 0.125, "P5": 0.125}
    manager_partner = "P1" if manager_type == 1 else "P2"

    # Distribute to partners and give manager fee
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
        "rooms": rooms,
        "hall_beds": hall_beds,
        "hall_doubles": hall_doubles,
        "total_reported_beds": total_reported_beds,
        "total_double_counts": total_double_counts,
        "total_bed_units": total_bed_units,
        "bed_price": bed_price,
        "monthly_income": monthly_income,
        "monthly_rent": monthly_rent,
        "upfront_months": upfront_months,
        "upfront_payment": upfront_payment,
        "commission_deposit": commission_deposit,
        "legal": legal,
        "furniture": furniture,
        "total_initial": total_initial,
        "operating_expenses": operating_expenses,
        "total_monthly_expenses": total_monthly_expenses,
        "net_monthly_profit": net_monthly_profit,
        "net_profit_10_months": net_profit_10_months,
        "true_net_profit": true_net_profit,
        "manager_fee": manager_fee,
        "remaining_after_manager": remaining_after_manager,
        "partners": partners,
        "manager_partner": manager_partner,
    }


# ---------------- FORMATTING ----------------
def money(a: float) -> str:
    return f"AED {a:,.2f}"


def build_partner_text(res: Dict, lang: str) -> str:
    lines = []
    if lang == "eg":
        lines.append("🔸 توزيع الأرباح:")
    else:
        lines.append("🔸 Partners distribution:")

    for p in res["partners"]:
        mgr = " 👑 (المدير)" if p["is_manager"] else ""
        if lang == "eg":
            lines.append(
                f"• {p['partner']}{mgr}\n"
                f"  - نسبة: {p['ownership_pct']:.2f}%\n"
                f"  - الاستثمار الابتدائي: {money(p['initial_investment'])}\n"
                f"  - الربح السنوي: {money(p['yearly_profit'])}\n"
                f"  - شهريًا: {money(p['monthly_profit'])}\n"
                f"  - عائد: {p['roi_pct']:.2f}%\n"
            )
        else:
            mgr_en = " 👑 (Manager)" if p["is_manager"] else ""
            lines.append(
                f"• {p['partner']}{mgr_en}\n"
                f"  - Own%: {p['ownership_pct']:.2f}%\n"
                f"  - Initial: {money(p['initial_investment'])}\n"
                f"  - Yearly: {money(p['yearly_profit'])}\n"
                f"  - Monthly: {money(p['monthly_profit'])}\n"
                f"  - ROI: {p['roi_pct']:.2f}%\n"
            )

    return "\n".join(lines)


def build_expenses_lines(res: Dict, lang: str) -> list:
    op = res["operating_expenses"]
    mr = res["monthly_rent"]
    total = res["total_monthly_expenses"]
    if lang == "eg":
        return [
            f"المصاريف التشغيلية (ثابتة): {money(op)} / شهر",
            f"الإيجار الشهري (من الإيجار السنوي): {money(mr)} / شهر",
            f"إجمالي المصروفات الشهرية: {money(total)} / شهر",
        ]
    else:
        return [
            f"Operating expenses (fixed): {money(op)} / month",
            f"Monthly rent (from yearly): {money(mr)} / month",
            f"Total monthly expenses: {money(total)} / month",
        ]


def format_report(res: Dict, lang: str) -> str:
    parts = []

    # Header and basics
    if lang == "eg":
        parts.append("📊 تقرير استثماري للشقة\n")
        parts.append("──────── ملخص الأسرة والأسرّة ────────")
        # beds summary
        parts.append(f"• الأوض: {len(res['rooms'])}")
        parts.append(f"• إجمالي الأسرة المبلغ عنها: {res['total_reported_beds']}")
        parts.append(f"• عدد الأسرة المزدوجة المبلغ عنها: {res['total_double_counts']}")
        parts.append(f"• إجمالي وحدات الأسرة (double counted as 2): {res['total_bed_units']}")
        parts.append(f"• سعر السرير الشهري: {money(res['bed_price'])}")
    else:
        parts.append("📊 Apartment Investment Report\n")
        parts.append("──────── Rooms & Beds Summary ────────")
        parts.append(f"• Rooms: {len(res['rooms'])}")
        parts.append(f"• Reported beds (count): {res['total_reported_beds']}")
        parts.append(f"• Double beds reported: {res['total_double_counts']}")
        parts.append(f"• Total bed-units (double counts as 2): {res['total_bed_units']}")
        parts.append(f"• Monthly bed price: {money(res['bed_price'])}")

    # Initial costs block
    parts.append("\n──────── تفاصيل التكاليف الأولية ────────" if lang == "eg" else "\n──────── Initial Cost Breakdown ────────")
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

    # Income & expenses with expanded details
    parts.append("\n──────── الدخل والمصروفات ────────" if lang == "eg" else "\n──────── Income & Expenses ────────")
    parts.append("```")
    parts.append(f"Total monthly income:   {money(res['monthly_income'])}")
    for ln in build_expenses_lines(res, lang):
        parts.append(ln)
    parts.append(f"Net monthly profit:     {money(res['net_monthly_profit'])}")
    parts.append(f"Net profit (10 months): {money(res['net_profit_10_months'])}")
    parts.append(f"True Net Profit (Y1):   {money(res['true_net_profit'])}")
    parts.append("```")

    # Manager fee
    parts.append("\n──────── رسوم المدير ────────" if lang == "eg" else "\n──────── Manager Fee ────────")
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

    # Partner distribution as text
    parts.append("\n" + build_partner_text(res, lang))

    # Profitability summary
    if lang == "eg":
        parts.append("\n──────── ملخص الربحية ────────")
        p1 = next(x for x in res["partners"] if x["partner"] == "P1")
        avg12 = sum(x["roi_pct"] for x in res["partners"] if x["partner"] != "P1") / 4.0
        parts.append(f"صافي الربح الحقيقي (سنة1): {money(res['true_net_profit'])}")
        parts.append(f"عائد شريك 50%: {p1['roi_pct']:.2f}%")
        parts.append(f"عائد الشركاء 12.5% (متوسط): {avg12:.2f}%")
        parts.append(f"مكافأة المدير: {money(res['manager_fee'])}")
        parts.append("\n" + TEXT["eg"]["done_prompt"])
    else:
        parts.append("\n──────── Profitability Summary ────────")
        p1 = next(x for x in res["partners"] if x["partner"] == "P1")
        avg12 = sum(x["roi_pct"] for x in res["partners"] if x["partner"] != "P1") / 4.0
        parts.append(f"Total true net profit (Y1): {money(res['true_net_profit'])}")
        parts.append(f"ROI - 50% partner: {p1['roi_pct']:.2f}%")
        parts.append(f"ROI - 12.5% partners (avg): {avg12:.2f}%")
        parts.append(f"Manager fee: {money(res['manager_fee'])}")
        parts.append("\n" + TEXT["en"]["done_prompt"])

    return "\n".join(parts)


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup(TEXT["en"]["choose_lang_buttons"], one_time_keyboard=False, resize_keyboard=True)
    await update.message.reply_text(TEXT["en"]["choose_lang"], reply_markup=kb)
    # initialize conversation data
    context.user_data.clear()
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

    # ask number of rooms
    await update.message.reply_text(TEXT[lang]["ask_rooms"], reply_markup=ReplyKeyboardRemove())
    return ROOMS_NUM


async def rooms_num_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip()
    if not txt.isdigit() or int(txt) < 0:
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return ROOMS_NUM

    rooms_count = int(txt)
    context.user_data["rooms_count"] = rooms_count
    context.user_data["rooms"] = []  # will store dicts {'beds': int, 'doubles': int}
    context.user_data["current_room"] = 1

    if rooms_count == 0:
        # skip straight to hall beds
        await update.message.reply_text(TEXT[lang]["ask_hall_beds"])
        return HALL_BEDS

    # ask about room 1 beds
    prompt = TEXT[lang]["ask_beds_room"].format(i=1)
    await update.message.reply_text(prompt)
    return ROOM_BEDS


async def room_beds_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip()
    if not txt.isdigit() or int(txt) < 0:
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return ROOM_BEDS

    beds = int(txt)
    context.user_data.setdefault("temp_room", {})["beds"] = beds

    # ask how many of these are double
    prompt = TEXT[lang]["ask_doubles_room"].format(i=context.user_data["current_room"], beds=beds)
    await update.message.reply_text(prompt)
    return ROOM_DOUBLES


async def room_doubles_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip()
    if not txt.isdigit() or int(txt) < 0:
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return ROOM_DOUBLES

    doubles = int(txt)
    temp = context.user_data.get("temp_room", {})
    beds = temp.get("beds", 0)
    if doubles > beds:
        # cannot have more doubles than beds
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return ROOM_DOUBLES

    # append room record
    context.user_data["rooms"].append({"beds": beds, "doubles": doubles})
    context.user_data.pop("temp_room", None)

    # proceed to next room or to hall
    current = context.user_data["current_room"]
    total_rooms = context.user_data.get("rooms_count", 0)
    if current < total_rooms:
        context.user_data["current_room"] = current + 1
        prompt = TEXT[lang]["ask_beds_room"].format(i=current + 1)
        await update.message.reply_text(prompt)
        return ROOM_BEDS
    else:
        # all rooms done -> ask hall beds
        await update.message.reply_text(TEXT[lang]["ask_hall_beds"])
        return HALL_BEDS


async def hall_beds_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip()
    if not txt.isdigit() or int(txt) < 0:
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return HALL_BEDS

    hall_beds = int(txt)
    context.user_data["hall_beds"] = hall_beds
    if hall_beds == 0:
        context.user_data["hall_doubles"] = 0
        # skip to bed price
        await update.message.reply_text(TEXT[lang]["ask_bed_price"])
        return BED_PRICE

    # ask hall doubles
    prompt = TEXT[lang]["ask_hall_doubles"].format(beds=hall_beds)
    await update.message.reply_text(prompt)
    return HALL_DOUBLES


async def hall_doubles_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip()
    if not txt.isdigit() or int(txt) < 0:
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return HALL_DOUBLES

    doubles = int(txt)
    hall_beds = context.user_data.get("hall_beds", 0)
    if doubles > hall_beds:
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return HALL_DOUBLES

    context.user_data["hall_doubles"] = doubles
    await update.message.reply_text(TEXT[lang]["ask_bed_price"])
    return BED_PRICE


async def bed_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip().replace(",", "")
    # bed price can be float
    try:
        val = float(txt)
        if val < 0:
            raise ValueError
    except:
        await update.message.reply_text(TEXT[lang]["invalid_number"])
        return BED_PRICE

    context.user_data["bed_price"] = val

    # Ask for yearly rent (we still need yearly rent to compute monthly rent/upfront)
    # We'll reuse existing prompt in English/Arabic for yearly rent as before.
    if lang == "eg":
        await update.message.reply_text("💰 اكتب الإيجار السنوي (AED) عشان نحسب الإيجار الشهري، لو مفيش اكتب 0")
    else:
        await update.message.reply_text("💰 Enter Yearly Rent (AED) so we can compute monthly rent/upfront. If none, send 0.")
    return MAN  # Reuse MAN state for manager after getting yearly rent? Actually we need yearly rent state first.
    # NOTE: For simplicity below we will accept manager or yearly rent in the same state:
    # We'll read the next message as yearly rent and then ask manager — simpler.


# To avoid adding another state, we'll handle yearly rent and manager selection in a single step:
async def manager_or_yearly_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This handler will read the yearly rent (number), store it, then prompt manager selection (buttons).
    We placed this function in the MAN state after BED_PRICE, as per design above.
    """
    lang = context.user_data.get("lang", "en")
    txt = update.message.text.strip().replace(",", "")
    # first message expected: yearly rent numeric
    if "yearly_rent_received" not in context.user_data:
        # attempt to parse yearly rent
        try:
            yr = float(txt)
            if yr < 0:
                raise ValueError
        except:
            await update.message.reply_text(TEXT[lang]["invalid_number"])
            return MAN
        context.user_data["yearly_rent"] = yr
        # compute monthly_rent and store for calculations
        context.user_data["monthly_rent_from_yearly"] = yr / 12.0
        context.user_data["yearly_rent_received"] = True
        # now ask manager selection
        kb = ReplyKeyboardMarkup(TEXT[lang]["manager_buttons"], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(TEXT[lang]["ask_manager"], reply_markup=kb)
        return MAN

    # if we already collected yearly rent and the user now sends manager choice:
    if txt.startswith("1"):
        manager_choice = 1
    elif txt.startswith("2"):
        manager_choice = 2
    else:
        await update.message.reply_text(TEXT[lang]["invalid_choice"])
        return MAN

    context.user_data["manager_type"] = manager_choice

    await update.message.reply_text(TEXT[lang]["processing"], reply_markup=ReplyKeyboardRemove())

    # compose inputs for calculation
    data = {
        "location": context.user_data.get("location", "dubai"),
        "rooms": context.user_data.get("rooms", []),
        "hall_beds": context.user_data.get("hall_beds", 0),
        "hall_doubles": context.user_data.get("hall_doubles", 0),
        "bed_price": context.user_data.get("bed_price", 0.0),
        "manager_type": context.user_data.get("manager_type", 1),
        "yearly_rent": context.user_data.get("yearly_rent", 0.0),
        "monthly_rent_from_yearly": context.user_data.get("monthly_rent_from_yearly", 0.0),
    }

    res = calculate_financials_from_inputs(data)

    report = format_report(res, context.user_data.get("lang", "en"))

    await update.message.reply_text(report, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

    # short done prompt
    if context.user_data.get("lang", "en") == "eg":
        await update.message.reply_text(TEXT["eg"]["done_prompt"])
    else:
        await update.message.reply_text(TEXT["en"]["done_prompt"])

    # clear user_data so subsequent /start is fresh
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


# ---------------- MAIN ----------------
def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_selected)],
            LOC: [MessageHandler(filters.TEXT & ~filters.COMMAND, location_received)],
            ROOMS_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, rooms_num_received)],
            ROOM_BEDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, room_beds_received)],
            ROOM_DOUBLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, room_doubles_received)],
            HALL_BEDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, hall_beds_received)],
            HALL_DOUBLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, hall_doubles_received)],
            BED_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bed_price_received)],
            # MAN state is reused to read yearly rent first, then manager choice
            MAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, manager_or_yearly_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("Use /start to run the flow.")))
    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
