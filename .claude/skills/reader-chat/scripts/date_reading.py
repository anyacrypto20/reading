#!/usr/bin/env python3
"""Знак, стихія, число життєвого шляху, китайський рік, збіги пари і найближчі дати за датами народження."""
import argparse
import re
import sys
from datetime import date, timedelta

SIGNS = [
    (1, 20, "Водолій", "Водолей", "Aquarius", "повітря", "з Водолієм", "Сатурн"),
    (2, 19, "Риби", "Рыбы", "Pisces", "вода", "з Рибами", "Юпітер"),
    (3, 21, "Овен", "Овен", "Aries", "вогонь", "з Овном", "Марс"),
    (4, 20, "Телець", "Телец", "Taurus", "земля", "з Тельцем", "Венера"),
    (5, 21, "Близнюки", "Близнецы", "Gemini", "повітря", "з Близнюками", "Меркурій"),
    (6, 21, "Рак", "Рак", "Cancer", "вода", "з Раком", "Місяць"),
    (7, 23, "Лев", "Лев", "Leo", "вогонь", "з Левом", "Сонце"),
    (8, 23, "Діва", "Дева", "Virgo", "земля", "з Дівою", "Меркурій"),
    (9, 23, "Терези", "Весы", "Libra", "повітря", "з Терезами", "Венера"),
    (10, 23, "Скорпіон", "Скорпион", "Scorpio", "вода", "зі Скорпіоном", "Марс"),
    (11, 22, "Стрілець", "Стрелец", "Sagittarius", "вогонь", "зі Стрільцем", "Юпітер"),
    (12, 22, "Козеріг", "Козерог", "Capricorn", "земля", "з Козерогом", "Сатурн"),
]
MODALITY = ["фіксований", "мутабельний", "кардинальний"]
ANIMALS = [("Щур", "Крыса", "Rat"), ("Бик", "Бык", "Ox"), ("Тигр", "Тигр", "Tiger"), ("Кролик", "Кролик", "Rabbit"),
           ("Дракон", "Дракон", "Dragon"), ("Змія", "Змея", "Snake"), ("Кінь", "Лошадь", "Horse"),
           ("Коза", "Коза", "Goat"), ("Мавпа", "Обезьяна", "Monkey"), ("Півень", "Петух", "Rooster"),
           ("Собака", "Собака", "Dog"), ("Свиня", "Свинья", "Pig")]
MONTHS = ["січня", "лютого", "березня", "квітня", "травня", "червня",
          "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]
FRIENDLY = {frozenset(["вогонь", "повітря"]), frozenset(["земля", "вода"])}
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


def sign_index(dt):
    idx = 11
    for i, (m, d, *_) in enumerate(SIGNS):
        if (dt.month, dt.day) >= (m, d):
            idx = i
    return idx


def sign_name(idx):
    uk, ru, en = SIGNS[idx][2:5]
    return f"{uk} ({ru}, {en})"


def parse(raw, dmy, mdy_proven=False):
    raw = raw.strip()
    if not re.fullmatch(r"\d{1,4}(?:[/.\-\s]+\d{1,4}){2}", raw):
        sys.exit(f"не розпізнала дату {raw}, потрібні цифри: ММ/ДД/РРРР або ДД.ММ.РРРР")
    parts = [int(p) for p in re.split(r"[/.\-\s]+", raw)]
    note = ""
    if parts[0] > 31:
        y, m, d = parts
    else:
        a, b, y = parts
        if y < 100:
            y += 1900 if y > TODAY.year % 100 else 2000
        if not dmy and "." in raw and "/" not in raw:
            dmy, note = True, "дата з крапками, прочитала як день першим"
        m, d = (b, a) if dmy else (a, b)
        if m > 12 and d <= 12:
            m, d = d, m
            note = "схоже на місяць першим, прочитала як ММ.ДД" if dmy else "схоже на день першим, прочитала як ДД/ММ"
        elif not dmy and not mdy_proven and a != b and a <= 12 and b <= 12:
            try:
                alt = date(y, b, a)
                note = (f"неоднозначна дата: прочитала як місяць першим; якщо день першим, "
                        f"це {human(alt)}, {SIGNS[sign_index(alt)][2]}")
            except ValueError:
                pass
    try:
        result = date(y, m, d)
    except ValueError:
        sys.exit(f"неможлива дата {raw}")
    if result > TODAY:
        sys.exit(f"дата {raw} ще не настала, перевір рік")
    return result, note


def cusp(dt, idx):
    start = date(dt.year, SIGNS[idx][0], SIGNS[idx][1])
    nxt = SIGNS[(idx + 1) % 12]
    end = date(dt.year + (1 if nxt[0] < dt.month else 0), nxt[0], nxt[1])
    if dt >= start and (dt - start).days <= 1:
        return f"на межі {SIGNS[idx - 1][6]}"
    if (end - dt).days == 1:
        return f"на межі {nxt[6]}"
    return ""


def reduce(n):
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(c) for c in str(n))
    return n


def life_path(dt):
    return reduce(sum(int(c) for c in dt.strftime("%m%d%Y")))


def chinese_year(dt):
    if (dt.month, dt.day) < (1, 21):
        return dt.year - 1
    if (dt.month, dt.day) > (2, 20):
        return dt.year
    return None


def animal_name(year):
    uk, ru, en = ANIMALS[(year - 4) % 12]
    return f"{uk} ({ru}, {en})"


def animal(dt):
    cy = chinese_year(dt)
    if cy is not None:
        return animal_name(cy)
    return (f"{animal_name(dt.year - 1)} або {animal_name(dt.year)}, "
            f"залежить від дати місячного нового року {dt.year}, знак краще не називати")


def next_birthday(dt):
    for y in (TODAY.year, TODAY.year + 1):
        try:
            bd = date(y, dt.month, dt.day)
        except ValueError:
            bd = date(y, 2, 28)
        if bd >= TODAY:
            return bd


def age(dt):
    bd = next_birthday(dt)
    return bd.year - dt.year - (bd > TODAY)


def gap(d1, d2):
    older, younger = sorted([d1, d2])
    months = (younger.year - older.year) * 12 + younger.month - older.month - (younger.day < older.day)
    y, m = divmod(months, 12)
    text = years(y) if y else ""
    if m:
        text = f"{text} і {plural(m, 'місяць', 'місяці', 'місяців')}" if text else plural(m, "місяць", "місяці", "місяців")
    return text or "менше місяця", older


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


def orthodox_easter(y):
    a, b, c = y % 4, y % 7, y % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month, day = divmod(d + e + 114, 31)
    return date(y, month, day + 1) + timedelta(days=13)


def holidays(y, region):
    if region == "us":
        return [
            (date(y, 1, 1), "Новий рік"), (date(y, 2, 14), "День святого Валентина"),
            (easter(y), "Великдень"), (nth_weekday(y, 5, 6, 2), "День матері"),
            (nth_weekday(y, 6, 6, 3), "День батька"), (date(y, 7, 4), "День незалежності США"),
            (date(y, 10, 31), "Хелловін"), (nth_weekday(y, 11, 3, 4), "День подяки"),
            (date(y, 12, 25), "Різдво"),
        ]
    common = [
        (date(y, 1, 1), "Новий рік"), (date(y, 2, 14), "День святого Валентина"),
        (date(y, 3, 8), "8 березня"), (orthodox_easter(y), "Великдень"),
    ]
    if region == "ua":
        return common + [(nth_weekday(y, 5, 6, 2), "День матері"), (date(y, 12, 25), "Різдво")]
    return common + [(date(y, 1, 7), "Різдво"), (date(y, 1, 14), "Старий Новий рік"),
                     (date(y, 7, 8), "День сім'ї, любові і вірності")]


def upcoming(people, region):
    events = []
    for name, dt in people:
        bd = next_birthday(dt)
        if (bd - TODAY).days <= HORIZON:
            turning = bd.year - dt.year
            mark = ", кругла дата" if turning % 10 == 0 else ""
            events.append((bd, f"день народження, {name}, виповниться {years(turning)}{mark}"))
    for y in (TODAY.year, TODAY.year + 1):
        events += [(d, n) for d, n in holidays(y, region) if 0 <= (d - TODAY).days <= HORIZON]
    print(f"найближчі 3 місяці від {human(TODAY)} {TODAY.year}, свята для регіону {region}:")
    if not events:
        print("  нічого")
    for d, name in sorted(events):
        left = (d - TODAY).days
        when = "сьогодні" if left == 0 else f"через {days(left)}"
        print(f"  {human(d)}, {when}: {name}")


def describe(label, dt, note):
    idx = sign_index(dt)
    element = SIGNS[idx][5]
    edge = cusp(dt, idx)
    bd = next_birthday(dt)
    left = (bd - TODAY).days
    print(f"{label}: {human(dt)} {dt.year}, {years(age(dt))}")
    if note:
        print(f"  {note}")
    print(f"  знак: {sign_name(idx)}, стихія {element}, {MODALITY[idx % 3]} хрест, управитель {SIGNS[idx][7]}"
          + (f", {edge}" if edge else ""))
    print(f"  число життєвого шляху: {life_path(dt)}")
    print(f"  китайський рік: {animal(dt)}")
    print(f"  наступний день народження: {human(bd)}, " + ("сьогодні" if left == 0 else f"через {days(left)}"))
    return idx


def pair(names, d1, i1, d2, i2):
    strong, other = [], []
    if (d1.month, d1.day) == (d2.month, d2.day):
        diff = abs(d1.year - d2.year)
        strong.append("однаковий день народження" + (f" з різницею рівно {years(diff)}" if diff else ""))
    if i1 == i2:
        strong.append(f"однаковий знак, {SIGNS[i1][2]}")
    elif abs(i1 - i2) == 6:
        strong.append("протилежні знаки, дзеркало")
    lp1, lp2 = life_path(d1), life_path(d2)
    if lp1 == lp2:
        strong.append(f"однакове число життєвого шляху {lp1}")
    c1, c2 = chinese_year(d1), chinese_year(d2)
    if c1 is not None and c2 is not None and (c1 - c2) % 12 == 0:
        strong.append(f"один китайський знак, {animal_name(c1)}")
    elif (c1 is None or c2 is None) and (d1.year - d2.year) % 12 == 0:
        other.append("китайський знак може збігатись, але одна дата біля місячного нового року")
    e1, e2 = SIGNS[i1][5], SIGNS[i2][5]
    if i1 != i2:
        if e1 == e2:
            other.append(f"одна стихія, {e1}")
        elif frozenset([e1, e2]) in FRIENDLY:
            other.append(f"стихії підсилюють одна одну, {e1} і {e2}: тяга")
        else:
            other.append(f"стихії тертя, {e1} і {e2}: сварки і паузи")
        if i1 % 3 == i2 % 3 and abs(i1 - i2) != 6:
            other.append(f"один хрест, {MODALITY[i1 % 3]}")
        if SIGNS[i1][7] == SIGNS[i2][7]:
            other.append(f"один управитель, {SIGNS[i1][7]}")
    other.append(f"число пари {reduce(lp1 + lp2)}")
    text, older = gap(d1, d2)
    other.append(f"різниця у віці {text}, старша людина: {names[0] if older == d1 else names[1]}")
    print("пара:")
    if strong:
        for h in strong:
            print(f"  сильний збіг: {h}")
    else:
        print("  сильних збігів немає")
    for h in other:
        print(f"  {h}")


def main():
    global TODAY
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dates", nargs="+", help="одна або дві дати; зі слешами місяць першим, з крапками день першим")
    ap.add_argument("--dmy", action="store_true", help="примусово день першим")
    ap.add_argument("--today", help="дата чату, РРРР-ММ-ДД, якщо працюєш зі старим чатом")
    ap.add_argument("--names", default="", help="імена через кому в тому ж порядку що й дати")
    ap.add_argument("--region", choices=["us", "ua", "ru"], help="свята; за замовчуванням us для дат зі слешами, ua для дат з крапками")
    args = ap.parse_args()
    if args.today:
        TODAY = date.fromisoformat(args.today)
    raw_dates = args.dates
    if len(raw_dates) in (3, 6) and all(x.isdigit() for x in raw_dates):
        raw_dates = [" ".join(raw_dates[i:i + 3]) for i in range(0, len(raw_dates), 3)]
    if len(raw_dates) > 2:
        sys.exit("максимум дві дати; дату з пробілами бери в лапки")
    given = [n.strip() for n in args.names.split(",") if n.strip()]
    labels = [given[i] if i < len(given) else f"дата {i + 1}" for i in range(2)]
    region = args.region or ("us" if any("/" in r for r in raw_dates) else "ua")
    split = [[int(x) for x in re.split(r"[/.\-\s]+", r.strip()) if x.isdigit()] for r in raw_dates]
    mdy_proven = any("/" in r and len(p) == 3 and p[0] <= 12 < p[1] for r, p in zip(raw_dates, split))
    parsed = [parse(raw, args.dmy, mdy_proven) for raw in raw_dates]
    idxs = [describe(labels[i], dt, note) for i, (dt, note) in enumerate(parsed)]
    if len(parsed) == 2:
        pair(labels, parsed[0][0], idxs[0], parsed[1][0], idxs[1])
    upcoming([(labels[i], dt) for i, (dt, _) in enumerate(parsed)], region)


if __name__ == "__main__":
    main()
