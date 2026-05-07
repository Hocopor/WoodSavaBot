from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.domain.flows import (
    BUTTON_BACK,
    BUTTON_CANCEL,
    BUTTON_HOME,
    BUTTON_NEXT,
    BUTTON_START,
    CONTACT_PROMPT,
    FLOW_DEFINITIONS,
    WELCOME_TEXT,
    detect_flow_from_text,
    flow_selection_text,
    format_question_text,
    question_buttons,
    topic_title,
)


def test_detect_flow_from_text() -> None:
    assert detect_flow_from_text("1") is FlowId.READY_MADE
    assert detect_flow_from_text("2") is FlowId.DESIGNER_PROJECT
    assert detect_flow_from_text("3") is FlowId.CUSTOM_DIMENSIONS
    assert detect_flow_from_text("unknown") is None


def test_flow_lengths_are_expected() -> None:
    assert len(FLOW_DEFINITIONS[FlowId.READY_MADE].questions) == 7
    assert len(FLOW_DEFINITIONS[FlowId.DESIGNER_PROJECT].questions) == 6
    assert len(FLOW_DEFINITIONS[FlowId.CUSTOM_DIMENSIONS].questions) == 1


def test_topic_title_uses_platform_prefix() -> None:
    telegram_title = topic_title(Platform.TELEGRAM, "Олег", "mako")
    vk_title = topic_title(Platform.VK, "Олег", None)

    assert telegram_title == "ТГ,Олег,@mako"
    assert vk_title == "ВК,Олег,без_ника"


def test_button_constants_exist() -> None:
    assert BUTTON_START == "Старт"
    assert BUTTON_CANCEL == "Отмена"
    assert BUTTON_HOME == "На главную"
    assert BUTTON_BACK == "Прошлый вопрос"
    assert BUTTON_NEXT == "Следующий вопрос"
    assert BUTTON_START not in WELCOME_TEXT


def test_flow_selection_text_contains_operator_context() -> None:
    ready_made = flow_selection_text(FlowId.READY_MADE)
    designer_project = flow_selection_text(FlowId.DESIGNER_PROJECT)
    custom_dimensions = flow_selection_text(FlowId.CUSTOM_DIMENSIONS)

    assert "1" in ready_made
    assert "2" in designer_project
    assert "3" in custom_dimensions
    assert ready_made != designer_project != custom_dimensions


def test_question_buttons_include_back_and_next_when_available() -> None:
    buttons = question_buttons(can_go_back=True, can_go_next=True)
    labels = [button.label for row in buttons for button in row]
    assert BUTTON_BACK in labels
    assert BUTTON_NEXT in labels
    assert BUTTON_CANCEL in labels


def test_format_question_text_includes_previous_answer_hint() -> None:
    text = format_question_text("Какой цвет?", previous_answer="Белый")
    assert "Введите:" in text
    assert "Ваш ответ:" in text
    assert "Белый" in text


def test_format_question_text_skips_enter_prefix_for_contact_prompt() -> None:
    text = format_question_text(CONTACT_PROMPT)
    assert not text.startswith("Введите:")
    assert text == CONTACT_PROMPT
