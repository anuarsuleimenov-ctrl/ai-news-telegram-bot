"""
AI News Daily Bot
"""
import requests, schedule, time, datetime, json, sys, os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SEND_HOUR = os.environ.get("SEND_HOUR", "03:00")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True}
    try:
        r = requests.post(url, json=payload, timeout=30)
        print(f"[{datetime.datetime.now()}] {'Sent!' if r.status_code == 200 else r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def fetch_news():
    import xml.etree.ElementTree as ET
    queries = ["artificial+intelligence+news", "AI+technology+2026", "machine+learning+breakthrough"]
    articles = []
    for q in queries:
        try:
            r = requests.get(f"https://news.google.com/rss/search?q={q}&hl=en&gl=US&ceid=US:en", timeout=15)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    link = item.find("link")
                    source = item.find("source")
                    if title is not None and link is not None:
                        articles.append({"title": title.text or "", "url": link.text or "", "source": source.text if source is not None else ""})
        except Exception as e:
            print(f"RSS error: {e}")
    seen = set()
    unique = []
    for a in articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)
    return unique[:10]

def send_daily_digest():
    print(f"\n[{datetime.datetime.now()}] Fetching news...")
    articles = fetch_news()
    if not articles:
        send_telegram_message("No news found today.")
        return
    today = datetime.date.today().strftime("%d.%m.%Y")
    lines = [f"AI & Tech Daily Digest\n{today}\n" + "=" * 30 + "\n"]
    for i, a in enumerate(articles, 1):
        source = f" ({a['source']})" if a.get("source") else ""
        lines.append(f"{i}. {a['title']}{source}\n   {a['url']}")
    lines.append("\nAI News Bot")
    msg = "\n".join(lines)
    if len(msg) > 4096:
        msg = msg[:4090] + "..."
    send_telegram_message(msg)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        send_telegram_message("AI News Bot connected! Bot is ready.")
    elif len(sys.argv) > 1 and sys.argv[1] == "once":
        send_daily_digest()
    else:
        print(f"Bot started! Daily at {SEND_HOUR}")
        send_daily_digest()
        schedule.every().day.at(SEND_HOUR).do(send_daily_digest)
        while True:
            schedule.run_pending()
            time.sleep(60)
"""
AI News Daily Bot
"""
import requests, schedule, time, datetime, json, sys, os, html

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SEND_HOUR = os.environ.get("SEND_HOUR", "03:00")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        r = requests.post(url, json=payload, timeout=30)
        print(f"[{datetime.datetime.now()}] {'Sent!' if r.status_code == 200 else r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def escape_html(text):
    return html.escape(str(text)) if text else ""

def fetch_news():
    import xml.etree.ElementTree as ET
    queries = ["artificial+intelligence+news", "AI+technology+2026", "machine+learning+breakthrough"]
    articles = []
    for q in queries:
        try:
            r = requests.get(f"https://news.google.com/rss/search?q={q}&hl=en&gl=US&ceid=US:en", timeout=15)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    link = item.find("link")
                    source = item.find("source")
                    if title is not None and link is not None:
                        articles.append({"title": title.text or "", "url": link.text or "", "source": source.text if source is not None else ""})
        except Exception as e:
            print(f"RSS error: {e}")
    seen = set()
    unique = []
    for a in articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)
    return unique[:10]

def send_daily_digest():
    print(f"\n[{datetime.datetime.now()}] Fetching news...")
    articles = fetch_news()
    if not articles:
        send_telegram_message("No news found today.")
        return
    today = datetime.date.today().strftime("%d.%m.%Y")
    msg = f"<b>AI & Tech Daily Digest</b>\n<i>{today}</i>\n{'=' * 30}\n\n"
    for i, a in enumerate(articles, 1):
        safe_title = escape_html(a["title"])
        source = f" ({escape_html(a['source'])})" if a.get("source") else ""
        msg += f'{i}. <a href=\"{a["url"]}\">{safe_title}</a>{source}\n\n'
    msg += "\n<i>AI News Bot</i>"
    if len(msg) > 4096:
        msg = msg[:4090] + "..."
    send_telegram_message(msg)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        send_telegram_message("<b>AI News Bot connected!</b>\nBot is ready.")
    elif len(sys.argv) > 1 and sys.argv[1] == "once":
        send_daily_digest()
    else:
        print(f"Bot started! Daily at {SEND_HOUR}")
        send_daily_digest()
        schedule.every().day.at(SEND_HOUR).do(send_daily_digest)
        while True:
            schedule.run_pending()
            time.sleep(60)
