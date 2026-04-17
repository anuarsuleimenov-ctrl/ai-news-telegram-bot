"""
AI News Daily Bot — Ежедневный дайджест AI новостей
Использует Claude API + Voice DNA Anuar для переписывания новостей
"""
import requests, schedule, time, datetime, sys, os, re, json, html
import xml.etree.ElementTree as ET
from anthropic import Anthropic

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SEND_HOUR = os.environ.get("SEND_HOUR", "03:00")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Ты — AI-аналитик и редактор Telegram-канала про AI и технологии.
Пишешь в стиле Николая Хлебинского: экспертно, с личным мнением, без воды.

СТИЛЬ И ТОН:
- Пишешь как эксперт, который разбирается в теме. Уверенно, от первого лица.
- Тон: аналитический, прямой, с характером. Не боишься высказать мнение.
- Без эмодзи в тексте. Только жирный заголовок и чистый текст.
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

    seen = set()
    unique = []
    for a in articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)
    return unique[:10]


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
            max_tokens=2500,
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
    """Replace [LINK] with HTML hyperlinks and escape Claude's text for HTML"""
    lines = rewritten_text.split("\n")
    result = []
    article_idx = 0

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
        else:
            # Escape HTML in Claude's text to prevent parse errors
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


def send_daily_digest():
    print(f"\n[{datetime.datetime.now()}] Fetching news...")
    articles = fetch_news()

    if not articles:
        send_telegram_message("Сегодня новостей не найдено.")
        return

    today = datetime.date.today().strftime("%d.%m.%Y")
    header = f"<b>AI &amp; Tech \u2014 Дайджест дня</b>\n{today}\n\n{'━' * 15}\n\n"
    footer = f"\n{'━' * 15}\n<i>AI News Bot | Ежедневно в 08:00</i>"

    rewritten = rewrite_with_claude(articles)
    if rewritten:
        body = inject_links_html(rewritten, articles)
        msg = header + body + footer
    else:
        # Fallback without Claude
        lines = []
        emojis = ["\U0001F525", "\u26A1", "\U0001F680", "\U0001F916", "\U0001F4A1",
                  "\U0001F9E0", "\U0001F4CA", "\U0001F52C", "\U0001F4BB", "\U0001F310"]
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
            time.sleep(1)  # Small delay between messages
        send_telegram_message(part)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        send_telegram_message("<b>AI News Bot подключён.</b>\nClaude API: " + ("да" if ANTHROPIC_API_KEY else "нет"))
    elif len(sys.argv) > 1 and sys.argv[1] == "once":
        send_daily_digest()
    else:
        print(f"Bot started! Daily at {SEND_HOUR}")
        print(f"Claude API: {'enabled' if ANTHROPIC_API_KEY else 'disabled'}")
        send_daily_digest()
        schedule.every().day.at(SEND_HOUR).do(send_daily_digest)
        while True:
            schedule.run_pending()
            time.sleep(60)

