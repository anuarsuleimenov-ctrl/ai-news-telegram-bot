"""
AI News Daily Bot — Ежедневный дайджест AI новостей
Использует Claude API + аналитический стиль для переписывания новостей
08:00 и 16:00 по Астане (03:00 и 11:00 UTC)
"""
import requests, schedule, time, datetime, sys, os, re, json, html
import xml.etree.ElementTree as ET
from anthropic import Anthropic

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Astana = UTC+5
# 08:00 Astana = 03:00 UTC
# 16:00 Astana = 11:00 UTC
# 19:00 Astana = 14:00 UTC
SEND_HOUR_MORNING = os.environ.get("SEND_HOUR_MORNING", "03:00")
SEND_HOUR_EVENING = os.environ.get("SEND_HOUR_EVENING", "11:00")
SEND_HOUR_NIGHT   = os.environ.get("SEND_HOUR_NIGHT",   "14:00")

NEWS_PER_SLOT = {
    "morning": 4,
    "evening": 4,
    "night":   2,
}

SYSTEM_PROMPT = """Ты — AI-аналитик и редактор Telegram-канала про AI и технологии.
Пишешь в стиле Николая Хлебинского: экспертно, с личным мнением, без воды.

СТИЛЬ И ТОН:
- Пишешь как эксперт, который разбирается в теме. Уверенно, от первого лица.
- Тон: аналитический, прямой, с характером. Не боишься высказать мнение.
- Без эмодзи в тексте. Только жирный заголовок и чистый секст.
- Конкретика: цифры, имена, суммы, проценты. Абстракции = мусор.
- Короткие абзацы. Одна мысль = один абзац.
- Можешь задать риторический вопрос, бросить провокацию.
- Бизнес-угол: как это влияет на рынок, деньги, стратегию.
- Если уместно — упомяни контекст для Казахстана/СНГ (Kaspi, Astana Hub, местные реалии).

ЗАПРЕЩЕНО:
- Пафос ("в эпоху перемен", "революционный прорыв", "уникальная возможность")
- Вода и канцелярит ("в рамках реализации", "данный продукт")
- Эмодзи (совсем — ни в заголовках, ни в тексте)
- Восторженность ("Это невероятно!", "Вау!")
- HTML теги. Только чистый текст.
- Выдумывать факты или додумывать то, чего нет в новости.

ФОРМАТ для КАЖДОЙ новости:

{Жирный заголовок — переосмысленный, цепляющий, без эмодзи}

{Контекст и суть: 2-4 предложения. Что случилось, почему это важно, цифры.}

{Мнение/вывод: 1-2 предложения — острое, честное, с позицией. Что это значит для рынка/бизнеса/пользователей.}

[LINK]

---

Правила:
- Заголовок — НЕ перевод оригинала. Переосмысли, сформулируй остро.
- Пиши по-русски, но английские термины оставляй как есть (API, open source, SaaS).
- НЕ нумеруй новости.
- Разделяй новости строкой --- между ними.
- Пиши [LINK] отдельной строкой после каждой новости — я заменю на ссылку.
- Разная глубина: где-то хватит 3 предложений, где-то новость заслуживает 5-6."""


def escape_html(text):
    """Escape HTML special characters"""
    return html.escape(str(text)) if text else ""


def send_telegram_message(text, use_html=True):
    """Send message to Telegram with HTML, fallback to plain text"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    if use_html:
        payload["parse_mode"] = "HTML"

    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            print(f"[{datetime.datetime.now()}] Sent!")
            return True
        else:
            print(f"[{datetime.datetime.now()}] Error: {r.text}")
            # Fallback: strip HTML and send as plain text
            if use_html:
                print("Falling back to plain text...")
                clean = re.sub(r'<[^>]+>', '', text)
                return send_telegram_message(clean, use_html=False)
            return False
    except Exception as e:
        print(f"Send error: {e}")
        return False


HISTORY_FILE = "sent_news_history.json"
HISTORY_DAYS = 7


def load_history():
    """Load previously sent news titles (last 7 days)"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"History load error: {e}")
    return {}


def save_history(history):
    """Save sent news history to disk"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"History save error: {e}")


def clean_old_history(history):
    """Remove entries older than HISTORY_DAYS days"""
    cutoff = (datetime.date.today() - datetime.timedelta(days=HISTORY_DAYS)).isoformat()
    return {k: v for k, v in history.items() if v >= cutoff}


def normalize_title(title):
    """Normalize title for duplicate comparison"""
    return re.sub(r"[^a-zA-Zа-яёА-ЯЁ0-9]", "", title.lower())


def is_duplicate(article, history):
    """Check if article title was already sent in the past 7 days"""
    norm = normalize_title(article["title"])
    return norm in history


def update_history(history, articles):
    """Add new articles to history with today's date"""
    today = datetime.date.today().isoformat()
    for a in articles:
        norm = normalize_title(a["title"])
        history[norm] = today
    return history


def fetch_news():
    queries = [
        "artificial+intelligence+news",
        "AI+technology+2026",
        "machine+learning+breakthrough"
    ]
    articles = []
    for q in queries:
        try:
            r = requests.get(
                f"https://news.google.com/rss/search?q={q}&hl=en&gl=US&ceid=US:en",
                timeout=15
            )
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    link = item.find("link")
                    source = item.find("source")
                    if title is not None and link is not None:
                        articles.append({
                            "title": title.text or "",
                            "url": link.text or "",
                            "source": source.text if source is not None else ""
                        })
        except Exception as e:
            print(f"RSS error: {e}")

    # Deduplicate within current fetch
    seen = set()
    unique = []
    for a in articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)

    # Filter against 7-day history
    history = clean_old_history(load_history())
    fresh = [a for a in unique if not is_duplicate(a, history)]
    skipped = len(unique) - len(fresh)
    if skipped > 0:
        print(f"Skipped {skipped} duplicate(s) from past {HISTORY_DAYS} days")

    return fresh


def rewrite_with_claude(articles):
    if not ANTHROPIC_API_KEY:
        print("No ANTHROPIC_API_KEY, using raw titles")
        return None

    titles_text = ""
    for i, a in enumerate(articles, 1):
        source = f" ({a['source']})" if a.get('source') else ""
        titles_text += f"{i}. {a['title']}{source}\n"

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Вот {len(articles)} новостей. Перепиши каждую. Пиши [LINK] отдельной строкой после каждой новости.\n\n{titles_text}"
            }]
        )
        result = message.content[0].text
        print(f"Claude done ({message.usage.input_tokens}+{message.usage.output_tokens} tokens)")
        return result
    except Exception as e:
        print(f"Claude API error: {e}")
        return None


def inject_links_html(rewritten_text, articles):
    """Replace [LINK] with HTML hyperlinks; auto-bold first line of each block"""
    lines = rewritten_text.split("\n")
    result = []
    article_idx = 0
    at_block_start = True  # first non-empty line of each news block = headline

    for line in lines:
        stripped = line.strip()
        if "[LINK]" in stripped and article_idx < len(articles):
            url = articles[article_idx]["url"]
            result.append(f'<a href="{url}">подробнее здесь</a>')
            article_idx += 1
        elif stripped == "---":
            result.append("")
            result.append("━" * 15)
            result.append("")
            at_block_start = True  # next non-empty line = new headline
        elif at_block_start and stripped:
            # First non-empty line of block → bold headline
            result.append(f"<b>{escape_html(stripped)}</b>")
            at_block_start = False
        else:
            result.append(escape_html(line))

    # Add remaining links if Claude didn't add enough [LINK]
    while article_idx < len(articles):
        url = articles[article_idx]["url"]
        result.append(f'<a href="{url}">подробнее здесь</a>')
        article_idx += 1

    return "\n".join(result)


def split_message_by_separator(full_msg, separator="━" * 15, max_len=4096):
    """Split a long message into parts at separator lines, respecting Telegram limit"""
    if len(full_msg) <= max_len:
        return [full_msg]

    parts = []
    current = ""
    # Split by the separator line
    blocks = full_msg.split(separator)

    for i, block in enumerate(blocks):
        # Add separator back (except before first block)
        candidate = current + (separator if current and i > 0 else "") + block
        if len(candidate) > max_len and current:
            # Current part is full, save it
            parts.append(current.strip())
            current = block
        else:
            current = candidate

    if current.strip():
        parts.append(current.strip())

    return parts if parts else [full_msg[:max_len]]


def send_daily_digest(slot="morning"):
    """
    Send digest for given time slot.
    slot: "morning" (08:00), "evening" (16:00), "night" (19:00) — Astana time
    """
    slot_labels = {"morning": "08:00", "evening": "16:00", "night": "19:00"}
    slot_label = slot_labels.get(slot, "08:00")
    count = NEWS_PER_SLOT.get(slot, 4)

    print(f"\n[{datetime.datetime.now()}] Fetching news for {slot_label} Astana digest ({count} items)...")
    articles = fetch_news()[:count]

    if not articles:
        send_telegram_message("Свежих новостей пока нет.")
        return

    today = datetime.date.today().strftime("%d.%m.%Y")
    header = f"<b>AI &amp; Tech — {today}, {slot_label}</b>\n\n{'━' * 15}\n\n"
    footer = f"\n{'━' * 15}\n<i>AI News | 08:00, 16:00 и 19:00 по Астане</i>"

    rewritten = rewrite_with_claude(articles)
    if rewritten:
        body = inject_links_html(rewritten, articles)
        msg = header + body + footer
    else:
        # Fallback without Claude
        lines = []
        emojis = ["🔥", "⚡", "🚀", "🤖"]
        for i, a in enumerate(articles):
            emoji = emojis[i % len(emojis)]
            safe_title = escape_html(a["title"])
            source = f" ({escape_html(a['source'])})" if a.get("source") else ""
            lines.append(f'{emoji} {safe_title}{source}\n<a href="{a["url"]}">подробнее здесь</a>')
        msg = header + "\n\n".join(lines) + footer

    # Split into multiple messages if too long
    parts = split_message_by_separator(msg)
    print(f"Sending {len(parts)} message(s)...")
    for i, part in enumerate(parts):
        if i > 0:
            time.sleep(1)
        send_telegram_message(part)

    # Save articles to history to avoid repeats next 7 days
    history = clean_old_history(load_history())
    history = update_history(history, articles)
    save_history(history)
    print(f"History updated: {len(history)} titles stored")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        send_telegram_message("<b>AI News Bot подключён.</b>\nClaude API: " + ("да" if ANTHROPIC_API_KEY else "нет"))
    elif len(sys.argv) > 1 and sys.argv[1] == "once":
        send_daily_digest("morning")
    else:
        print(f"Bot started!")
        print(f"Morning digest : {SEND_HOUR_MORNING} UTC (08:00 Astana) — 4 новости")
        print(f"Evening digest : {SEND_HOUR_EVENING} UTC (16:00 Astana) — 4 новости")
        print(f"Night digest   : {SEND_HOUR_NIGHT}   UTC (19:00 Astana) — 2 новости")
        print(f"Claude API: {'enabled' if ANTHROPIC_API_KEY else 'disabled'}")

        # Send once on startup
        send_daily_digest("morning")

        # Schedule morning (08:00 Astana = 03:00 UTC)
        schedule.every().day.at(SEND_HOUR_MORNING).do(send_daily_digest, slot="morning")
        # Schedule evening (16:00 Astana = 11:00 UTC)
        schedule.every().day.at(SEND_HOUR_EVENING).do(send_daily_digest, slot="evening")
        # Schedule night (19:00 Astana = 14:00 UTC)
        schedule.every().day.at(SEND_HOUR_NIGHT).do(send_daily_digest, slot="night")

        while True:
            schedule.run_pending()
            time.sleep(60)
