from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class ActionType(str, Enum):
    EXAMINE = "EXAMINE"
    USE_ITEM = "USE_ITEM"
    TAKE_ITEM = "TAKE_ITEM"
    ENTER_CODE = "ENTER_CODE"
    LOOK_AROUND = "LOOK_AROUND"
    CHECK_INVENTORY = "CHECK_INVENTORY"
    UNKNOWN = "UNKNOWN"

class ActionIntent(BaseModel):
    """Structured representation of player intent parsed from natural language."""
    action_type: ActionType = Field(
        ...,
        description="The primary action category the player intends to perform."
    )
    target_object: Optional[str] = Field(
        None,
        description="The entity or object targeted by the action (e.g., bookshelf, painting, desk, locked_drawer, exit_door, torn_cipher_strip)."
    )
    item_used: Optional[str] = Field(
        None,
        description="The tool or inventory item the player attempts to use (e.g., tension_wrench, uv_penlight, brass_magnifier)."
    )
    code_attempt: Optional[str] = Field(
        None,
        description="Any numeric or alphanumeric code sequence the player enters or speaks."
    )

class ActionResult(BaseModel):
    """Deterministic outcome produced by the Python state engine."""
    success: bool
    action_type: ActionType
    event_summary: str
    discovered_items: List[str] = Field(default_factory=list)
    trace_increment: int
    current_trace: int
    is_game_over: bool
    is_victory: bool

class GameState(BaseModel):
    """Single source of truth for the escape room state."""
    inventory: List[str] = Field(default_factory=list)
    examined_objects: List[str] = Field(default_factory=list)
    bookshelf_searched: bool = False
    painting_opened: bool = False
    desk_uv_inspected: bool = False
    drawer_unlocked: bool = False
    cipher_magnified: bool = False
    exit_door_unlocked: bool = False
    lockdown_trace: int = 0
    turn_count: int = 0
    game_over: bool = False
    victory: bool = False
