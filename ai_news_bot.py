"""
AI News Daily Bot — Ежедневный дайджест AI новостей
Использует Claude API для переписывания новостей в живом стиле
"""
import requests, schedule, time, datetime, sys, os, html, re, json
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

Правила:
- Заголовок — не перевод, а переосмысление. Должен цеплять.
- Выжимка — коротко и ясно, без терминов
- Мнение — дерзкое, честное, можно с иронией
- Используй разные эмодзи по смыслу: 🤖 AI, 💰 деньги, 🚀 запуски, ⚡ срочное, 🧠 наука, 🔒 безопасность, 📱 мобильные, 💻 софт, 🌍 глобальное
- НЕ выдумывай факты
- НЕ начинай каждую новость с "Компания X объявила..."
- Между новостями пустая строка
- Когда уместно — отсылки к казахстанским реалиям (Kaspi, Astana Hub, местный рынок)"""


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            print(f"[{datetime.datetime.now()}] Sent!")
            return True
        else:
            print(f"[{datetime.datetime.now()}] HTML error: {r.text}")
            fallback = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True}
            r2 = requests.post(url, json=fallback, timeout=30)
            print(f"[{datetime.datetime.now()}] Fallback plain: {'Sent!' if r2.status_code == 200 else r2.text}")
            return r2.status_code == 200
    except Exception as e:
        print(f"Send error: {e}")
        return False


def escape_html(text):
    return html.escape(str(text)) if text else ""


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
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Вот {len(articles)} новостей из RSS. Перепиши каждую в живом стиле:\n\n{titles_text}"
            }]
        )
        result = message.content[0].text
        print(f"Claude rewrite done ({message.usage.input_tokens}+{message.usage.output_tokens} tokens)")
        return result
    except Exception as e:
        print(f"Claude API error: {e}")
        return None


def build_fallback_digest(articles):
    lines = []
    emojis = ["🔥", "⚡", "🚀", "🤖", "💡", "🧠", "📊", "🔬", "💻", "🌐"]
    for i, a in enumerate(articles):
        emoji = emojis[i % len(emojis)]
        safe_title = escape_html(a["title"])
        source = f"  📌 {escape_html(a['source'])}" if a.get("source") else ""
        lines.append(f'{emoji} <b>{safe_title}</b>{source}\n    🔗 <a href="{a["url"]}">Подробнее здесь</a>')
    return "\n\n".join(lines)


def send_daily_digest():
    print(f"\n[{datetime.datetime.now()}] Fetching news...")
    articles = fetch_news()
    if not articles:
        send_telegram_message("😔 Сегодня новостей не найдено.")
        return

    today = datetime.date.today().strftime("%d.%m.%Y")

    # Try Claude rewrite
    rewritten = rewrite_with_claude(articles)

    if rewritten:
        # Build message with Claude's rewrite + links
        msg = f"🗞 <b>AI & Tech — Дайджест дня</b>\n📅 {today}\n\n━━━━━━━━━━━━━━━\n\n"

        # Add links after each news block
        blocks = rewritten.strip().split("\n\n")
        block_idx = 0
        article_idx = 0

        for block in blocks:
            if block.strip():
                msg += escape_html(block) + "\n"
                block_idx += 1
                # Every 3 blocks (emoji+title, summary, opinion) = 1 news item
                if block_idx % 3 == 0 and article_idx < len(articles):
                    msg += f'🔗 <a href="{articles[article_idx]["url"]}">Подробнее здесь</a>\n\n'
                    article_idx += 1
                else:
                    msg += "\n"

        # If we haven't added all links, add remaining
        while article_idx < len(articles):
            msg += f'🔗 <a href="{articles[article_idx]["url"]}">Подробнее здесь</a>\n'
            article_idx += 1
    else:
        # Fallback without Claude
        msg = f"🗞 <b>AI & Tech — Дайджест дня</b>\n📅 {today}\n\n━━━━━━━━━━━━━━━\n\n"
        msg += build_fallback_digest(articles)

    msg += "\n━━━━━━━━━━━━━━━\n🤖 <i>AI News Bot | Ежедневно в 08:00</i>"

    if len(msg) > 4096:
        msg = msg[:4090] + "..."

    send_telegram_message(msg)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        send_telegram_message("✅ <b>AI News Bot подключён!</b>\nClaude API: " + ("✅" if ANTHROPIC_API_KEY else "❌"))
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
