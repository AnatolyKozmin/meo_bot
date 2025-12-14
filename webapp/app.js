// ===== Конфигурация =====
// Если фронтенд и бэкенд на одном сервере — оставь пустым
// Если на разных — укажи полный URL бэкенда
const API_URL = '';

// ===== Telegram WebApp Initialization =====
const tg = window.Telegram.WebApp;

// Инициализируем WebApp
tg.ready();
tg.expand();

// ===== DOM Elements =====
const scannerContainer = document.getElementById('scanner-container');
const scannerPlaceholder = document.getElementById('scanner-placeholder');
const scanBtn = document.getElementById('scan-btn');
const stopBtn = document.getElementById('stop-btn');
const statusEl = document.getElementById('status');
const statusIcon = statusEl.querySelector('.status-icon');
const statusText = statusEl.querySelector('.status-text');

// ===== QR Scanner =====
let html5QrCode = null;
let isScanning = false;

// Показать статус
function showStatus(type, icon, text) {
    statusEl.className = `status ${type}`;
    statusIcon.textContent = icon;
    statusText.textContent = text;
}

// Скрыть статус
function hideStatus() {
    statusEl.classList.add('hidden');
}

// Запуск сканера
async function startScanner() {
    try {
        hideStatus();
        
        // Создаём сканер если ещё нет
        if (!html5QrCode) {
            html5QrCode = new Html5Qrcode("reader");
        }
        
        // Показываем сканер
        scannerContainer.classList.add('active');
        scannerPlaceholder.classList.add('hidden');
        scanBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');
        
        // Запускаем сканирование с ЗАДНЕЙ камерой (facingMode: environment)
        await html5QrCode.start(
            { facingMode: "environment" },  // Задняя камера
            {
                fps: 10,
                qrbox: { width: 200, height: 200 },
                aspectRatio: 1.0
            },
            onScanSuccess,
            onScanFailure
        );
        
        isScanning = true;
        
    } catch (err) {
        console.error('Ошибка запуска сканера:', err);
        
        let errorMessage = 'Не удалось запустить камеру';
        if (err.name === 'NotAllowedError') {
            errorMessage = 'Разрешите доступ к камере';
        } else if (err.name === 'NotFoundError') {
            errorMessage = 'Камера не найдена';
        } else if (err.name === 'OverconstrainedError') {
            // Если задняя камера недоступна, пробуем любую
            try {
                await html5QrCode.start(
                    { facingMode: "user" },
                    {
                        fps: 10,
                        qrbox: { width: 200, height: 200 },
                        aspectRatio: 1.0
                    },
                    onScanSuccess,
                    onScanFailure
                );
                isScanning = true;
                return;
            } catch (e) {
                errorMessage = 'Камера недоступна';
            }
        }
        
        showStatus('error', '❌', errorMessage);
        resetUI();
    }
}

// Остановка сканера
async function stopScanner() {
    if (html5QrCode && isScanning) {
        try {
            await html5QrCode.stop();
            isScanning = false;
        } catch (err) {
            console.error('Ошибка остановки сканера:', err);
        }
    }
    resetUI();
}

// Сброс UI
function resetUI() {
    scannerContainer.classList.remove('active');
    scannerPlaceholder.classList.remove('hidden');
    scanBtn.classList.remove('hidden');
    stopBtn.classList.add('hidden');
}

// Успешное сканирование
async function onScanSuccess(decodedText, decodedResult) {
    console.log('QR отсканирован:', decodedText);
    
    // Вибрация для обратной связи
    if (tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
    }
    
    // Останавливаем сканер
    await stopScanner();
    
    // Показываем статус
    showStatus('loading', '⏳', 'Проверка кода...');
    
    // Отправляем запрос на API
    try {
        const response = await fetch(`${API_URL}/api/check-in`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code: decodedText.trim(),
                initData: tg.initData
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Вибрация успеха
            if (tg.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
            
            if (result.already_marked) {
                showStatus('success', '✅', result.message);
            } else {
                showStatus('success', '✅', `${result.message}\nВсего дней: ${result.total_days}/5`);
            }
            
            // Закрываем Mini App через 2 секунды
            setTimeout(() => {
                tg.close();
            }, 2000);
            
        } else {
            // Вибрация ошибки
            if (tg.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('error');
            }
            
            showStatus('error', '❌', result.error || 'Ошибка');
        }
        
    } catch (err) {
        console.error('Ошибка запроса:', err);
        
        // Fallback: отправляем через sendData если API недоступен
        try {
            const data = JSON.stringify({
                action: 'check_in',
                code: decodedText.trim()
            });
            tg.sendData(data);
            showStatus('success', '✅', 'Код отправлен!');
        } catch (e) {
            showStatus('error', '❌', 'Ошибка соединения');
        }
    }
}

// Ошибка сканирования (вызывается постоянно пока не найден QR)
function onScanFailure(error) {
    // Игнорируем, это нормально пока QR не в кадре
}

// ===== Event Listeners =====
scanBtn.addEventListener('click', startScanner);
stopBtn.addEventListener('click', stopScanner);

// Закрытие по кнопке "Назад" в Telegram
tg.onEvent('backButtonClicked', () => {
    if (isScanning) {
        stopScanner();
    } else {
        tg.close();
    }
});

// Показываем кнопку "Назад"
tg.BackButton.show();

// ===== Очистка при закрытии =====
window.addEventListener('beforeunload', () => {
    if (html5QrCode && isScanning) {
        html5QrCode.stop();
    }
});
