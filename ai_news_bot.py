"""
AI News Daily Bot — Ежедневный дайджест AI новостей
Использует Claude API для переписывания новостей в живом стиле
"""
import requests, schedule, time, datetime, sys, os, re, json
import xml.etree.ElementTree as ET
from anthropic import Anthropic

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SEND_HOUR = os.environ.get("SEND_HOUR", "03:00")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Ты — AI-редактор русскоязычного Telegram-канала про технологии и искусственный интеллект.

Твоя задача: взять список сухих заголовков новостей (из RSS, обычно на английском) и превратить их в живой, интересный дайджест на русском.

Стиль: как умный друг рассказывает за кофе. Дерзко, с юмором, простыми словами. Можно с иронией.

Для КАЖДОЙ новости напиши СТРОГО в формате:

{эмодзи} {Цепляющий заголовок на русском}

{Выжимка: 1-2 предложения что произошло, простым языком}

{Мнение: 1 предложение — почему важно или что значит}

---

Правила:
- Заголовок — не перевод, а переосмысление. Должен цеплять.
- Выжимка — коротко и ясно, без терминов
- Мнение — дерзкое, честное, можно с иронией
- Используй разные эмодзи по смыслу
- НЕ выдумывай факты
- НЕ используй HTML теги. Только чистый текст.
- Разделяй новости строкой --- между ними
- Когда уместно — отсылки к казахстанским реалиям"""


def send_telegram_message(text):
    """Send plain text message to Telegram (no HTML to avoid parsing errors)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            print(f"[{datetime.datetime.now()}] Sent!")
            return True
        else:
            print(f"[{datetime.datetime.now()}] Error: {r.text}")
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
                "content": f"Вот {len(articles)} новостей. Перепиши каждую в живом стиле. После каждой новости добавь строку с текстом 'Подробнее: [LINK]' где [LINK] — я заменю на реальную ссылку.\n\n{titles_text}"
            }]
        )
        result = message.content[0].text
        print(f"Claude done ({message.usage.input_tokens}+{message.usage.output_tokens} tokens)")
        return result
    except Exception as e:
        print(f"Claude API error: {e}")
        return None


def inject_links(rewritten_text, articles):
    """Replace [LINK] placeholders and --- separators with real URLs"""
    lines = rewritten_text.split("\n")
    result = []
    article_idx = 0

    for line in lines:
        if "[LINK]" in line and article_idx < len(articles):
            result.append(line.replace("[LINK]", articles[article_idx]["url"]))
            article_idx += 1
        elif line.strip() == "---":
            result.append("")
            result.append("━━━━━━━━━━━━━━━")
            result.append("")
        else:
            result.append(line)

    while article_idx < len(articles):
        result.append("🔗 Подробнее: " + articles[article_idx]["url"])
        article_idx += 1

    return "\n".join(result)


def send_daily_digest():
    print(f"\n[{datetime.datetime.now()}] Fetching news...")
    articles = fetch_news()

    if not articles:
        send_telegram_message("😔 Сегодня новостей не найдено.")
        return

    today = datetime.date.today().strftime("%d.%m.%Y")
    header = f"🗞Paragraph AI & Tech — Дайджест дня\n📅 {today}\n\n━━━━━━━━━━━━━━━\n\n"
    footer = f"\n━━━━━━━━━━━━━━━\n🤖 AI News Bot | Ежедневно в 08:00"

    rewritten = rewrite_with_claude(articles)
    if rewritten:
        body = inject_links(rewritten, articles)
        msg = header + body + footer
    else:
        lines = []
        emojis = ["🔥", "⚡", "🚀", "🤖", "💡", "🧠", "📊", "🔬", "💻", "🌐"]
        for i, a in enumerate(articles):
            emoji = emojis[i % len(emojis)]
            source = f" ({a['source']})" if a.get("source") else ""
            lines.append(f"{emoji} {a['title']}{source}\n🔗 Подробнее: {a['url']}")
        msg = header + "\n\n".join(lines) + footer

    if len(msg) > 4096:
        msg = msg[:4090] + "..."

    send_telegram_message(msg)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        send_telegram_message("✅ AI News Bot подключён!\nClaude API: " + ("✅" if ANTHROPIC_API_KEY else "❌"))
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
