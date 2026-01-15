"""Common UI helper functions."""


def get_status_emoji(status: str) -> str:
    """Get emoji for resource status."""
    status_map = {
        "running": ":large_green_circle:",
        "idle": ":large_yellow_circle:",
        "stopped": ":red_circle:",
        "error": ":warning:",
        "unknown": ":white_circle:",
    }
    return status_map.get(status.lower(), ":white_circle:")


def get_service_emoji(service: str) -> str:
    """Get emoji for service type."""
    service_map = {
        "StreamLive": ":tv:",
        "StreamLink": ":link:",
    }
    return service_map.get(service, ":gear:")


def get_task_status_emoji(status: str) -> str:
    """Get emoji for task status."""
    status_map = {
        "pending": ":hourglass_flowing_sand:",
        "running": ":arrows_counterclockwise:",
        "completed": ":white_check_mark:",
        "failed": ":x:",
        "cancelled": ":no_entry:",
    }
    return status_map.get(status.lower(), ":question:")


def get_schedule_status_emoji(status: str) -> str:
    """Get emoji for schedule status."""
    status_map = {
        "scheduled": ":calendar:",
        "active": ":red_circle:",
        "completed": ":white_check_mark:",
        "cancelled": ":no_entry:",
    }
    return status_map.get(status.lower(), ":question:")


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def create_divider_block() -> dict:
    """Create a divider block."""
    return {"type": "divider"}


def create_context_block(text: str) -> dict:
    """Create a context block."""
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": text}],
    }


def create_header_block(text: str) -> dict:
    """Create a header block."""
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": text, "emoji": True},
    }


def create_section_block(text: str, accessory: dict = None) -> dict:
    """Create a section block."""
    block = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": text},
    }
    if accessory:
        block["accessory"] = accessory
    return block


def create_button(text: str, action_id: str, value: str = "", style: str = None) -> dict:
    """Create a button element."""
    button = {
        "type": "button",
        "text": {"type": "plain_text", "text": text, "emoji": True},
        "action_id": action_id,
        "value": value or action_id,
    }
    if style in ["primary", "danger"]:
        button["style"] = style
    return button


def create_actions_block(elements: list, block_id: str = None) -> dict:
    """Create an actions block."""
    block = {"type": "actions", "elements": elements}
    if block_id:
        block["block_id"] = block_id
    return block
