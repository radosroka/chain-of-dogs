#!/usr/bin/env python3
import sys
import os
import sqlite3

from game_state import GameState
from events import EventSystem
from ui import UI, clear
import sounds
import music

DB_FILE = os.path.join(os.path.dirname(__file__), 'scores.db')


def _get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            score INTEGER NOT NULL,
            won   INTEGER NOT NULL
        )
    """)
    conn.commit()
    return conn


def load_scores():
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT name, score, won FROM scores ORDER BY score DESC LIMIT 100"
        ).fetchall()
    return [{'name': r[0], 'score': r[1], 'won': bool(r[2])} for r in rows]


def save_score(name, score, won):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO scores (name, score, won) VALUES (?, ?, ?)",
            (name, score, int(won))
        )
        conn.commit()
    scores = load_scores()
    rank = next(
        i for i, e in enumerate(scores)
        if e['name'] == name and e['score'] == score
    )
    return rank, scores


def calc_score(state):
    score = state.refugees + state.soldiers * 5 - state.day * 20
    if state.won:
        score += 10000
    return max(0, score)


ACTION_SOUNDS = {
    'march':  sounds.play_march,
    'forced': sounds.play_forced,
    'rest':   sounds.play_rest,
    'forage': sounds.play_forage,
}

TACTIC_SOUNDS = {
    1: sounds.play_battle,
    2: sounds.play_battle,
    3: sounds.play_battle,
    4: sounds.play_battle,
}


def main():
    ui = UI()
    name = ui.ask_name()
    sounds.play_start()
    music.generate_all()
    music.play_ambient()

    state = GameState()
    events = EventSystem(state)

    ui.show_intro()

    while not state.game_over:
        clear()
        ui.render(state)

        action = ui.get_action()
        if action == 'quit':
            sounds.play_danger()
            print("\n  The march is abandoned.")
            print("  Coltaine weeps.")
            sys.exit(0)

        ACTION_SOUNDS.get(action, sounds.play_click)()

        # Play action animation
        if action == 'march':
            ui.anim_march()
        elif action == 'forced':
            ui.anim_forced_march()
        elif action == 'rest':
            ui.anim_rest()
        elif action == 'forage':
            ui.anim_forage()

        event = events.process_day(action)

        if state.game_over:
            break

        if event is None:
            continue

        if event.type == 'attack':
            sounds.play_danger()
            music.play_battle()
            ui.anim_attack_incoming(event.data['name'], event.data['enemy_size'], state.soldiers)
            tactic = ui.render_battle(state, event.data['enemy_size'], event.data['name'])
            ui.anim_battle_clash()
            sounds.play_battle()
            result = events.resolve_battle(tactic, event.data['enemy_size'])
            clear()
            ui.render_battle_result(state, result)
            input("\n  [Press Enter to continue...]")
            state.check_loss()
            music.play_ambient()

        elif event.type != 'nothing':
            msg = event.data.get('message', '')
            if msg:
                ui.show_event_notification(state, msg)

    clear()
    score = calc_score(state)
    rank, scores = save_score(name, score, state.won)

    music.stop()
    if state.won:
        ui.anim_victory()
        sounds.play_victory()
        ui.show_victory(state, score, rank, scores)
    else:
        ui.anim_defeat()
        sounds.play_defeat()
        ui.show_defeat(state, score, rank, scores)


if __name__ == '__main__':
    main()
