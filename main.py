import os
import json
import re
from tkinter import Tk, Label, Entry, Button, Text, Scrollbar, END, Frame
from tkinter.ttk import Notebook, Panedwindow
from telethon import TelegramClient
import asyncio
import openpyxl

# Загрузка конфигурации


def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()

API_ID = config["API_ID"]
API_HASH = config["API_HASH"]
PHONE_NUMBER = config["PHONE_NUMBER"]
DATA_FOLDER = config["DATA_FOLDER"]
LINKS_FILE = config["LINKS_FILE"]
ALLOWED_PHRASES_FILE = config["ALLOWED_PHRASES_FILE"]

message_links = {}

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Сохранение ссылок


def save_links():
    with open(LINKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(message_links, f, ensure_ascii=False, indent=4)

# Загрузка ссылок


def load_links():
    global message_links
    try:
        with open(LINKS_FILE, 'r', encoding='utf-8') as f:
            message_links = json.load(f)
    except FileNotFoundError:
        message_links = {}

# Разбор ссылки


def parse_link(link):
    match = re.match(r"https://t\.me/(\w+)/(\d+)", link)
    if match:
        return match.groups()
    else:
        raise ValueError("Некорректная ссылка")

# Асинхронная загрузка сообщений


async def fetch_messages(output_text):
    async with TelegramClient('session_name', API_ID, API_HASH) as client:
        output_text.delete(1.0, END)
        if not message_links:
            output_text.insert(END, 'Список ссылок пуст.')
            return

        try:
            for index, (name, link) in enumerate(message_links.items(), start=1):
                try:
                    username, message_id = parse_link(link)
                    entity = await client.get_entity(username)
                    message = await client.get_messages(entity, ids=int(message_id))
                    if message:
                        output_text.insert(
                            END, f"{index}. {name}({link}): \n{message.text}\n\n")
                    else:
                        output_text.insert(
                            END, f"{index}. {name}: Сообщение по ссылке {link} не найдено.\n\n")
                except ValueError as ve:
                    output_text.insert(
                        END, f"Ошибка с ссылкой {link}: {str(ve)}\n\n")
                except Exception as e:
                    output_text.insert(
                        END, f"Ошибка с ссылкой {link}: {str(e)}\n\n")
        except Exception as e:
            output_text.insert(END, f"Ошибка: {str(e)}")

# Добавление ссылки


def add_link():
    name = name_entry.get()
    link = channel_entry.get()
    if name and link:
        message_links[name] = link
        save_links()
        name_entry.delete(0, END)
        channel_entry.delete(0, END)
        show_links()

# Отображение ссылок


def show_links():
    list_text.delete(1.0, END)
    if message_links:
        for index, (name, link) in enumerate(message_links.items(), start=1):
            list_text.insert(END, f"{index}. {name}: {link}\n")
    else:
        list_text.insert(END, "Список ссылок пуст.\n")

# Удаление ссылки


def delete_link():
    try:
        number = int(delete_entry.get())
        if 1 <= number <= len(message_links):
            key_to_delete = list(message_links.keys())[number - 1]
            del message_links[key_to_delete]
            save_links()
            show_links()
            delete_entry.delete(0, END)
        else:
            list_text.insert(END, "\nОшибка: Некорректный номер ссылки.\n")
    except ValueError:
        list_text.insert(END, "\nОшибка: Введите корректный номер.\n")

# Обновление сообщений


def get_messages():
    output_text.delete(1.0, END)
    output_text.insert(END, 'Загрузка...\n')
    asyncio.run(fetch_messages(output_text))

# Сохранение допустимых фраз


def save_allowed_phrases():
    allowed_phrases = allowed_phrases_text.get(1.0, END).strip()
    if allowed_phrases:
        phrases_list = allowed_phrases.splitlines()
        with open(ALLOWED_PHRASES_FILE, 'w', encoding='utf-8') as f:
            json.dump(phrases_list, f, ensure_ascii=False, indent=4)
        output_text.insert(
            END, "\nСписок допустимых фраз сохранен в файл 'allowed_phrases.json'.\n")
    else:
        output_text.insert(END, "\nОшибка: Список фраз пуст.\n")

# Загрузка допустимых фраз


def load_allowed_phrases():
    try:
        with open(ALLOWED_PHRASES_FILE, 'r', encoding='utf-8') as f:
            phrases_list = json.load(f)
        return phrases_list
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Подготовка контента


def prepare_for_editing(content, allowed_phrases):
    result = []
    for line in content.splitlines():
        if any(phrase.lower() in line.lower() for phrase in allowed_phrases):
            line = line.replace("*", "")
            line = re.sub(r'\s*-\s*', '-', line)
            result.append(line)
    return '\n'.join(result)

# Обновление контента для редактирования


def prepare_and_update_output():
    allowed_phrases = load_allowed_phrases()
    allowed_phrases_text.delete(1.0, END)
    if allowed_phrases:
        allowed_phrases_text.insert(END, "\n".join(allowed_phrases))

    content = output_text.get(1.0, END)
    prepared_content = prepare_for_editing(content, allowed_phrases)
    output_text.delete(1.0, END)
    output_text.insert(END, prepared_content)

# Создание Excel файла с сообщениями


def create_excel():
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "Messages"
    sheet.append(["Название", "Текст сообщения"])

    for index, (name, link) in enumerate(message_links.items(), start=1):
        try:
            username, message_id = parse_link(link)
            with TelegramClient('session_name', API_ID, API_HASH) as client:
                entity = client.loop.run_until_complete(
                    client.get_entity(username))
                message = client.loop.run_until_complete(
                    client.get_messages(entity, ids=int(message_id)))
            if message:
                sheet.append([name, message.text])
        except Exception as e:
            output_text.insert(
                END, f"Ошибка при получении сообщения {name}: {e}\n")

    wb.save(os.path.join(DATA_FOLDER, "messages.xlsx"))

# Создание Excel файла Name-Price


def create_excel_name_price():
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "Name and Price"
    sheet.append(["Название", "Цена закупа"])

    content = output_text.get(1.0, END).strip()
    lines = content.splitlines()

    for line in lines:
        match = re.match(r"^(.*?)\s*-\s*(\d+[.,]?\d*)", line)
        if match:
            name = match.group(1).strip()
            price = match.group(2).replace(",", ".").strip()
            sheet.append([name, price])

    wb.save(os.path.join(DATA_FOLDER, "name_price.xlsx"))
    output_text.insert(END, "\nExcel файл 'name_price.xlsx' успешно создан.\n")

# Сохранение в текстовый файл


def save_to_txt():
    content = output_text.get(1.0, END).strip()
    if content:
        with open(os.path.join(DATA_FOLDER, "messages.txt"), 'w', encoding='utf-8') as f:
            f.write(content)
        output_text.insert(END, "\nФайл messages.txt успешно сохранен.\n")
    else:
        output_text.insert(
            END, "\nОшибка: Нет данных для сохранения в файл.\n")

# Отправка файлов в Telegram


def send_files_to_telegram():
    async def send_files():
        client = TelegramClient('session_name', API_ID, API_HASH)
        await client.start(PHONE_NUMBER)
        user = await client.get_entity('@uzalovgamid')

        messages_file = os.path.join(DATA_FOLDER, "messages.txt")
        excel_file = os.path.join(DATA_FOLDER, "name_price.xlsx")

        if os.path.exists(messages_file):
            await client.send_file(user, messages_file)
            output_text.insert(END, "\nФайл messages.txt отправлен.\n")
        if os.path.exists(excel_file):
            await client.send_file(user, excel_file)
            output_text.insert(END, "\nФайл name_price.xlsx отправлен.\n")
        await client.disconnect()

    asyncio.run(send_files())


load_links()

app = Tk()
app.title('Получение сообщений Telegram')
app.attributes('-fullscreen', True)
app.resizable(False, False)

notebook = Notebook(app)
notebook.pack(expand=True, fill='both')

main_frame = Frame(notebook)
notebook.add(main_frame, text='Главная')

paned_window_main = Panedwindow(main_frame, orient='horizontal')
paned_window_main.pack(fill='both', expand=True)

output_frame = Frame(paned_window_main)
paned_window_main.add(output_frame, weight=1)

Label(output_frame, text="Информация из постов:").pack(pady=5)
output_text = Text(output_frame, wrap='word', height=15, width=70)
output_text.pack(pady=5, padx=5, fill='both', expand=True)

scrollbar_main = Scrollbar(output_frame, command=output_text.yview)
output_text.config(yscrollcommand=scrollbar_main.set)

links_frame = Frame(notebook)
notebook.add(links_frame, text='Ссылки')

paned_window = Panedwindow(links_frame, orient='horizontal')
paned_window.pack(fill='both', expand=True)

left_frame = Frame(paned_window)
paned_window.add(left_frame, weight=1)

Label(left_frame, text="Список допустимых фраз:").pack(pady=5)
allowed_phrases_text = Text(left_frame, wrap='word', height=5, width=30)
allowed_phrases_text.pack(pady=5, padx=5, fill='both', expand=True)

Button(left_frame, text="Сохранить список фраз",
       command=save_allowed_phrases).pack(pady=5)

right_frame = Frame(paned_window)
paned_window.add(right_frame, weight=2)

Label(right_frame, text="Список ссылок:").pack(pady=5)

list_text = Text(right_frame, wrap='word', height=15, width=70)
list_text.pack(pady=5, padx=5, fill='both', expand=True)

scrollbar_links = Scrollbar(right_frame, command=list_text.yview)
list_text.config(yscrollcommand=scrollbar_links.set)

name_entry = Entry(right_frame, width=25)
name_entry.pack(side='left', padx=5)

channel_entry = Entry(right_frame, width=30)
channel_entry.pack(side='left', padx=5)

Button(right_frame, text='Добавить ссылку',
       command=add_link).pack(side='left', padx=5)

delete_entry = Entry(right_frame, width=10)
delete_entry.pack(side='left', padx=5)
Button(right_frame, text='Удалить ссылку',
       command=delete_link).pack(side='left', padx=5)

button_frame = Frame(main_frame)
button_frame.pack(side='bottom', fill='x', pady=10)

Button(button_frame, text="1. Обновить сообщения",
       command=get_messages).pack(side='left', padx=5)
Button(button_frame, text="2. Подготовить к редактированию",
       command=prepare_and_update_output).pack(side='left', padx=5)
Button(button_frame, text="3. Сохранить в TXT",
       command=save_to_txt).pack(side='left', padx=5)

Button(button_frame, text="4. Создать файл Name-Price",
       command=create_excel_name_price).pack(side='left', padx=5)

Button(button_frame, text="5. Отправить результат",
       command=send_files_to_telegram).pack(side='left', padx=5)

show_links()

allowed_phrases_list = load_allowed_phrases()
if allowed_phrases_list:
    allowed_phrases_text.insert(END, "\n".join(allowed_phrases_list))

app.mainloop()
