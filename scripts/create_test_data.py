# create_test_data.py
# Скрипт для создания Excel файла с данными пользователей

import os
from openpyxl import Workbook


def create_test_excel(file_path=None):
    if file_path is None:
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", "users.xlsx")
    """Создает Excel файл с пользователями."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    # Заголовки столбцов
    ws.append(["Name", "Email", "Interests", "Sentiment Filter"])

    # Данные пользователей
    # Interests: оставьте пустым или "default" чтобы получить все новости без фильтра
    # Sentiment Filter: "<4", ">7", ">=5", "<=3" или пустое (без фильтра)
    users = [
        ["Student", "student@example.com", "iqtisodiyot", "<4"],
        ["Azam", "azam@example.com", "iqtisodiyot", "<4"],
    ]

    for user in users:
        ws.append(user)

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20

    wb.save(file_path)
    print(f"[OK] Файл '{file_path}' создан с {len(users)} пользователями!")


if __name__ == "__main__":
    create_test_excel()

