#!/usr/bin/env python3
"""Знак, стихія, число життєвого шляху, китайський рік і збіги пари за датами народження."""
import argparse
import re
import sys
from datetime import date

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


def parse(raw, dmy):
    parts = [int(p) for p in re.split(r"[/.\-\s]+", raw.strip()) if p]
    if len(parts) != 3:
        sys.exit(f"не розпізнала дату {raw}")
    a, b, y = parts
    if y < 100:
        y += 1900 if y > date.today().year % 100 else 2000
    m, d = (b, a) if dmy else (a, b)
    note = ""
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
    today = date.today()
    return today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))


def years(n):
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} рік"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} роки"
    return f"{n} років"


def describe(label, dt, note):
    idx = sign_index(dt)
    _, _, uk, en, element, _ = SIGNS[idx]
    edge = cusp(dt, idx)
    print(f"{label}: {dt.day} {MONTHS[dt.month - 1]} {dt.year}, {years(age(dt))}")
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dates", nargs="+", help="одна або дві дати, за замовчуванням ММ/ДД/РРРР")
    ap.add_argument("--dmy", action="store_true", help="дати в форматі ДД.ММ.РРРР")
    args = ap.parse_args()
    if len(args.dates) > 2:
        sys.exit("максимум дві дати")
    parsed = [parse(raw, args.dmy) for raw in args.dates]
    signs = [describe(f"дата {i}", dt, note) for i, (dt, note) in enumerate(parsed, 1)]
    if len(parsed) == 2:
        pair(parsed[0][0], signs[0], parsed[1][0], signs[1])


if __name__ == "__main__":
    main()
