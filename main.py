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
    conn = sqlite3.connect(DB_FILE, timeout=10)
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


def _prompt_int(prompt, default, lo, hi):
    while True:
        raw = input(f"  {prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            v = int(raw)
            if lo <= v <= hi:
                return v
            print(f"  Enter a value between {lo} and {hi}.")
        except ValueError:
            print("  Numbers only.")


def ask_custom_diff():
    from game_state import DIFFICULTIES
    base = DIFFICULTIES['normal']
    clear()
    print("\n  CUSTOM DIFFICULTY — configure your own march.")
    print("  Press Enter to keep the default (shown in brackets).\n")
    print("  --- Resources ---")
    soldiers     = _prompt_int("Starting soldiers  (1600-3600)", base['soldiers'],    1600, 3600)
    food         = _prompt_int("Starting food days (8-25)",      base['food'],        8,    25)
    water        = _prompt_int("Starting water days (2-8)",      base['water'],       2,    8)
    morale       = _prompt_int("Starting morale    (40-90)",     base['morale'],      40,   90)
    print("\n  --- Enemy ---")
    print("  Attack frequency — 1=low, 2=medium, 3=high")
    freq = _prompt_int("  Choice", 2, 1, 3)
    atk_weight = {1: 12, 2: 20, 3: 30}[freq]
    atk_bonus  = {1:  4, 2:  8, 3: 14}[freq]
    print("  Battle difficulty — 1=easier, 2=standard, 3=harder")
    bdiff = _prompt_int("  Choice", 2, 1, 3)
    tmod = {1: -0.07, 2: 0.0, 3: 0.07}[bdiff]
    print("\n  --- Survival ---")
    min_ref      = _prompt_int("Min refugees to survive (100-8000)", base['min_refugees'], 100, 8000)
    disease_max  = _prompt_int("Max disease deaths per outbreak (200-1500)", base['disease_max'], 200, 1500)

    return {
        'soldiers':         soldiers,
        'food':             food,
        'water':            water,
        'morale':           morale,
        'march_r_loss':     base['march_r_loss'],
        'forced_r_loss':    base['forced_r_loss'],
        'forced_s_loss':    base['forced_s_loss'],
        'min_refugees':     min_ref,
        'attack_weight':    atk_weight,
        'attack_day_bonus': atk_bonus,
        'attack_min':       base['attack_min'],
        'attack_max':       base['attack_max'],
        'disease_min':      base['disease_min'],
        'disease_max':      disease_max,
        'betrayal_morale':  base['betrayal_morale'],
        'threshold_mod':    tmod,
    }


def ask_difficulty():
    clear()
    print("\n  Choose difficulty:\n")
    print("    [1] Easy   — more supplies, fewer attacks, battles easier")
    print("    [2] Normal — the Chain of Dogs as written")
    print("    [3] Hard   — scarce resources, relentless attacks, high loss threshold")
    print("    [4] Custom — set your own parameters (unranked)\n")
    while True:
        choice = input("  > ").strip()
        if choice == '1':
            return 'easy', None
        if choice == '2':
            return 'normal', None
        if choice == '3':
            return 'hard', None
        if choice == '4':
            return 'custom', ask_custom_diff()
        print("  Enter 1–4.")


def main():
    ui = UI()
    name = ui.ask_name()
    difficulty, custom_diff = ask_difficulty()
    sounds.play_start()
    music.generate_all()
    music.play_ambient()

    state = GameState(difficulty, custom_diff)
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
            from events import FACTION_WEAKNESSES, FACTION_WEAKNESS_HINTS, min_roll_for_victory
            sounds.play_danger()

            edata = event.data
            enemy_name = edata['name']
            intel = edata.get('intel', False)
            multi_wave = edata.get('multi_wave', False)
            weakness_tactic = FACTION_WEAKNESSES.get(enemy_name)
            weakness_hint = FACTION_WEAKNESS_HINTS.get(enemy_name)

            # ── Wave 1 ──────────────────────────────────────────────────
            wave_label = 1 if multi_wave else None
            min_rolls = {t: min_roll_for_victory(state, t, edata['enemy_size']) for t in range(1, 5)}
            ui.anim_attack_incoming(enemy_name, edata['enemy_size'], state.soldiers, intel)
            tactic = ui.render_battle(state, edata['enemy_size'], enemy_name, intel,
                                      weakness_tactic, weakness_hint, wave=wave_label,
                                      min_rolls=min_rolls)
            dice_roll = ui.get_dice_roll(sounds.play_dice_roll)
            ui.anim_battle_clash()
            sounds.play_battle()
            result = events.resolve_battle(tactic, edata['enemy_size'], enemy_name, dice_roll=dice_roll)
            clear()
            ui.render_battle_result(state, result, wave=wave_label)
            input("\n  [Press Enter to continue...]")
            state.check_loss()

            # ── Wave 2 (only if multi-wave, wave 1 was a win, not a retreat, still alive) ──
            if multi_wave and result['victory'] and not result.get('retreated') and not state.game_over:
                wave2_size = int(edata['enemy_size'] * 0.5)
                min_rolls2 = {t: min_roll_for_victory(state, t, wave2_size) for t in range(1, 5)}
                ui.anim_attack_incoming(enemy_name, wave2_size, state.soldiers, intel)
                tactic2 = ui.render_battle(state, wave2_size, enemy_name, intel,
                                           weakness_tactic, weakness_hint, wave=2,
                                           min_rolls=min_rolls2)
                dice_roll2 = ui.get_dice_roll(sounds.play_dice_roll)
                ui.anim_battle_clash()
                sounds.play_battle()
                result2 = events.resolve_battle(tactic2, wave2_size, enemy_name, dice_roll=dice_roll2)
                clear()
                ui.render_battle_result(state, result2, wave=2)
                input("\n  [Press Enter to continue...]")
                state.check_loss()


        elif event.type != 'nothing':
            msg = event.data.get('message', '')
            if msg:
                ui.show_event_notification(state, msg)

    clear()
    score = state.calc_score()
    music.stop()

    if state.difficulty == 'custom':
        rank, winners, losers = -1, [], []
    else:
        rank, all_scores = save_score(name, score, state.won, state.difficulty)
        diff_scores = all_scores[state.difficulty]
        winners, losers = diff_scores['winners'], diff_scores['losers']

    if state.won:
        ui.anim_victory()
        sounds.play_victory()
        ui.show_victory(state, score, rank, winners, losers, state.difficulty)
    else:
        ui.anim_defeat()
        sounds.play_defeat()
        ui.show_defeat(state, score, rank, winners, losers, state.difficulty)


if __name__ == '__main__':
    main()
