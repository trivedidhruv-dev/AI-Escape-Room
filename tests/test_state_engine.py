import pytest
from v2_reliable.models import ActionType, ActionIntent
from v2_reliable.state_engine import StateEngine

def test_initial_state():
    engine = StateEngine()
    state = engine.get_state()
    assert state.inventory == []
    assert state.lockdown_trace == 0
    assert state.turn_count == 0
    assert not state.game_over
    assert not state.victory
    assert not state.bookshelf_searched
    assert not state.painting_opened
    assert not state.drawer_unlocked
    assert not state.exit_door_unlocked

def test_examine_bookshelf_yields_tools():
    engine = StateEngine()
    intent = ActionIntent(
        action_type=ActionType.EXAMINE,
        target_object="bookshelf"
    )
    result = engine.execute_action(intent)
    assert result.success is True
    assert "tension_wrench" in result.discovered_items
    assert "catalog_card" in result.discovered_items
    assert result.trace_increment == 5
    assert result.current_trace == 5

    state = engine.get_state()
    assert "tension_wrench" in state.inventory
    assert "catalog_card" in state.inventory
    assert state.bookshelf_searched is True

def test_inventory_enforcement_prevents_hallucination():
    engine = StateEngine()
    # Thief attempts to use tension_wrench before examining the bookshelf
    intent = ActionIntent(
        action_type=ActionType.USE_ITEM,
        target_object="painting",
        item_used="tension_wrench"
    )
    result = engine.execute_action(intent)
    assert result.success is False
    assert "not in your satchel" in result.event_summary
    assert result.trace_increment == 15
    assert result.current_trace == 15

    state = engine.get_state()
    assert state.painting_opened is False

def test_full_escape_happy_path():
    engine = StateEngine()

    # Step 1: Examine Bookshelf -> get tension_wrench & catalog_card
    res1 = engine.execute_action(ActionIntent(
        action_type=ActionType.EXAMINE,
        target_object="bookshelf"
    ))
    assert res1.success is True
    assert "tension_wrench" in res1.discovered_items

    # Step 2: Use tension_wrench on painting -> get torn_cipher_strip & uv_penlight
    res2 = engine.execute_action(ActionIntent(
        action_type=ActionType.USE_ITEM,
        target_object="painting",
        item_used="tension_wrench"
    ))
    assert res2.success is True
    assert "torn_cipher_strip" in res2.discovered_items
    assert "uv_penlight" in res2.discovered_items

    # Step 3: Use uv_penlight on desk -> reveals drawer combination 492
    res3 = engine.execute_action(ActionIntent(
        action_type=ActionType.USE_ITEM,
        target_object="desk",
        item_used="uv_penlight"
    ))
    assert res3.success is True
    assert "492" in res3.event_summary

    # Step 4: Enter code 492 on locked_drawer -> unlocks drawer, yields brass_magnifier
    res4 = engine.execute_action(ActionIntent(
        action_type=ActionType.ENTER_CODE,
        target_object="locked_drawer",
        code_attempt="492"
    ))
    assert res4.success is True
    assert "brass_magnifier" in res4.discovered_items
    assert engine.get_state().drawer_unlocked is True

    # Step 5: Combine brass_magnifier with torn_cipher_strip -> reveals exit code 8316
    res5 = engine.execute_action(ActionIntent(
        action_type=ActionType.USE_ITEM,
        target_object="torn_cipher_strip",
        item_used="brass_magnifier"
    ))
    assert res5.success is True
    assert "8316" in res5.event_summary

    # Step 6: Enter 8316 on exit_door keypad -> disengages vault door
    res6 = engine.execute_action(ActionIntent(
        action_type=ActionType.ENTER_CODE,
        target_object="exit_door",
        code_attempt="8316"
    ))
    assert res6.success is True
    assert res6.is_victory is True
    assert engine.get_state().victory is True
    assert engine.get_state().exit_door_unlocked is True
    # 6 turns * 5% = 30% trace
    assert engine.get_state().lockdown_trace == 30

def test_invalid_code_penalty():
    engine = StateEngine()
    # Enter wrong code on drawer
    res_drawer = engine.execute_action(ActionIntent(
        action_type=ActionType.ENTER_CODE,
        target_object="locked_drawer",
        code_attempt="000"
    ))
    assert res_drawer.success is False
    assert res_drawer.trace_increment == 15
    assert res_drawer.current_trace == 15
    assert engine.get_state().drawer_unlocked is False

    # Enter wrong code on exit door
    res_door = engine.execute_action(ActionIntent(
        action_type=ActionType.ENTER_CODE,
        target_object="exit_door",
        code_attempt="9999"
    ))
    assert res_door.success is False
    assert res_door.trace_increment == 15
    assert res_door.current_trace == 30
    assert engine.get_state().exit_door_unlocked is False

def test_trace_meter_lockdown_game_over():
    engine = StateEngine()
    # Repeatedly send invalid actions until trace hits 100%
    for _ in range(6):  # 6 * 15% = 90%
        engine.execute_action(ActionIntent(action_type=ActionType.UNKNOWN))
    assert engine.get_state().lockdown_trace == 90
    assert engine.get_state().game_over is False

    # 7th invalid action: 90% + 15% = 100% (capped)
    res_over = engine.execute_action(ActionIntent(action_type=ActionType.UNKNOWN))
    assert res_over.current_trace == 100
    assert res_over.is_game_over is True
    assert engine.get_state().game_over is True

    # Any subsequent action is rejected due to active lockdown
    res_subsequent = engine.execute_action(ActionIntent(
        action_type=ActionType.EXAMINE,
        target_object="bookshelf"
    ))
    assert res_subsequent.success is False
    assert "Emergency lockdown active" in res_subsequent.event_summary
