import logging
import re
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загрузка переменных окружения
load_dotenv()

# Настройки из .env
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL", "https://ecp.mis66.ru")
LOGIN = os.getenv("SYSTEM_LOGIN")
PASSWORD = os.getenv("SYSTEM_PASSWORD")

# Хранилище сессий для разных пользователей
user_sessions = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

class UserSession:
    """Класс для хранения сессии пользователя"""
    def __init__(self, user_id):
        self.user_id = user_id
        self.session = requests.Session()
        self.headers = {
            "accept": "*/*",
            "accept-language": "ru,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "Referer": f"{BASE_URL}/?c=promed"
        }
        self.last_auth = None
        self.is_authenticated = False
        
    def login(self):
        """Авторизация в системе"""
        try:
            print(f"Выполняется авторизация для пользователя {self.user_id}...")
            
            # Сначала получаем PHPSESSID
            init_response = self.session.get(f"{BASE_URL}/?c=promed", timeout=10)
            
            # Получаем cookies из ответа
            cookies = self.session.cookies.get_dict()
            if 'PHPSESSID' in cookies:
                self.headers['cookie'] = f"PHPSESSID={cookies['PHPSESSID']}"
            
            # Выполняем авторизацию
            auth_url = f"{BASE_URL}/api/user/login"
            auth_headers = {
                "Login": LOGIN,
                "Password": PASSWORD
            }
            
            response = self.session.request("GET", auth_url, headers=auth_headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Авторизация успешна для пользователя {self.user_id}")
            self.is_authenticated = True
            self.last_auth = datetime.now()
            
            # Обновляем cookies в headers
            cookies = self.session.cookies.get_dict()
            cookie_parts = []
            if 'PHPSESSID' in cookies:
                cookie_parts.append(f"PHPSESSID={cookies['PHPSESSID']}")
            if 'login' in cookies:
                cookie_parts.append(f"login={cookies['login']}")
            if 'route' in cookies:
                cookie_parts.append(f"route={cookies['route']}")
            if 'JSESSIONID' in cookies:
                cookie_parts.append(f"JSESSIONID={cookies['JSESSIONID']}")
            
            if cookie_parts:
                self.headers['cookie'] = "; ".join(cookie_parts)
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка авторизации для пользователя {self.user_id}: {e}")
            self.is_authenticated = False
            return False
        except ValueError as e:
            logger.error(f"Ошибка парсинга JSON при авторизации: {e}")
            self.is_authenticated = False
            return False
    
    def check_and_renew_auth(self):
        """Проверяет и обновляет авторизацию при необходимости"""
        if not self.is_authenticated or not self.last_auth:
            return self.login()
        
        # Проверяем, не прошло ли больше 30 минут с последней авторизации
        time_diff = (datetime.now() - self.last_auth).total_seconds()
        if time_diff > 1800:  # 30 минут
            logger.info(f"Обновление авторизации для пользователя {self.user_id}")
            return self.login()
        
        return True
    
    def get_headers(self):
        """Возвращает заголовки с актуальными cookies"""
        return self.headers.copy()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if update.message:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Создаем сессию для пользователя
        if user_id not in user_sessions:
            user_sessions[user_id] = UserSession(user_id)
            await update.message.reply_text(
                f"Привет, {username}! Создана новая сессия.\n\n"
                "Отправьте список направлений в формате:\n"
                "147849720 21.11.2025\n145052203 05.11.2025\n..."
            )
        else:
            await update.message.reply_text(
                f"С возвращением, {username}!\n\n"
                "Отправьте список направлений в формате:\n"
                "147849720 21.11.2025\n145052203 05.11.2025\n..."
            )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для принудительной авторизации"""
    if update.message:
        user_id = update.effective_user.id
        
        if user_id not in user_sessions:
            user_sessions[user_id] = UserSession(user_id)
        
        session = user_sessions[user_id]
        await update.message.reply_text("Выполняю авторизацию...")
        
        if session.login():
            await update.message.reply_text("✅ Авторизация успешно выполнена!")
        else:
            await update.message.reply_text("❌ Ошибка авторизации. Проверьте логин и пароль в .env файле.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для проверки статуса сессии"""
    if update.message:
        user_id = update.effective_user.id
        
        if user_id in user_sessions:
            session = user_sessions[user_id]
            status = "авторизован" if session.is_authenticated else "не авторизован"
            last_auth = session.last_auth.strftime("%H:%M:%S") if session.last_auth else "никогда"
            
            await update.message.reply_text(
                f"📊 Статус сессии:\n"
                f"• Авторизация: {status}\n"
                f"• Последняя авторизация: {last_auth}\n"
                f"• ID сессии: {id(session)}\n"
                f"• Всего активных сессий: {len(user_sessions)}"
            )
        else:
            await update.message.reply_text("У вас нет активной сессии. Используйте /start для создания.")

def parse_input(text: str) -> list[tuple[str, str]]:
    """Парсинг ввода пользователя"""
    lines = text.strip().splitlines()
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        num, date = parts
        if re.match(r"^\d+$", num) and re.match(r"^\d{2}\.\d{2}\.\d{4}$", date):
            result.append((num, date))
    return result

async def cancel_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик отмены направлений"""
    # Проверяем, что есть сообщение и текст
    if not update.message or not update.message.text:
        logger.warning("Получено пустое сообщение или не текст")
        return

    user_id = update.effective_user.id
    text = update.message.text

    # Проверяем наличие сессии
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
    
    session = user_sessions[user_id]
    
    # Проверяем авторизацию
    if not session.check_and_renew_auth():
        await update.message.reply_text("❌ Ошибка авторизации. Используйте /login для повторной авторизации.")
        return

    directions = parse_input(text)
    if not directions:
        await update.message.reply_text("Не удалось распознать направления. Проверьте формат.")
        return

    # Отправляем сообщение о начале обработки
    processing_msg = await update.message.reply_text(f"🔍 Обрабатываю {len(directions)} направлений...")

    report = []
    processed_count = 0
    
    for num, date in directions:
        try:
            processed_count += 1
            await processing_msg.edit_text(f"🔍 Обрабатываю {processed_count}/{len(directions)}: {num} ({date})...")
            
            # Шаг 1: Поиск направления
            search_url = f"{BASE_URL}/?c=EvnLabRequest&m=loadEvnLabRequestList"
            search_data = {
                "EvnDirection_Num": num,
                "MedServiceType_SysNick": "lab",
                "MedService_id": "5759",
                "start": "0",
                "limit": "100",
                "begDate": date,
                "endDate": date
            }
            search_resp = session.session.post(search_url, headers=session.get_headers(), data=search_data, timeout=10)
            search_json = search_resp.json()

            if not search_json.get("data"):
                report.append(f"❌ {num} ({date}): не найдено в системе")
                continue

            item = search_json["data"][0]
            evn_lab_request_id = item["EvnLabRequest_id"]
            evn_direction_id = item["EvnDirection_id"]

            # Шаг 2: Отмена проб (первый этап)
            cancel_sample1_url = f"{BASE_URL}/?c=EvnLabRequest&m=cancelLabSample"
            cancel_sample1_data = {
                "MedServiceType_SysNick": "lab",
                "EvnLabRequests": f'["{evn_lab_request_id}"]',
                "MedService_did": "5759"
            }
            resp1 = session.session.post(cancel_sample1_url, headers=session.get_headers(), data=cancel_sample1_data, timeout=10)
            if not resp1.json().get("success"):
                report.append(f"❌ {num} ({date}): ошибка на шаге 1 отмены проб")
                continue

            # Шаг 3: Отмена проб (второй этап)
            cancel_sample2_url = f"{BASE_URL}/?c=EvnLabSample&m=delSamplesQueue"
            files = {
                "MedServiceType_SysNick": (None, "lab"),
                "EvnLabRequests": (None, f'["{evn_lab_request_id}"]'),
                "MedService_did": (None, "5759")
            }
            
            # Убираем content-type для multipart/form-data
            headers_step2 = session.get_headers()
            if 'content-type' in headers_step2:
                del headers_step2['content-type']
                
            resp2 = session.session.post(cancel_sample2_url, headers=headers_step2, files=files, timeout=10)
            if not resp2.json().get("success"):
                report.append(f"❌ {num} ({date}): ошибка на шаге 2 отмены проб")
                continue

            # Шаг 4: Отмена направления
            cancel_dir_url = f"{BASE_URL}/?c=EvnLabRequest&m=cancelDirection"
            cancel_dir_data = {
                "EvnDirection_ids": f'["{evn_direction_id}"]',
                "EvnStatusCause_id": "1",
                "EvnStatusHistory_Cause": ""
            }
            resp3 = session.session.post(cancel_dir_url, headers=session.get_headers(), data=cancel_dir_data, timeout=10)
            if not resp3.json().get("success"):
                report.append(f"❌ {num} ({date}): ошибка при отмене направления")
                continue

            report.append(f"✅ {num} ({date}): успешно отменено")

        except Exception as e:
            logger.error(f"Ошибка при обработке {num}: {e}")
            report.append(f"❌ {num} ({date}): произошла ошибка ({str(e)[:50]}...)")

    # Удаляем сообщение о процессе
    await processing_msg.delete()
    
    # Отправляем результат
    if report:
        result_text = "\n".join(report)
        # Разбиваем на части, если сообщение слишком длинное
        if len(result_text) > 4000:
            parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(result_text)
        
        # Добавляем статистику
        success_count = sum(1 for line in report if line.startswith("✅"))
        fail_count = sum(1 for line in report if line.startswith("❌"))
        await update.message.reply_text(f"📊 Итог: {success_count} успешно, {fail_count} с ошибками")
    else:
        await update.message.reply_text("❌ Не удалось обработать ни одного направления")

def main():
    """Основная функция запуска бота"""
    # Проверка переменных окружения
    if not TOKEN:
        logger.error("Не найден TELEGRAM_BOT_TOKEN в .env файле!")
        return
    
    if not LOGIN or not PASSWORD:
        logger.error("Не найдены SYSTEM_LOGIN или SYSTEM_PASSWORD в .env файле!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Обработчик текстовых сообщений (для направлений)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_direction))
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()