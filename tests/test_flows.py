from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.domain.flows import (
    BUTTON_CANCEL,
    BUTTON_HOME,
    BUTTON_START,
    FLOW_DEFINITIONS,
    WELCOME_TEXT,
    detect_flow_from_text,
    flow_selection_text,
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

    assert telegram_title.endswith("@mako")
    assert "Олег" in telegram_title
    assert vk_title.endswith("без_ника")
    assert "Олег" in vk_title


def test_button_constants_exist() -> None:
    assert BUTTON_START
    assert BUTTON_CANCEL
    assert BUTTON_HOME
    assert BUTTON_START in WELCOME_TEXT or BUTTON_START == "Старт"


def test_flow_selection_text_contains_operator_context() -> None:
    ready_made = flow_selection_text(FlowId.READY_MADE)
    designer_project = flow_selection_text(FlowId.DESIGNER_PROJECT)
    custom_dimensions = flow_selection_text(FlowId.CUSTOM_DIMENSIONS)

    assert "1" in ready_made
    assert "2" in designer_project
    assert "3" in custom_dimensions
    assert ready_made != designer_project != custom_dimensions
