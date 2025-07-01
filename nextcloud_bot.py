import requests
import json
import time
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup

class NextcloudTalkBot:
    def __init__(self, server_url, username, app_password):
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.app_password = app_password
        self.session = requests.Session()
        self.session.auth = (username, app_password)
        self.session.headers.update({
            'OCS-APIRequest': 'true',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.rooms = {}
        self.last_message_id = {}
        
    def get_rooms(self):
        """Отримати список кімнат"""
        url = f"{self.server_url}/ocs/v2.php/apps/spreed/api/v4/room"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                rooms = {}
                for room in data['ocs']['data']:
                    rooms[room['token']] = {
                        'name': room['displayName'],
                        'id': room['id']
                    }
                self.rooms = rooms
                return rooms
            else:
                print(f"Помилка отримання кімнат: {response.status_code}")
                print(response.text)
                return {}
        except Exception as e:
            print(f"Помилка підключення: {e}")
            return {}
    
    def find_room_by_name(self, room_name):
        """Знайти кімнату за назвою"""
        for token, room_info in self.rooms.items():
            if room_info['name'].lower() == room_name.lower():
                return token
        return None
    
    def get_messages(self, room_token, limit=50):
        """Отримати повідомлення з кімнати"""
        url = f"{self.server_url}/ocs/v2.php/apps/spreed/api/v1/chat/{room_token}"
        params = {
            'lookIntoFuture': 0,
            'limit': limit,
            'includeLastKnown': 1
        }
        
        try:
            response = self.session.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data['ocs']['data']
            else:
                print(f"Помилка отримання повідомлень: {response.status_code}")
                return []
        except Exception as e:
            print(f"Помилка: {e}")
            return []
    
    def send_message(self, room_token, message):
        """Надіслати повідомлення в кімнату"""
        url = f"{self.server_url}/ocs/v2.php/apps/spreed/api/v1/chat/{room_token}"
        data = {
            'message': message,
            'referenceId': hashlib.sha256(f"{message}{time.time()}".encode()).hexdigest()
        }
        
        try:
            response = self.session.post(url, json=data)
            if response.status_code == 201:
                print(f"✅ Повідомлення надіслано: {message}")
                return True
            else:
                print(f"❌ Помилка надсилання: {response.status_code}")
                print(response.text)
                return False
        except Exception as e:
            print(f"❌ Помилка: {e}")
            return False
    
    def get_tascombank_news(self, limit=5):
        """Отримати останні новини з сайту ТАСКОМБАНКУ"""
        try:
            url = "https://tascombank.ua/news"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            news_items = soup.select('.grid__col.grid__col--6-of-12')
            
            news_list = []
            for item in news_items[:limit]:
                title = item.select_one('.header-imp-news').get_text(strip=True)
                link = "https://tascombank.ua" + item.find('a')['href']
                image = "https://tascombank.ua" + item.find('img')['src'] if item.find('img') else None
                
                news_list.append({
                    'title': title,
                    'link': link,
                    'image': image
                })
            
            return news_list
        except Exception as e:
            print(f"❌ Помилка при отриманні новин: {e}")
            return []
    
    def get_exchange_rates(self):
        """Отримати курси валют ТАСКОМБАНКУ"""
        try:
            url = "https://tascombank.ua/api/currencies"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Основні валюти для відображення
            main_currencies = ['USD', 'EUR', 'PLN']
            rates = []
            
            # Обробляємо перший масив з курсами валют
            for currency in data[0]:
                if currency['short_name'] in main_currencies and currency['kurs_type'] == 'exchange':
                    rates.append({
                        'currency': currency['short_name'],
                        'buy': float(currency['kurs_buy']),
                        'sale': float(currency['kurs_sale']),
                        'type': currency['kurs_type_description']
                    })
            
            # Сортування за популярністю
            ordered_rates = []
            for code in main_currencies:
                for rate in rates:
                    if rate['currency'] == code:
                        ordered_rates.append(rate)
                        break
            
            return ordered_rates
        except Exception as e:
            print(f"❌ Помилка при отриманні курсів валют: {e}")
            return []
    
    def format_news_message(self, news_list):
        """Форматувати список новин у повідомлення для чату"""
        if not news_list:
            return "❌ Не вдалося отримати новини"
        
        message = "📰 **Останні новини ТАСКОМБАНКУ:**\n\n"
        for i, news in enumerate(news_list, 1):
            message += f"{i}. [{news['title']}]({news['link']})\n"
        
        message += "\nℹ️ Детальніше: https://tascombank.ua/news"
        return message
    
    def format_exchange_rates_message(self, rates):
        """Форматувати курси валют у повідомлення для чату"""
        if not rates:
            return "❌ Не вдалося отримати курси валют"
        
        message = "💱 **Курси валют ТАСКОМБАНКУ (Обмінний):**\n\n"
        message += "| Валюта | Купівля | Продаж |\n"
        message += "|--------|---------|--------|\n"
        
        for rate in rates:
            message += f"| {rate['currency']} | {rate['buy']:.2f} | {rate['sale']:.2f} |\n"
        
        message += "\nℹ️ Офіційний курс НБУ: https://bank.gov.ua"
        message += "\n🔄 Дані оновлено: " + datetime.now().strftime("%H:%M %d.%m.%Y")
        return message
    
    def process_command(self, message):
        """Обробка команд"""
        message = message.strip()
        
        if message == '/help':
            return """🤖 **Доступні команди:**
            • `/help` - показати це меню
            • `/time` - поточний час
            • `/echo [текст]` - повторити текст
            • `/hello` - привітання
            • `/info` - інформація про бота
            • `/news` - останні новини ТАСКОМБАНКУ
            • `/rates` - курси валют ТАСКОМБАНКУ"""
        
        elif message == '/time':
            current_time = datetime.now().strftime("%H:%M:%S %d.%m.%Y")
            return f"🕐 **Поточний час:** {current_time}"
        
        elif message.startswith('/echo '):
            text_to_echo = message[6:]  # Видаляємо '/echo '
            if text_to_echo:
                return f"📢 **Echo:** {text_to_echo}"
            else:
                return "❌ Використання: `/echo [ваш текст]`"
        
        elif message == '/hello':
            return "👋 **Привіт!** Я бот для Nextcloud Talk. Введіть `/help` для списку команд."
        
        elif message == '/info':
            return """ℹ️ **Інформація про бота:**
            • Версія: 1.2
            • Платформа: Nextcloud Talk
            • Статус: Активний ✅
            • Спеціальні функції:
              - Отримання новин ТАСКОМБАНКУ
              - Перегляд курсів валют"""
        
        elif message == '/news':
            news = self.get_tascombank_news(limit=5)
            return self.format_news_message(news)
        
        elif message == '/rates':
            rates = self.get_exchange_rates()
            return self.format_exchange_rates_message(rates)
        
        else:
            return None  # Команда не розпізнана
    
    def monitor_room(self, room_name):
        """Моніторинг кімнати та обробка команд"""
        print(f"🔍 Пошук кімнати '{room_name}'...")
        
        # Оновлюємо список кімнат
        rooms = self.get_rooms()
        if not rooms:
            print("❌ Не вдалося отримати список кімнат")
            return
        
        print(f"📋 Знайдено кімнат: {len(rooms)}")
        for token, info in rooms.items():
            print(f"  • {info['name']} (ID: {info['id']})")
        
        # Знаходимо потрібну кімнату
        room_token = self.find_room_by_name(room_name)
        if not room_token:
            print(f"❌ Кімнату '{room_name}' не знайдено")
            return
        
        print(f"✅ Знайдено кімнату: {room_name}")
        print(f"🚀 Починаю моніторинг кімнати...")
        print("💬 Напишіть команду в чаті (наприклад: /help)")
        print("⏹️  Натисніть Ctrl+C для зупинки\n")
        
        # Отримуємо початкові повідомлення
        initial_messages = self.get_messages(room_token, limit=5)
        if initial_messages:
            self.last_message_id[room_token] = initial_messages[0]['id']
        
        try:
            while True:
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
                    if message['actorType'] == 'users' and message['actorId'] == self.username:
                        msg_text = message['message']
                        print(f"📨 Отримано: {msg_text}")
                        
                        # Обробляємо команду
                        if msg_text.startswith('/'):
                            response = self.process_command(msg_text)
                            if response:
                                self.send_message(room_token, response)
                            else:
                                self.send_message(room_token, f"❓ Невідома команда: `{msg_text}`. Введіть `/help` для списку команд.")
                
                # Затримка перед наступною перевіркою
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n🛑 Бот зупинено користувачем")
        except Exception as e:
            print(f"\n❌ Помилка: {e}")

def main():
    # Налаштування
    print("🤖 Nextcloud Talk Bot")
    print("=" * 30)
    
    SERVER_URL = "https://cloud.tascombank.ua"
    USERNAME = input("Введіть ваш username: ").strip()
    APP_PASSWORD = input("Введіть App Password: ").strip()
    ROOM_NAME = input("Введіть назву кімнати (за замовчуванням 'test-bot'): ").strip() or "test-bot"
    
    print(f"\n🔗 Підключення до {SERVER_URL}")
    print(f"👤 Користувач: {USERNAME}")
    print(f"🏠 Кімната: {ROOM_NAME}")
    
    # Створюємо та запускаємо бота
    bot = NextcloudTalkBot(SERVER_URL, USERNAME, APP_PASSWORD)
    bot.monitor_room(ROOM_NAME)

if __name__ == "__main__":
    main()