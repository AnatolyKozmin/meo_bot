"""
API для Telegram Mini App.
Обрабатывает запросы на отметку посещения.
"""

import hashlib
import hmac
import json
from urllib.parse import parse_qsl

from aiohttp import web

import database as db
from config import BOT_TOKEN


def verify_telegram_data(init_data: str) -> dict | None:
    """
    Проверяет подлинность данных от Telegram WebApp.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        
        if "hash" not in parsed_data:
            return None
        
        received_hash = parsed_data.pop("hash")
        
        # Создаём строку для проверки
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )
        
        # Создаём secret key
        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash == received_hash:
            # Парсим user данные
            if "user" in parsed_data:
                parsed_data["user"] = json.loads(parsed_data["user"])
            return parsed_data
        
        return None
    except Exception as e:
        print(f"Ошибка верификации: {e}")
        return None


async def handle_check_in(request: web.Request) -> web.Response:
    """
    Обработчик отметки посещения.
    POST /api/check-in
    Body: { "code": "КОД", "initData": "telegram_init_data" }
    """
    # CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    
    if request.method == "OPTIONS":
        return web.Response(headers=headers)
    
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"success": False, "error": "Неверный формат данных"},
            status=400,
            headers=headers
        )
    
    code = data.get("code", "").strip().upper()
    init_data = data.get("initData", "")
    
    if not code:
        return web.json_response(
            {"success": False, "error": "Код не указан"},
            status=400,
            headers=headers
        )
    
    # Проверяем данные от Telegram
    verified_data = verify_telegram_data(init_data)
    if not verified_data:
        return web.json_response(
            {"success": False, "error": "Ошибка авторизации"},
            status=401,
            headers=headers
        )
    
    user_id = verified_data.get("user", {}).get("id")
    if not user_id:
        return web.json_response(
            {"success": False, "error": "Пользователь не найден"},
            status=401,
            headers=headers
        )
    
    # Проверяем, зарегистрирован ли пользователь
    user = await db.get_user(user_id)
    if not user:
        return web.json_response(
            {"success": False, "error": "Вы не зарегистрированы. Напишите /start боту."},
            status=400,
            headers=headers
        )
    
    # Проверяем активный день
    active_day = await db.get_active_day()
    if not active_day:
        return web.json_response(
            {"success": False, "error": "Сейчас нет активного дня"},
            status=400,
            headers=headers
        )
    
    # Проверяем, не отмечен ли уже
    already_marked = await db.check_attendance(user_id, active_day["day_number"])
    if already_marked:
        return web.json_response(
            {
                "success": True,
                "already_marked": True,
                "message": f"Вы уже отмечены на День {active_day['day_number']}!",
                "day": active_day["day_number"]
            },
            headers=headers
        )
    
    # Проверяем код
    if code != active_day["code"].upper():
        return web.json_response(
            {"success": False, "error": "Неверный код"},
            status=400,
            headers=headers
        )
    
    # Отмечаем посещение
    await db.mark_attendance(user_id, active_day["day_number"])
    attendance = await db.get_user_attendance(user_id)
    
    return web.json_response(
        {
            "success": True,
            "message": f"Вы отмечены на День {active_day['day_number']}!",
            "day": active_day["day_number"],
            "total_days": len(attendance)
        },
        headers=headers
    )


async def handle_status(request: web.Request) -> web.Response:
    """
    Получить статус текущего дня.
    GET /api/status
    """
    headers = {
        "Access-Control-Allow-Origin": "*",
    }
    
    active_day = await db.get_active_day()
    
    if active_day:
        return web.json_response(
            {
                "active": True,
                "day": active_day["day_number"]
            },
            headers=headers
        )
    else:
        return web.json_response(
            {"active": False},
            headers=headers
        )


def create_app() -> web.Application:
    """Создание веб-приложения."""
    app = web.Application()
    
    # API эндпоинты
    app.router.add_route("*", "/api/check-in", handle_check_in)
    app.router.add_get("/api/status", handle_status)
    
    # Раздача статических файлов (фронтенд)
    import os
    webapp_path = os.path.join(os.path.dirname(__file__), 'webapp')
    if os.path.exists(webapp_path):
        app.router.add_static('/', webapp_path, name='static')
    
    return app

