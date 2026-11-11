#!/usr/bin/env python3
"""Проверка второго мозга (CLAUDE.md или AGENTS.md) без нейросети.

Что смотрит:
  1. один ли второй мозг в папке (CLAUDE.md рядом с AGENTS.md - только ссылкой);
  2. живы ли все адреса из файла: пути в обратных кавычках и [[вики-ссылки]];
  3. нет ли в rules/ файлов, на которые второй мозг не ссылается;
  4. нет ли дублей: одна строка и во втором мозге, и в файле правил;
  5. нет ли похожего на ключи, токены и пароли - во втором мозге, в его
     копиях *.bak* и в папках ai-clone/, business/, rules/, plans/, prompts/;
  6. не вышел ли файл за потолок, записанный в нём самом, а если его нет - 200 строк.

Запуск из папки проекта:
    python3 tools/check-claude-md.py            # найдёт AGENTS.md или CLAUDE.md сам
    python3 tools/check-claude-md.py GEMINI.md  # другой файл

Код выхода всегда 0, смотреть строку «ИТОГ». Файлы программа не меняет.
"""
import os
import re
import sys

POTOLOK_PO_UMOLCHANIYU = 200
KANDIDATY = ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md"]
RASSHIRENIYA = r"(?:md|txt|py|sh|js|ts|json|yaml|yml|toml|csv|pdf|xlsx|docx)"

problemy = []


def razdel(nazvanie):
    print("\n" + nazvanie)
    print("-" * len(nazvanie))


def najti_mozg():
    if len(sys.argv) > 1:
        return sys.argv[1]
    for imya in KANDIDATY:
        if os.path.isfile(imya):
            # CLAUDE.md-ссылка на AGENTS.md: проверяем сам AGENTS.md
            return os.path.realpath(imya) if os.path.islink(imya) else imya
    return None


def chitat(put):
    with open(put, encoding="utf-8", errors="replace") as f:
        return f.read()


def normalno(stroka):
    return re.sub(r"\s+", " ", stroka.strip(" -*|>#\t").lower())


mozg = najti_mozg()
if not mozg or not os.path.isfile(mozg):
    print("Второй мозг не найден: нет AGENTS.md, CLAUDE.md, GEMINI.md или .github/copilot-instructions.md.")
    print("ИТОГ: проверять нечего")
    sys.exit(0)

imya_mozga = os.path.relpath(mozg)
tekst = chitat(mozg)
stroki = tekst.splitlines()
print(f"Второй мозг: {imya_mozga}, {len(stroki)} строк")

# --- 1. один второй мозг ---
razdel("1. Один второй мозг")
if os.path.exists("CLAUDE.md") and os.path.exists("AGENTS.md"):
    if os.path.islink("CLAUDE.md"):
        cel = os.readlink("CLAUDE.md")
        ok = os.path.basename(cel) == "AGENTS.md"
        print(f"  {'ok  ' if ok else 'НЕТ '} CLAUDE.md - ссылка на {cel}")
        if not ok:
            problemy.append(f"CLAUDE.md ссылается на {cel}, а не на AGENTS.md")
    elif chitat("CLAUDE.md").strip() == "@AGENTS.md":
        print("  ok   CLAUDE.md - строка @AGENTS.md")
    else:
        print("  НЕТ  CLAUDE.md и AGENTS.md - два разных файла")
        problemy.append("в папке два разных вторых мозга: CLAUDE.md и AGENTS.md - сведи в AGENTS.md, CLAUDE.md сделай ссылкой")
else:
    print("  ok   второй мозг один")

# --- 2. адреса ---
razdel("2. Адреса из второго мозга")
adresa = set()
for kusok in re.findall(r"`([^`\n]+)`", tekst):
    kusok = kusok.strip()
    if " " in kusok or kusok.startswith(("@", "/", "~", "http", "-")):
        continue  # команда, флаг, ссылка или путь вне проекта
    if re.fullmatch(r"[\w.\-/]+\." + RASSHIRENIYA, kusok) or re.fullmatch(r"[\w.\-/]+/", kusok):
        adresa.add(kusok)
for kusok in re.findall(r"\[\[([^\]|#]+)", tekst):
    adresa.add(kusok.strip())
for put in sorted(adresa):
    if re.search(r"<|>|ГГГГ|YYYY|\[|\*", put):
        print(f"  шаблон {put} - пропускаю")
        continue
    est = os.path.exists(put) or os.path.exists(put + ".md")
    print(f"  {'ok  ' if est else 'НЕТ '} {put}")
    if not est:
        problemy.append(f"адрес {put} ведёт в пустоту - создай файл или убери строку")
if not adresa:
    print("  адресов нет")

# --- 3. сироты в rules/ ---
razdel("3. Файлы правил без адреса во втором мозге")
if os.path.isdir("rules"):
    for imya in sorted(os.listdir("rules")):
        if not imya.endswith(".md"):
            continue
        upomyanut = f"rules/{imya}" in tekst or f"rules/{imya[:-3]}" in tekst
        print(f"  {'ok    ' if upomyanut else 'СИРОТА'} rules/{imya}")
        if not upomyanut:
            problemy.append(f"rules/{imya} нигде не упомянут - агент его не найдёт")
else:
    print("  папки rules/ нет")

# --- 4. дубли ---
razdel("4. Дубли")
svoi = {}
for nomer, stroka in enumerate(stroki, 1):
    n = normalno(stroka)
    if len(n) >= 40 and not n.startswith(("```", "|---")):
        svoi.setdefault(n, []).append(nomer)
dubli = 0
for n, nomera in svoi.items():
    if len(nomera) > 1:
        dubli += 1
        print(f"  ДУБЛЬ внутри файла, строки {nomera}: {n[:70]}")
        problemy.append(f"одна и та же строка повторяется в {imya_mozga}, строки {nomera}")
if os.path.isdir("rules"):
    for imya in sorted(os.listdir("rules")):
        if not imya.endswith(".md"):
            continue
        for stroka in chitat(os.path.join("rules", imya)).split("\n"):
            n = normalno(stroka)
            if n in svoi:
                dubli += 1
                print(f"  ДУБЛЬ с rules/{imya}: {n[:70]}")
                problemy.append(f"строка расписана и во втором мозге, и в rules/{imya} - оставь в одном месте, во втором мозге адрес")
if not dubli:
    print("  дублей нет")

# --- 5. ключи ---
razdel("5. Похожее на ключи, токены и пароли")
UZORY = [
    (r"sk-[A-Za-z0-9_\-]{16,}", "ключ вида sk-"),
    (r"gh[pousr]_[A-Za-z0-9]{20,}", "токен GitHub"),
    (r"xox[abprs]-[A-Za-z0-9\-]{10,}", "токен Slack"),
    (r"AKIA[0-9A-Z]{16}", "ключ AWS"),
    (r"AIza[0-9A-Za-z_\-]{30,}", "ключ Google"),
    (r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}", "токен Telegram-бота"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "приватный ключ"),
    (r"(?i)(password|passwd|пароль|api[_\- ]?key|secret|token|токен)\s*[:=]\s*\S{6,}", "пароль или ключ значением"),
]
PAPKI_MOZGA = ["ai-clone", "business", "rules", "plans", "prompts"]
na_proverku = [mozg] + sorted(i for i in os.listdir(".") if ".bak" in i and os.path.isfile(i))
for papka in PAPKI_MOZGA:
    for koren, _, imena in os.walk(papka):
        na_proverku += [os.path.join(koren, i) for i in sorted(imena) if i.endswith((".md", ".txt"))]
nashlos = 0
for fajl in na_proverku:
    soderzhimoe = chitat(fajl)
    for uzor, chto in UZORY:
        for m in re.finditer(uzor, soderzhimoe):
            nashlos += 1
            nomer = soderzhimoe[: m.start()].count("\n") + 1
            imya = os.path.relpath(fajl)
            print(f"  ЕСТЬ  {imya}, строка {nomer}: {chto}")
            problemy.append(f"{imya}, строка {nomer} похожа на {chto} - убери значение, оставь только где он лежит")
print(f"  просмотрено файлов: {len(na_proverku)}")
if not nashlos:
    print("  ничего похожего")

# --- 6. потолок ---
razdel("6. Длина")
m = re.search(r"(?i)потол[а-я]*\s*[-:]?\s*(\d{2,4})\s*строк", tekst)
potolok = int(m.group(1)) if m else POTOLOK_PO_UMOLCHANIYU
otkuda = "записан в файле" if m else "по умолчанию"
print(f"  {len(stroki)} строк, потолок {potolok} ({otkuda})")
if len(stroki) > potolok:
    problemy.append(f"{imya_mozga} - {len(stroki)} строк при потолке {potolok}: вынеси справочное в папки или дай промпт похудения")

# --- ИТОГ ---
razdel("ИТОГ")
if problemy:
    for p in problemy:
        print(f"  ПРОБЛЕМА: {p}")
    print(f"ИТОГ: проблем {len(problemy)}")
else:
    print("ИТОГ: проблем не найдено")
sys.exit(0)
