import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS
from keyboards import (
    get_admin_menu, get_day_selection_kb, get_back_to_admin_kb,
    get_cancel_broadcast_kb, get_confirm_broadcast_kb, get_qr_day_selection_kb
)
from qr_generator import generate_qr_code

router = Router()


class AdminStates(StatesGroup):
    """Состояния админа."""
    entering_day_code = State()
    broadcast_message = State()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом."""
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Админ-панель."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await state.clear()
    active_day = await db.get_active_day()
    status = f"🟢 Активен День {active_day['day_number']} (код: {active_day['code']})" if active_day else "🔴 Нет активного дня"
    
    users = await db.get_all_users()
    
    await message.answer(
        f"🔧 <b>Админ-панель</b>\n\n"
        f"📊 Всего участников: {len(users)}\n"
        f"📅 Статус: {status}",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    """Возврат в админ-панель."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.clear()
    active_day = await db.get_active_day()
    status = f"🟢 Активен День {active_day['day_number']} (код: {active_day['code']})" if active_day else "🔴 Нет активного дня"
    
    users = await db.get_all_users()
    
    await callback.message.edit_text(
        f"🔧 <b>Админ-панель</b>\n\n"
        f"📊 Всего участников: {len(users)}\n"
        f"📅 Статус: {status}",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )
    await callback.answer()


# === Управление днями ===

@router.callback_query(F.data == "admin_new_day")
async def new_day_select(callback: CallbackQuery):
    """Выбор дня для открытия."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    days = await db.get_all_days()
    active_day = await db.get_active_day()
    
    days_info = ""
    for day in days:
        status = "🟢" if day['is_active'] else "⚪"
        days_info += f"{status} День {day['day_number']} - {day['attendees'] if 'attendees' in day else 0} чел.\n"
    
    if not days_info:
        days_info = "Дни ещё не создавались"
    
    current = f"\n\n🔔 Сейчас активен: День {active_day['day_number']}" if active_day else ""
    
    await callback.message.edit_text(
        f"📅 <b>Выберите день для открытия</b>\n\n"
        f"{days_info}{current}",
        parse_mode="HTML",
        reply_markup=get_day_selection_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_day_"))
async def select_day(callback: CallbackQuery, state: FSMContext):
    """Выбор конкретного дня."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    day_number = int(callback.data.split("_")[-1])
    await state.update_data(selected_day=day_number)
    
    await callback.message.edit_text(
        f"🔐 Введите код для Дня {day_number}:\n\n"
        f"(Участники будут вводить этот код для отметки)",
        parse_mode="HTML",
        reply_markup=get_back_to_admin_kb()
    )
    await state.set_state(AdminStates.entering_day_code)
    await callback.answer()


@router.message(AdminStates.entering_day_code)
async def process_day_code(message: Message, state: FSMContext):
    """Обработка кода дня."""
    if not is_admin(message.from_user.id):
        return
    
    code = message.text.strip()
    if len(code) < 3:
        await message.answer("❌ Код должен содержать минимум 3 символа. Попробуйте ещё раз:")
        return
    
    data = await state.get_data()
    day_number = data.get('selected_day')
    
    if not day_number:
        await state.clear()
        await message.answer("❌ Ошибка. Начните заново через /admin")
        return
    
    await db.create_day(day_number, code)
    await state.clear()
    
    await message.answer(
        f"✅ <b>День {day_number} открыт!</b>\n\n"
        f"🔐 Код: <code>{code}</code>\n\n"
        f"Участники теперь могут отмечаться, используя этот код.\n\n"
        f"Используйте /admin для возврата в панель.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_close_day")
async def close_day(callback: CallbackQuery):
    """Закрытие текущего дня."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    active_day = await db.get_active_day()
    if not active_day:
        await callback.answer("❌ Нет активного дня для закрытия", show_alert=True)
        return
    
    await db.deactivate_all_days()
    
    await callback.message.edit_text(
        f"🔒 <b>День {active_day['day_number']} закрыт</b>\n\n"
        f"Участники больше не могут отмечаться.",
        parse_mode="HTML",
        reply_markup=get_back_to_admin_kb()
    )
    await callback.answer("День закрыт!")


# === Статистика ===

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику по дням."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    day_stats = await db.get_day_stats()
    users = await db.get_all_users()
    
    if not day_stats:
        stats_text = "📊 Статистика пока пуста"
    else:
        stats_text = "📊 <b>Статистика по дням:</b>\n\n"
        for day in day_stats:
            status = "🟢" if day['is_active'] else "⚪"
            stats_text += f"{status} День {day['day_number']}: {day['attendees']} чел.\n"
    
    await callback.message.edit_text(
        f"{stats_text}\n\n"
        f"👥 Всего зарегистрировано: {len(users)} чел.",
        parse_mode="HTML",
        reply_markup=get_back_to_admin_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def show_users(callback: CallbackQuery):
    """Показать список участников."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    stats = await db.get_attendance_stats()
    
    if not stats:
        await callback.message.edit_text(
            "👥 Пока нет зарегистрированных участников.",
            reply_markup=get_back_to_admin_kb()
        )
        await callback.answer()
        return
    
    text = "👥 <b>Список участников:</b>\n\n"
    for i, user in enumerate(stats[:20], 1):  # Ограничим до 20 для читаемости
        fio = f"{user['last_name']} {user['first_name']}"
        if user['patronymic']:
            fio += f" {user['patronymic']}"
        days = user['attended_days'] or "0"
        text += f"{i}. {fio} ({user['group_name']}) - {user['total_days']} дн.\n"
    
    if len(stats) > 20:
        text += f"\n... и ещё {len(stats) - 20} участников"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_to_admin_kb()
    )
    await callback.answer()


# === Полный отчёт ===

@router.callback_query(F.data == "admin_full_report")
async def full_report(callback: CallbackQuery, bot: Bot):
    """Полный отчёт со всеми участниками и их посещениями."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    stats = await db.get_attendance_stats()
    day_stats = await db.get_day_stats()
    
    if not stats:
        await callback.message.edit_text(
            "📋 Пока нет данных для отчёта.",
            reply_markup=get_back_to_admin_kb()
        )
        await callback.answer()
        return
    
    # Формируем текстовый отчёт
    report = "📋 <b>ПОЛНЫЙ ОТЧЁТ</b>\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Статистика по дням
    report += "📊 <b>Статистика по дням:</b>\n"
    for day in day_stats:
        status = "🟢" if day['is_active'] else "⚪"
        report += f"  {status} День {day['day_number']}: {day['attendees']} чел.\n"
    report += "\n"
    
    # Таблица участников
    report += "👥 <b>Участники:</b>\n\n"
    
    for i, user in enumerate(stats, 1):
        fio = f"{user['last_name']} {user['first_name']}"
        if user['patronymic']:
            fio += f" {user['patronymic']}"
        
        # Формируем визуализацию посещений
        attended_days = set(
            map(int, user['attended_days'].split(',')) 
            if user['attended_days'] else []
        )
        days_visual = ""
        for d in range(1, 6):
            days_visual += "✅" if d in attended_days else "⬜"
        
        report += f"<b>{i}. {fio}</b>\n"
        report += f"   📚 {user['group_name']}\n"
        report += f"   {days_visual} ({user['total_days']}/5)\n\n"
    
    report += f"━━━━━━━━━━━━━━━━━━━━\n"
    report += f"📈 <b>Итого: {len(stats)} участников</b>"
    
    # Если отчёт слишком длинный, разбиваем на части
    if len(report) > 4000:
        # Отправляем новым сообщением, т.к. edit не поддерживает длинные тексты
        await callback.message.edit_text(
            "📋 Отчёт слишком большой, отправляю отдельными сообщениями...",
            reply_markup=None
        )
        
        # Разбиваем на части по 4000 символов
        chunks = []
        current_chunk = ""
        for line in report.split('\n'):
            if len(current_chunk) + len(line) + 1 > 4000:
                chunks.append(current_chunk)
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        if current_chunk:
            chunks.append(current_chunk)
        
        for chunk in chunks:
            await bot.send_message(
                callback.from_user.id,
                chunk,
                parse_mode="HTML"
            )
        
        await bot.send_message(
            callback.from_user.id,
            "✅ Отчёт отправлен!",
            reply_markup=get_back_to_admin_kb()
        )
    else:
        await callback.message.edit_text(
            report,
            parse_mode="HTML",
            reply_markup=get_back_to_admin_kb()
        )
    
    await callback.answer()


# === Генерация QR-кодов ===

@router.callback_query(F.data == "admin_qr_codes")
async def qr_codes_menu(callback: CallbackQuery):
    """Меню генерации QR-кодов."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    days = await db.get_all_days()
    
    if not days:
        await callback.message.edit_text(
            "❌ Сначала создайте хотя бы один день через 'Открыть новый день'",
            reply_markup=get_back_to_admin_kb()
        )
        await callback.answer()
        return
    
    days_info = ""
    for day in days:
        days_info += f"📅 День {day['day_number']} — код: <code>{day['code']}</code>\n"
    
    await callback.message.edit_text(
        f"🔲 <b>Генерация QR-кодов</b>\n\n"
        f"{days_info}\n"
        f"Выберите день для генерации QR-кода:",
        parse_mode="HTML",
        reply_markup=get_qr_day_selection_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qr_day_"))
async def generate_qr_for_day(callback: CallbackQuery, bot: Bot):
    """Генерация QR-кода для конкретного дня."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    day_number = int(callback.data.split("_")[-1])
    days = await db.get_all_days()
    
    day = next((d for d in days if d['day_number'] == day_number), None)
    
    if not day:
        await callback.answer("❌ День не найден. Сначала создайте его.", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"⏳ Генерирую QR-код для Дня {day_number}...",
        reply_markup=None
    )
    
    # Генерируем QR
    qr_buffer = generate_qr_code(day['code'], day_number)
    
    # Отправляем изображение
    photo = BufferedInputFile(
        qr_buffer.read(),
        filename=f"qr_day_{day_number}.png"
    )
    
    await bot.send_photo(
        callback.from_user.id,
        photo=photo,
        caption=(
            f"🔲 <b>QR-код для Дня {day_number}</b>\n\n"
            f"📝 Код: <code>{day['code']}</code>\n\n"
            f"Распечатайте этот QR-код и покажите участникам для сканирования."
        ),
        parse_mode="HTML"
    )
    
    await bot.send_message(
        callback.from_user.id,
        "✅ QR-код сгенерирован!",
        reply_markup=get_back_to_admin_kb()
    )
    await callback.answer()


# === Рассылка ===

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    users = await db.get_all_users()
    
    await callback.message.edit_text(
        f"📨 <b>Рассылка</b>\n\n"
        f"Получателей: {len(users)} чел.\n\n"
        f"Введите текст сообщения для рассылки:",
        parse_mode="HTML",
        reply_markup=get_cancel_broadcast_kb()
    )
    await state.set_state(AdminStates.broadcast_message)
    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.clear()
    
    active_day = await db.get_active_day()
    status = f"🟢 Активен День {active_day['day_number']} (код: {active_day['code']})" if active_day else "🔴 Нет активного дня"
    users = await db.get_all_users()
    
    await callback.message.edit_text(
        f"🔧 <b>Админ-панель</b>\n\n"
        f"📊 Всего участников: {len(users)}\n"
        f"📅 Статус: {status}",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )
    await callback.answer("Рассылка отменена")


@router.message(AdminStates.broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка текста рассылки."""
    if not is_admin(message.from_user.id):
        return
    
    await state.update_data(broadcast_text=message.text)
    
    users = await db.get_all_users()
    
    await message.answer(
        f"📨 <b>Превью рассылки:</b>\n\n"
        f"{message.text}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Получателей: {len(users)} чел.\n\n"
        f"Отправить?",
        parse_mode="HTML",
        reply_markup=get_confirm_broadcast_kb()
    )


@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и отправка рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    data = await state.get_data()
    text = data.get('broadcast_text')
    
    if not text:
        await callback.answer("❌ Текст рассылки не найден", show_alert=True)
        await state.clear()
        return
    
    await state.clear()
    
    user_ids = await db.get_all_user_ids()
    
    await callback.message.edit_text(
        f"⏳ Отправка рассылки...\n\n"
        f"Прогресс: 0/{len(user_ids)}",
        reply_markup=None
    )
    
    sent = 0
    failed = 0
    
    for i, user_id in enumerate(user_ids):
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except Exception:
            failed += 1
        
        # Обновляем прогресс каждые 10 сообщений
        if (i + 1) % 10 == 0:
            await callback.message.edit_text(
                f"⏳ Отправка рассылки...\n\n"
                f"Прогресс: {i + 1}/{len(user_ids)}"
            )
        
        # Небольшая задержка для избежания флуда
        await asyncio.sleep(0.05)
    
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}",
        parse_mode="HTML",
        reply_markup=get_back_to_admin_kb()
    )
    await callback.answer()

