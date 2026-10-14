#!/usr/bin/env python3
"""Перевіряє чернетку повідомлень рідера (розділені порожнім рядком) на ШІ маркери."""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

MARKERS = Path(__file__).resolve().parent.parent / "references" / "ai-markers.json"
EMOJI_BASE = r"[\U0001F000-\U0001F3FA\U0001F400-\U0001FAFF☀-➿⭐❤⌚⌛⏩-⏺]"
EMOJI = re.compile(rf"{EMOJI_BASE}(?:[\U0001F3FB-\U0001F3FF️]|‍{EMOJI_BASE})*")
EMOJI_TAIL = re.compile(rf"(?:{EMOJI_BASE}|[\U0001F3FB-\U0001F3FF️‍\s])+$")
WORD = re.compile(r"[\w']+")
UK_ONLY = re.compile("[іїєґІЇЄҐ]")
RU_ONLY = re.compile("[ыэъёЫЭЪЁ]")
CYR = re.compile("[а-яА-ЯіїєґІЇЄҐёЁ]")
RU_WORDS = re.compile(r"(?<!\w)(?:и|что|как|когда|если|очень|сейчас|меня|тебя|мне|она|его|будет|также|тоже|только|конечно|спасибо|привет|рождения|рождение|чувствую|пожалуйста|более|милая|дорогая|думает|хочет|знает|может|вижу|чтобы|нет)(?!\w)", re.I)
UK_WORDS = re.compile(r"(?<!\w)(?:що|він|вона|це|дуже|теж|дякую|якщо|тобою)(?!\w)", re.I)
BOOKING = re.compile(r"(?i)заброн|\bbook\b")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
PROPER = re.compile(r"(?<=[\w,;:]\s)([A-ZА-ЯІЇЄҐЁ][\w']*)")
ANSWER_START = re.compile(r"(?i)(?:бо|тому що|потому что|because)(?!\w)")

FILLER = (r"(?:вже|уже|тут|теж|також|тоже|ще|еще|ещё|знов|знову|снова|опять|сьогодні|сегодня|зараз|сейчас|щойно|тільки|только|так|дуже|"
          r"очень|і|й|и|не|би|б|бы|сама|сам|давно|одразу|сразу|тебе|тобі|його|її|йому|їй|тебя|ему|ей|его|ее|её|вас|вам|нас)")
NOT_VERBS = r"(?!(?:знов|любов|знову|себе)(?!\w))"
UK_MASC = r"готовий|радий|вдячний|впевнений|міг|ніс|\w+ився|\w+(?:ав|ив|ів|їв|ов|ув|яв)(?:ся)?"
UK_FEM = r"готова|рада|вдячна|впевнена|могла|\w+ла|\w+лась|\w+лася"
RU_MASC = r"рад|готов|уверен|благодарен|\w*мог|\w*ш[её]л|\w+(?:ел|ал|ил|ял|ыл|ул)(?:ся)?"
RU_FEM = r"рада|готова|уверена|благодарна|\w+ла|\w+лась"
WORDS = {("uk", "m"): UK_MASC, ("uk", "f"): UK_FEM, ("ru", "m"): RU_MASC, ("ru", "f"): RU_FEM}
ADDRESS = {
    ("uk", "f"): r"мій друже|друже|мій дорогий|мій хороший",
    ("uk", "m"): r"моя хороша|моя мила|моя дорога|моя люба",
    ("ru", "f"): r"друг мой|мой друг|дорогой|мой хороший",
    ("ru", "m"): r"милая|дорогая|моя хорошая|моя дорогая",
    ("en", "m"): r"my darling|darling|my girl|sweetheart|my sweet",
}
OTHER = {"m": "f", "f": "m"}


def gender_rx(pronouns, words):
    return re.compile(rf"(?<!\w)(?:{pronouns})\s+(?:{FILLER}\s+){{0,2}}?{NOT_VERBS}(?:{words})(?!\w)", re.I)


def thanks_rx(words):
    return re.compile(rf"(?<!\w)(?:дякую|спасибо)\s*,?\s*(?:що|что)\s+(?:(?:ти|ты)\s+)?(?:{FILLER}\s+){{0,2}}?{NOT_VERBS}(?:{words})(?!\w)", re.I)


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} {one}"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"


def msgs(n):
    return plural(n, "повідомлення", "повідомлення", "повідомлень")


def detect_lang(text):
    uk, ru = UK_ONLY.search(text), RU_ONLY.search(text)
    if uk and ru:
        return "mixed"
    if uk:
        return "uk"
    if ru:
        return "ru"
    if CYR.search(text):
        return "ru" if RU_WORDS.search(text) and not UK_WORDS.search(text) else "uk"
    return "en"


def phrase_regex(phrase):
    stem = phrase.rstrip("*")
    tail = r"\w*" if phrase.endswith("*") else ""
    return re.compile(r"(?<!\w)" + re.escape(stem) + tail + r"(?!\w)", re.I)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", nargs="?", help="файл з чернеткою, без нього читається stdin")
    ap.add_argument("--lang", choices=["uk", "ru", "en"], help="мова, за замовчуванням визначається сама")
    ap.add_argument("--persona", choices=["f", "m"], default="f", help="рід рідера, за замовчуванням жінка")
    ap.add_argument("--client", choices=["f", "m"], help="рід клієнта, якщо відомий")
    ap.add_argument("--names", default="", help="імена через кому, з них можна починати повідомлення")
    args = ap.parse_args()

    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    text = re.sub("[’ʼ`]", "'", text.replace("\r\n", "\n"))
    messages = [m.strip() for m in re.split(r"\n\s*\n", text) if m.strip()]
    data = json.loads(MARKERS.read_text(encoding="utf-8"))
    patterns = [(p, re.compile(p["pattern"], re.I | re.M)) for p in data["patterns"]]
    names = {n.strip().lower() for n in args.names.split(",") if n.strip()}
    names |= {w.lower() for w in PROPER.findall(text) if w != "I"}

    lang = args.lang or detect_lang(text)
    found = []

    def add(n, level, note, frag="", family=None):
        found.append((n, level, note, frag, family))

    if lang == "mixed":
        add(0, "error", "суміш української і російської літер")
    phrase_sets = {}
    for code in ("uk", "ru", "en"):
        phrase_sets[code] = [(p, phrase_regex(p)) for p in data["phrases"][code]]

    for n, msg in enumerate(messages, 1):
        msg_lang = detect_lang(msg) if lang == "mixed" else lang
        if msg_lang == "mixed":
            add(n, "error", "в повідомленні українські і російські літери", msg[:40])
            msg_lang = "uk"
        for p, rx in patterns:
            m = rx.search(msg)
            if m:
                add(n, p["level"], p["note"], msg[max(0, m.start() - 20):m.end() + 20], p.get("family"))
        for p, rx in phrase_sets[msg_lang]:
            if rx.search(msg):
                add(n, "error", "ШІ фраза", p)

        if msg_lang == "uk":
            m = RU_ONLY.search(msg) or RU_WORDS.search(msg)
            if m:
                add(n, "error", "російська літера або слово в українському тексті", m.group(0))
        if msg_lang == "ru":
            m = UK_ONLY.search(msg) or UK_WORDS.search(msg)
            if m:
                add(n, "error", "українська літера або слово в російському тексті", m.group(0))
        if msg_lang in ("uk", "ru"):
            me, you = ("я", "ти") if msg_lang == "uk" else ("я", "ты")
            m = gender_rx(me, WORDS[(msg_lang, OTHER[args.persona])]).search(msg)
            if m:
                add(n, "error", "рід не збігається з персоною", m.group(0))
            if args.client:
                wrong = WORDS[(msg_lang, OTHER[args.client])]
                m = gender_rx(you, wrong).search(msg) or thanks_rx(wrong).search(msg)
                if m:
                    add(n, "error", "рід не збігається з клієнтом", m.group(0))
        if args.client and (msg_lang, args.client) in ADDRESS:
            m = re.search(rf"(?<!\w)(?:{ADDRESS[(msg_lang, args.client)]})(?!\w)", msg, re.I)
            if m:
                add(n, "error", "звертання не того роду", m.group(0))

        for s in SENTENCE_SPLIT.split(msg):
            fw = WORD.search(s)
            if fw and fw.group(0)[0].isupper() and fw.group(0).lower() not in names:
                add(n, "warn", "велика літера на початку речення; ім'я передай через --names", s[:30])
        body = EMOJI_TAIL.sub("", msg)
        if body.endswith(".") and not body.endswith("..."):
            add(n, "warn", "крапка в кінці повідомлення", msg[-30:])
        emojis = EMOJI.findall(msg)
        if len(emojis) > 2:
            add(n, "error", f"емоджі {len(emojis)}, максимум 2", "".join(emojis))
        if emojis and EMOJI.search(body):
            add(n, "warn", "емоджі не в кінці")
        if len(WORD.findall(msg)) == 1:
            add(n, "warn", "повідомлення з одного слова", msg)
        if not BOOKING.search(msg):
            if len(msg) > 450:
                add(n, "warn", f"{plural(len(msg), 'символ', 'символи', 'символів')}, розбий на кілька повідомлень", msg[:40])
            sentences = [s for s in SENTENCE_SPLIT.split(msg) if WORD.search(s)]
            if len(sentences) > 3:
                add(n, "warn", f"{plural(len(sentences), 'речення', 'речення', 'речень')}, максимум три", msg[:40])

        short_run = 0
        for s in SENTENCE_SPLIT.split(msg):
            short_run = short_run + 1 if 0 < len(WORD.findall(s)) <= 3 else 0
            if short_run == 3:
                add(n, "error", "три короткі речення підряд", msg[:60])
                break

    run = 0
    for n, msg in enumerate(messages, 1):
        run = run + 1 if 0 < len(WORD.findall(msg)) <= 3 else 0
        if run == 3:
            add(n, "warn", "три короткі повідомлення підряд", msg)
            break
    for n in range(2, len(messages) + 1):
        if messages[n - 2].rstrip().endswith("?") and ANSWER_START.match(messages[n - 1]):
            add(n, "warn", "питання і одразу відповідь наступним повідомленням", messages[n - 1][:40])

    neg = sorted({f[0] for f in found if f[4] == "neg"})
    if len(neg) > 1:
        add(0, "error", f"заперечення і заміна (не X а Y) в {msgs(len(neg))}: {', '.join('#' + str(x) for x in neg)}")

    see = sum(len(re.findall(r"(?<!\w)(?:я бачу|я вижу|i see)(?!\w)", m, re.I)) for m in messages)
    if see > max(1, len(messages) // 3):
        add(0, "warn", f"я бачу {plural(see, 'раз', 'рази', 'разів')} на {msgs(len(messages))}, чергуй вступні")

    openers = Counter(" ".join(w.lower() for w in WORD.findall(m)[:2]) for m in messages)
    for opener, count in openers.items():
        if opener and count > 2:
            add(0, "warn", f"{msgs(count)} починаються однаково", opener)
    firsts = [WORD.findall(m)[0].lower() if WORD.findall(m) else "" for m in messages]
    for i in range(len(firsts) - 2):
        if firsts[i] and firsts[i] == firsts[i + 1] == firsts[i + 2]:
            add(i + 3, "warn", "три повідомлення підряд з того самого слова", firsts[i])
            break

    if not found:
        print(f"чисто, {msgs(len(messages))}, мова {lang}")
        return 0
    for n, level, note, frag, _ in found:
        where = f"#{n}" if n else "всі"
        label = "ПОМИЛКА" if level == "error" else "увага"
        tail = f" :: {frag.strip()}" if frag else ""
        print(f"{where} {label}: {note}{tail}")
    errors = sum(1 for f in found if f[1] == "error")
    print(f"\n{plural(errors, 'помилка', 'помилки', 'помилок')}, "
          f"{plural(len(found) - errors, 'попередження', 'попередження', 'попереджень')}, {msgs(len(messages))}, мова {lang}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
