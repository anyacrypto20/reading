#!/usr/bin/env python3
"""Перевіряє чернетку повідомлень рідера (розділені порожнім рядком) на ШІ маркери."""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

MARKERS = Path(__file__).resolve().parent.parent / "references" / "ai-markers.json"
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B50\u2764]")
EMOJI_TAIL = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B50\u2764\uFE0F\u200D\\s]+$")
UK_ONLY = re.compile("[іїєґІЇЄҐ]")
RU_ONLY = re.compile("[ыэъёЫЭЪЁ]")
CYR = re.compile("[а-яА-ЯіїєґІЇЄҐёЁ]")
BOOKING = re.compile(r"(?i)заброн|читанн|чтени|book|reading")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
RU_I = re.compile(r"(?<!\w)и(?!\w)", re.I)
UK_MASC = r"готовий|радий|вдячний|впевнений|побачив|відчув|почав|зрозумів|хотів|бачив|помітив|зробив|написав|розкрив|зчитав|глянув|був|прийшов|\w+ився"
UK_FEM = r"готова|рада|вдячна|впевнена|\w+ла|\w+лась"
RU_MASC = r"рад|готов|уверен|благодарен|пришел|пришёл|\w+(?:ел|ал|ил|ял|ыл|ул)(?:ся)?"
RU_FEM = r"рада|готова|уверена|благодарна|\w+ла|\w+лась"
NOT_VERBS = r"(?!(?:знов|любов|здоров|готов|знову|себе)(?!\w))"


def gender_rx(pronouns, words):
    return re.compile(rf"(?<!\w)(?:{pronouns})\s+(?:\w+\s+){{0,2}}?{NOT_VERBS}(?:{words})(?!\w)", re.I)


GENDER_SLIP = {
    ("uk", "f"): gender_rx("я", UK_MASC), ("uk", "m"): gender_rx("я", UK_FEM),
    ("ru", "f"): gender_rx("я", RU_MASC), ("ru", "m"): gender_rx("я", RU_FEM),
}
CLIENT_SLIP = {
    ("uk", "f"): gender_rx("ти", UK_MASC), ("uk", "m"): gender_rx("ти", UK_FEM),
    ("ru", "f"): gender_rx("ты", RU_MASC), ("ru", "m"): gender_rx("ты", RU_FEM),
}


def detect_lang(text):
    uk, ru = bool(UK_ONLY.search(text)), bool(RU_ONLY.search(text))
    if uk and ru:
        return "mixed"
    if uk:
        return "uk"
    if ru:
        return "ru"
    return "uk" if CYR.search(text) else "en"


def phrase_regex(phrase):
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.I)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", nargs="?", help="файл з чернеткою, без нього читається stdin")
    ap.add_argument("--lang", choices=["uk", "ru", "en"], help="мова, за замовчуванням визначається сама")
    ap.add_argument("--persona", choices=["f", "m"], default="f", help="рід рідера, за замовчуванням жінка")
    ap.add_argument("--client", choices=["f", "m"], help="рід клієнта, якщо відомий")
    args = ap.parse_args()

    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    messages = [m.strip() for m in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if m.strip()]
    data = json.loads(MARKERS.read_text(encoding="utf-8"))
    patterns = [(p, re.compile(p["pattern"], re.I | re.M)) for p in data["patterns"]]

    lang = args.lang or detect_lang(text)
    found = []

    def add(n, level, note, frag=""):
        found.append((n, level, note, frag))

    if lang == "mixed":
        add(0, "error", "суміш української і російської літер", "")
        lang_phrases = list(dict.fromkeys(data["phrases"]["uk"] + data["phrases"]["ru"]))
    else:
        lang_phrases = data["phrases"].get(lang, [])
    phrases = [(p, phrase_regex(p)) for p in lang_phrases]

    for n, msg in enumerate(messages, 1):
        for p, rx in patterns:
            m = rx.search(msg)
            if m:
                add(n, p["level"], p["note"], msg[max(0, m.start() - 20):m.end() + 20])
        for p, rx in phrases:
            if rx.search(msg):
                add(n, "error", "ШІ фраза", p)
        msg_lang = detect_lang(msg) if lang == "mixed" else lang
        if msg_lang == "uk" and RU_I.search(msg):
            add(n, "error", "російське и в українському тексті", msg[:40])
        if msg_lang in ("uk", "ru"):
            m = GENDER_SLIP[(msg_lang, args.persona)].search(msg)
            if m:
                add(n, "error", "рід не збігається з персоною", m.group(0))
            m = args.client and CLIENT_SLIP[(msg_lang, args.client)].search(msg)
            if m:
                add(n, "error", "рід не збігається з клієнтом", m.group(0))

        first = next((c for c in msg if c.isalpha()), "")
        if first.isupper():
            add(n, "warn", "велика літера на початку, можна тільки ім'я або карта", msg[:30])
        body = EMOJI_TAIL.sub("", msg)
        if body.endswith(".") and not body.endswith("..."):
            add(n, "warn", "крапка в кінці повідомлення", msg[-30:])
        emojis = EMOJI.findall(msg)
        if len(emojis) > 2:
            add(n, "error", f"емоджі {len(emojis)}, максимум 2", "".join(emojis))
        if emojis and EMOJI.search(body):
            add(n, "warn", "емоджі не в кінці", "")
        if len(re.findall(r"\w+", msg)) == 1:
            add(n, "warn", "повідомлення з одного слова", msg)
        if len(msg) > 450 and not BOOKING.search(msg):
            add(n, "warn", f"{len(msg)} символів, розбий на кілька повідомлень", msg[:40])

        short_run = 0
        for s in SENTENCE_SPLIT.split(msg):
            short_run = short_run + 1 if 0 < len(re.findall(r"\w+", s)) <= 3 else 0
            if short_run == 3:
                add(n, "error", "три короткі речення підряд", msg[:60])
                break

    see = sum(len(re.findall(r"(?<!\w)(?:я бачу|я вижу|i see)(?!\w)", m, re.I)) for m in messages)
    if see > max(1, len(messages) // 3):
        add(0, "warn", f"я бачу {see} разів на {len(messages)} повідомлень, чергуй вступні", "")

    openers = Counter(" ".join(re.findall(r"\w+", m.lower())[:2]) for m in messages)
    for opener, count in openers.items():
        if opener and count > 2:
            add(0, "warn", f"{count} повідомлення починаються однаково", opener)

    if not found:
        print(f"чисто, {len(messages)} повідомлень, мова {lang}")
        return 0
    for n, level, note, frag in found:
        where = f"#{n}" if n else "всі"
        label = "ПОМИЛКА" if level == "error" else "увага"
        tail = f" :: {frag.strip()}" if frag else ""
        print(f"{where} {label}: {note}{tail}")
    errors = sum(1 for f in found if f[1] == "error")
    print(f"\n{errors} помилок, {len(found) - errors} попереджень, {len(messages)} повідомлень, мова {lang}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
