#!/usr/bin/env python3
"""
Chain of Dogs — Monte Carlo Simulation
Runs thousands of automated games across all difficulties and strategies,
reporting win rates, survival stats, and cause-of-death breakdown.
"""
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from game_state import GameState
from events import EventSystem, TACTIC_DATA, FACTION_WEAKNESSES, min_roll_for_victory


# ── Strategy definitions ──────────────────────────────────────────────────────

def pick_action_smart(state):
    """Forage when low on supplies, rest when morale is critical, else march."""
    if state.water <= 1 or state.food <= 2:
        return 'forage'
    if state.morale < 30:
        return 'rest'
    return 'march'

def pick_action_aggressive(state):
    """Forced march when possible; only forage when truly desperate."""
    if state.water == 0 or state.food == 0:
        return 'forage'
    if state.morale < 20:
        return 'rest'
    return 'forced'

def pick_action_conservative(state):
    """Rest often, forage liberally, rarely force march."""
    if state.water <= 2 or state.food <= 3:
        return 'forage'
    if state.morale < 50:
        return 'rest'
    return 'march'

def pick_action_always_march(state):
    return 'march'


def pick_tactic_optimal(state, enemy_size, enemy_name):
    """Use the faction weakness if known, else pick the tactic with the best
    chance of victory given current force ratio and morale."""
    # Always exploit known weakness
    if enemy_name and enemy_name in FACTION_WEAKNESSES:
        return FACTION_WEAKNESSES[enemy_name]

    # Otherwise pick tactic with lowest minimum roll requirement
    best_tactic = 4  # NIGHT ASSAULT as fallback
    best_min = 999
    for t in range(1, 5):
        mr = min_roll_for_victory(state, t, enemy_size)
        if mr is None:
            continue
        if mr < best_min:
            best_min = mr
            best_tactic = t
    return best_tactic

def pick_tactic_fixed(tactic_id):
    return lambda state, enemy_size, enemy_name: tactic_id

def pick_tactic_random(state, enemy_size, enemy_name):
    return random.randint(1, 4)


def roll_2d6():
    return random.randint(1, 6) + random.randint(1, 6)


# ── Simulation runner ─────────────────────────────────────────────────────────

@dataclass
class RunResult:
    won: bool
    day: int
    score: int
    refugees_final: int
    soldiers_final: int
    refugees_lost: int
    soldiers_lost: int
    battles: int
    battle_wins: int
    death_cause: Optional[str]  # None if victory


def run_one(difficulty='normal', action_fn=pick_action_smart,
            tactic_fn=pick_tactic_optimal) -> RunResult:
    state = GameState(difficulty=difficulty)
    events = EventSystem(state)

    battles = 0
    battle_wins = 0
    death_cause = None

    while not state.game_over:
        action = action_fn(state)
        event = events.process_day(action)

        if state.game_over:
            break
        if event is None:
            break

        if event.type == 'attack':
            battles += 1
            es = event.data['enemy_size']
            name = event.data.get('name')
            tactic = tactic_fn(state, es, name)
            dice = roll_2d6()
            result = events.resolve_battle(tactic, es, name, dice_roll=dice)
            if result['victory']:
                battle_wins += 1

            # Multi-wave
            if (event.data.get('multi_wave') and result['victory']
                    and not result.get('retreated') and not state.game_over):
                wave2 = int(es * 0.5)
                battles += 1
                tactic2 = tactic_fn(state, wave2, name)
                dice2 = roll_2d6()
                result2 = events.resolve_battle(tactic2, wave2, name, dice_roll=dice2)
                if result2['victory']:
                    battle_wins += 1

            state.check_loss()

    # Determine cause of defeat
    if not state.won:
        if state.soldiers <= 0:
            death_cause = 'soldiers_gone'
        elif state.morale <= 0:
            death_cause = 'morale_collapse'
        else:
            death_cause = 'refugees_lost'

    return RunResult(
        won=state.won,
        day=state.day,
        score=state.calc_score(),
        refugees_final=state.refugees,
        soldiers_final=state.soldiers,
        refugees_lost=state.total_refugees_lost,
        soldiers_lost=state.total_soldiers_lost,
        battles=battles,
        battle_wins=battle_wins,
        death_cause=death_cause,
    )


# ── Stats aggregation ─────────────────────────────────────────────────────────

def aggregate(results):
    n = len(results)
    wins = [r for r in results if r.won]
    losses = [r for r in results if not r.won]

    win_rate = len(wins) / n * 100

    def avg(seq, key):
        vals = [getattr(r, key) for r in seq]
        return sum(vals) / len(vals) if vals else 0

    causes = defaultdict(int)
    for r in losses:
        causes[r.death_cause] += 1

    return {
        'n': n,
        'win_rate': win_rate,
        'avg_score': avg(results, 'score'),
        'avg_score_win': avg(wins, 'score'),
        'avg_score_loss': avg(losses, 'score'),
        'avg_day': avg(results, 'day'),
        'avg_day_win': avg(wins, 'day'),
        'avg_day_loss': avg(losses, 'day'),
        'avg_refugees_win': avg(wins, 'refugees_final'),
        'avg_refugees_loss': avg(losses, 'refugees_final'),
        'avg_refugees_lost': avg(results, 'refugees_lost'),
        'avg_battles': avg(results, 'battles'),
        'avg_battle_wins': avg(results, 'battle_wins'),
        'battle_win_rate': (avg(results, 'battle_wins') / avg(results, 'battles') * 100
                            if avg(results, 'battles') > 0 else 0),
        'death_soldiers': causes['soldiers_gone'],
        'death_morale': causes['morale_collapse'],
        'death_refugees': causes['refugees_lost'],
    }


# ── Printer ───────────────────────────────────────────────────────────────────

def print_stats(label, stats):
    n = stats['n']
    losses = n - round(stats['win_rate'] * n / 100)
    print(f"\n  {'─' * 58}")
    print(f"  {label}")
    print(f"  {'─' * 58}")
    print(f"  Runs          : {n:,}")
    print(f"  Win rate      : {stats['win_rate']:5.1f}%")
    print(f"  Avg score     : {stats['avg_score']:>8,.0f}  "
          f"(win: {stats['avg_score_win']:>8,.0f}  loss: {stats['avg_score_loss']:>8,.0f})")
    print(f"  Avg day ended : {stats['avg_day']:>5.1f}  "
          f"(wins: {stats['avg_day_win']:>5.1f}  losses: {stats['avg_day_loss']:>5.1f})")
    print(f"  Avg refugees  : surviving in wins: {stats['avg_refugees_win']:>7,.0f}  "
          f"at death: {stats['avg_refugees_loss']:>7,.0f}")
    print(f"  Avg ref. lost : {stats['avg_refugees_lost']:>7,.0f}")
    print(f"  Battles/game  : {stats['avg_battles']:>4.1f}  "
          f"battle win rate: {stats['battle_win_rate']:>4.1f}%")
    if losses > 0:
        print(f"  Deaths by     : soldiers={stats['death_soldiers']} ({stats['death_soldiers']/losses*100:.0f}%)  "
              f"morale={stats['death_morale']} ({stats['death_morale']/losses*100:.0f}%)  "
              f"refugees={stats['death_refugees']} ({stats['death_refugees']/losses*100:.0f}%)")


# ── Main ──────────────────────────────────────────────────────────────────────

SCENARIOS = [
    # (label, difficulty, action_fn, tactic_fn)
    ("EASY   | smart action | optimal tactic",   'easy',   pick_action_smart,        pick_tactic_optimal),
    ("NORMAL | smart action | optimal tactic",   'normal', pick_action_smart,        pick_tactic_optimal),
    ("HARD   | smart action | optimal tactic",   'hard',   pick_action_smart,        pick_tactic_optimal),
    ("NORMAL | smart action | always CHARGE",    'normal', pick_action_smart,        pick_tactic_fixed(1)),
    ("NORMAL | smart action | always HOLD LINE", 'normal', pick_action_smart,        pick_tactic_fixed(2)),
    ("NORMAL | smart action | always FEINT",     'normal', pick_action_smart,        pick_tactic_fixed(3)),
    ("NORMAL | smart action | always NIGHT",     'normal', pick_action_smart,        pick_tactic_fixed(4)),
    ("NORMAL | smart action | random tactic",    'normal', pick_action_smart,        pick_tactic_random),
    ("NORMAL | aggressive   | optimal tactic",   'normal', pick_action_aggressive,   pick_tactic_optimal),
    ("NORMAL | conservative | optimal tactic",   'normal', pick_action_conservative, pick_tactic_optimal),
    ("NORMAL | always march | optimal tactic",   'normal', pick_action_always_march, pick_tactic_optimal),
    ("HARD   | aggressive   | optimal tactic",   'hard',   pick_action_aggressive,   pick_tactic_optimal),
    ("HARD   | conservative | optimal tactic",   'hard',   pick_action_conservative, pick_tactic_optimal),
]

N_RUNS = 10_000

if __name__ == '__main__':
    if '--quick' in sys.argv:
        N_RUNS = 1_000

    print("=" * 62)
    print("  CHAIN OF DOGS — MONTE CARLO SIMULATION")
    print(f"  {N_RUNS:,} runs per scenario")
    print("=" * 62)

    for label, diff, action_fn, tactic_fn in SCENARIOS:
        results = [run_one(diff, action_fn, tactic_fn) for _ in range(N_RUNS)]
        print_stats(label, aggregate(results))

    print(f"\n  {'─' * 58}")
    print()
