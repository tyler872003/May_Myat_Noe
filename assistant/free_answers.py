import re

WHY_WORDS = ('why', 'increase', 'higher', 'went up', 'ဘာကြောင့်', 'တက်')
SAVE_WORDS = ('save', 'saving', 'စုချင်', 'စုဆောင်း', 'စုမိ')
UNUSUAL_WORDS = ('unusual', 'ပုံမှန်မဟုတ်')
BUDGET_WORDS = ('budget',)
FORECAST_WORDS = ('forecast', 'expect', 'predict', 'ခန့်မှန်း')
TOP_WORDS = ('most', 'highest', 'top', 'category', 'အများဆုံး')


def _burmese(text):
    return bool(re.search('[\u1000-\u109F]', text))


def _n(value):
    return f'{value:,.0f}'


def _has(q, words):
    return any(w in q for w in words)


def answer_without_ai(question, facts):
    q = question.lower()
    my = _burmese(question)
    numbers = re.findall(r'\d[\d,]*', question)

    if _has(q, WHY_WORDS):
        return _why_up(facts, my)
    if numbers and _has(q, SAVE_WORDS):
        target = int(numbers[0].replace(',', ''))
        if target > 0:
            return _savings_plan(target, facts, my)
    if _has(q, UNUSUAL_WORDS):
        return _unusual(facts, my)
    if _has(q, BUDGET_WORDS):
        return _budgets(facts, my)
    if _has(q, FORECAST_WORDS):
        return _forecast(facts, my)
    if _has(q, TOP_WORDS):
        return _top_category(facts, my)
    if _has(q, SAVE_WORDS):
        return _saved(facts, my)

    if my:
        return ('အောက်ပါမေးခွန်းတွေကို ဖြေနိုင်ပါတယ် - အသုံးစရိတ်အများဆုံး Category၊ '
                'အသုံးစရိတ် တက်လာရတဲ့အကြောင်းရင်း၊ စုဆောင်းငွေ ပန်းတိုင် (ဥပမာ - တစ်လကို 100,000 ကျပ် စုချင်တယ်)၊ '
                'Budget၊ ခန့်မှန်းချက်၊ ပုံမှန်မဟုတ်တဲ့ အသုံးစရိတ်။')
    return ("I can answer questions about: your top spending category, why spending went up, "
            "a savings target (for example 'save 100,000 per month'), budgets, the forecast, "
            "and unusual spending.")


def _top_category(facts, my):
    cats = facts['this_month']['spending_by_category']
    if not cats:
        return 'ဒီလမှာ အသုံးစရိတ် မှတ်တမ်း မရှိသေးပါဘူး။' if my else 'No expenses recorded this month yet.'
    top = cats[0]
    if my:
        return f"ဒီလမှာ အသုံးစရိတ်အများဆုံး Category က {top['name']} ဖြစ်ပြီး {_n(top['total'])} ကျပ် ဖြစ်ပါတယ်။"
    return f"This month your highest spending is on {top['name']}: {_n(top['total'])} MMK."


def _why_up(facts, my):
    last = facts['last_month']
    now = facts['this_month']['summary']['expenses']
    before = last['summary']['expenses']
    ups = [c for c in facts['category_change_vs_last_month'] if c['change'] > 0][:3]

    if now <= before or not ups:
        if my:
            return (f"ဒီလ အခုထိ အသုံးစရိတ် ({_n(now)} ကျပ်) က {last['label']} ({_n(before)} ကျပ်) ထက် "
                    f"မများသေးပါဘူး။ ဒီလ မပြီးသေးတာကိုလည်း သတိပြုပါ။")
        return (f"So far this month you have spent {_n(now)} MMK, which is not higher than "
                f"{last['label']} ({_n(before)} MMK). The month is not over yet.")

    parts = ', '.join(f"{c['category']} +{_n(c['change'])}" for c in ups)
    if my:
        return (f"ဒီလ အခုထိ {_n(now)} ကျပ် သုံးထားပြီး {last['label']} မှာ {_n(before)} ကျပ် သုံးခဲ့ပါတယ်။ "
                f"ပြီးခဲ့တဲ့လနဲ့ ယှဉ်ရင် အများဆုံး တက်နေတဲ့ Category တွေက - {parts} (ကျပ်) ဖြစ်ပါတယ်။")
    return (f"So far this month you have spent {_n(now)} MMK, compared with {_n(before)} MMK in "
            f"{last['label']}. The biggest increases by category are: {parts} MMK.")


def _savings_plan(target, facts, my):
    last = facts['last_month']
    base = last if (last['summary']['income'] or last['summary']['expenses']) else facts['this_month']
    s, label = base['summary'], base['label']
    income, spent, saved = s['income'], s['expenses'], s['savings']

    if saved >= target:
        if my:
            return (f"{label} မှာ {_n(saved)} ကျပ် စုဆောင်းနိုင်ခဲ့လို့ တစ်လကို {_n(target)} ကျပ် "
                    f"ပန်းတိုင်ကို ရောက်ပြီးသား ဖြစ်ပါတယ်။")
        return (f"In {label} you saved {_n(saved)} MMK, which already meets your target of "
                f"{_n(target)} MMK per month.")
    if target > income:
        if my:
            return (f"{label} မှာ ဝင်ငွေက {_n(income)} ကျပ် ပဲ ရှိလို့ တစ်လကို {_n(target)} ကျပ် စုဖို့ဆိုရင် "
                    f"အသုံးစရိတ်လျှော့ရုံနဲ့ မလုံလောက်ပါဘူး၊ ဝင်ငွေပါ တိုးဖို့ လိုပါတယ်။")
        return (f"In {label} your income was {_n(income)} MMK, so saving {_n(target)} MMK a month "
                f"would need more income, not just lower spending.")

    gap = target - saved
    pct = gap / spent * 100
    top = ', '.join(f"{c['name']} {_n(c['total'])}" for c in base['spending_by_category'][:3])
    if my:
        return (f"{label} အခြေခံပြီး တွက်ကြည့်ရင် ဝင်ငွေ {_n(income)} ကျပ်၊ အသုံးစရိတ် {_n(spent)} ကျပ်၊ "
                f"စုဆောင်းငွေ {_n(saved)} ကျပ် ဖြစ်ပါတယ်။ တစ်လကို {_n(target)} ကျပ် စုဖို့ဆိုရင် "
                f"အသုံးစရိတ်ကို {_n(gap)} ကျပ် ({pct:.0f}%) လောက် လျှော့ဖို့ လိုပါတယ်။ "
                f"အသုံးစရိတ်အများဆုံး Category တွေက - {top} ဖြစ်ပါတယ်။")
    return (f"Based on {label}: income {_n(income)} MMK, expenses {_n(spent)} MMK, saved {_n(saved)} MMK. "
            f"To save {_n(target)} MMK per month you would need to cut about {_n(gap)} MMK "
            f"({pct:.0f}% of your spending). Your biggest categories were: {top}.")


def _unusual(facts, my):
    items = facts['this_month']['unusual_spending']
    if not items:
        return 'ဒီလမှာ ပုံမှန်မဟုတ်တဲ့ အသုံးစရိတ် မတွေ့ပါဘူး။' if my else 'No unusual spending found this month.'
    parts = '; '.join(f"{u['category']} {_n(u['amount'])} ({u['times_typical']}x)" for u in items)
    if my:
        return f"ပုံမှန်ထက် များနေတဲ့ အသုံးစရိတ်တွေက - {parts} (ကျပ်) ဖြစ်ပါတယ်။"
    return f"Spending well above your usual for its category: {parts} MMK."


def _budgets(facts, my):
    budgets = facts['this_month']['budgets']
    if not budgets:
        return 'Budget မသတ်မှတ်ရသေးပါဘူး။' if my else 'You have not set any budgets yet.'
    if my:
        return ' '.join(f"{b['category']} - {b['percent_used']}% သုံးပြီးပါပြီ။" for b in budgets)
    return ' '.join(f"{b['category']}: {b['percent_used']}% used." for b in budgets)


def _forecast(facts, my):
    f = facts['expected_spending_this_month']
    if not f:
        return 'ခန့်မှန်းဖို့ အချက်အလက် မလုံလောက်သေးပါဘူး။' if my else 'There is not enough history for a forecast yet.'
    total = _n(f['expected_total_for_this_month'])
    if my:
        return f"ဒီလ အသုံးစရိတ် စုစုပေါင်း ခန့်မှန်းချက်က {total} ကျပ်လောက် ဖြစ်ပါတယ်။ ဒါဟာ ခန့်မှန်းချက်သာ ဖြစ်ပါတယ်။"
    return f"Expected spending this month is about {total} MMK. This is only an estimate."


def _saved(facts, my):
    s = facts['this_month']['summary']
    if my:
        return (f"ဒီလ အခုထိ ဝင်ငွေ {_n(s['income'])} ကျပ်၊ အသုံးစရိတ် {_n(s['expenses'])} ကျပ် ဖြစ်လို့ "
                f"စုဆောင်းငွေ {_n(s['savings'])} ကျပ် ရှိပါတယ်။")
    return (f"This month so far you earned {_n(s['income'])} MMK and spent {_n(s['expenses'])} MMK, "
            f"so you have saved {_n(s['savings'])} MMK.")