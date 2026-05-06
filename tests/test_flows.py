from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.domain.flows import (
    BUTTON_CANCEL,
    BUTTON_HOME,
    BUTTON_START,
    FLOW_DEFINITIONS,
    detect_flow_from_text,
    topic_title,
)


def test_detect_flow_from_text() -> None:
    assert detect_flow_from_text("1") is FlowId.READY_MADE
    assert detect_flow_from_text("2️⃣") is FlowId.DESIGNER_PROJECT
    assert detect_flow_from_text("3") is FlowId.CUSTOM_DIMENSIONS
    assert detect_flow_from_text("unknown") is None


def test_flow_lengths_are_expected() -> None:
    assert len(FLOW_DEFINITIONS[FlowId.READY_MADE].questions) == 7
    assert len(FLOW_DEFINITIONS[FlowId.DESIGNER_PROJECT].questions) == 6
    assert len(FLOW_DEFINITIONS[FlowId.CUSTOM_DIMENSIONS].questions) == 1


def test_topic_title_uses_platform_prefix() -> None:
    assert topic_title(Platform.TELEGRAM, "Олег", "mako") == "ТГ,Олег,@mako"
    assert topic_title(Platform.VK, "Олег", None) == "ВК,Олег,без_ника"


def test_button_constants_exist() -> None:
    assert BUTTON_START == "Старт"
    assert BUTTON_CANCEL == "Отмена"
    assert BUTTON_HOME == "На главную"
