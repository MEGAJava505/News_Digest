# main.py
# Автоматическая отправка Email с новостями kun.uz + сентимент-анализ

import os
import smtplib
import feedparser
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openpyxl import load_workbook
from deep_translator import GoogleTranslator
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Загружаем переменные из .env файла
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)


# ─────────────────────────────────────────────
# Класс 1: ExcelFile — чтение данных из Excel
# ─────────────────────────────────────────────
class ExcelFile:
    """Читает данные пользователей из Excel файла."""

    def __init__(self, file_path):
        self.file_path = file_path

    def get_data(self):
        """Возвращает список словарей с данными пользователей.

        Ключи: 'name', 'email', 'interests', 'sentiment_filter'.
        """
        wb = load_workbook(self.file_path)
        ws = wb.active

        users = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            row_data = list(row) + [""] * (4 - len(row))  # Дополняем до 4 столбцов
            name, email, interests, sent_filter = row_data[0], row_data[1], row_data[2], row_data[3]

            if name and email:
                interests_str = str(interests).strip() if interests else ""
                if interests_str.lower() in ("", "none", "default"):
                    interests_str = ""

                sent_filter_str = str(sent_filter).strip() if sent_filter else ""

                users.append({
                    "name": name,
                    "email": email,
                    "interests": interests_str,
                    "sentiment_filter": sent_filter_str,
                })

        wb.close()
        return users


# ─────────────────────────────────────────────
# Класс 2: NewsFeed — новости с kun.uz RSS
# ─────────────────────────────────────────────
class NewsFeed:
    """Получает реальные новости с kun.uz через RSS."""

    RSS_URL = "https://kun.uz/news/rss"

    # Маппинг категорий (кириллица из RSS -> латиница для фильтрации)
    CATEGORY_MAP = {
        # Кириллица (как приходит из RSS)
        "\u040e\u0437\u0431\u0435\u043a\u0438\u0441\u0442\u043e\u043d": "uzbekiston",
        "\u0416\u0430\u04b3\u043e\u043d": "jahon",
        "\u0416\u0430\u043c\u0438\u044f\u0442": "jamiyat",
        "\u0421\u043f\u043e\u0440\u0442": "sport",
        "\u0410\u0432\u0442\u043e": "avto",
        "\u041a\u045e\u0447\u043c\u0430\u0441 \u043c\u0443\u043b\u043a": "kuchmas mulk",
        "\u0418\u049b\u0442\u0438\u0441\u043e\u0434\u0438\u0451\u0442": "iqtisodiyot",
        "\u0422\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0438\u044f": "texnologiya",
    }

    def __init__(self):
        self._feed = None

    def _load(self):
        """Загружает RSS ленту kun.uz."""
        if self._feed is None:
            print("[1] Zagrujayu novosti s kun.uz...")
            self._feed = feedparser.parse(self.RSS_URL)
            print(f"    Naideno novostei: {len(self._feed.entries)}")
        return self._feed

    def _normalize_category(self, category):
        """Приводит категорию к нижнему регистру латиницы."""
        if not category:
            return ""
        mapped = self.CATEGORY_MAP.get(category, category)
        return mapped.lower().strip()

    def _get_image(self, url):
        """Извлекает URL картинки статьи через og:image."""
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                return og["content"]
        except Exception:
            pass
        return ""

    def data(self):
        """Возвращает все новости без фильтра."""
        feed = self._load()
        news_list = []

        for entry in feed.entries:
            category_raw = entry.get("category", "")
            url = entry.get("link", "")
            news_list.append({
                "title": entry.get("title", "").rstrip("."),
                "description": entry.get("description", "").rstrip("."),
                "url": url,
                "pub_date": entry.get("published", ""),
                "category": category_raw,
                "category_normalized": self._normalize_category(category_raw),
                "image_url": "",  # Заполним позже для выбранных новостей
            })

        return news_list

    def get(self, topic, limit=3):
        """Возвращает новости по теме. Если topic пустой — все новости.
        Ограничивает количество до limit (по умолчанию 3)."""
        all_news = self.data()

        if not topic:
            return all_news[:limit]

        topic_lower = topic.lower().strip()
        filtered = [n for n in all_news if topic_lower in n["category_normalized"]]

        if filtered:
            return filtered[:limit]

        # Фолбэк: поиск по заголовку и описанию
        filtered = [
            n for n in all_news
            if topic_lower in n["title"].lower() or topic_lower in n["description"].lower()
        ]

        return filtered[:limit] if filtered else all_news[:limit]


# ─────────────────────────────────────────────
# Класс 3: SentimentAnalyzer — анализ тональности
# ─────────────────────────────────────────────
class SentimentAnalyzer:
    """Переводит узбекский текст на английский и анализирует тональность."""

    def __init__(self):
        self.translator = GoogleTranslator(source="uz", target="en")
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text):
        """Анализирует тональность текста.

        Args:
            text: Текст на узбекском языке.

        Returns:
            Словарь с ключами: score, label, css_class, bar_width.
        """
        try:
            # Переводим на английский
            en_text = self.translator.translate(text)
        except Exception:
            en_text = text  # Если перевод не удался, анализируем как есть

        # Анализируем через VADER
        scores = self.analyzer.polarity_scores(en_text)
        compound = scores["compound"]

        # Преобразуем compound (-1..1) в score (0..10)
        score = round((compound + 1) * 5, 1)
        bar_width = int(score * 10)

        # Определяем label и CSS класс
        if compound >= 0.05:
            label = "Positive"
            label_uz = "Ijobiy"
            css_class = "positive"
            bar_color = "#6BBF8A"
        elif compound <= -0.05:
            label = "Negative"
            label_uz = "Salbiy"
            css_class = "negative"
            bar_color = "#D4706A"
        else:
            label = "Neutral"
            label_uz = "Neytral"
            css_class = "neutral"
            bar_color = "#E0B866"

        return {
            "score": score,
            "label": label,
            "label_uz": label_uz,
            "css_class": css_class,
            "bar_width": bar_width,
            "bar_color": bar_color,
        }


# ─────────────────────────────────────────────
# Класс 4: Email — формирование и отправка HTML письма
# ─────────────────────────────────────────────
class Email:
    """Формирует и отправляет HTML email."""

    def __init__(self, sender, receiver, subject, html_body):
        self.sender = sender
        self.receiver = receiver
        self.subject = subject
        self.html_body = html_body

    def send(self, smtp_server, smtp_port, password):
        """Отправляет HTML email через SMTP."""
        msg = MIMEMultipart("alternative")
        msg["From"] = self.sender
        msg["To"] = self.receiver
        msg["Subject"] = self.subject
        msg.attach(MIMEText(self.html_body, "html", "utf-8"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(self.sender, password)
            server.send_message(msg)


# ─────────────────────────────────────────────
# Настройки SMTP серверов
# ─────────────────────────────────────────────
SMTP_SERVERS = {
    "gmail": {"server": "smtp.gmail.com", "port": 587},
    "yandex": {"server": "smtp.yandex.ru", "port": 587},
    "mail.ru": {"server": "smtp.mail.ru", "port": 587},
    "outlook": {"server": "smtp-mail.outlook.com", "port": 587},
}


# ─────────────────────────────────────────────
# Фильтр по сентименту
# ─────────────────────────────────────────────
import re

def _apply_sentiment_filter(news_list, filter_str):
    """Фильтрует новости по sentiment score.

    Поддерживает: '<4', '>7', '<=3', '>=5', '=5'.
    """
    match = re.match(r'^([<>]=?|=)\s*(\d+\.?\d*)$', filter_str.strip())
    if not match:
        return news_list  # Неверный формат — не фильтруем

    op, value = match.group(1), float(match.group(2))

    ops = {
        '<': lambda s: s < value,
        '>': lambda s: s > value,
        '<=': lambda s: s <= value,
        '>=': lambda s: s >= value,
        '=': lambda s: s == value,
    }

    check = ops.get(op)
    if not check:
        return news_list

    return [n for n in news_list if check(n["sentiment"]["score"])]


# ─────────────────────────────────────────────
# Главный блок
# ─────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  KUN.UZ NEWS DIGEST + SENTIMENT ANALYSIS")
    print("=" * 50)

    # -- Nastroiki iz .env --
    sender_email = os.getenv("SENDER_EMAIL")
    app_password = os.getenv("APP_PASSWORD")
    service = os.getenv("SMTP_SERVICE", "gmail").lower()

    if not sender_email or not app_password:
        print("[OSHIBKA] V faile .env ne ukazany SENDER_EMAIL i APP_PASSWORD!")
        return

    smtp_config = SMTP_SERVERS.get(service)
    if not smtp_config:
        print(f"[OSHIBKA] Neizvestnyi servis '{service}'!")
        return

    print(f"\n    Otpravitel: {sender_email}")
    print(f"    Servis: {service}")

    # -- Chitaem Excel --
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "users.xlsx")
    try:
        excel = ExcelFile(file_path)
        users = excel.get_data()
    except FileNotFoundError:
        print(f"[OSHIBKA] Fail '{file_path}' ne naiden!")
        return
    except Exception as e:
        print(f"[OSHIBKA] Ne udalos prochitat fail: {e}")
        return

    if not users:
        print("[OSHIBKA] V faile net dannykh polzovatelei!")
        return

    print(f"    Polzovatelei: {len(users)}")

    # -- Zagruzhaem novosti --
    news_feed = NewsFeed()
    sentiment = SentimentAnalyzer()

    # -- Podgotavlivaem Jinja2 shablon --
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("template.html")

    today = datetime.now().strftime("%d.%m.%Y")
    edition = datetime.now().strftime("%B %Y")

    # Визуальные стили для карточек (чередуются)
    card_styles = [
        {
            "gradient_start": "#D4E8D4", "gradient_end": "#A8CCA8",
            "icon_bg": "rgba(107,191,138,0.2)", "icon": "&#9889;",
        },
        {
            "gradient_start": "#EDE8D4", "gradient_end": "#D4CBA8",
            "icon_bg": "rgba(224,184,102,0.2)", "icon": "&#9733;",
        },
        {
            "gradient_start": "#D4DEE8", "gradient_end": "#A8B8CC",
            "icon_bg": "rgba(120,150,190,0.2)", "icon": "&#9672;",
        },
    ]

    # Стили категорий
    cat_styles = {
        "positive": "color:#3D7A50; background:#E8F5EC; border:1px solid #C8E8D0;",
        "neutral": "color:#9B8A4A; background:#FBF8EE; border:1px solid #E8DDB8;",
        "negative": "color:#A84040; background:#FBF0EE; border:1px solid #E8C8C8;",
    }

    # -- Otpravlyaem pisma --
    print("\n[2] Analiz tonalnosti i otpravka...\n")
    sent = 0
    errors = 0

    for user in users:
        name = user["name"]
        email_addr = user["email"]
        topic = user["interests"]
        has_filter = bool(user["sentiment_filter"])

        # Загружаем все доступные новости для этой темы (лимит большой, чтобы получить все)
        fetch_limit = 100
        news_list = news_feed.get(topic, limit=fetch_limit)
        if not news_list:
            print(f"  [!] Dlya '{name}' novosti ne naideny, propuskayu")
            continue

        # Sentiment-analiz + zagruzka kartinok
        print(f"  Analiziruyu {len(news_list)} novostei dlya {name}...")
        for i, news in enumerate(news_list):
            full_text = f"{news['title']}. {news['description']}"
            news["sentiment"] = sentiment.analyze(full_text)

            # Загружаем реальную картинку статьи
            print(f"    [{i+1}/{len(news_list)}] score={news['sentiment']['score']} | {news['title'][:45]}...")
            news["image_url"] = news_feed._get_image(news["url"])
            news["category_style"] = cat_styles.get(news["sentiment"]["css_class"], cat_styles["neutral"])

        # Применяем фильтр по сентименту
        sent_filter = user["sentiment_filter"]
        if sent_filter:
            news_list = _apply_sentiment_filter(news_list, sent_filter)
            print(f"    Filtr '{sent_filter}': ostalos {len(news_list)} novostei")
            if not news_list:
                print(f"  [!] Posle filtra ne ostalos novostei dlya {name}, propuskayu")
                continue

        # Renderim HTML
        html = template.render(
            user_name=name,
            date=today,
            edition=edition,
            news_count=len(news_list),
            news_list=news_list,
        )

        subject = f"The Brief - {len(news_list)} ta yangilik ({datetime.now().strftime('%d.%m.%Y')})"

        # Otpravlyaem
        try:
            email_msg = Email(
                sender=sender_email,
                receiver=email_addr,
                subject=subject,
                html_body=html,
            )
            email_msg.send(
                smtp_server=smtp_config["server"],
                smtp_port=smtp_config["port"],
                password=app_password,
            )
            sent += 1
            print(f"  [OK] {name} ({email_addr}) - otpravleno!")
        except Exception as e:
            errors += 1
            print(f"  [OSHIBKA] {name} ({email_addr}) - {e}")

    # Itogi
    print("\n" + "=" * 50)
    print(f"  ITOGO: otpravleno {sent}, oshibok {errors}")
    print("=" * 50)


if __name__ == "__main__":
    main()
