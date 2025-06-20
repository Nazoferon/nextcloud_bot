import requests
import json
import time
import hashlib
from datetime import datetime
import logging

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class NextcloudTalkBot:
    def __init__(self, server_url, username, app_password, debug=True):
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.app_password = app_password
        self.debug = debug
        self.session = requests.Session()
        self.session.auth = (username, app_password)
        self.session.headers.update({
            'OCS-APIRequest': 'true',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.rooms = {}
        self.last_message_id = {}
        
        logger.info(f"🤖 Ініціалізація бота для сервера: {self.server_url}")
        logger.info(f"👤 Користувач: {self.username}")
        
    def log_json_response(self, operation, response):
        """Логування JSON відповідей для демонстрації"""
        if self.debug and response.status_code == 200:
            try:
                data = response.json()
                logger.info(f"📋 {operation} - JSON Response:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                logger.info("=" * 50)
            except:
                logger.warning(f"⚠️ Не вдалося розпарсити JSON для {operation}")
    
    def get_rooms(self):
        """Отримати список кімнат"""
        url = f"{self.server_url}/ocs/v2.php/apps/spreed/api/v4/room"
        logger.info(f"🔍 Запит списку кімнат: GET {url}")
        
        try:
            response = self.session.get(url)
            logger.info(f"📡 HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                self.log_json_response("GET_ROOMS", response)
                
                data = response.json()
                rooms = {}
                for room in data['ocs']['data']:
                    rooms[room['token']] = {
                        'name': room['displayName'],
                        'id': room['id']
                    }
                self.rooms = rooms
                
                logger.info(f"✅ Знайдено кімнат: {len(rooms)}")
                for token, room_info in rooms.items():
                    logger.info(f"  📁 {room_info['name']} (ID: {room_info['id']}, Token: {token[:8]}...)")
                
                return rooms
            else:
                logger.error(f"❌ Помилка отримання кімнат: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return {}
        except Exception as e:
            logger.error(f"💥 Помилка підключення: {e}")
            return {}
    
    def find_room_by_name(self, room_name):
        """Знайти кімнату за назвою"""
        logger.info(f"🔎 Пошук кімнати: '{room_name}'")
        for token, room_info in self.rooms.items():
            if room_info['name'].lower() == room_name.lower():
                logger.info(f"✅ Кімнату знайдено: {room_info['name']} (Token: {token[:8]}...)")
                return token
        logger.warning(f"❌ Кімнату '{room_name}' не знайдено")
        return None
    
    def get_messages(self, room_token, limit=50):
        """Отримати повідомлення з кімнати"""
        url = f"{self.server_url}/ocs/v2.php/apps/spreed/api/v1/chat/{room_token}"
        params = {
            'lookIntoFuture': 0,
            'limit': limit,
            'includeLastKnown': 1
        }
        
        logger.debug(f"📨 Запит повідомлень: GET {url}")
        logger.debug(f"Parameters: {params}")
        
        try:
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                if self.debug:
                    self.log_json_response("GET_MESSAGES", response)
                
                data = response.json()
                messages = data['ocs']['data']
                logger.info(f"📬 Отримано повідомлень: {len(messages)}")
                return messages
            else:
                logger.error(f"❌ Помилка отримання повідомлень: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"💥 Помилка: {e}")
            return []
    
    def send_message(self, room_token, message):
        """Надіслати повідомлення в кімнату"""
        url = f"{self.server_url}/ocs/v2.php/apps/spreed/api/v1/chat/{room_token}"
        reference_id = hashlib.sha256(f"{message}{time.time()}".encode()).hexdigest()
        data = {
            'message': message,
            'referenceId': reference_id
        }
        
        logger.info(f"📤 Відправка повідомлення: {message}")
        logger.debug(f"POST {url}")
        logger.debug(f"Data: {json.dumps(data, ensure_ascii=False)}")
        
        try:
            response = self.session.post(url, json=data)
            logger.info(f"📡 HTTP Status: {response.status_code}")
            
            if response.status_code == 201:
                if self.debug:
                    self.log_json_response("SEND_MESSAGE", response)
                logger.info(f"✅ Повідомлення надіслано успішно")
                return True
            else:
                logger.error(f"❌ Помилка надсилання: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"💥 Помилка: {e}")
            return False
    
    def process_command(self, message):
        """Обробка команд"""
        message = message.strip()
        logger.info(f"⚙️ Обробка команди: {message}")
        
        if message == '/help':
            response = """🤖 **Доступні команди:**
• `/help` - показати це меню
• `/time` - поточний час
• `/echo [текст]` - повторити текст
• `/hello` - привітання
• `/info` - інформація про бота
• `/debug on/off` - увімкнути/вимкнути debug режим"""
            logger.info("📋 Команда /help - показую список команд")
            return response
        
        elif message == '/time':
            current_time = datetime.now().strftime("%H:%M:%S %d.%m.%Y")
            response = f"🕐 **Поточний час:** {current_time}"
            logger.info(f"⏰ Команда /time - {current_time}")
            return response
        
        elif message.startswith('/echo '):
            text_to_echo = message[6:]  # Видаляємо '/echo '
            if text_to_echo:
                response = f"📢 **Echo:** {text_to_echo}"
                logger.info(f"🔊 Команда /echo - повторюю: {text_to_echo}")
                return response
            else:
                logger.warning("⚠️ Команда /echo без тексту")
                return "❌ Використання: `/echo [ваш текст]`"
        
        elif message == '/hello':
            response = "👋 **Привіт!** Я тестовий бот для Nextcloud Talk. Введіть `/help` для списку команд."
            logger.info("👋 Команда /hello - вітаю користувача")
            return response
        
        elif message == '/info':
            response = f"""ℹ️ **Інформація про бота:**
• Версія: 1.0 (Test)
• Платформа: Nextcloud Talk
• Статус: Активний ✅
• Сервер: {self.server_url}
• Користувач: {self.username}
• Debug режим: {'Увімкнено' if self.debug else 'Вимкнено'}
• Створено для тестування API"""
            logger.info("ℹ️ Команда /info - показую інформацію про бота")
            return response
        
        elif message == '/debug on':
            self.debug = True
            logger.info("🔧 Debug режим увімкнено")
            return "🔧 **Debug режим увімкнено**"
        
        elif message == '/debug off':
            self.debug = False
            logger.info("🔧 Debug режим вимкнено")
            return "🔧 **Debug режим вимкнено**"
        
        else:
            logger.warning(f"❓ Невідома команда: {message}")
            return None  # Команда не розпізнана
    
    def monitor_room(self, room_name):
        """Моніторинг кімнати та обробка команд"""
        logger.info("=" * 60)
        logger.info("🚀 ПОЧАТОК МОНІТОРИНГУ КІМНАТИ")
        logger.info("=" * 60)
        
        # Оновлюємо список кімнат
        rooms = self.get_rooms()
        if not rooms:
            logger.error("❌ Не вдалося отримати список кімнат. Завершення роботи.")
            return
        
        # Знаходимо потрібну кімнату
        room_token = self.find_room_by_name(room_name)
        if not room_token:
            logger.error(f"❌ Кімнату '{room_name}' не знайдено. Завершення роботи.")
            return
        
        logger.info("=" * 60)
        logger.info(f"✅ Підключено до кімнати: {room_name}")
        logger.info(f"🎯 Token кімнати: {room_token[:8]}...")
        logger.info("💬 Очікую команди... (Ctrl+C для зупинки)")
        logger.info("=" * 60)
        
        # Отримуємо початкові повідомлення
        initial_messages = self.get_messages(room_token, limit=5)
        if initial_messages:
            self.last_message_id[room_token] = initial_messages[0]['id']
            logger.info(f"📌 Останнє повідомлення ID: {self.last_message_id[room_token]}")
        
        try:
            while True:
                logger.debug("🔄 Перевіряю нові повідомлення...")
                
                # Отримуємо нові повідомлення
                messages = self.get_messages(room_token, limit=10)
                
                # Обробляємо тільки нові повідомлення
                new_messages = []
                if room_token in self.last_message_id:
                    for msg in messages:
                        if msg['id'] > self.last_message_id[room_token]:
                            new_messages.append(msg)
                else:
                    new_messages = messages[:1] if messages else []
                
                # Оновлюємо ID останнього повідомлення
                if messages:
                    self.last_message_id[room_token] = messages[0]['id']
                
                # Обробляємо нові повідомлення
                for message in reversed(new_messages):  # Обробляємо від старших до новіших
                    if message['actorType'] == 'users' and message['actorId'] != self.username:
                        msg_text = message['message']
                        actor = message['actorDisplayName']
                        timestamp = message['timestamp']
                        
                        logger.info("=" * 40)
                        logger.info(f"📨 НОВЕ ПОВІДОМЛЕННЯ")
                        logger.info(f"👤 Від: {actor} ({message['actorId']})")
                        logger.info(f"⏰ Час: {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")
                        logger.info(f"💬 Текст: {msg_text}")
                        logger.info("=" * 40)
                        
                        # Обробляємо команду
                        if msg_text.startswith('/'):
                            response = self.process_command(msg_text)
                            if response:
                                self.send_message(room_token, response)
                            else:
                                error_msg = f"❓ Невідома команда: `{msg_text}`. Введіть `/help` для списку команд."
                                logger.warning(f"Надсилаю повідомлення про помилку")
                                self.send_message(room_token, error_msg)
                        else:
                            logger.info("ℹ️ Повідомлення не є командою (не починається з '/')")
                
                # Затримка перед наступною перевіркою
                time.sleep(3)
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info("🛑 БОТ ЗУПИНЕНО КОРИСТУВАЧЕМ")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"\n💥 КРИТИЧНА ПОМИЛКА: {e}")
            logger.error("=" * 60)

def main():
    print("🤖 Nextcloud Talk Bot v1.0 (Test)")
    print("=" * 50)
    
    SERVER_URL = "https://cloud.tascombank.ua"
    USERNAME = input("Введіть ваш username: ").strip()
    APP_PASSWORD = input("Введіть App Password: ").strip()
    ROOM_NAME = input("Введіть назву кімнати (за замовчуванням 'test-bot'): ").strip() or "test-bot"
    
    print(f"\n🔗 Підключення до {SERVER_URL}")
    print(f"👤 Користувач: {USERNAME}")
    print(f"🏠 Кімната: {ROOM_NAME}")
    print(f"🔧 Debug режим: Увімкнено")
    print("=" * 50)
    
    # Створюємо та запускаємо бота
    bot = NextcloudTalkBot(SERVER_URL, USERNAME, APP_PASSWORD, debug=True)
    bot.monitor_room(ROOM_NAME)

if __name__ == "__main__":
    main()