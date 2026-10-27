"""
Reply klaviaturalar to'plami
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_reply_keyboard(is_admin: bool = False, is_owner: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [
            KeyboardButton(text="🔍 Anime qidirish"),
            KeyboardButton(text="📂 Janrlar")
        ],
        [
            KeyboardButton(text="🎲 Tasodifiy anime"),
            KeyboardButton(text="⭐ Sevimlilar")
        ],
        [
            KeyboardButton(text="👑 VIP a'zolik"),
            KeyboardButton(text="✍️ Taklif / Zayavka")
        ]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    if is_owner:
        buttons.append([KeyboardButton(text="👑 Owner (Egasi) Paneli")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Quyidagi menyudan tanlang..."
    )


def get_cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )


def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Anime qo'shish"), KeyboardButton(text="➕ Qism (Seriya) qo'shish")],
            [KeyboardButton(text="📢 Kanalga post qilish"), KeyboardButton(text="🗑 Anime o'chirish")],
            [KeyboardButton(text="📋 Zayavkalarni ko'rish"), KeyboardButton(text="◀️ Asosiy menyu")]
        ],
        resize_keyboard=True
    )


def get_owner_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Admin qo'shish / o'chirish"), KeyboardButton(text="📢 Kanallarni sozlash")],
            [KeyboardButton(text="🎁 VIP Promo yaratish"), KeyboardButton(text="📊 To'liq statistika")],
            [KeyboardButton(text="✉️ Xabar tarqatish (Broadcast)"), KeyboardButton(text="◀️ Asosiy menyu")]
        ],
        resize_keyboard=True
    )
