from typing import Tuple, List
from v2_reliable.models import ActionType, ActionIntent, ActionResult, GameState

class StateEngine:
    """
    Deterministic State Engine for WARDEN Escape Room.
    Acts as the single source of truth for:
    - Room object states and puzzle progression
    - Player satchel inventory
    - Secret codes (stored strictly in Python, NEVER passed to LLM)
    - Lockdown Trace Meter (0% to 100%) and win/loss states
    """
    DRAWER_CODE = "492"
    EXIT_CODE = "8316"

    VALID_ROOM_OBJECTS = {"bookshelf", "painting", "desk", "locked_drawer", "exit_door"}

    def __init__(self):
        self.state = GameState()

    def get_state(self) -> GameState:
        return self.state

    def reset(self) -> None:
        self.state = GameState()

    def _normalize_string(self, text: str) -> str:
        if not text:
            return ""
        return text.strip().lower().replace(" ", "_").replace("-", "_")

    def _add_trace(self, amount: int) -> Tuple[int, bool]:
        """Advance trace meter and check for lockdown failure."""
        self.state.lockdown_trace = min(100, self.state.lockdown_trace + amount)
        is_over = self.state.lockdown_trace >= 100
        if is_over:
            self.state.game_over = True
        return amount, is_over

    def execute_action(self, intent: ActionIntent) -> ActionResult:
        """
        Deterministically evaluates player intent against the current game state.
        Returns an ActionResult containing the verified outcome.
        """
        self.state.turn_count += 1
        
        # If game is already over or won, halt state changes
        if self.state.game_over:
            return ActionResult(
                success=False,
                action_type=intent.action_type,
                event_summary="Emergency lockdown active. All systems are permanently sealed.",
                discovered_items=[],
                trace_increment=0,
                current_trace=self.state.lockdown_trace,
                is_game_over=True,
                is_victory=False
            )
        if self.state.victory:
            return ActionResult(
                success=True,
                action_type=intent.action_type,
                event_summary="The vault door is already unlocked and open. Escape path is clear.",
                discovered_items=[],
                trace_increment=0,
                current_trace=self.state.lockdown_trace,
                is_game_over=False,
                is_victory=True
            )

        target = self._normalize_string(intent.target_object) if intent.target_object else None
        item = self._normalize_string(intent.item_used) if intent.item_used else None
        code = intent.code_attempt.strip() if intent.code_attempt else None

        # Route by ActionType
        if intent.action_type == ActionType.LOOK_AROUND:
            return self._handle_look_around()

        elif intent.action_type == ActionType.CHECK_INVENTORY:
            return self._handle_check_inventory()

        elif intent.action_type == ActionType.EXAMINE:
            return self._handle_examine(target)

        elif intent.action_type == ActionType.USE_ITEM:
            return self._handle_use_item(item, target)

        elif intent.action_type == ActionType.ENTER_CODE:
            return self._handle_enter_code(target, code)

        elif intent.action_type == ActionType.TAKE_ITEM:
            return self._handle_take_item(target)

        else:  # UNKNOWN or invalid
            inc, is_over = self._add_trace(15)
            return ActionResult(
                success=False,
                action_type=ActionType.UNKNOWN,
                event_summary="Unrecognized or unauthorized command. Estate security protocols flag suspicious activity.",
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

    def _handle_look_around(self) -> ActionResult:
        inc, is_over = self._add_trace(5)
        summary = (
            "You scan the Locked Library. Five points of interest stand out: "
            "a towering 'bookshelf' of antique tomes, an ornate oil 'painting', "
            "an executive 'desk', a 'locked_drawer' with a 3-digit combination dial, "
            "and a heavy steel 'exit_door' with a glowing 4-digit keypad."
        )
        return ActionResult(
            success=True,
            action_type=ActionType.LOOK_AROUND,
            event_summary=summary,
            discovered_items=[],
            trace_increment=inc,
            current_trace=self.state.lockdown_trace,
            is_game_over=is_over,
            is_victory=False
        )

    def _handle_check_inventory(self) -> ActionResult:
        inc, is_over = self._add_trace(5)
        if not self.state.inventory:
            summary = "Your satchel is empty. You currently hold no tools or discovered clues."
        else:
            items_str = ", ".join(self.state.inventory)
            summary = f"Your satchel contains: {items_str}."
        
        return ActionResult(
            success=True,
            action_type=ActionType.CHECK_INVENTORY,
            event_summary=summary,
            discovered_items=[],
            trace_increment=inc,
            current_trace=self.state.lockdown_trace,
            is_game_over=is_over,
            is_victory=False
        )

    def _handle_examine(self, target: str) -> ActionResult:
        if not target:
            inc, is_over = self._add_trace(15)
            return ActionResult(
                success=False,
                action_type=ActionType.EXAMINE,
                event_summary="Examine target not specified.",
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        # Inventory item examination
        if target in self.state.inventory:
            inc, is_over = self._add_trace(5)
            if target == "tension_wrench":
                summary = "A precision steel tension wrench, ideal for popping lock clasps and mechanical pins."
            elif target == "catalog_card":
                summary = "An archival catalog card with handwritten notes: 'Patriarch portrait frame hides the secondary key'."
            elif target == "uv_penlight":
                summary = "A compact 395nm ultraviolet penlight. Useful for revealing invisible fluorescent security markings."
            elif target == "torn_cipher_strip":
                if "brass_magnifier" in self.state.inventory or self.state.cipher_magnified:
                    self.state.cipher_magnified = True
                    summary = (
                        "Examining the torn cipher strip through the brass magnifier brings micro-engraved "
                        "numbers into focus: the 4-digit code is '8316'."
                    )
                else:
                    summary = (
                        "A torn strip of parchment printed with dense, microscopic cryptographic lines. "
                        "The print is far too small to decipher with the naked eye."
                    )
            elif target == "brass_magnifier":
                summary = "A heavy brass jeweler's magnifier with distortion-free optical glass."
            else:
                summary = f"You inspect the {target}. It appears standard."

            return ActionResult(
                success=True,
                action_type=ActionType.EXAMINE,
                event_summary=summary,
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        # Room objects
        if target == "bookshelf":
            inc, is_over = self._add_trace(5)
            if not self.state.bookshelf_searched:
                self.state.bookshelf_searched = True
                new_items = ["tension_wrench", "catalog_card"]
                for it in new_items:
                    if it not in self.state.inventory:
                        self.state.inventory.append(it)
                summary = (
                    "Running your fingers along the mahogany bookshelf, you discover a hollow first-edition spine. "
                    "Inside is a concealed 'tension_wrench' and a library 'catalog_card' with a note pointing to the portrait painting. "
                    "You slip both into your satchel."
                )
                return ActionResult(
                    success=True,
                    action_type=ActionType.EXAMINE,
                    event_summary=summary,
                    discovered_items=new_items,
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=is_over,
                    is_victory=False
                )
            else:
                summary = "The bookshelf contains only classical leather-bound volumes now. The secret spine compartment is empty."
                return ActionResult(
                    success=True,
                    action_type=ActionType.EXAMINE,
                    event_summary=summary,
                    discovered_items=[],
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=is_over,
                    is_victory=False
                )

        elif target == "painting":
            inc, is_over = self._add_trace(5)
            if not self.state.painting_opened:
                summary = (
                    "You inspect the imposing oil portrait of the estate patriarch. Tucked behind the lower carved "
                    "edge of the gilded frame, you feel a concealed brass mechanical clasp locking a small cavity."
                )
            else:
                summary = "The painting's lower frame compartment is popped open and empty."
            return ActionResult(
                success=True,
                action_type=ActionType.EXAMINE,
                event_summary=summary,
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        elif target == "desk":
            inc, is_over = self._add_trace(5)
            if self.state.desk_uv_inspected:
                summary = "Under the lingering UV glow on the leather desk blotter, the 3-digit number '492' is clearly legible."
            else:
                summary = (
                    "A massive walnut executive desk with an antique leather blotter and bronze stationery accessories. "
                    "Under the room's normal ambient light, nothing unusual is visible on the surface."
                )
            return ActionResult(
                success=True,
                action_type=ActionType.EXAMINE,
                event_summary=summary,
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        elif target == "locked_drawer":
            inc, is_over = self._add_trace(5)
            if self.state.drawer_unlocked:
                summary = "The desk drawer is unlocked and standing open. Its interior velvet lining is empty."
            else:
                summary = (
                    "A reinforced drawer built into the right desk pedestal, secured with a 3-digit rotating brass combination lock. "
                    "It requires a 3-digit numeric code to open."
                )
            return ActionResult(
                success=True,
                action_type=ActionType.EXAMINE,
                event_summary=summary,
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        elif target == "exit_door":
            inc, is_over = self._add_trace(5)
            if self.state.exit_door_unlocked:
                summary = "The reinforced vault door stands wide open, leading out to the estate grounds."
            else:
                summary = (
                    "A heavy blast-rated steel vault door. A digital keypad with 4 glowing digit slots "
                    "and an armed security LED bars passage."
                )
            return ActionResult(
                success=True,
                action_type=ActionType.EXAMINE,
                event_summary=summary,
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        else:
            inc, is_over = self._add_trace(15)
            return ActionResult(
                success=False,
                action_type=ActionType.EXAMINE,
                event_summary=f"There is no '{target}' in the Locked Library to examine.",
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

    def _handle_use_item(self, item: str, target: str) -> ActionResult:
        # Crucial Rule 1: Item must be present in player's inventory
        if not item or item not in self.state.inventory:
            inc, is_over = self._add_trace(15)
            return ActionResult(
                success=False,
                action_type=ActionType.USE_ITEM,
                event_summary=f"Action failed: '{item or 'unspecified item'}' is not in your satchel.",
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        # Puzzle Step 2: Use tension_wrench on painting
        if item == "tension_wrench" and target == "painting":
            inc, is_over = self._add_trace(5)
            if not self.state.painting_opened:
                self.state.painting_opened = True
                new_items = ["torn_cipher_strip", "uv_penlight"]
                for it in new_items:
                    if it not in self.state.inventory:
                        self.state.inventory.append(it)
                summary = (
                    "You slip the tension wrench into the hidden brass clasp behind the portrait frame and twist. "
                    "With a sharp click, a secret spring compartment pops open! Inside, you retrieve a "
                    "'torn_cipher_strip' and a compact 'uv_penlight'."
                )
                return ActionResult(
                    success=True,
                    action_type=ActionType.USE_ITEM,
                    event_summary=summary,
                    discovered_items=new_items,
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=is_over,
                    is_victory=False
                )
            else:
                summary = "The painting frame compartment has already been popped open and cleared out."
                return ActionResult(
                    success=True,
                    action_type=ActionType.USE_ITEM,
                    event_summary=summary,
                    discovered_items=[],
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=is_over,
                    is_victory=False
                )

        # Puzzle Step 3: Use uv_penlight on desk
        if item == "uv_penlight" and target == "desk":
            inc, is_over = self._add_trace(5)
            self.state.desk_uv_inspected = True
            summary = (
                "You switch on the UV penlight and bathe the leather desk blotter in purple glow. "
                "Fluorescent residue flares to life, clearly revealing three hand-scrawled digits: '492'."
            )
            return ActionResult(
                success=True,
                action_type=ActionType.USE_ITEM,
                event_summary=summary,
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        # Puzzle Step 4: Combine / use brass_magnifier on torn_cipher_strip
        if (item == "brass_magnifier" and target == "torn_cipher_strip") or \
           (item == "torn_cipher_strip" and target == "brass_magnifier"):
            inc, is_over = self._add_trace(5)
            self.state.cipher_magnified = True
            summary = (
                "Aligning the brass magnifier's lens over the torn cipher strip reveals microscopic engraving "
                "along the frayed fiber edge: the keypad code '8316'."
            )
            return ActionResult(
                success=True,
                action_type=ActionType.USE_ITEM,
                event_summary=summary,
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        # Ineffective use
        inc, is_over = self._add_trace(15)
        summary = f"Attempting to use '{item}' on '{target or 'air'}' yielded no result. Security sensors register the clumsy attempt."
        return ActionResult(
            success=False,
            action_type=ActionType.USE_ITEM,
            event_summary=summary,
            discovered_items=[],
            trace_increment=inc,
            current_trace=self.state.lockdown_trace,
            is_game_over=is_over,
            is_victory=False
        )

    def _handle_enter_code(self, target: str, code: str) -> ActionResult:
        if not code:
            inc, is_over = self._add_trace(15)
            return ActionResult(
                success=False,
                action_type=ActionType.ENTER_CODE,
                event_summary="No code combination was provided.",
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        # Target: locked_drawer (requires 492)
        if target in ("locked_drawer", "drawer"):
            if self.state.drawer_unlocked:
                inc, is_over = self._add_trace(5)
                return ActionResult(
                    success=True,
                    action_type=ActionType.ENTER_CODE,
                    event_summary="The locked drawer is already open.",
                    discovered_items=[],
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=is_over,
                    is_victory=False
                )

            if code == self.DRAWER_CODE:
                inc, is_over = self._add_trace(5)
                self.state.drawer_unlocked = True
                new_item = "brass_magnifier"
                if new_item not in self.state.inventory:
                    self.state.inventory.append(new_item)
                summary = (
                    f"You dial '{code}' into the drawer combination lock. Tumblers align with a mechanical snap! "
                    "The drawer unlocks, revealing an optical 'brass_magnifier'. You place it in your satchel."
                )
                return ActionResult(
                    success=True,
                    action_type=ActionType.ENTER_CODE,
                    event_summary=summary,
                    discovered_items=[new_item],
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=is_over,
                    is_victory=False
                )
            else:
                inc, is_over = self._add_trace(15)
                summary = f"Code '{code}' failed on locked_drawer. The lock resists and an acoustic chime sounds."
                return ActionResult(
                    success=False,
                    action_type=ActionType.ENTER_CODE,
                    event_summary=summary,
                    discovered_items=[],
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=is_over,
                    is_victory=False
                )

        # Target: exit_door (requires 8316)
        elif target in ("exit_door", "door", "keypad"):
            if self.state.exit_door_unlocked:
                inc, is_over = self._add_trace(5)
                return ActionResult(
                    success=True,
                    action_type=ActionType.ENTER_CODE,
                    event_summary="The exit door is already disengaged and open.",
                    discovered_items=[],
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=is_over,
                    is_victory=True
                )

            if code == self.EXIT_CODE:
                inc, is_over = self._add_trace(5)
                self.state.exit_door_unlocked = True
                self.state.victory = True
                summary = (
                    f"You enter '{code}' on the exit keypad. The digital display flashes GREEN. "
                    "Pneumatic seals hiss and magnetic clamps release! The heavy vault door swings open to the cool night air. "
                    "Escape successful!"
                )
                return ActionResult(
                    success=True,
                    action_type=ActionType.ENTER_CODE,
                    event_summary=summary,
                    discovered_items=[],
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=False,
                    is_victory=True
                )
            else:
                inc, is_over = self._add_trace(15)
                summary = f"Keypad code '{code}' rejected on exit_door. Alarm beacon blinks red and lockdown trace accelerates."
                return ActionResult(
                    success=False,
                    action_type=ActionType.ENTER_CODE,
                    event_summary=summary,
                    discovered_items=[],
                    trace_increment=inc,
                    current_trace=self.state.lockdown_trace,
                    is_game_over=is_over,
                    is_victory=False
                )

        else:
            inc, is_over = self._add_trace(15)
            return ActionResult(
                success=False,
                action_type=ActionType.ENTER_CODE,
                event_summary=f"Cannot enter code into '{target or 'unknown'}'. Object has no keypad or dial.",
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

    def _handle_take_item(self, target: str) -> ActionResult:
        # Most items are automatically gathered during examination/use
        if not target:
            inc, is_over = self._add_trace(15)
            return ActionResult(
                success=False,
                action_type=ActionType.TAKE_ITEM,
                event_summary="Take target not specified.",
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )
        
        if target in self.state.inventory:
            inc, is_over = self._add_trace(5)
            return ActionResult(
                success=True,
                action_type=ActionType.TAKE_ITEM,
                event_summary=f"The '{target}' is already in your satchel.",
                discovered_items=[],
                trace_increment=inc,
                current_trace=self.state.lockdown_trace,
                is_game_over=is_over,
                is_victory=False
            )

        inc, is_over = self._add_trace(15)
        return ActionResult(
            success=False,
            action_type=ActionType.TAKE_ITEM,
            event_summary=f"Cannot take '{target}'. It is either fixed in place or not discovered yet.",
            discovered_items=[],
            trace_increment=inc,
            current_trace=self.state.lockdown_trace,
            is_game_over=is_over,
            is_victory=False
        )
