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
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            score      INTEGER NOT NULL,
            won        INTEGER NOT NULL,
            difficulty TEXT NOT NULL DEFAULT 'normal'
        )
    """)
    try:
        conn.execute("ALTER TABLE scores ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'normal'")
    except Exception:
        pass
    conn.commit()
    return conn


def load_scores():
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT name, score, won, difficulty FROM scores ORDER BY score DESC LIMIT 300"
        ).fetchall()
    by_diff = {d: {'winners': [], 'losers': []} for d in ('easy', 'normal', 'hard')}
    for name, score, won, diff in rows:
        if diff not in by_diff:
            diff = 'normal'
        key = 'winners' if won else 'losers'
        lst = by_diff[diff][key]
        if len(lst) < 10:
            lst.append({'name': name, 'score': score})
    return by_diff


def save_score(name, score, won, difficulty):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO scores (name, score, won, difficulty) VALUES (?, ?, ?, ?)",
            (name, score, int(won), difficulty)
        )
        conn.commit()
    scores = load_scores()
    group = scores[difficulty]['winners' if won else 'losers']
    rank = next(
        (i for i, e in enumerate(group) if e['name'] == name and e['score'] == score),
        len(group) - 1,
    )
    return rank, scores


def calc_score(state):
    bonus = 50000 if state.won else 0
    return max(0, state.refugees + state.soldiers * 5 - state.day * 20 + bonus)


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


def ask_difficulty():
    clear()
    print("\n  Choose difficulty:\n")
    print("    [1] Easy   — more supplies, fewer attacks, battles easier")
    print("    [2] Normal — the Chain of Dogs as written")
    print("    [3] Hard   — scarce resources, relentless attacks, high loss threshold\n")
    while True:
        choice = input("  > ").strip()
        if choice == '1':
            return 'easy'
        if choice == '2':
            return 'normal'
        if choice == '3':
            return 'hard'
        print("  Enter 1, 2, or 3.")


def main():
    ui = UI()
    name = ui.ask_name()
    difficulty = ask_difficulty()
    sounds.play_start()
    music.generate_all()
    music.play_ambient()

    state = GameState(difficulty)
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
    rank, all_scores = save_score(name, score, state.won, state.difficulty)
    diff_scores = all_scores[state.difficulty]

    music.stop()
    if state.won:
        ui.anim_victory()
        sounds.play_victory()
        ui.show_victory(state, score, rank, diff_scores['winners'], diff_scores['losers'], state.difficulty)
    else:
        ui.anim_defeat()
        sounds.play_defeat()
        ui.show_defeat(state, score, rank, diff_scores['winners'], diff_scores['losers'], state.difficulty)


if __name__ == '__main__':
    main()
