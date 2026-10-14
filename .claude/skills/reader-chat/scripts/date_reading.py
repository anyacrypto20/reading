#!/usr/bin/env python3
"""Знак, стихія, число життєвого шляху, китайський рік, збіги пари і найближчі дати за датами народження."""
import argparse
import re
import sys
from datetime import date, timedelta

SIGNS = [
    (1, 20, "Водолій", "Aquarius", "повітря", "з Водолієм"),
    (2, 19, "Риби", "Pisces", "вода", "з Рибами"),
    (3, 21, "Овен", "Aries", "вогонь", "з Овном"),
    (4, 20, "Телець", "Taurus", "земля", "з Тельцем"),
    (5, 21, "Близнюки", "Gemini", "повітря", "з Близнюками"),
    (6, 21, "Рак", "Cancer", "вода", "з Раком"),
    (7, 23, "Лев", "Leo", "вогонь", "з Левом"),
    (8, 23, "Діва", "Virgo", "земля", "з Дівою"),
    (9, 23, "Терези", "Libra", "повітря", "з Терезами"),
    (10, 23, "Скорпіон", "Scorpio", "вода", "зі Скорпіоном"),
    (11, 22, "Стрілець", "Sagittarius", "вогонь", "зі Стрільцем"),
    (12, 22, "Козеріг", "Capricorn", "земля", "з Козерогом"),
]
ANIMALS = ["Щур", "Бик", "Тигр", "Кролик", "Дракон", "Змія", "Кінь", "Коза", "Мавпа", "Півень", "Собака", "Свиня"]
MONTHS = ["січня", "лютого", "березня", "квітня", "травня", "червня",
          "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]
FRIENDLY = {frozenset(["вогонь", "повітря"]), frozenset(["земля", "вода"])}
FIXED_HOLIDAYS = [
    (1, 1, "Новий рік"), (2, 14, "День святого Валентина"), (3, 17, "День святого Патрика"),
    (7, 4, "День незалежності США"), (10, 31, "Хелловін"), (12, 25, "Різдво"),
]
HORIZON = 92
TODAY = date.today()


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} {one}"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"


def years(n):
    return plural(n, "рік", "роки", "років")


def days(n):
    return plural(n, "день", "дні", "днів")


def human(dt):
    return f"{dt.day} {MONTHS[dt.month - 1]}"


def parse(raw, dmy):
    parts = [int(p) for p in re.split(r"[/.\-\s]+", raw.strip()) if p]
    if len(parts) != 3:
        sys.exit(f"не розпізнала дату {raw}")
    a, b, y = parts
    if y < 100:
        y += 1900 if y > TODAY.year % 100 else 2000
    note = ""
    if not dmy and "." in raw and "/" not in raw:
        dmy, note = True, "дата з крапками, прочитала як день першим"
    m, d = (b, a) if dmy else (a, b)
    if m > 12 and d <= 12:
        m, d, note = d, m, "схоже на день першим, прочитала як ДД/ММ"
    try:
        return date(y, m, d), note
    except ValueError:
        sys.exit(f"неможлива дата {raw}")


def sign_index(dt):
    idx = 11
    for i, (m, d, *_) in enumerate(SIGNS):
        if (dt.month, dt.day) >= (m, d):
            idx = i
    return idx


def cusp(dt, idx):
    start = date(dt.year, SIGNS[idx][0], SIGNS[idx][1])
    nxt = SIGNS[(idx + 1) % 12]
    end = date(dt.year + (1 if nxt[0] < dt.month else 0), nxt[0], nxt[1])
    if dt >= start and (dt - start).days <= 1:
        return f"на межі {SIGNS[idx - 1][5]}"
    if (end - dt).days == 1:
        return f"на межі {nxt[5]}"
    return ""


def reduce(n):
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(c) for c in str(n))
    return n


def life_path(dt):
    return reduce(sum(int(c) for c in dt.strftime("%m%d%Y")))


def animal(dt):
    name = ANIMALS[(dt.year - 4) % 12]
    if (dt.month, dt.day) < (2, 20):
        return f"{name}, але якщо місячний новий рік ще не настав, то {ANIMALS[(dt.year - 5) % 12]}"
    return name


def age(dt):
    return TODAY.year - dt.year - ((TODAY.month, TODAY.day) < (dt.month, dt.day))


def next_birthday(dt):
    for y in (TODAY.year, TODAY.year + 1):
        try:
            bd = date(y, dt.month, dt.day)
        except ValueError:
            bd = date(y, 2, 28)
        if bd >= TODAY:
            return bd


def nth_weekday(y, m, weekday, n):
    first = date(y, m, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def holidays(y):
    events = [(date(y, m, d), name) for m, d, name in FIXED_HOLIDAYS]
    events += [
        (easter(y), "Великдень"),
        (nth_weekday(y, 5, 6, 2), "День матері в США"),
        (nth_weekday(y, 6, 6, 3), "День батька в США"),
        (nth_weekday(y, 11, 3, 4), "День подяки"),
    ]
    return events


def upcoming(births):
    events = []
    for label, dt in births:
        bd = next_birthday(dt)
        if (bd - TODAY).days <= HORIZON:
            events.append((bd, f"день народження людини з {label}, виповниться {years(bd.year - dt.year)}"))
    for y in (TODAY.year, TODAY.year + 1):
        events += [(d, n) for d, n in holidays(y) if 0 <= (d - TODAY).days <= HORIZON]
    print(f"найближчі 3 місяці від {human(TODAY)} {TODAY.year}:")
    if not events:
        print("  нічого")
    for d, name in sorted(events):
        left = (d - TODAY).days
        when = "сьогодні" if left == 0 else f"через {days(left)}"
        print(f"  {human(d)}, {when}: {name}")


def describe(label, dt, note):
    idx = sign_index(dt)
    _, _, uk, en, element, _ = SIGNS[idx]
    edge = cusp(dt, idx)
    print(f"{label}: {human(dt)} {dt.year}, {years(age(dt))}")
    if note:
        print(f"  {note}")
    print(f"  знак: {uk} ({en}), стихія {element}" + (f", {edge}" if edge else ""))
    print(f"  число життєвого шляху: {life_path(dt)}")
    print(f"  китайський рік: {animal(dt)}")
    return idx, element


def pair(d1, s1, d2, s2):
    print("пара:")
    hits = []
    if (d1.month, d1.day) == (d2.month, d2.day):
        hits.append("однаковий день народження")
    gap = abs(d1.year - d2.year)
    if gap and gap % 12 == 0:
        hits.append(f"різниця {years(gap)} за роком, кратна 12, один китайський знак")
    diff = abs(s1[0] - s2[0])
    if diff == 0:
        hits.append("однаковий знак зодіаку")
    elif diff == 6:
        hits.append("протилежні знаки, дзеркало")
    if s1[1] == s2[1]:
        hits.append(f"одна стихія, {s1[1]}")
    elif frozenset([s1[1], s2[1]]) in FRIENDLY:
        hits.append(f"стихії підсилюють одна одну, {s1[1]} і {s2[1]}")
    else:
        hits.append(f"стихії тертя, {s1[1]} і {s2[1]}")
    lp1, lp2 = life_path(d1), life_path(d2)
    if lp1 == lp2:
        hits.append(f"однакове число життєвого шляху {lp1}")
    hits.append(f"число пари {reduce(lp1 + lp2)}")
    hits.append(f"різниця у віці {years(abs(age(d1) - age(d2)))}")
    for h in hits:
        print(f"  {h}")


def main():
    global TODAY
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dates", nargs="+", help="одна або дві дати; зі слешами місяць першим, з крапками день першим")
    ap.add_argument("--dmy", action="store_true", help="примусово день першим")
    ap.add_argument("--today", help="яку дату вважати сьогоднішньою, РРРР-ММ-ДД")
    args = ap.parse_args()
    if args.today:
        TODAY = date.fromisoformat(args.today)
    if len(args.dates) > 2:
        sys.exit("максимум дві дати")
    parsed = [parse(raw, args.dmy) for raw in args.dates]
    signs = [describe(f"дата {i}", dt, note) for i, (dt, note) in enumerate(parsed, 1)]
    if len(parsed) == 2:
        pair(parsed[0][0], signs[0], parsed[1][0], signs[1])
    upcoming([(f"дати {i}", dt) for i, (dt, _) in enumerate(parsed, 1)])


if __name__ == "__main__":
    main()
