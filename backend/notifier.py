import os
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram(message: str) -> bool:
    """Send a message to your Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[notifier] Telegram not configured — skipping")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[notifier] Telegram send failed: {e}")
        return False


def format_signal_alert(symbol, timeframe, signal) -> str:
    """Build a nice alert message from an SMC signal."""
    bias = signal.get("bias", "neutral").upper()
    conf = signal.get("confidence", 0)
    entry = signal.get("entry")
    sl = signal.get("stop_loss")
    tp1 = signal.get("take_profit_1")
    tp2 = signal.get("take_profit_2")
    reasons = signal.get("reasons", [])

    emoji = "🟢" if bias == "BULLISH" else "🔴" if bias == "BEARISH" else "⚪"

    def fmt(v):
        if v is None:
            return "—"
        n = float(v)
        if n < 10:
            return f"{n:.5f}"
        if n < 1000:
            return f"{n:.2f}"
        return f"{n:,.2f}"

    lines = [
        f"{emoji} <b>{bias} SIGNAL</b>",
        f"<b>{symbol}</b> · {timeframe}",
        f"Confidence: <b>{conf}%</b>",
        "",
        f"Entry: <b>{fmt(entry)}</b>",
        f"Stop Loss: {fmt(sl)}",
        f"TP1: {fmt(tp1)}",
        f"TP2: {fmt(tp2)}",
    ]

    if reasons:
        lines.append("")
        lines.append("<b>Why:</b>")
        for r in reasons[:4]:
            lines.append(f"• {r}")

    return "\n".join(lines)
