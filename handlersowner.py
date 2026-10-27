"""
Bot Egasi (Owner) Paneli Routeri
"""
import asyncio
import secrets
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import config
from database import db
from filters.admin_filter import IsOwnerFilter
from states.fsm import (
    AdminManageFSM,
    ChannelManageFSM,
    CreateVipCodeFSM,
    BroadcastFSM
)
from keyboards.reply import (
    get_owner_reply_keyboard,
    get_cancel_reply_keyboard,
    get_main_reply_keyboard
)

owner_router = Router(name="owner_router")
owner_router.message.filter(IsOwnerFilter())
owner_router.callback_query.filter(IsOwnerFilter())


@owner_router.message(F.text == "👑 Owner (Egasi) Paneli")
async def owner_panel_home(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👑 <b>Bot Egasining Boshqaruv Markazi</b>\n\n"
        "Adminlar, majburiy kanallar, promo-kodlar yaratish va butun botga xabar tarqatishni boshqaring:",
        reply_markup=get_owner_reply_keyboard()
    )


@owner_router.message(F.text == "👥 Admin qo'shish / o'chirish")
async def manage_admins_menu(message: Message) -> None:
    admins = await db.get_admins()
    text = "👥 <b>Hozirgi Bot Adminlari:</b>\n\n"
    for a in admins:
        name = a.get("full_name") or "Noma'lum"
        username = f"(@{a['username']})" if a.get("username") else ""
        text += f"• <code>{a['user_id']}</code> — <b>{name}</b> {username}\n"
    text += (
        "\n<b>Admin qo'shish uchun:</b> <code>/add_admin ID</code>\n"
        "<b>Adminni o'chirish uchun:</b> <code>/del_admin ID</code>"
    )
    await message.answer(text)


@owner_router.message(F.text.startswith("/add_admin"))
async def add_admin_command(message: Message) -> None:
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: <code>/add_admin 123456789</code>")
        return
    admin_id = int(parts[1])
    success = await db.add_admin(admin_id, added_by=config.OWNER_ID)
    if success:
        await message.answer(f"✅ <code>{admin_id}</code> ID li foydalanuvchi <b>Admin</b> qilindi.")
    else:
        await message.answer("❌ Bu foydalanuvchi allaqachon admin yoki xatolik yuz berdi.")


@owner_router.message(F.text.startswith("/del_admin"))
async def del_admin_command(message: Message) -> None:
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: <code>/del_admin 123456789</code>")
        return
    admin_id = int(parts[1])
    if admin_id == config.OWNER_ID:
        await message.answer("❌ O'zingizni adminga chiqarib tashlay olmaysiz!")
        return
    success = await db.delete_admin(admin_id)
    if success:
        await message.answer(f"✅ <code>{admin_id}</code> adminlikdan chiqarildi.")
    else:
        await message.answer("❌ Ushbu ID li admin topilmadi.")


@owner_router.message(F.text == "📢 Kanallarni sozlash")
async def manage_channels_menu(message: Message) -> None:
    channels = await db.get_channels()
    text = "📢 <b>Majburiy Obuna Kanallari Ro'yxati:</b>\n\n"
    if not channels:
        text += "<i>Hozircha majburiy kanallar belgilanmagan.</i>\n"
    else:
        for idx, ch in enumerate(channels, start=1):
            text += f"{idx}. <b>{ch['name']}</b>\nID: <code>{ch['channel_id']}</code>\nHavola: {ch['url']}\n\n"
    text += (
        "<b>Kanal qo'shish uchun:</b> <code>/add_channel KANAL_ID NOMI HAVOLA</code>\n"
        "<i>Masalan:</i> <code>/add_channel -1001234567890 AnimeRasmiy https://t.me/animerasmiy</code>\n\n"
        "<b>Kanalni o'chirish uchun:</b> <code>/del_channel KANAL_ID</code>"
    )
    await message.answer(text)


@owner_router.message(F.text.startswith("/add_channel"))
async def add_channel_command(message: Message) -> None:
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer(
            "❌ To'liq ma'lumot kiriting:\n"
            "<code>/add_channel -1001234567890 KanalNomi https://t.me/kanal</code>"
        )
        return
    ch_id = parts[1].strip()
    ch_name = parts[2].strip()
    ch_url = parts[3].strip()
    success = await db.add_channel(ch_id, ch_name, ch_url)
    if success:
        await message.answer(f"✅ <b>{ch_name}</b> kanali muvaffaqiyatli qo'shildi!")
    else:
        await message.answer("❌ Kanal qo'shishda xatolik yuz berdi.")


@owner_router.message(F.text.startswith("/del_channel"))
async def del_channel_command(message: Message) -> None:
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Foydalanish: <code>/del_channel -1001234567890</code>")
        return
    ch_id = parts[1].strip()
    success = await db.delete_channel(ch_id)
    if success:
        await message.answer(f"✅ <code>{ch_id}</code> kanali o'chirildi.")
    else:
        await message.answer("❌ Kanal topilmadi.")


@owner_router.message(F.text == "🎁 VIP Promo yaratish")
async def start_create_vip_code(message: Message, state: FSMContext) -> None:
    await state.set_state(CreateVipCodeFSM.waiting_duration_days)
    await message.answer(
        "🎁 <b>VIP Promo-kod yaratish</b>\n\n"
        "Promo-kod necha kunlik VIP berishi kerak? (Masalan: <code>30</code>):",
        reply_markup=get_cancel_reply_keyboard()
    )


@owner_router.message(CreateVipCodeFSM.waiting_duration_days)
async def process_vip_duration(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 30):")
        return
    days = int(text)
    random_str = secrets.token_hex(3).upper()
    promo_code = f"VIP-{days}D-{random_str}"
    success = await db.create_vip_code(promo_code, days)
    await state.clear()

    if success:
        await message.answer(
            f"🎉 <b>Yangi VIP Promo-kod yaratildi!</b>\n\n"
            f"🔑 Kod: <code>{promo_code}</code>\n"
            f"⏳ Muddat: <b>{days} kun</b>\n\n"
            f"<i>Buni foydalanuvchiga taqdim qilishingiz mumkin.</i>",
            reply_markup=get_owner_reply_keyboard()
        )
    else:
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.", reply_markup=get_owner_reply_keyboard())


@owner_router.message(F.text == "📊 To'liq statistika")
async def show_full_statistics(message: Message) -> None:
    total_users = await db.get_all_users_count()
    vip_users = await db.get_vip_count()
    total_anime = await db.get_total_anime_count()
    total_episodes = await db.get_total_episodes_count()
    channels = await db.get_channels()
    admins = await db.get_admins()

    stats_text = (
        "📊 <b>Botning Umumiy Statistikasi:</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {total_users:,} ta\n"
        f"👑 <b>Faol VIP a'zolar:</b> {vip_users} ta\n"
        f"🎬 <b>Jami animelar soni:</b> {total_anime} ta\n"
        f"🎞 <b>Jami epizodlar (qismlar):</b> {total_episodes} ta\n"
        f"📢 <b>Majburiy kanallar:</b> {len(channels)} ta\n"
        f"🛡 <b>Adminlar soni:</b> {len(admins)} nafar\n"
        f"⚡️ <b>Aiogram versiyasi:</b> 3.x\n"
        f"🗄 <b>Baza:</b> SQLite (aiosqlite Asinxron)"
    )
    await message.answer(stats_text)


@owner_router.message(F.text == "✉️ Xabar tarqatish (Broadcast)")
async def start_broadcast(message: Message, state: FSMContext) -> None:
    await state.set_state(BroadcastFSM.waiting_message)
    await message.answer(
        "✉️ <b>Barcha foydalanuvchilarga xabar tarqatish</b>\n\n"
        "Foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:",
        reply_markup=get_cancel_reply_keyboard()
    )


@owner_router.message(BroadcastFSM.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await message.answer("🚀 Xabar tarqatish boshlandi... Iltimos, kuting.", reply_markup=get_owner_reply_keyboard())

    user_ids = await db.get_all_users_ids()
    sent_count = 0
    blocked_count = 0

    for uid in user_ids:
        try:
            await message.copy_to(chat_id=uid)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            blocked_count += 1

    await message.answer(
        f"🏁 <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"✅ Yuborildi: <b>{sent_count}</b> ta\n"
        f"🚫 Yetib bormadi (bloklagan): <b>{blocked_count}</b> ta\n"
        f"📊 Jami qamrov: <b>{len(user_ids)}</b> ta"
    )
