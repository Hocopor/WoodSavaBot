from __future__ import annotations

from dataclasses import dataclass

from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.domain.models import Button

WELCOME_TEXT = (
    "Здравствуйте! \n"
    "Рады вас видеть в WOOD-SAVA индивидуальная мебель!\n"
    "Мы ценим ваше время и наших менеджеров, по этому предлагаем ответить на несколько важных вопросов ниже!🪑🌿🛋\n\n"
    "1. Изготовить мебель по индивидуальным размерам.\n"
    "2. Есть готовый дизайнерский проект\n"
    "3. Есть фото, артикул, название готовой мебели, изготовить такую же."
)

START_TEXT = (
    "Здравствуйте! Чтобы начать работу, нажмите кнопку «Старт»."
)

THANK_YOU_TEXT = "Спасибо, ожидайте звонка😊"
CONTACT_PROMPT = (
    "📩Пожалуйста напишите имя, телефон для связи, и адрес доставки. "
    "С вами свяжется первый освободившийся менеджер."
)
CONTACT_PROMPT_PLAIN = (
    "📩Пожалуйста напишите имя, телефон для связи, и адрес доставки. "
    "С вами свяжется первый освободившийся менеджер."
)
DESIGN_PROJECT_UPLOAD_PROMPT = "Пришлите дизайн проект в мессенджер или на почту wood-sava@yandex.ru"

BUTTON_START = "Старт"
BUTTON_CANCEL = "Отмена"
BUTTON_HOME = "На главную"
BUTTON_BACK = "Прошлый вопрос"
BUTTON_NEXT = "Следующий вопрос"


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
            "Укажите размеры (высота, ширина, глубина).",
            "Материал фасадов ( МДФ в пленке ПВХ, AGT, эмаль, лдсп).",
            "Фурнитура( премиальная/ стандартная/ бюджетная)",
            CONTACT_PROMPT_PLAIN,
        ],
    ),
    FlowId.DESIGNER_PROJECT: FlowDefinition(
        flow_id=FlowId.DESIGNER_PROJECT,
        entry_label="2️⃣",
        questions=[
            DESIGN_PROJECT_UPLOAD_PROMPT,
            "Укажите контактные данные для связи и город обращения.",
        ],
    ),
    FlowId.CUSTOM_DIMENSIONS: FlowDefinition(
        flow_id=FlowId.CUSTOM_DIMENSIONS,
        entry_label="3️⃣",
        questions=[
            "Артикул / название модели и фото (если есть).",
            CONTACT_PROMPT_PLAIN,
        ],
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


def question_buttons(
    *,
    can_go_back: bool,
    can_go_next: bool,
) -> list[list[Button]]:
    if not can_go_back and not can_go_next:
        return [[Button(BUTTON_CANCEL)]]

    navigation_row: list[Button] = []
    if can_go_back:
        navigation_row.append(Button(BUTTON_BACK))
    if can_go_next:
        navigation_row.append(Button(BUTTON_NEXT))

    return [navigation_row, [Button(BUTTON_CANCEL)]]


def format_question_text(question: str, previous_answer: str | None = None) -> str:
    if question in {CONTACT_PROMPT, CONTACT_PROMPT_PLAIN, DESIGN_PROJECT_UPLOAD_PROMPT}:
        text = question
    else:
        text = f"Введите:\n{question}"
    if previous_answer:
        text += (
            f"\n\nВаш ответ:\n{previous_answer}"
            "\n\nЕсли хотите изменить ответ, просто отправьте новый в текущем сообщении."
        )
    return text


def flow_selection_text(flow_id: FlowId) -> str:
    mapping = {
        FlowId.READY_MADE: "Пользователь выбрал: 1️⃣ - Вы хотите рассчитать стоимость готового изделия",
        FlowId.DESIGNER_PROJECT: "Пользователь выбрал: 2️⃣ - У Вас готовый проект от дизайнера",
        FlowId.CUSTOM_DIMENSIONS: "Пользователь выбрал: 3️⃣ - Сделать мебель по индивидуальным размерам",
    }
    return mapping[flow_id]


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
