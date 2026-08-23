"""Shared handler helpers."""
import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.format import strip_share_links

logger = logging.getLogger(__name__)

PARSE_MARKDOWN = "Markdown"
PARSE_HTML = "HTML"


def is_admin(user, admin_ids: list[int]) -> bool:
    return getattr(user, "is_admin", False) or (
        user is not None and user.telegram_id in admin_ids
    )


async def reply_markdown(message: Message, text: str, reply_markup=None) -> Message:
    """Send text preferring legacy Markdown, falling back to HTML."""
    text = strip_share_links(text)
    try:
        return await message.answer(
            text, parse_mode=PARSE_MARKDOWN, reply_markup=reply_markup
        )
    except TelegramBadRequest:
        from app.utils.format import esc

        return await message.answer(
            esc(text), parse_mode=PARSE_HTML, reply_markup=reply_markup
        )


async def edit_markdown(query: CallbackQuery, text: str, keyboard=None):
    text = strip_share_links(text)
    try:
        await query.message.edit_text(text, parse_mode=PARSE_MARKDOWN, reply_markup=keyboard)
    except TelegramBadRequest:
        from app.utils.format import esc

        await query.message.edit_text(
            esc(text), parse_mode=PARSE_HTML, reply_markup=keyboard
        )


async def edit_html(query: CallbackQuery, text: str, keyboard=None):
    await query.message.edit_text(text, parse_mode=PARSE_HTML, reply_markup=keyboard)


def cancel_row() -> "InlineKeyboardMarkup":
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="cmd:cancel")]]
    )
