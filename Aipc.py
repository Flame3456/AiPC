# -*- coding: utf-8 -*-
import customtkinter as ctk
import requests
import json
import sys
import os
import re
import subprocess
import tempfile
import tkinter as tk
from tkinter import messagebox

def enable_copy_paste(widget):
    widget.bind("<Control-c>", lambda e: widget.event_generate("<<Copy>>"))
    widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>"))
    widget.bind("<Control-x>", lambda e: widget.event_generate("<<Cut>>"))
    widget.bind("<Control-a>", lambda e: widget.event_generate("<<SelectAll>>"))

TRANSLATIONS = {
    "ru": {
        "title": "AI PC Assistant с Gemini",
        "send": "Отправить запрос в Gemini",
        "yes": "Да",
        "no": "Нет",
        "settings": "Настройки",
        "new_key": "Новый API ключ Gemini",
        "updated": "Ключ обновлён!",
        "done": "✔ Действия выполнены.",
        "no_code": "⚠ Нет кода для выполнения.",
        "cancelled": "Действия отменены.",
        "save": "Сохранить",
        "lang_saved_restart": "Язык сохранён. Перезапустите программу для применения."
    },
    "en": {
        "title": "AI PC Assistant with Gemini",
        "send": "Send request to Gemini",
        "yes": "Yes",
        "no": "No",
        "settings": "Settings",
        "new_key": "New Gemini API key",
        "updated": "Key updated!",
        "done": "✔ Actions completed.",
        "no_code": "⚠ No code to execute.",
        "save": "Save",
        "cancelled": "Actions cancelled.",
        "lang_saved_restart": "Language saved. Restart the app to apply."
    }
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BLOCKED_KEYWORDS = [
    "вирус", "virus", "trojan", "читер", "чит", "hack", "hacking",
    "exploit", "malware", "ransomware", "ddos", "sql injection"
]

def load_config():
    if os.path.exists(CONFIG_PATH):
        # если конфиг уже есть — читаем его
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # если конфиг отсутствует — создаём дефолт
        config = {"app_language": "en"}   # дефолтный язык — английский

        # окно для выбора языка и ввода ключа
        lang_win = ctk.CTk()
        lang_win.title("Setup")
        lang_var = tk.StringVar(value="en")   # по умолчанию English
        key_var = tk.StringVar()

        ctk.CTkLabel(lang_win, text="Choose language:").pack(pady=5)
        ctk.CTkRadioButton(lang_win, text="Русский", variable=lang_var, value="ru").pack(pady=5)
        ctk.CTkRadioButton(lang_win, text="English", variable=lang_var, value="en").pack(pady=5)

        ctk.CTkLabel(lang_win, text="Enter Gemini API key:").pack(pady=5)
        key_entry = ctk.CTkEntry(lang_win, textvariable=key_var, width=250)
        key_entry.pack(pady=5)
        enable_copy_paste(key_entry)

        def save_config():
            config["app_language"] = lang_var.get()
            config["gemini_api_key"] = key_var.get().strip()
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Info", TRANSLATIONS[lang_var.get()]["lang_saved_restart"])
            lang_win.destroy()

        ctk.CTkButton(lang_win, text=TRANSLATIONS["en"]["save"], fg_color="black", corner_radius=20, command=save_config).pack(pady=10)
        lang_win.mainloop()
        return config

CONFIG = load_config()
API_KEY = CONFIG.get("gemini_api_key")
APP_LANG = CONFIG.get("app_language", "en")


def normalize_text(text: str) -> str:
    text = text.lower()
    # заменяем похожие символы
    text = text.replace("1", "i").replace("!", "i").replace("$", "s").replace("@", "a")
    # убираем всё кроме букв/цифр
    text = re.sub(r"[^a-zа-я0-9]", "", text)
    return text


actions_code = ""
selected_language = "python"

def send_query():
    global actions_code, selected_language
    user_text = entry.get().strip()
    if not user_text:
        return

    # фильтр
    norm = normalize_text(user_text)
    for bad in BLOCKED_KEYWORDS:
        if bad in norm:
            text_box.delete("1.0", "end")
            text_box.insert("end", "⚠ Запрос заблокирован: обнаружено запрещённое слово.")
            return

    lang_choice = language_var.get()
    selected_language = lang_choice.lower()
    actions_code = ask_gemini(user_text, language=selected_language)
    text_box.delete("1.0", "end")
    text_box.insert("end", actions_code)

def confirm_yes():
    global actions_code
    if actions_code.strip():
        execute_generated_code(actions_code, selected_language)
        text_box.insert("end", f"\n\n{TRANSLATIONS[APP_LANG]['done']}")
    else:
        text_box.insert("end", f"\n\n{TRANSLATIONS[APP_LANG]['no_code']}")

def confirm_no():
    text_box.insert("end", f"\n\n{TRANSLATIONS[APP_LANG]['cancelled']}")

def change_key():
    global API_KEY
    new_key = key_entry.get().strip()
    if new_key:
        API_KEY = new_key
        CONFIG["gemini_api_key"] = API_KEY
        with open(CONFIG_PATH, "w") as f:
            json.dump(CONFIG, f, indent=4)
        status_label.configure(text=f"{TRANSLATIONS[APP_LANG]['updated']}\n{CONFIG_PATH}", text_color="green")

def open_settings():
    settings_win = ctk.CTkToplevel(app)
    settings_win.title(TRANSLATIONS[APP_LANG]["settings"])
    settings_win.geometry("300x200")
    lang_var = tk.StringVar(value=APP_LANG)

    ctk.CTkRadioButton(settings_win, text="Русский", variable=lang_var, value="ru").pack(pady=5)
    ctk.CTkRadioButton(settings_win, text="English", variable=lang_var, value="en").pack(pady=5)

    def save_lang():
        CONFIG["app_language"] = lang_var.get()
        with open(CONFIG_PATH, "w") as f:
            json.dump(CONFIG, f, indent=4)
        messagebox.showinfo("Info", TRANSLATIONS[APP_LANG]["lang_saved_restart"])
        settings_win.destroy()

    ctk.CTkButton(
        settings_win,
        text=TRANSLATIONS[APP_LANG]["save"],
        fg_color="black",
        corner_radius=20,
        command=save_lang
    ).pack(pady=10)


MODEL_LIST = [
    "gemini-2.0-flash",
    "gemini-2.0-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.5-flash"
]

def ask_gemini(user_query: str, language="python") -> str:
    prompt = f'Верни только готовый {language} код без комментариев и текста. Запрос: "{user_query}"'
    headers = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}
    last_error = None
    for model_name in MODEL_LIST:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            res_json = response.json()
            if "candidates" in res_json:
                result = res_json["candidates"][0]["content"]["parts"][0]["text"]
                # убираем блоки ```python ... ```
                if "```" in result:
                    parts = result.split("```")
                    if len(parts) >= 2:
                        result = parts[1].strip()
                # убираем лишнее слово "python" в начале
                if result.lower().startswith("python"):
                    result = result[len("python"):].strip()
                return result
            elif "error" in res_json:
                last_error = res_json["error"]
                continue
            else:
                last_error = res_json
                continue
        except Exception as e:
            last_error = str(e)
            continue
    return f"⚠ Не удалось получить код от Gemini. Последняя ошибка: {last_error}"

def execute_generated_code(code: str, language="python"):
    try:
        if language.lower() == "python":
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py", dir=BASE_DIR, encoding="utf-8") as f:
                f.write("# -*- coding: utf-8 -*-\n")
                f.write(code)
                temp_name = f.name
            result = subprocess.run(
                ["python", temp_name],
                shell=False,
                capture_output=True,
                text=True
            )
            os.remove(temp_name)
            # выводим stdout и stderr в text_box
            if result.stdout:
                text_box.insert("end", result.stdout)
            if result.stderr:
                text_box.insert("end", result.stderr)
        elif language.lower() == "powershell":
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".ps1", dir=BASE_DIR, encoding="utf-8") as f:
                f.write(code)
                temp_name = f.name
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_name],
                shell=False,
                capture_output=True,
                text=True
            )
            os.remove(temp_name)
            if result.stdout:
                text_box.insert("end", result.stdout)
            if result.stderr:
                text_box.insert("end", result.stderr)
        elif language.lower() in ["bat", "cmd"]:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".bat", dir=BASE_DIR, encoding="utf-8") as f:
                f.write(code)
                temp_name = f.name
            result = subprocess.run(
                temp_name,
                shell=True,
                capture_output=True,
                text=True
            )
            os.remove(temp_name)
            if result.stdout:
                text_box.insert("end", result.stdout)
            if result.stderr:
                text_box.insert("end", result.stderr)
    except Exception as e:
        text_box.insert("end", f"\nОшибка при выполнении кода: {e}")

app = ctk.CTk()
app.title(TRANSLATIONS[APP_LANG]["title"])
app.geometry("800x650")

# применяем иконку
icon_path = os.path.join(BASE_DIR, "ai pc.ico")
if os.path.exists(icon_path):
    app.iconbitmap(icon_path)

settings_button = ctk.CTkButton(app, text=TRANSLATIONS[APP_LANG]["settings"], fg_color="black", corner_radius=20, command=open_settings)
settings_button.pack(pady=5)

label_path = ctk.CTkLabel(app, text=f"{TRANSLATIONS[APP_LANG]['new_key']}: {CONFIG_PATH}")
label_path.pack(padx=10, pady=5)

entry = ctk.CTkEntry(app, placeholder_text=TRANSLATIONS[APP_LANG]["send"], width=600)
entry.pack(fill="x", padx=10, pady=10)
entry.focus()
enable_copy_paste(entry)

language_var = ctk.StringVar(value="Python")
lang_frame = ctk.CTkFrame(app)
lang_frame.pack(pady=5, fill="x", padx=10)
ctk.CTkRadioButton(lang_frame, text="Python", variable=language_var, value="Python").pack(side="left", padx=5)
ctk.CTkRadioButton(lang_frame, text="PowerShell", variable=language_var, value="PowerShell").pack(side="left", padx=5)
ctk.CTkRadioButton(lang_frame, text="BAT", variable=language_var, value="BAT").pack(side="left", padx=5)

send_button = ctk.CTkButton(app, text=TRANSLATIONS[APP_LANG]["send"], command=send_query)
send_button.pack(pady=5)

text_box = ctk.CTkTextbox(app, width=760, height=300)
text_box.pack(padx=10, pady=10)
enable_copy_paste(text_box)

class TextRedirector:
    def __init__(self, widget):
        self.widget = widget
    def write(self, string):
        self.widget.insert("end", string)
        self.widget.see("end")
    def flush(self):
        pass


sys.stdout = TextRedirector(text_box)
sys.stderr = TextRedirector(text_box)

frame = ctk.CTkFrame(app)
frame.pack(pady=10)
yes_btn = ctk.CTkButton(frame, text=TRANSLATIONS[APP_LANG]["yes"], fg_color="green", command=confirm_yes)
yes_btn.grid(row=0, column=0, padx=10)
no_btn = ctk.CTkButton(frame, text=TRANSLATIONS[APP_LANG]["no"], fg_color="red", command=confirm_no)
no_btn.grid(row=0, column=1)

key_frame = ctk.CTkFrame(app)
key_frame.pack(pady=10, fill="x", padx=10)

key_entry = ctk.CTkEntry(key_frame, placeholder_text=TRANSLATIONS[APP_LANG]["new_key"], width=500)
key_entry.pack(side="left", fill="x", expand=True, padx=5)

key_button = ctk.CTkButton(key_frame, text=TRANSLATIONS[APP_LANG]["settings"], command=change_key)
key_button.pack(side="left", padx=5)

status_label = ctk.CTkLabel(app, text="")
status_label.pack(pady=5)

enable_copy_paste(entry)
enable_copy_paste(text_box)
enable_copy_paste(key_entry)

app.mainloop()