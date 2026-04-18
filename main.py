#!/usr/bin/env python3
import sys

from game_state import GameState
from events import EventSystem
from ui import UI, clear


def main():
    ui = UI()
    state = GameState()
    events = EventSystem(state)

    ui.show_intro()

    while not state.game_over:
        clear()
        ui.render(state)

        action = ui.get_action()
        if action == 'quit':
            print("\n  The march is abandoned.")
            print("  Coltaine weeps.")
            sys.exit(0)

        event = events.process_day(action)

        if state.game_over:
            break

        if event is None:
            continue

        if event.type == 'attack':
            clear()
            tactic = ui.render_battle(state, event.data['enemy_size'], event.data['name'])
            result = events.resolve_battle(tactic, event.data['enemy_size'])
            clear()
            ui.render_battle_result(state, result)
            input("\n  [Press Enter to continue...]")
            state.check_loss()

        elif event.type != 'nothing':
            msg = event.data.get('message', '')
            if msg:
                ui.show_event_notification(state, msg)

    clear()
    if state.won:
        ui.show_victory(state)
    else:
        ui.show_defeat(state)


if __name__ == '__main__':
    main()
