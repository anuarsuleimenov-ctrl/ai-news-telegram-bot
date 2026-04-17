"""
AI News Daily Bot â ÐÐ¶ÐµÐ´Ð½ÐµÐ²Ð½ÑÐ¹ Ð´Ð°Ð¹Ð´Ð¶ÐµÑÑ AI Ð½Ð¾Ð²Ð¾ÑÑÐµÐ¹
ÐÑÐ¿Ð¾Ð»ÑÐ·ÑÐµÑ Claude API + Ð°Ð½Ð°Ð»Ð¸ÑÐ¸ÑÐµÑÐºÐ¸Ð¹ ÑÑÐ¸Ð»Ñ Ð´Ð»Ñ Ð¿ÐµÑÐµÐ¿Ð¸ÑÑÐ²Ð°Ð½Ð¸Ñ Ð½Ð¾Ð²Ð¾ÑÑÐµÐ¹
08:00 Ð¸ 16:00 Ð¿Ð¾ ÐÑÑÐ°Ð½Ðµ (03:00 Ð¸ 11:00 UTC)
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

SYSTEM_PROMPT = """Ð¢Ñ â AI-Ð°Ð½Ð°Ð»Ð¸ÑÐ¸Ðº Ð¸ ÑÐµÐ´Ð°ÐºÑÐ¾Ñ Telegram-ÐºÐ°Ð½Ð°Ð»Ð° Ð¿ÑÐ¾ AI Ð¸ ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸.
ÐÐ¸ÑÐµÑÑ Ð² ÑÑÐ¸Ð»Ðµ ÐÐ¸ÐºÐ¾Ð»Ð°Ñ Ð¥Ð»ÐµÐ±Ð¸Ð½ÑÐºÐ¾Ð³Ð¾: ÑÐºÑÐ¿ÐµÑÑÐ½Ð¾, Ñ Ð»Ð¸ÑÐ½ÑÐ¼ Ð¼Ð½ÐµÐ½Ð¸ÐµÐ¼, Ð±ÐµÐ· Ð²Ð¾Ð´Ñ.

Ð¡Ð¢ÐÐÐ¬ Ð Ð¢ÐÐ:
- ÐÐ¸ÑÐµÑÑ ÐºÐ°Ðº ÑÐºÑÐ¿ÐµÑÑ, ÐºÐ¾ÑÐ¾ÑÑÐ¹ ÑÐ°Ð·Ð±Ð¸ÑÐ°ÐµÑÑÑ Ð² ÑÐµÐ¼Ðµ. Ð£Ð²ÐµÑÐµÐ½Ð½Ð¾, Ð¾Ñ Ð¿ÐµÑÐ²Ð¾Ð³Ð¾ Ð»Ð¸ÑÐ°.
- Ð¢Ð¾Ð½: Ð°Ð½Ð°Ð»Ð¸ÑÐ¸ÑÐµÑÐºÐ¸Ð¹, Ð¿ÑÑÐ¼Ð¾Ð¹, Ñ ÑÐ°ÑÐ°ÐºÑÐµÑÐ¾Ð¼. ÐÐµ Ð±Ð¾Ð¸ÑÑÑÑ Ð²ÑÑÐºÐ°Ð·Ð°ÑÑ Ð¼Ð½ÐµÐ½Ð¸Ðµ.
- ÐÐµÐ· ÑÐ¼Ð¾Ð´Ð·Ð¸ Ð² ÑÐµÐºÑÑÐµ. Ð¢Ð¾Ð»ÑÐºÐ¾ Ð¶Ð¸ÑÐ½ÑÐ¹ Ð·Ð°Ð³Ð¾Ð»Ð¾Ð²Ð¾Ðº Ð¸ ÑÐ¸ÑÑÑÐ¹ ÑÐµÐºÑÑ.
- ÐÐ¾Ð½ÐºÑÐµÑÐ¸ÐºÐ°: ÑÐ¸ÑÑÑ, Ð¸Ð¼ÐµÐ½Ð°, ÑÑÐ¼Ð¼Ñ, Ð¿ÑÐ¾ÑÐµÐ½ÑÑ. ÐÐ±ÑÑÑÐ°ÐºÑÐ¸Ð¸ = Ð¼ÑÑÐ¾Ñ.
- ÐÐ¾ÑÐ¾ÑÐºÐ¸Ðµ Ð°Ð±Ð·Ð°ÑÑ. ÐÐ´Ð½Ð° Ð¼ÑÑÐ»Ñ = Ð¾Ð´Ð¸Ð½ Ð°Ð±Ð·Ð°Ñ.
- ÐÐ¾Ð¶ÐµÑÑ Ð·Ð°Ð´Ð°ÑÑ ÑÐ¸ÑÐ¾ÑÐ¸ÑÐµÑÐºÐ¸Ð¹ Ð²Ð¾Ð¿ÑÐ¾Ñ, Ð±ÑÐ¾ÑÐ¸ÑÑ Ð¿ÑÐ¾Ð²Ð¾ÐºÐ°ÑÐ¸Ñ.
- ÐÐ¸Ð·Ð½ÐµÑ-ÑÐ³Ð¾Ð»: ÐºÐ°Ðº ÑÑÐ¾ Ð²Ð»Ð¸ÑÐµÑ Ð½Ð° ÑÑÐ½Ð¾Ðº, Ð´ÐµÐ½ÑÐ³Ð¸, ÑÑÑÐ°ÑÐµÐ³Ð¸Ñ.
- ÐÑÐ»Ð¸ ÑÐ¼ÐµÑÑÐ½Ð¾ â ÑÐ¿Ð¾Ð¼ÑÐ½Ð¸ ÐºÐ¾Ð½ÑÐµÐºÑÑ Ð´Ð»Ñ ÐÐ°Ð·Ð°ÑÑÑÐ°Ð½Ð°/Ð¡ÐÐ (Kaspi, Astana Hub, Ð¼ÐµÑÑÐ½ÑÐµ ÑÐµÐ°Ð»Ð¸Ð¸).

ÐÐÐÐ ÐÐ©ÐÐÐ:
- ÐÐ°ÑÐ¾Ñ ("Ð² ÑÐ¿Ð¾ÑÑ Ð¿ÐµÑÐµÐ¼ÐµÐ½", "ÑÐµÐ²Ð¾Ð»ÑÑÐ¸Ð¾Ð½Ð½ÑÐ¹ Ð¿ÑÐ¾ÑÑÐ²", "ÑÐ½Ð¸ÐºÐ°Ð»ÑÐ½Ð°Ñ Ð²Ð¾Ð·Ð¼Ð¾Ð¶Ð½Ð¾ÑÑÑ")
- ÐÐ¾Ð´Ð° Ð¸ ÐºÐ°Ð½ÑÐµÐ»ÑÑÐ¸Ñ ("Ð² ÑÐ°Ð¼ÐºÐ°Ñ ÑÐµÐ°Ð»Ð¸Ð·Ð°ÑÐ¸Ð¸", "Ð´Ð°Ð½Ð½ÑÐ¹ Ð¿ÑÐ¾Ð´ÑÐºÑ")
- Ð­Ð¼Ð¾Ð´Ð·Ð¸ (ÑÐ¾Ð²ÑÐµÐ¼ â Ð½Ð¸ Ð² Ð·Ð°Ð³Ð¾Ð»Ð¾Ð²ÐºÐ°Ñ, Ð½Ð¸ Ð² ÑÐµÐºÑÑÐµ)
- ÐÐ¾ÑÑÐ¾ÑÐ¶ÐµÐ½Ð½Ð¾ÑÑÑ ("Ð­ÑÐ¾ Ð½ÐµÐ²ÐµÑÐ¾ÑÑÐ½Ð¾!", "ÐÐ°Ñ!")
- HTML ÑÐµÐ³Ð¸. Ð¢Ð¾Ð»ÑÐºÐ¾ ÑÐ¸ÑÑÑÐ¹ ÑÐµÐºÑÑ.
- ÐÑÐ´ÑÐ¼ÑÐ²Ð°ÑÑ ÑÐ°ÐºÑÑ Ð¸Ð»Ð¸ Ð´Ð¾Ð´ÑÐ¼ÑÐ²Ð°ÑÑ ÑÐ¾, ÑÐµÐ³Ð¾ Ð½ÐµÑ Ð² Ð½Ð¾Ð²Ð¾ÑÑÐ¸.

Ð¤ÐÐ ÐÐÐ¢ Ð´Ð»Ñ ÐÐÐÐÐÐ Ð½Ð¾Ð²Ð¾ÑÑÐ¸:

{ÐÐ¸ÑÐ½ÑÐ¹ Ð·Ð°Ð³Ð¾Ð»Ð¾Ð²Ð¾Ðº â Ð¿ÐµÑÐµÐ¾ÑÐ¼ÑÑÐ»ÐµÐ½Ð½ÑÐ¹, ÑÐµÐ¿Ð»ÑÑÑÐ¸Ð¹, Ð±ÐµÐ· ÑÐ¼Ð¾Ð´Ð·Ð¸}

{ÐÐ¾Ð½ÑÐµÐºÑÑ Ð¸ ÑÑÑÑ: 2-4 Ð¿ÑÐµÐ´Ð»Ð¾Ð¶ÐµÐ½Ð¸Ñ. Ð§ÑÐ¾ ÑÐ»ÑÑÐ¸Ð»Ð¾ÑÑ, Ð¿Ð¾ÑÐµÐ¼Ñ ÑÑÐ¾ Ð²Ð°Ð¶Ð½Ð¾, ÑÐ¸ÑÑÑ.}

{ÐÐ½ÐµÐ½Ð¸Ðµ/Ð²ÑÐ²Ð¾Ð´: 1-2 Ð¿ÑÐµÐ´Ð»Ð¾Ð¶ÐµÐ½Ð¸Ñ â Ð¾ÑÑÑÐ¾Ðµ, ÑÐµÑÑÐ½Ð¾Ðµ, Ñ Ð¿Ð¾Ð·Ð¸ÑÐ¸ÐµÐ¹. Ð§ÑÐ¾ ÑÑÐ¾ Ð·Ð½Ð°ÑÐ¸Ñ Ð´Ð»Ñ ÑÑÐ½ÐºÐ°/Ð±Ð¸Ð·Ð½ÐµÑÐ°/Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÐµÐ¹.}

[LINK]

---

ÐÑÐ°Ð²Ð¸Ð»Ð°:
- ÐÐ°Ð³Ð¾Ð»Ð¾Ð²Ð¾Ðº â ÐÐ Ð¿ÐµÑÐµÐ²Ð¾Ð´ Ð¾ÑÐ¸Ð³Ð¸Ð½Ð°Ð»Ð°. ÐÐµÑÐµÐ¾ÑÐ¼ÑÑÐ»Ð¸, ÑÑÐ¾ÑÐ¼ÑÐ»Ð¸ÑÑÐ¹ Ð¾ÑÑÑÐ¾.
- ÐÐ¸ÑÐ¸ Ð¿Ð¾-ÑÑÑÑÐºÐ¸, Ð½Ð¾ Ð°Ð½Ð³Ð»Ð¸Ð¹ÑÐºÐ¸Ðµ ÑÐµÑÐ¼Ð¸Ð½Ñ Ð¾ÑÑÐ°Ð²Ð»ÑÐ¹ ÐºÐ°Ðº ÐµÑÑÑ (API, open source, SaaS).
- ÐÐ Ð½ÑÐ¼ÐµÑÑÐ¹ Ð½Ð¾Ð²Ð¾ÑÑÐ¸.
- Ð Ð°Ð·Ð´ÐµÐ»ÑÐ¹ Ð½Ð¾Ð²Ð¾ÑÑÐ¸ ÑÑÑÐ¾ÐºÐ¾Ð¹ --- Ð¼ÐµÐ¶Ð´Ñ Ð½Ð¸Ð¼Ð¸.
- ÐÐ¸ÑÐ¸ [LINK] Ð¾ÑÐ´ÐµÐ»ÑÐ½Ð¾Ð¹ ÑÑÑÐ¾ÐºÐ¾Ð¹ Ð¿Ð¾ÑÐ»Ðµ ÐºÐ°Ð¶Ð´Ð¾Ð¹ Ð½Ð¾Ð²Ð¾ÑÑÐ¸ â Ñ Ð·Ð°Ð¼ÐµÐ½Ñ Ð½Ð° ÑÑÑÐ»ÐºÑ.
- Ð Ð°Ð·Ð½Ð°Ñ Ð³Ð»ÑÐ±Ð¸Ð½Ð°: Ð³Ð´Ðµ-ÑÐ¾ ÑÐ²Ð°ÑÐ¸Ñ 3 Ð¿ÑÐµÐ´Ð»Ð¾Ð¶ÐµÐ½Ð¸Ð¹, Ð³Ð´Ðµ-ÑÐ¾ Ð½Ð¾Ð²Ð¾ÑÑÑ Ð·Ð°ÑÐ»ÑÐ¶Ð¸Ð²Ð°ÐµÑ 5-6."""


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
    return re.sub(r"[^a-zA-ZÐ°-ÑÑÐ-Ð¯Ð0-9]", "", title.lower())


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
                "content": f"ÐÐ¾Ñ {len(articles)} Ð½Ð¾Ð²Ð¾ÑÑÐµÐ¹. ÐÐµÑÐµÐ¿Ð¸ÑÐ¸ ÐºÐ°Ð¶Ð´ÑÑ. ÐÐ¸ÑÐ¸ [LINK] Ð¾ÑÐ´ÐµÐ»ÑÐ½Ð¾Ð¹ ÑÑÑÐ¾ÐºÐ¾Ð¹ Ð¿Ð¾ÑÐ»Ðµ ÐºÐ°Ð¶Ð´Ð¾Ð¹ Ð½Ð¾Ð²Ð¾ÑÑÐ¸.\n\n{titles_text}"
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
            result.append(f'<a href="{url}">Ð¿Ð¾Ð´ÑÐ¾Ð±Ð½ÐµÐµ Ð·Ð´ÐµÑÑ</a>')
            article_idx += 1
        elif stripped == "---":
            result.append("")
            result.append("â" * 15)
            result.append("")
        else:
            # Escape HTML in Claude's text to prevent parse errors
            result.append(escape_html(line))

    # Add remaining links if Claude didn't add enough [LINK]
    while article_idx < len(articles):
        url = articles[article_idx]["url"]
        result.append(f'<a href="{url}">Ð¿Ð¾Ð´ÑÐ¾Ð±Ð½ÐµÐµ Ð·Ð´ÐµÑÑ</a>')
        article_idx += 1

    return "\n".join(result)


def split_message_by_separator(full_msg, separator="â" * 15, max_len=4096):
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
        if len(candidate) > max_len and cu2rent:
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
    slot: "morning" (08:00), "evening" (16:00), "night" (19:00) â Astana time
    """
    slot_labels = {"morning": "08:00", "evening": "16:00", "night": "19:00"}
    slot_label = slot_labels.get(slot, "08:00")
    count = NEWS_PER_SLOT.get(slot, 4)

    print(f"\n[{datetime.datetime.now()}] Fetching news for {slot_label} Astana digest ({count} items)...")
    articles = fetch_news()[:count]

    if not articles:
        send_telegram_message("Ð¡Ð²ÐµÐ¶Ð¸Ñ Ð½Ð¾Ð²Ð¾ÑÑÐµÐ¹ Ð¿Ð¾ÐºÐ° Ð½ÐµÑ.")
        return

    today = datetime.date.today().strftime("%d.%m.%Y")
    header = f"<b>AI &amp; Tech â {today}, {slot_label}</b>\n\n{'â' * 15}\n\n"
    footer = f"\n{'â' * 15}\n<i>AI News | 08:00, 16:00 Ð¸ 19:00 Ð¿Ð¾ ÐÑÑÐ°Ð½Ðµ</i>"

    rewritten = rewrite_with_claude(articles)
    if rewritten:
        body = inject_links_html(rewritten, articles)
        msg = header + body + footer
    else:
        # Fallback without Claude
        lines = []
        emojis = ["ð¥", "â¡", "ð", "ð¤"]
        for i, a in enumerate(articles):
            emoji = emojis[i % len(emojis)]
            safe_title = escape_html(a["title"])
            source = f" ({escape_html(a['source'])})" if a.get("source") else ""
            lines.append(f'{emoji} {safe_title}{source}\n<a href="{a["url"]}">Ð¿Ð¾Ð´ÑÐ¾Ð±Ð½ÐµÐµ Ð·Ð´ÐµÑÑ</a>')
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
        send_telegram_message("<b>AI News Bot Ð¿Ð¾Ð´ÐºÐ»ÑÑÑÐ½.</b>\nClaude API: " + ("Ð´Ð°" if ANTHROPIC_API_KEY else "Ð½ÐµÑ"))
    elif len(sys.argv) > 1 and sys.argv[1] == "once":
        send_daily_digest("morning")
    else:
        print(f"Bot started!")
        print(f"Morning digest : {SEND_HOUR_MORNING} UTC (08:00 Astana) â 4 Ð½Ð¾Ð²Ð¾ÑÑÐ¸")
        print(f"Evening digest : {SEND_HOUR_EVENING} UTC (16:00 Astana) â 4 Ð½Ð¾Ð²Ð¾ÑÑÐ¸")
        print(f"Night digest   : {SEND_HOUR_NIGHT}   UTC (19:00 Astana) â 2 Ð½Ð¾Ð²Ð¾ÑÑÐ¸")
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

