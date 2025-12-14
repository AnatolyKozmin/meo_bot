"""
Генератор QR-кодов для дней мероприятия.
"""

import io
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer


def generate_qr_code(code: str, day_number: int) -> io.BytesIO:
    """
    Генерирует QR-код для дня мероприятия.
    
    Args:
        code: Код дня
        day_number: Номер дня
    
    Returns:
        BytesIO с PNG изображением QR-кода
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    # QR содержит только код
    qr.add_data(code)
    qr.make(fit=True)
    
    # Создаём изображение с закруглёнными модулями
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        fill_color="#2E211B",  # Цвет из брендбука
        back_color="#EAE0C7"   # Фон из брендбука
    )
    
    # Сохраняем в BytesIO
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return buffer

