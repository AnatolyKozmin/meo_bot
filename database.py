import aiosqlite
from config import DB_PATH


async def init_db():
    """Инициализация базы данных."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица участников
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                patronymic TEXT,
                group_name TEXT NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица дней мероприятия
        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_days (
                day_number INTEGER PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица посещений
        await db.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                day_number INTEGER NOT NULL,
                marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (day_number) REFERENCES event_days(day_number),
                UNIQUE(user_id, day_number)
            )
        """)
        
        await db.commit()


# === Работа с пользователями ===

async def add_user(user_id: int, first_name: str, last_name: str, 
                   patronymic: str | None, group_name: str) -> bool:
    """Добавить нового участника."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """INSERT INTO users (user_id, first_name, last_name, patronymic, group_name)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, first_name, last_name, patronymic, group_name)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_user(user_id: int) -> dict | None:
    """Получить информацию о пользователе."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_users() -> list[dict]:
    """Получить всех пользователей."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_all_user_ids() -> list[int]:
    """Получить ID всех пользователей для рассылки."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


# === Работа с днями мероприятия ===

async def create_day(day_number: int, code: str) -> bool:
    """Создать новый день с кодом."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Деактивируем все предыдущие дни
            await db.execute("UPDATE event_days SET is_active = 0")
            # Создаём новый день или обновляем существующий
            await db.execute(
                """INSERT INTO event_days (day_number, code, is_active)
                   VALUES (?, ?, 1)
                   ON CONFLICT(day_number) DO UPDATE SET code = ?, is_active = 1""",
                (day_number, code, code)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_active_day() -> dict | None:
    """Получить активный день."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM event_days WHERE is_active = 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def deactivate_all_days():
    """Деактивировать все дни."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE event_days SET is_active = 0")
        await db.commit()


async def get_all_days() -> list[dict]:
    """Получить все дни."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM event_days ORDER BY day_number"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# === Работа с посещениями ===

async def mark_attendance(user_id: int, day_number: int) -> bool:
    """Отметить посещение."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """INSERT INTO attendance (user_id, day_number)
                   VALUES (?, ?)""",
                (user_id, day_number)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def check_attendance(user_id: int, day_number: int) -> bool:
    """Проверить, отмечен ли пользователь в этот день."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM attendance WHERE user_id = ? AND day_number = ?",
            (user_id, day_number)
        ) as cursor:
            return await cursor.fetchone() is not None


async def get_user_attendance(user_id: int) -> list[int]:
    """Получить дни посещения пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT day_number FROM attendance WHERE user_id = ? ORDER BY day_number",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_attendance_stats() -> list[dict]:
    """Получить статистику посещений для экспорта."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT 
                u.user_id,
                u.last_name,
                u.first_name,
                u.patronymic,
                u.group_name,
                GROUP_CONCAT(a.day_number) as attended_days,
                COUNT(a.day_number) as total_days
            FROM users u
            LEFT JOIN attendance a ON u.user_id = a.user_id
            GROUP BY u.user_id
            ORDER BY u.last_name, u.first_name
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_day_stats() -> list[dict]:
    """Получить статистику по дням."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT 
                ed.day_number,
                ed.code,
                ed.is_active,
                COUNT(a.user_id) as attendees
            FROM event_days ed
            LEFT JOIN attendance a ON ed.day_number = a.day_number
            GROUP BY ed.day_number
            ORDER BY ed.day_number
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

