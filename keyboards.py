from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# === Клавиатуры пользователя ===

def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню пользователя."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📝 Ввести код дня"))
    builder.row(KeyboardButton(text="📊 Моя статистика"))
    return builder.as_markup(resize_keyboard=True)


def get_cancel_kb() -> ReplyKeyboardMarkup:
    """Клавиатура отмены."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def get_skip_patronymic_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для пропуска отчества."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⏭ Пропустить"))
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


# === Клавиатуры админа ===

def get_admin_menu() -> InlineKeyboardMarkup:
    """Админ-панель."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Открыть новый день", callback_data="admin_new_day"))
    builder.row(InlineKeyboardButton(text="🔒 Закрыть текущий день", callback_data="admin_close_day"))
    builder.row(InlineKeyboardButton(text="📊 Статистика по дням", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="👥 Список участников", callback_data="admin_users"))
    builder.row(InlineKeyboardButton(text="📋 Полный отчёт", callback_data="admin_full_report"))
    builder.row(InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"))
    return builder.as_markup()


def get_day_selection_kb() -> InlineKeyboardMarkup:
    """Выбор дня для открытия."""
    builder = InlineKeyboardBuilder()
    for day in range(1, 6):
        builder.add(InlineKeyboardButton(
            text=f"День {day}",
            callback_data=f"select_day_{day}"
        ))
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back"))
    return builder.as_markup()


def get_back_to_admin_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в админку."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back"))
    return builder.as_markup()


def get_cancel_broadcast_kb() -> InlineKeyboardMarkup:
    """Клавиатура отмены рассылки."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить рассылку", callback_data="cancel_broadcast"))
    return builder.as_markup()


def get_confirm_broadcast_kb() -> InlineKeyboardMarkup:
    """Подтверждение рассылки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_broadcast"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")
    )
    return builder.as_markup()

