#!/bin/bash

# ============================================
# Скрипт установки Meo Bot на Ubuntu/Debian
# ============================================

set -e

echo "🚀 Установка Meo Bot"
echo "===================="

# Проверяем что запущено от root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Запустите скрипт от root: sudo bash install.sh"
    exit 1
fi

# Запрашиваем данные
read -p "Введите домен (например mybot.ru): " DOMAIN
read -p "Введите BOT_TOKEN: " BOT_TOKEN
read -p "Введите ваш Telegram ID (ADMIN_IDS): " ADMIN_IDS
read -p "Введите email для SSL сертификата: " EMAIL

echo ""
echo "📦 Установка Docker..."
apt-get update
apt-get install -y ca-certificates curl gnupg

# Добавляем Docker репозиторий
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo ""
echo "📦 Установка Nginx и Certbot..."
apt-get install -y nginx certbot python3-certbot-nginx

echo ""
echo "🔧 Настройка Nginx..."

# Создаём конфиг Nginx
cat > /etc/nginx/sites-available/$DOMAIN << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Активируем сайт
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверяем конфиг
nginx -t
systemctl reload nginx

echo ""
echo "🔐 Получение SSL сертификата..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $EMAIL

echo ""
echo "📁 Создание директории проекта..."
mkdir -p /opt/meo_bot
cd /opt/meo_bot

echo ""
echo "📝 Создание .env файла..."
cat > .env << EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_IDS=$ADMIN_IDS
WEBAPP_URL=https://$DOMAIN/
API_PORT=8080
EOF

echo ""
echo "✅ Установка завершена!"
echo ""
echo "Теперь:"
echo "1. Скопируйте файлы проекта в /opt/meo_bot/"
echo "2. Запустите: cd /opt/meo_bot && docker compose up -d --build"
echo ""
echo "🌐 Ваш Mini App будет доступен по адресу: https://$DOMAIN/"

