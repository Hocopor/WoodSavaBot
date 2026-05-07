from __future__ import annotations

from dataclasses import dataclass

from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.domain.models import Button

WELCOME_TEXT = (
    "Здравствуйте! Рады видеть вас в Wood - Sava.👩‍💻\n"
    "1️⃣ - Вы хотите рассчитать стоимость готового изделия\n"
    "2️⃣ - У Вас готовый проект от дизайнера\n"
    "3️⃣ - Сделать мебель по индивидуальным размерам"
)

START_TEXT = (
    "Здравствуйте! Чтобы начать работу, нажмите кнопку «Старт»."
)

THANK_YOU_TEXT = "Спасибо, ожидайте звонка😊"
CONTACT_PROMPT = (
    "Пожалуйста, напишите имя и номер телефона для связи, "
    "менеджер с Вами свяжется в ближайшее время.😊"
)
CONTACT_PROMPT_PLAIN = (
    "Пожалуйста, напишите имя и номер телефона для связи, "
    "менеджер с Вами свяжется в ближайшее время."
)

BUTTON_START = "Старт"
BUTTON_CANCEL = "Отмена"
BUTTON_HOME = "На главную"


@dataclass(frozen=True, slots=True)
class FlowDefinition:
    flow_id: FlowId
    entry_label: str
    questions: list[str]


FLOW_DEFINITIONS = {
    FlowId.READY_MADE: FlowDefinition(
        flow_id=FlowId.READY_MADE,
        entry_label="1️⃣",
        questions=[
            "Артикул / название модели и фото (если есть).",
            "Какие размеры (длина×ширина×высота).",
            "Материал корпуса и фасада (лдсп, мдф, массив).",
            "Цвет / декор.",
            "Фурнитура (ручки, доводчики, подсветка).",
            "Нужна ли доставка и сборка.",
            CONTACT_PROMPT,
        ],
    ),
    FlowId.DESIGNER_PROJECT: FlowDefinition(
        flow_id=FlowId.DESIGNER_PROJECT,
        entry_label="2️⃣",
        questions=[
            "В каком формате проект (PDF, SketchUp, развертки)?",
            "Есть ли спецификация материалов и фурнитуры?",
            "Размеры по месту (погрешности стен/пола).",
            "Нужны ли изменения в раскрое или фурнитуре?",
            "Требуется ли авторский надзор за сборкой.",
            CONTACT_PROMPT,
        ],
    ),
    FlowId.CUSTOM_DIMENSIONS: FlowDefinition(
        flow_id=FlowId.CUSTOM_DIMENSIONS,
        entry_label="3️⃣",
        questions=[CONTACT_PROMPT_PLAIN],
    ),
}

FLOW_BY_LABEL = {
    "1": FlowId.READY_MADE,
    "1️⃣": FlowId.READY_MADE,
    "2": FlowId.DESIGNER_PROJECT,
    "2️⃣": FlowId.DESIGNER_PROJECT,
    "3": FlowId.CUSTOM_DIMENSIONS,
    "3️⃣": FlowId.CUSTOM_DIMENSIONS,
}


def detect_flow_from_text(text: str | None) -> FlowId | None:
    if not text:
        return None
    return FLOW_BY_LABEL.get(text.strip())


def main_menu_buttons() -> list[list[Button]]:
    return [[Button("1️⃣")], [Button("2️⃣")], [Button("3️⃣")]]


def start_buttons(platform: Platform) -> list[list[Button]]:
    if platform is Platform.TELEGRAM:
        return [[Button(BUTTON_START, "/start")]]
    return [[Button(BUTTON_START)]]


def cancel_buttons() -> list[list[Button]]:
    return [[Button(BUTTON_CANCEL)]]


def home_buttons() -> list[list[Button]]:
    return [[Button(BUTTON_HOME)]]


def topic_title(platform: Platform, display_name: str | None, username: str | None) -> str:
    prefix = {
        Platform.TELEGRAM: "ТГ",
        Platform.VK: "ВК",
        Platform.MAX: "МАКС",
    }[platform]
    name = display_name or "без_имени"
    if platform is Platform.TELEGRAM and username:
        user_part = f"@{username.lstrip('@')}"
    else:
        user_part = username or "без_ника"
    return f"{prefix},{name},{user_part}"
