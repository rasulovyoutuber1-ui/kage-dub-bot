"""
Admin Boshqaruv Paneli Routeri
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import config
from database import db
from filters.admin_filter import IsAdminFilter
from states.fsm import AnimeAddFSM, EpisodeAddFSM, AnimePostFSM, AnimeDeleteFSM
from keyboards.reply import (
    get_admin_reply_keyboard,
    get_cancel_reply_keyboard,
    get_main_reply_keyboard
)
from keyboards.inline import get_channel_post_keyboard

admin_router = Router(name="admin_router")
admin_router.message.filter(IsAdminFilter())
admin_router.callback_query.filter(IsAdminFilter())


@admin_router.message(F.text == "⚙️ Admin Panel")
async def admin_panel_home(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "⚙️ <b>Admin Boshqaruv Paneliga xush kelibsiz!</b>\n\n"
        "Quyidagi buyruqlardan birini tanlang:",
        reply_markup=get_admin_reply_keyboard()
    )


@admin_router.message(F.text == "◀️ Asosiy menyu")
async def back_to_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    is_owner = (message.from_user.id == config.OWNER_ID)
    await message.answer(
        "Asosiy menyuga qaytdingiz.",
        reply_markup=get_main_reply_keyboard(is_admin=True, is_owner=is_owner)
    )


@admin_router.message(F.text == "➕ Anime qo'shish")
async def start_add_anime(message: Message, state: FSMContext) -> None:
    await state.set_state(AnimeAddFSM.waiting_code)
    await message.answer(
        "➕ <b>Yangi anime qo'shish:</b>\n\n"
        "1-qadam: Anime uchun unikal <b>KOD</b> kiriting (masalan: <code>101</code>):",
        reply_markup=get_cancel_reply_keyboard()
    )


@admin_router.message(AnimeAddFSM.waiting_code)
async def process_anime_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip()
    exists = await db.get_anime_by_code(code)
    if exists:
        await message.answer(f"❌ <code>{code}</code> kodli anime allaqachon mavjud! Boshqa kod kiriting:")
        return
    await state.update_data(code=code)
    await state.set_state(AnimeAddFSM.waiting_title)
    await message.answer("2-qadam: Anime <b>NOMI</b>ni kiriting (masalan: <i>Naruto Shippuden</i>):")


@admin_router.message(AnimeAddFSM.waiting_title)
async def process_anime_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(AnimeAddFSM.waiting_description)
    await message.answer("3-qadam: Anime <b>TAVSIFI</b>ni kiriting:")


@admin_router.message(AnimeAddFSM.waiting_description)
async def process_anime_desc(message: Message, state: FSMContext) -> None:
    desc = message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(AnimeAddFSM.waiting_genres)
    await message.answer("4-qadam: Anime <b>JANRLARI</b>ni kiriting (vergul bilan):")


@admin_router.message(AnimeAddFSM.waiting_genres)
async def process_anime_genres(message: Message, state: FSMContext) -> None:
    genres = message.text.strip()
    await state.update_data(genres=genres)
    await state.set_state(AnimeAddFSM.waiting_year)
    await message.answer("5-qadam: Chiqarilgan <b>YILI</b>ni kiriting (masalan: <code>2024</code>):")


@admin_router.message(AnimeAddFSM.waiting_year)
async def process_anime_year(message: Message, state: FSMContext) -> None:
    year_text = message.text.strip()
    if not year_text.isdigit():
        await message.answer("Iltimos, yilni faqat raqamda kiriting:")
        return
    await state.update_data(year=int(year_text))
    await state.set_state(AnimeAddFSM.waiting_status)
    await message.answer("6-qadam: Anime <b>HOLATI</b> (Davom etmoqda / Tugallangan):")


@admin_router.message(AnimeAddFSM.waiting_status)
async def process_anime_status(message: Message, state: FSMContext) -> None:
    status = message.text.strip()
    await state.update_data(status=status)
    await state.set_state(AnimeAddFSM.waiting_vip)
    await message.answer("7-qadam: Ushbu anime faqat <b>VIP a'zolar</b> uchunmi? (Ha / Yo'q):")


@admin_router.message(AnimeAddFSM.waiting_vip)
async def process_anime_vip(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    is_vip_only = 1 if text in ["ha", "yes", "vip", "1"] else 0
    await state.update_data(is_vip_only=is_vip_only)
    await state.set_state(AnimeAddFSM.waiting_poster)
    await message.answer("8-qadam: Anime <b>POSTERINI (rasmini)</b> yuboring:")


@admin_router.message(AnimeAddFSM.waiting_poster, F.photo)
async def process_anime_poster_photo(message: Message, state: FSMContext) -> None:
    poster_id = message.photo[-1].file_id
    await complete_add_anime(message, state, poster_id)


@admin_router.message(AnimeAddFSM.waiting_poster, F.text)
async def process_anime_poster_text(message: Message, state: FSMContext) -> None:
    poster_id = message.text.strip()
    await complete_add_anime(message, state, poster_id)


async def complete_add_anime(message: Message, state: FSMContext, poster_id: str) -> None:
    data = await state.get_data()
    anime_id = await db.add_anime(
        code=data["code"],
        title=data["title"],
        description=data["description"],
        poster_id=poster_id,
        genres=data["genres"],
        year=data["year"],
        status=data["status"],
        is_vip_only=data["is_vip_only"]
    )
    await state.clear()
    await message.answer(
        f"✅ <b>Anime muvaffaqiyatli saqlandi!</b>\n\n"
        f"🆔 ID: {anime_id}\n"
        f"🎬 Nomi: <b>{data['title']}</b>\n"
        f"🔢 Kodi: <code>{data['code']}</code>\n"
        f"👑 VIP: {'Ha' if data['is_vip_only'] else 'Yo\\'q'}\n\n"
        f"Endi ushbu animega qismlar qo'shishingiz yoki kanalga post qilishingiz mumkin.",
        reply_markup=get_admin_reply_keyboard()
    )


@admin_router.message(F.text == "➕ Qism (Seriya) qo'shish")
async def start_add_episode(message: Message, state: FSMContext) -> None:
    await state.set_state(EpisodeAddFSM.waiting_anime_code)
    await message.answer(
        "➕ <b>Qism qo'shish</b>\n\n"
        "Qaysi animega seriya qo'shmoqchisiz? Anime <b>KODI</b>ni kiriting:",
        reply_markup=get_cancel_reply_keyboard()
    )


@admin_router.message(EpisodeAddFSM.waiting_anime_code)
async def episode_step_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip()
    anime = await db.get_anime_by_code(code)
    if not anime:
        await message.answer(f"❌ <code>{code}</code> kodli anime topilmadi! Qaytadan tekshiring:")
        return
    await state.update_data(anime_id=anime["id"], anime_title=anime["title"], anime_code=code)
    await state.set_state(EpisodeAddFSM.waiting_episode_num)
    await message.answer(
        f"Tanlangan anime: <b>{anime['title']}</b>\n\n"
        f"Nechanchi <b>QISM (seriya raqami)</b>ni yuklamoqchisiz? (Masalan: <code>1</code>):"
    )


@admin_router.message(EpisodeAddFSM.waiting_episode_num)
async def episode_step_number(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting:")
        return
    ep_num = int(text)
    await state.update_data(episode_number=ep_num)
    await state.set_state(EpisodeAddFSM.waiting_video)
    await message.answer(
        f"🎬 <b>{ep_num}-qism</b> uchun <b>VIDEO faylini</b> yuboring (yoki video file_id sini yozing):"
    )


@admin_router.message(EpisodeAddFSM.waiting_video, F.video)
async def episode_step_video(message: Message, state: FSMContext) -> None:
    file_id = message.video.file_id
    await state.update_data(video_file_id=file_id)
    await state.set_state(EpisodeAddFSM.waiting_quality)
    await message.answer("Videoning <b>SIFATI</b> qanday? Yozing: <code>480</code>, <code>720</code> yoki <code>1080</code>:")


@admin_router.message(EpisodeAddFSM.waiting_video, F.text)
async def episode_step_video_text(message: Message, state: FSMContext) -> None:
    file_id = message.text.strip()
    await state.update_data(video_file_id=file_id)
    await state.set_state(EpisodeAddFSM.waiting_quality)
    await message.answer("Videoning <b>SIFATI</b> qanday? Yozing: <code>480</code>, <code>720</code> yoki <code>1080</code>:")


@admin_router.message(EpisodeAddFSM.waiting_quality)
async def episode_step_quality(message: Message, state: FSMContext) -> None:
    quality = message.text.strip()
    data = await state.get_data()

    file_480 = data["video_file_id"] if quality == "480" else None
    file_720 = data["video_file_id"] if quality in ["720", "HD", "hd"] else None
    file_1080 = data["video_file_id"] if quality in ["1080", "full", "FHD"] else None

    if not (file_480 or file_720 or file_1080):
        file_720 = data["video_file_id"]

    await db.add_episode(
        anime_id=data["anime_id"],
        episode_number=data["episode_number"],
        file_id_480=file_480,
        file_id_720=file_720,
        file_id_1080=file_1080,
        title=f"{data['anime_title']} - {data['episode_number']}-qism"
    )
    await state.clear()
    await message.answer(
        f"✅ <b>{data['anime_title']}</b> animesiga <b>{data['episode_number']}-qism</b> muvaffaqiyatli saqlandi!",
        reply_markup=get_admin_reply_keyboard()
    )


@admin_router.message(F.text == "📢 Kanalga post qilish")
async def ask_post_anime_code(message: Message, state: FSMContext) -> None:
    await state.set_state(AnimePostFSM.waiting_code)
    await message.answer(
        "📢 <b>Kanalga avtomatik post chiqarish</b>\n\n"
        "Qaysi animeni kanalga chiqarmoqchisiz? Anime <b>KODI</b>ni yuboring:",
        reply_markup=get_cancel_reply_keyboard()
    )


@admin_router.message(AnimePostFSM.waiting_code)
async def process_channel_post(message: Message, state: FSMContext, bot: Bot) -> None:
    code = message.text.strip()
    anime = await db.get_anime_by_code(code)
    await state.clear()

    if not anime:
        await message.answer(f"❌ <code>{code}</code> kodli anime topilmadi.", reply_markup=get_admin_reply_keyboard())
        return

    bot_info = await bot.get_me()
    episodes = await db.get_episodes(anime["id"])
    kb = get_channel_post_keyboard(anime["code"], bot_info.username)

    post_caption = (
        f"🎬 <b>{anime['title']}</b>\n\n"
        f"🔢 <b>Kodi:</b> <code>{anime['code']}</code>\n"
        f"🏷 <b>Janrlar:</b> {anime['genres']}\n"
        f"📅 <b>Yili:</b> {anime['year']}-yil\n"
        f"📌 <b>Holati:</b> {anime['status']}\n"
        f"🎞 <b>Qismlar soni:</b> {len(episodes)} ta\n\n"
        f"📖 <b>Qisqacha mazmuni:</b>\n<i>{anime['description'][:400]}...</i>\n\n"
        f"👇 <b>Bot orqali tomosha qilish uchun quyidagi tugmani bosing:</b>"
    )

    try:
        if anime.get("poster_id"):
            await bot.send_photo(
                chat_id=config.CHANNEL_POST_ID,
                photo=anime["poster_id"],
                caption=post_caption,
                reply_markup=kb
            )
        else:
            await bot.send_message(
                chat_id=config.CHANNEL_POST_ID,
                text=post_caption,
                reply_markup=kb
            )
        await message.answer(
            f"✅ Post muvaffaqiyatli <b>{config.CHANNEL_POST_ID}</b> kanaliga yuborildi!",
            reply_markup=get_admin_reply_keyboard()
        )
    except Exception as e:
        await message.answer(
            f"❌ Kanalga post yuborishda xatolik yuz berdi: {e}",
            reply_markup=get_admin_reply_keyboard()
        )


@admin_router.message(F.text == "🗑 Anime o'chirish")
async def ask_delete_anime(message: Message, state: FSMContext) -> None:
    await state.set_state(AnimeDeleteFSM.waiting_code)
    await message.answer(
        "🗑 <b>Anime o'chirish</b>\n\n"
        "O'chirmoqchi bo'lgan anime <b>KODI</b>ni kiriting:",
        reply_markup=get_cancel_reply_keyboard()
    )


@admin_router.message(AnimeDeleteFSM.waiting_code)
async def process_delete_anime(message: Message, state: FSMContext) -> None:
    code = message.text.strip()
    anime = await db.get_anime_by_code(code)
    await state.clear()

    if not anime:
        await message.answer(f"❌ <code>{code}</code> kodli anime topilmadi.", reply_markup=get_admin_reply_keyboard())
        return

    success = await db.delete_anime(anime["id"])
    if success:
        await message.answer(
            f"✅ <b>{anime['title']}</b> (Kodi: <code>{code}</code>) va uning barcha seriyalari o'chirildi.",
            reply_markup=get_admin_reply_keyboard()
        )
    else:
        await message.answer("❌ O'chirishda xatolik yuz berdi.", reply_markup=get_admin_reply_keyboard())


@admin_router.message(F.text == "📋 Zayavkalarni ko'rish")
async def view_requests(message: Message) -> None:
    requests = await db.get_requests(limit=10)
    if not requests:
        await message.answer("Hozircha yangi taklif / zayavkalar yo'q.")
        return

    text = "📋 <b>So'nggi foydalanuvchi takliflari:</b>\n\n"
    for r in requests:
        user_mention = f"@{r['username']}" if r.get("username") else f"ID: {r['user_id']}"
        text += (
            f"▫️ <b>#{r['id']}</b> | 👤 {user_mention}\n"
            f"🎬 Anime: <b>{r['anime_name']}</b>\n"
            f"💬 Izoh: {r['comment'] if r['comment'] else '—'}\n"
            f"📅 Vaqt: {r['created_at'][:16]}\n"
            f"─────────────\n"
        )
    await message.answer(text)
