"""Small formatting helpers shared by handlers."""
import html
import re


def esc(text: str) -> str:
    """Escape HTML special characters for Telegram parse_mode=HTML."""
    return html.escape(str(text), quote=False)


def truncate(text: str, limit: int = 3800) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def clean_markdown_v1(text: str) -> str:
    """The legacy Markdown parser chokes on unbalanced chars; strip them."""
    text = re.sub(r"[_*`~>]", "", text)
    return text


# Telegram rejects messages whose text/markdown carries a tg://share (or any
# tg://) deep link with "BOT_SHARE_TEXT_INVALID". Strip these before sending,
# especially for untrusted AI-generated content.
_MD_SHARE_LINK_RE = re.compile(r"\[[^\]]*\]\(\s*tg://[^\)]*\)", re.IGNORECASE)
_SHARE_SCHEME_RE = re.compile(r"tg://[^\s\)\]]*", re.IGNORECASE)


def strip_share_links(text: str) -> str:
    """Remove tg:// deep links so Telegram won't reject the message."""
    if not text:
        return text
    text = _MD_SHARE_LINK_RE.sub("[link]", text)
    text = _SHARE_SCHEME_RE.sub("", text)
    return text


def safe_markdown(text: str) -> str:
    """Return text safe for MarkdownV2 parsing by escaping special chars.

    We build our own emphasis with asterisks, so escape everything else.
    """
    special = r"_*[]()~`>#+-=|{}.!"
    return re.sub(r"([%s])" % re.escape(special), r"\\\1", str(text))


def humanize_seconds(seconds: int) -> str:
    minutes, sec = divmod(int(seconds), 60)
    if minutes >= 60:
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h {minutes}m"
    return f"{minutes}m {sec}s" if minutes else f"{sec}s"
