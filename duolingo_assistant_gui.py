import os
import threading
import requests
from google import genai

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label

import arabic_reshaper
from bidi.algorithm import get_display

# =========================
# دانلود و ثبت فونت فارسی (فقط بار اول)
# =========================

FONT_PATH = "/data/user/0/ru.iiec.pydroid3/app_HOME/Vazirmatn-Regular.ttf"
FONT_URL = "https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/fonts/ttf/Vazirmatn-Regular.ttf"

if not os.path.exists(FONT_PATH):
    try:
        r = requests.get(FONT_URL, timeout=20)
        with open(FONT_PATH, "wb") as f:
            f.write(r.content)
    except Exception:
        pass

if os.path.exists(FONT_PATH):
    LabelBase.register(name="Vazir", fn_regular=FONT_PATH)
    FONT_NAME = "Vazir"
else:
    FONT_NAME = "Roboto"


def fa(text):
    """تبدیل متن فارسی به شکل درست برای نمایش در Kivy"""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def clean_markdown(text):
    """حذف نشانه‌های مارک‌داون که در نمایش ساده زشت به نظر می‌رسند"""
    text = text.replace("**", "")
    text = text.replace("###", "")
    text = text.replace("##", "")
    text = text.replace("# ", "")
    text = text.replace("---", "")
    text = text.replace("* ", "• ")
    return text


# =========================
# کلیدهای API
# =========================

ocr_api_key = "K82348133188957"
gemini_api_key = "AQ.Ab8RN6KOaCbV0sz9U5ZnYCglbUZ9kevb0vXWy434_vYasCxkzg"

screenshots_folder = "/storage/emulated/0/DCIM/Screenshots"
image_extensions = (".jpg", ".jpeg", ".png", ".webp")


def find_latest_duolingo_screenshot():
    files_list = []
    for filename in os.listdir(screenshots_folder):
        full_path = os.path.join(screenshots_folder, filename)
        if (
            os.path.isfile(full_path)
            and filename.lower().endswith(image_extensions)
            and "duolingo" in filename.lower()
        ):
            files_list.append(full_path)

    if not files_list:
        return None

    return max(files_list, key=os.path.getmtime)


def run_ocr(image_path):
    url = "https://api.ocr.space/parse/image"
    with open(image_path, "rb") as image_file:
        files = {"file": image_file}
        data = {"apikey": ocr_api_key, "language": "ger"}
        result = requests.post(url, files=files, data=data, timeout=30)

    ocr_result = result.json()

    if "ParsedResults" not in ocr_result or not ocr_result["ParsedResults"]:
        return None

    return ocr_result["ParsedResults"][0]["ParsedText"]


def ask_gemini(ocr_text):
    client = genai.Client(api_key=gemini_api_key)

    prompt = (
        "این متن از یک صفحه درس آلمانی در دولینگو استخراج شده:\n\n"
        + ocr_text
        + """

لطفاً به فارسی و خیلی ساده توضیح بده:

1. معنی جمله یا کلمات چیست؟
2. هر کلمه مهم را جداگانه معنی کن.
3. اگر جمله وجود دارد، ساختار جمله را توضیح بده.
4. نکته گرامری مهم را ساده توضیح بده.
5. تلفظ آلمانی کلمات مهم را با حروف فارسی بنویس.

توضیحات برای یک زبان‌آموز مبتدی باشد.

مهم: پاسخ را فقط با متن ساده فارسی بنویس. از نشانه‌های مارک‌داون مثل ستاره (*)، پوند (#) یا خط تیره (---) برای تیتر یا بولد کردن استفاده نکن. اگر لازم است لیست بنویسی، فقط از خط جدید و شماره استفاده کن.
"""
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return response.text


class DuolingoAssistantApp(App):
    def build(self):
        self.root_layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        title = Label(
            text=fa("دستیار آلمانی من"),
            font_name=FONT_NAME,
            size_hint=(1, 0.1),
            font_size="22sp",
        )

        self.analyze_button = Button(
            text=fa("تحلیل آخرین اسکرین‌شات"),
            font_name=FONT_NAME,
            size_hint=(1, 0.1),
            font_size="18sp",
        )
        self.analyze_button.bind(on_press=self.on_analyze_pressed)

        self.scroll = ScrollView(size_hint=(1, 0.8))
        self.result_label = Label(
            text=fa("برای شروع، یک اسکرین‌شات از دولینگو بگیرید و دکمه بالا را بزنید."),
            font_name=FONT_NAME,
            size_hint_y=None,
            halign="right",
            valign="top",
            font_size="16sp",
        )
        self.result_label.bind(
            width=lambda *x: self.result_label.setter("text_size")(
                self.result_label, (self.result_label.width, None)
            )
        )
        self.result_label.bind(
            texture_size=lambda *x: setattr(
                self.result_label, "height", self.result_label.texture_size[1]
            )
        )
        self.scroll.add_widget(self.result_label)

        self.root_layout.add_widget(title)
        self.root_layout.add_widget(self.analyze_button)
        self.root_layout.add_widget(self.scroll)

        return self.root_layout

    def set_result_text(self, text):
        self.result_label.text = fa(text)

    def on_analyze_pressed(self, instance):
        self.analyze_button.disabled = True
        self.set_result_text("در حال پیدا کردن آخرین اسکرین‌شات...")

        # اجرای کارهای اینترنتی در یک ترد جدا تا صفحه قفل نشود
        thread = threading.Thread(target=self.process_in_background)
        thread.start()

    def process_in_background(self):
        try:
            image_path = find_latest_duolingo_screenshot()

            if not image_path:
                Clock.schedule_once(
                    lambda dt: self.finish_with_text("❌ هیچ اسکرین‌شات Duolingo پیدا نشد.")
                )
                return

            Clock.schedule_once(
                lambda dt: self.set_result_text(
                    "✅ عکس پیدا شد:\n" + image_path + "\n\nدر حال استخراج متن (OCR)..."
                )
            )

            ocr_text = run_ocr(image_path)

            if not ocr_text:
                Clock.schedule_once(
                    lambda dt: self.finish_with_text(
                        "❌ استخراج متن انجام نشد. لطفاً دوباره امتحان کنید."
                    )
                )
                return

            Clock.schedule_once(
                lambda dt: self.set_result_text(
                    "متن استخراج شده:\n" + ocr_text + "\n\nدر حال گرفتن توضیح فارسی..."
                )
            )

            explanation = ask_gemini(ocr_text)
            explanation = clean_markdown(explanation)

            final_text = (
                "متن استخراج شده:\n"
                + ocr_text
                + "\n\n===== توضیح فارسی =====\n\n"
                + explanation
            )

            Clock.schedule_once(lambda dt: self.finish_with_text(final_text))

        except Exception as e:
            Clock.schedule_once(
                lambda dt: self.finish_with_text("❌ خطایی رخ داد:\n" + str(e))
            )

    def finish_with_text(self, text):
        self.set_result_text(text)
        self.analyze_button.disabled = False


if __name__ == "__main__":
    DuolingoAssistantApp().run()
