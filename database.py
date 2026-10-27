"""
Asinxron ma'lumotlar bazasi moduli (aiosqlite)
"""
import aiosqlite
import datetime
from typing import Optional, Any
import config


class Database:
    def __init__(self, db_name: str = config.DB_NAME):
        self.db_name = db_name

    async def init_db(self) -> None:
        """Barcha jadvallarni yaratish"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    is_vip INTEGER DEFAULT 0,
                    vip_until TEXT,
                    joined_at TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS anime (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    poster_id TEXT,
                    genres TEXT,
                    year INTEGER,
                    status TEXT DEFAULT 'Davom etmoqda',
                    is_vip_only INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anime_id INTEGER NOT NULL,
                    episode_number INTEGER NOT NULL,
                    file_id_480 TEXT,
                    file_id_720 TEXT,
                    file_id_1080 TEXT,
                    title TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (anime_id) REFERENCES anime (id) ON DELETE CASCADE,
                    UNIQUE (anime_id, episode_number)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    anime_id INTEGER NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    UNIQUE (user_id, anime_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    added_by INTEGER,
                    added_at TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS vip_codes (
                    code TEXT PRIMARY KEY,
                    duration_days INTEGER NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    used_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now')),
                    used_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    anime_name TEXT NOT NULL,
                    comment TEXT,
                    status TEXT DEFAULT 'Kutilmoqda',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.commit()

    # ================= Foydalanuvchilar =================
    async def add_user(self, user_id: int, full_name: str, username: Optional[str] = None) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("""
                INSERT INTO users (user_id, full_name, username)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    username = excluded.username
            """, (user_id, full_name, username))
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_users_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    async def get_all_users_ids(self) -> list[int]:
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT user_id FROM users") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def is_vip(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if not user or not user.get("is_vip"):
            return False
        vip_until = user.get("vip_until")
        if not vip_until:
            return False
        try:
            until_dt = datetime.datetime.fromisoformat(vip_until)
            if datetime.datetime.now() < until_dt:
                return True
            # Muddati o'tgan
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "UPDATE users SET is_vip = 0, vip_until = NULL WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
            return False
        except Exception:
            return False

    async def set_vip(self, user_id: int, days: int) -> str:
        until = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("""
                UPDATE users SET is_vip = 1, vip_until = ? WHERE user_id = ?
            """, (until, user_id))
            await db.commit()
        return until

    # ================= VIP Promo Kodlar =================
    async def create_vip_code(self, code: str, duration_days: int) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            try:
                await db.execute("""
                    INSERT INTO vip_codes (code, duration_days) VALUES (?, ?)
                """, (code, duration_days))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def activate_vip_code(self, code: str, user_id: int) -> tuple[bool, str, int]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM vip_codes WHERE code = ?", (code,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False, "Bunday promo-kod mavjud emas!", 0
                if row["is_used"]:
                    return False, "Ushbu promo-kod allaqachon ishlatilgan!", 0

                days = row["duration_days"]
                now_str = datetime.datetime.now().isoformat()
                await db.execute("""
                    UPDATE vip_codes
                    SET is_used = 1, used_by = ?, used_at = ?
                    WHERE code = ?
                """, (user_id, now_str, code))
                await db.commit()

        until_date = await self.set_vip(user_id, days)
        return True, until_date, days

    async def get_vip_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1") as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

    # ================= Anime Boshqaruvi =================
    async def add_anime(self, code: str, title: str, description: str, poster_id: str,
                        genres: str, year: int, status: str = "Davom etmoqda", is_vip_only: int = 0) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("""
                INSERT INTO anime (code, title, description, poster_id, genres, year, status, is_vip_only)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, title, description, poster_id, genres, year, status, is_vip_only))
            await db.commit()
            return cursor.lastrowid

    async def get_anime_by_code(self, code: str) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM anime WHERE code = ?", (code.strip(),)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_anime_by_id(self, anime_id: int) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def search_anime_by_title(self, query: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            search_query = f"%{query}%"
            async with db.execute("""
                SELECT * FROM anime
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY id DESC LIMIT 15
            """, (search_query, search_query)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_anime_by_genre(self, genre: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM anime
                WHERE genres LIKE ?
                ORDER BY id DESC LIMIT 20
            """, (f"%{genre}%",)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_random_anime(self) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM anime ORDER BY RANDOM() LIMIT 1") as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def increment_views(self, anime_id: int) -> None:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("UPDATE anime SET views = views + 1 WHERE id = ?", (anime_id,))
            await db.commit()

    async def delete_anime(self, anime_id: int) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM episodes WHERE anime_id = ?", (anime_id,))
            await db.execute("DELETE FROM favorites WHERE anime_id = ?", (anime_id,))
            cursor = await db.execute("DELETE FROM anime WHERE id = ?", (anime_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_total_anime_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT COUNT(*) FROM anime") as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

    # ================= Epizodlar =================
    async def add_episode(self, anime_id: int, episode_number: int,
                          file_id_480: Optional[str] = None,
                          file_id_720: Optional[str] = None,
                          file_id_1080: Optional[str] = None,
                          title: str = "") -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("""
                INSERT INTO episodes (anime_id, episode_number, file_id_480, file_id_720, file_id_1080, title)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(anime_id, episode_number) DO UPDATE SET
                    file_id_480 = COALESCE(excluded.file_id_480, episodes.file_id_480),
                    file_id_720 = COALESCE(excluded.file_id_720, episodes.file_id_720),
                    file_id_1080 = COALESCE(excluded.file_id_1080, episodes.file_id_1080),
                    title = excluded.title
            """, (anime_id, episode_number, file_id_480, file_id_720, file_id_1080, title))
            await db.commit()
            return cursor.lastrowid

    async def get_episodes(self, anime_id: int) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_number ASC
            """, (anime_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_episode_by_id(self, episode_id: int) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def delete_episode(self, anime_id: int, episode_number: int) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("""
                DELETE FROM episodes WHERE anime_id = ? AND episode_number = ?
            """, (anime_id, episode_number))
            await db.commit()
            return cursor.rowcount > 0

    async def get_total_episodes_count(self) -> int:
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT COUNT(*) FROM episodes") as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

    # ================= Sevimlilar =================
    async def toggle_favorite(self, user_id: int, anime_id: int) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("""
                SELECT id FROM favorites WHERE user_id = ? AND anime_id = ?
            """, (user_id, anime_id)) as cursor:
                exists = await cursor.fetchone()

            if exists:
                await db.execute("DELETE FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
                await db.commit()
                return False
            else:
                await db.execute("INSERT INTO favorites (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
                await db.commit()
                return True

    async def is_favorite(self, user_id: int, anime_id: int) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("""
                SELECT 1 FROM favorites WHERE user_id = ? AND anime_id = ?
            """, (user_id, anime_id)) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def get_user_favorites(self, user_id: int) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT a.* FROM anime a
                INNER JOIN favorites f ON a.id = f.anime_id
                WHERE f.user_id = ?
                ORDER BY f.id DESC
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # ================= Majburiy Kanallar =================
    async def add_channel(self, channel_id: str, name: str, url: str) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            try:
                await db.execute("""
                    INSERT INTO channels (channel_id, name, url) VALUES (?, ?, ?)
                    ON CONFLICT(channel_id) DO UPDATE SET name = excluded.name, url = excluded.url
                """, (channel_id, name, url))
                await db.commit()
                return True
            except Exception:
                return False

    async def delete_channel(self, channel_id: str) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_channels(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM channels") as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # ================= Adminlar =================
    async def add_admin(self, user_id: int, added_by: int) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            try:
                await db.execute("""
                    INSERT INTO admins (user_id, added_by) VALUES (?, ?)
                    ON CONFLICT(user_id) DO NOTHING
                """, (user_id, added_by))
                await db.commit()
                return True
            except Exception:
                return False

    async def delete_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def is_admin(self, user_id: int) -> bool:
        if user_id == config.OWNER_ID:
            return True
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def get_admins(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT a.*, u.full_name, u.username
                FROM admins a
                LEFT JOIN users u ON a.user_id = u.user_id
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # ================= Zayavka / Takliflar =================
    async def add_request(self, user_id: int, anime_name: str, comment: str = "") -> int:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("""
                INSERT INTO requests (user_id, anime_name, comment) VALUES (?, ?, ?)
            """, (user_id, anime_name, comment))
            await db.commit()
            return cursor.lastrowid

    async def get_requests(self, limit: int = 15) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT r.*, u.full_name, u.username
                FROM requests r
                LEFT JOIN users u ON r.user_id = u.user_id
                ORDER BY r.id DESC LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]


db = Database()
