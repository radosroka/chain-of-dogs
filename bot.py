#!/usr/bin/env python3
"""
Chain of Dogs - AI Bot
Plays the game automatically using the optimal strategy from balance analysis:
  - Forage when water <= 1 or food <= 2
  - Rest when morale < 30
  - March otherwise
  - Always use Tactic 3: WICKAN FEINT in battles
"""
import sys
import os
import sqlite3

from game_state import GameState, WAYPOINTS, TOTAL_DIST
from events import EventSystem

DB_FILE = os.path.join(os.path.dirname(__file__), 'scores.db')

BOT_NAME = "BOT_WICKAN"
BATTLE_TACTIC = 3   # WICKAN FEINT: best score, 2nd-best win rate


def choose_action(state):
    if state.water <= 1 or state.food <= 2:
        return 'forage'
    if state.morale < 30:
        return 'rest'
    return 'march'


def calc_score(state):
    bonus = 50000 if state.won else 0
    return max(0, state.refugees + state.soldiers * 5 - state.day * 20 + bonus)


def save_score(name, score, won):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            score INTEGER NOT NULL,
            won   INTEGER NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO scores (name, score, won) VALUES (?, ?, ?)",
        (name, score, int(won))
    )
    conn.commit()
    rows = conn.execute(
        "SELECT name, score, won FROM scores ORDER BY score DESC LIMIT 100"
    ).fetchall()
    conn.close()
    winners = [{'name': r[0], 'score': r[1]} for r in rows if r[2]]
    losers  = [{'name': r[0], 'score': r[1]} for r in rows if not r[2]]
    group = winners if won else losers
    rank = next(
        i for i, e in enumerate(group)
        if e['name'] == name and e['score'] == score
    )
    return rank + 1, winners, losers


def bar(value, max_value, width=20, char='#'):
    filled = int(width * value / max(1, max_value))
    return f"[{char * filled}{'-' * (width - filled)}]"


def run():
    state = GameState()
    events = EventSystem(state)

    print("=" * 60)
    print("  CHAIN OF DOGS — AI BOT  (Tactic: WICKAN FEINT)")
    print("=" * 60)
    print(f"  Start: {state.soldiers:,} soldiers, {state.refugees:,} refugees")
    print(f"  Journey: {TOTAL_DIST} march-days across {len(WAYPOINTS)} waypoints")
    print()

    while not state.game_over:
        action = choose_action(state)
        event = events.process_day(action)

        wp = WAYPOINTS[state.waypoint_idx]['short']
        progress = f"{state.overall_progress * 100:.0f}%"
        print(
            f"  Day {state.day:>3} | {action:<6} | {wp:<8} {progress:>4} "
            f"| sol={state.soldiers:>4} ref={state.refugees:>6,} "
            f"food={state.food:>2} wat={state.water} mor={state.morale:>3}"
        )

        if state.game_over:
            break

        if event is None:
            break

        if event.type == 'attack':
            es = event.data['enemy_size']
            result = events.resolve_battle(BATTLE_TACTIC, es)
            outcome = "WIN" if result['victory'] else "HOLD"
            print(
                f"           BATTLE [{outcome}] vs {es:,} enemies | "
                f"-{result['soldier_losses']:,} sol, -{result['refugee_losses']:,} ref, "
                f"enemy -{result['enemy_losses']:,}"
            )
            state.check_loss()

        elif event.type not in ('nothing', 'scouts'):
            print(f"           EVENT: {event.data.get('message', event.type)}")

    print()
    print("=" * 60)
    score = calc_score(state)
    outcome = "VICTORY" if state.won else "DEFEAT"
    print(f"  {outcome} on day {state.day}")
    print(f"  Refugees surviving: {state.refugees:,}")
    print(f"  Soldiers surviving: {state.soldiers:,}")
    print(f"  Total refugee losses: {state.total_refugees_lost:,}")
    print(f"  Total soldier losses: {state.total_soldiers_lost:,}")
    print(f"  Score: {score:,}")

    rank, winners, losers = save_score(BOT_NAME, score, state.won)
    group_name = "VICTORIES" if state.won else "LAST STANDS"
    print(f"  Rank in {group_name}: #{rank}")
    print()
    for title, group, highlight in [
        ("VICTORIES — THE CHAIN HOLDS", winners, state.won),
        ("LAST STANDS — THE CHAIN BREAKS", losers, not state.won),
    ]:
        print(f"  {title}")
        for i, s in enumerate(group[:5], 1):
            marker = " <--" if highlight and s['name'] == BOT_NAME and s['score'] == score else ""
            print(f"    {i}. {s['name']:<20} {s['score']:>8,}{marker}")
        if not group:
            print("    (none yet)")
        print()
    print("=" * 60)


if __name__ == '__main__':
    run()
