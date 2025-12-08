from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import get_main_menu, get_cancel_kb, get_skip_patronymic_kb

router = Router()


class Registration(StatesGroup):
    """Состояния регистрации."""
    last_name = State()
    first_name = State()
    patronymic = State()
    group_name = State()


class EnterCode(StatesGroup):
    """Состояние ввода кода."""
    waiting_code = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    user = await db.get_user(message.from_user.id)
    
    if user:
        # Пользователь уже зарегистрирован
        fio = f"{user['last_name']} {user['first_name']}"
        if user['patronymic']:
            fio += f" {user['patronymic']}"
        
        await message.answer(
            f"👋 С возвращением, {fio}!\n\n"
            f"📚 Группа: {user['group_name']}\n\n"
            "Используй меню для навигации.",
            reply_markup=get_main_menu()
        )
    else:
        # Начинаем регистрацию
        await message.answer(
            "👋 Добро пожаловать на мероприятие!\n\n"
            "Для участия необходимо зарегистрироваться.\n"
            "Введите вашу фамилию:",
            reply_markup=get_cancel_kb()
        )
        await state.set_state(Registration.last_name)


@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия."""
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    user = await db.get_user(message.from_user.id)
    
    if user:
        await message.answer("Действие отменено.", reply_markup=get_main_menu())
    else:
        await message.answer(
            "Регистрация отменена. Для начала регистрации отправьте /start",
            reply_markup=None
        )


# === Регистрация ===

@router.message(Registration.last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Обработка фамилии."""
    if not message.text or len(message.text) < 2:
        await message.answer("❌ Пожалуйста, введите корректную фамилию:")
        return
    
    await state.update_data(last_name=message.text.strip())
    await message.answer("Отлично! Теперь введите ваше имя:")
    await state.set_state(Registration.first_name)


@router.message(Registration.first_name)
async def process_first_name(message: Message, state: FSMContext):
    """Обработка имени."""
    if not message.text or len(message.text) < 2:
        await message.answer("❌ Пожалуйста, введите корректное имя:")
        return
    
    await state.update_data(first_name=message.text.strip())
    await message.answer(
        "Введите ваше отчество (или нажмите 'Пропустить'):",
        reply_markup=get_skip_patronymic_kb()
    )
    await state.set_state(Registration.patronymic)


@router.message(Registration.patronymic)
async def process_patronymic(message: Message, state: FSMContext):
    """Обработка отчества."""
    if message.text == "⏭ Пропустить":
        await state.update_data(patronymic=None)
    else:
        await state.update_data(patronymic=message.text.strip())
    
    await message.answer(
        "Последний шаг! Введите вашу группу:",
        reply_markup=get_cancel_kb()
    )
    await state.set_state(Registration.group_name)


@router.message(Registration.group_name)
async def process_group_name(message: Message, state: FSMContext):
    """Обработка группы и завершение регистрации."""
    if not message.text or len(message.text) < 2:
        await message.answer("❌ Пожалуйста, введите корректное название группы:")
        return
    
    data = await state.get_data()
    data['group_name'] = message.text.strip()
    
    success = await db.add_user(
        user_id=message.from_user.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        patronymic=data['patronymic'],
        group_name=data['group_name']
    )
    
    await state.clear()
    
    if success:
        fio = f"{data['last_name']} {data['first_name']}"
        if data['patronymic']:
            fio += f" {data['patronymic']}"
        
        await message.answer(
            f"✅ Регистрация завершена!\n\n"
            f"👤 ФИО: {fio}\n"
            f"📚 Группа: {data['group_name']}\n\n"
            "Теперь вы можете отмечать посещение, вводя код дня.",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            "❌ Ошибка регистрации. Возможно, вы уже зарегистрированы.\n"
            "Попробуйте /start",
            reply_markup=None
        )


# === Ввод кода дня ===

@router.message(F.text == "📝 Ввести код дня")
async def enter_code_start(message: Message, state: FSMContext):
    """Начало ввода кода дня."""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            "❌ Вы не зарегистрированы. Используйте /start для регистрации."
        )
        return
    
    active_day = await db.get_active_day()
    if not active_day:
        await message.answer(
            "⏳ Сейчас нет активного дня. Ожидайте открытия нового дня.",
            reply_markup=get_main_menu()
        )
        return
    
    # Проверяем, не отмечен ли уже
    already_marked = await db.check_attendance(message.from_user.id, active_day['day_number'])
    if already_marked:
        await message.answer(
            f"✅ Вы уже отмечены на День {active_day['day_number']}!",
            reply_markup=get_main_menu()
        )
        return
    
    await message.answer(
        f"🔐 Введите код для Дня {active_day['day_number']}:",
        reply_markup=get_cancel_kb()
    )
    await state.set_state(EnterCode.waiting_code)


@router.message(EnterCode.waiting_code)
async def process_code(message: Message, state: FSMContext):
    """Обработка введённого кода."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_main_menu())
        return
    
    active_day = await db.get_active_day()
    if not active_day:
        await state.clear()
        await message.answer(
            "⏳ День был закрыт. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
        return
    
    entered_code = message.text.strip().upper()
    correct_code = active_day['code'].upper()
    
    if entered_code == correct_code:
        success = await db.mark_attendance(message.from_user.id, active_day['day_number'])
        await state.clear()
        
        if success:
            attendance = await db.get_user_attendance(message.from_user.id)
            await message.answer(
                f"✅ Отлично! Вы отмечены на День {active_day['day_number']}!\n\n"
                f"📊 Всего посещено дней: {len(attendance)} из 5",
                reply_markup=get_main_menu()
            )
        else:
            await message.answer(
                f"✅ Вы уже были отмечены на День {active_day['day_number']}!",
                reply_markup=get_main_menu()
            )
    else:
        await message.answer(
            "❌ Неверный код. Попробуйте ещё раз или отмените:",
            reply_markup=get_cancel_kb()
        )


# === Статистика ===

@router.message(F.text == "📊 Моя статистика")
async def show_my_stats(message: Message):
    """Показать статистику пользователя."""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            "❌ Вы не зарегистрированы. Используйте /start для регистрации."
        )
        return
    
    attendance = await db.get_user_attendance(message.from_user.id)
    
    fio = f"{user['last_name']} {user['first_name']}"
    if user['patronymic']:
        fio += f" {user['patronymic']}"
    
    days_str = ", ".join([f"День {d}" for d in attendance]) if attendance else "Пока нет отметок"
    
    # Визуализация посещений
    days_visual = ""
    for day in range(1, 6):
        if day in attendance:
            days_visual += f"✅ День {day}\n"
        else:
            days_visual += f"⬜ День {day}\n"
    
    await message.answer(
        f"📊 <b>Ваша статистика</b>\n\n"
        f"👤 {fio}\n"
        f"📚 Группа: {user['group_name']}\n\n"
        f"<b>Посещения:</b>\n{days_visual}\n"
        f"📈 Итого: {len(attendance)} из 5 дней",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

