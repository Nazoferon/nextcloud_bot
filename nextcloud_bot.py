from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
from datetime import datetime
import logging

# Налаштування логування
logging.basicConfig(filename="webhook.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Створення FastAPI-додатка
app = FastAPI()

class NextcloudTalkBot:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth = ("Basic", (username, password))

    def send_message(self, room_id: str, message: str) -> bool:
        url = f"{self.base_url}/ocs/v2.php/apps/spreed/api/v1/chat/{room_id}"
        headers = {"OCS-APIRequest": "true", "Accept": "application/json"}
        data = {"message": message}
        response = requests.post(url, headers=headers, auth=self.auth, json=data)
        if response.status_code == 201:
            logging.info(f"Повідомлення відправлено: {message}")
            print(f"Повідомлення відправлено: {message}")
            return True
        logging.error(f"Помилка відправлення: {response.status_code}, текст: {response.text}")
        print(f"Помилка відправлення: {response.status_code}, текст: {response.text}")
        return False

    def process_command(self, message: str) -> str:
        if message.startswith("/help"):
            return "Доступні команди: /help, /time, /echo <текст>, /hello, /info"
        elif message.startswith("/time"):
            return f"Поточний час: {datetime.now().strftime('%H:%M:%S')}"
        elif message.startswith("/echo"):
            return message.replace("/echo", "").strip() or "Введіть текст для echo!"
        elif message.startswith("/hello"):
            return "Привіт! Я тестовий бот для Nextcloud Talk."
        elif message.startswith("/info"):
            return "Я бот, створений для практики в Таскомбанку. Версія 0.1."
        return None

BASE_URL = "https://cloud.tascombank.ua"
USERNAME = "usr-stud117"
PASSWORD = "ibRrg-LiQAy-qdKWq-njzEc-nZimp"

# Ініціалізація бота (розкоментуй після введення даних)
# bot = None
bot = NextcloudTalkBot(BASE_URL, USERNAME, PASSWORD)

class WebhookMessage(BaseModel):
    message: str
    roomId: str
    token: str

@app.post("/webhook")
async def handle_webhook(data: WebhookMessage):
    logging.info(f"Отримано: message={data.message}, roomId={data.roomId}, token={data.token}")
    print(f"Отримано: message={data.message}, roomId={data.roomId}, token={data.token}")
    if bot:
        message = data.message
        room_id = data.roomId
        if message.startswith("/"):
            response = bot.process_command(message)
            if response:
                bot.send_message(room_id, response)
        return {"status": "ok"}
    return {"status": "error", "message": "Bot not initialized"}

@app.get("/")
async def root():
    return {"message": "Webhook server for Nextcloud Talk Bot"}