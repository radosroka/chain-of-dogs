import os
import time

from game_state import WAYPOINTS, TOTAL_DIST


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


_DICE_PIPS = {
    1: ["     ", "  o  ", "     "],
    2: [" o   ", "     ", "   o "],
    3: [" o   ", "  o  ", "   o "],
    4: [" o o ", "     ", " o o "],
    5: [" o o ", "  o  ", " o o "],
    6: [" o o ", " o o ", " o o "],
}

def _dice_face(n):
    r = _DICE_PIPS[n]
    return [".-----.", f"|{r[0]}|", f"|{r[1]}|", f"|{r[2]}|", "'-----'"]

def _two_dice(n1, n2):
    f1, f2 = _dice_face(n1), _dice_face(n2)
    return "\n".join(f"  {a}  {b}" for a, b in zip(f1, f2))


def bar(value, maxv, width=20, fill='█', empty='░'):
    filled = max(0, min(width, int((value / max(1, maxv)) * width)))
    return fill * filled + empty * (width - filled)


INTRO_TEXT = """
  +========================================================================+
  |                                                                        |
  |        C H A I N   O F   D O G S                                      |
  |                                                                        |
  |                 The March to Aren                                      |
  |                                                                        |
  |        Based on "Deadhouse Gates" by Steven Erikson                   |
  |                                                                        |
  +========================================================================+

  Seven Cities has erupted in the Whirlwind Rebellion.

  You are COLTAINE of the Crow Clan, Fist of the 7th Malazan Army.
  Your mission: escort 50,000 refugees from Hissar to the fortress city
  of Aren -- across 300 leagues of hostile desert while Sha'ik's vast
  rebel armies hunt you at every step.

  History will call it the Chain of Dogs.
  The refugees are the chain. You are the dog.

  -------------------------------------------------------------------------
  TIPS:
    - Watch your water -- the desert kills faster than rebels
    - Forced march gains ground but costs lives and morale
    - Rest when morale is low or your army will dissolve
    - In battle, match your tactic to your strength
  -------------------------------------------------------------------------
"""

VICTORY_ART = """
  +======================================================+
  |                                                      |
  |   V I C T O R Y                                     |
  |                                                      |
  |   The Chain of Dogs reaches Aren.                   |
  |                                                      |
  +======================================================+

        /\\
       /  \\
      / /\\ \\      THE WALLS OF AREN RISE BEFORE YOU.
     / /  \\ \\
    /________\\    Coltaine stands at the gate.
    |        |
    | A R E N|    The refugees pour through.
    |        |
    |________|    The chain holds.
"""

DEFEAT_ART = """
  +======================================================+
  |                                                      |
  |   T H E   C H A I N   B R E A K S                  |
  |                                                      |
  +======================================================+

    The desert claims what the rebels could not.

    Somewhere in the wastes of Seven Cities,
    the refugees march no more.

    Coltaine of the Crow Clan has failed.
    The Whirlwind howls in triumph.
"""


class UI:
    def ask_name(self):
        clear()
        print(INTRO_TEXT)
        while True:
            name = input("  Enter your name, Fist: ").strip()
            if name:
                return name
            print("  A name is required.")

    def show_intro(self):
        input("  [Press Enter to begin the march...]")

    def render(self, state):
        W = 72
        print("=" * W)
        title = "  CHAIN OF DOGS - THE MARCH TO AREN"
        day_str = f"Day {state.day}  "
        print(title + " " * (W - len(title) - len(day_str)) + day_str)
        print("=" * W)
        print()
        self._render_map(state)
        print()
        self._render_status(state)
        print()
        self._render_log(state)
        print()
        self._render_actions()

    def _render_map(self, state):
        MAP_W = 62
        n = len(WAYPOINTS) - 1
        wp_cols = [round(i / n * MAP_W) for i in range(len(WAYPOINTS))]

        overall = state.overall_progress
        player_col = min(MAP_W, int(overall * MAP_W))

        chars = []
        for col in range(MAP_W + 1):
            wp_here = None
            for i, wc in enumerate(wp_cols):
                if col == wc:
                    wp_here = i
                    break

            if col == player_col:
                chars.append('^')
            elif wp_here is not None:
                chars.append('*' if wp_here <= state.waypoint_idx else 'o')
            elif col < player_col:
                chars.append('=')
            else:
                chars.append('-')

        print("  " + "".join(chars))

        # Waypoint names centered under their columns
        name_buf = [' '] * (MAP_W + 6)
        for i, wp in enumerate(WAYPOINTS):
            col = wp_cols[i] + 2
            name = wp["short"]
            start = max(0, col - len(name) // 2)
            for j, c in enumerate(name):
                if start + j < len(name_buf):
                    name_buf[start + j] = c
        print("".join(name_buf))

        nxt = state.next_waypoint
        if nxt:
            days_left = nxt["dist"] - state.days_traveled
            print(f"  Segment: {state.current_waypoint['name']}  -->  {nxt['name']}  ({days_left} days away)")
        else:
            print(f"  Location: {state.current_waypoint['name']}")

    def _render_status(self, state):
        BAR_W = 20

        def row(label, val, maxv, suffix=""):
            b = bar(val, maxv, BAR_W)
            warn = " (!)" if val <= maxv * 0.2 else "    "
            return f"  {label:<10} [{b}]  {val:>7,}{warn}{suffix}"

        print("  " + "-" * 68)
        print(row("Soldiers",  state.soldiers, 3200))
        print(row("Refugees",  state.refugees, 50000))
        print(row("Food",      state.food,     20,   " days"))
        print(row("Water",     state.water,    10,   " days"))
        print(row("Morale",    int(state.morale),   100))
        print("  " + "-" * 68)
        print(f"  Enemy strength: ~{state.enemy_strength:,}    Rerolls: {state.rerolls}")

    def _render_log(self, state):
        print("  RECENT EVENTS:")
        entries = state.log[:5]
        if not entries:
            print("    (none yet)")
        else:
            for entry in entries:
                print(f"    {entry}")

    def _render_actions(self):
        print("  ACTIONS:")
        print("    [1] March        - Advance the column (normal pace)")
        print("    [2] Forced March - Push hard (2x speed, costs morale & lives)")
        print("    [3] Rest         - Rest the column (recover morale)")
        print("    [4] Forage       - Gather supplies (gain food & water)")
        print("    [q] Quit")
        print()

    def get_action(self):
        action_map = {'1': 'march', '2': 'forced', '3': 'rest', '4': 'forage', 'q': 'quit'}
        while True:
            choice = input("  > ").strip().lower()
            if choice in action_map:
                return action_map[choice]
            print("  Invalid choice. Enter 1-4 or q.")

    def render_battle(self, state, enemy_size, enemy_name, intel=True,
                      weakness_tactic=None, weakness_hint=None, wave=None, min_rolls=None):
        clear()
        print()
        print("  +" + "=" * 66 + "+")
        if wave:
            print(f"  |{'!! BATTLE — WAVE ' + str(wave) + ' !!':^66}|")
        else:
            print(f"  |{'!! BATTLE !!':^66}|")
        print("  +" + "=" * 66 + "+")
        print()
        print(f"  {enemy_name}")
        if intel:
            print(f"  strikes with {enemy_size:,} warriors!")
        else:
            low = round(enemy_size * 0.6 / 500) * 500
            high = round(enemy_size * 1.5 / 500) * 500
            print(f"  strikes with an estimated {low:,}–{high:,} warriors!")
            print(f"  (No scout intel — exact strength unknown.)")
        print()

        max_force = max(enemy_size, state.soldiers, 1)
        enemy_bars = max(1, int(enemy_size / max_force * 40))
        player_bars = max(1, int(state.soldiers / max_force * 40))

        if intel:
            print(f"  ENEMY  ({enemy_size:>7,}):  " + "#" * enemy_bars)
        else:
            print(f"  ENEMY  ({'?':>7}):  " + "#" * enemy_bars)
        print(f"  YOURS  ({state.soldiers:>7,}):  " + "+" * player_bars)
        print()
        print(f"  REFUGEE COLUMN: ~~~~~~~~~~~~~~~~~~~ ({state.refugees:,})")
        print()

        # Warnings
        if state.food == 0 and state.water == 0:
            print("  *** STARVING AND DEHYDRATED — soldiers fight at severe penalty ***")
        elif state.food == 0:
            print("  *** STARVING — hungry soldiers fight at a penalty ***")
        elif state.water == 0:
            print("  *** DEHYDRATED — parched soldiers fight at a penalty ***")
        days_gap = state.day - state.last_battle_day
        if state.last_battle_day > 0 and days_gap < 3:
            print(f"  *** BATTLE FATIGUE — fought {days_gap} day(s) ago, soldiers haven't recovered ***")

        if intel and weakness_hint:
            print(f"  [INTEL] {weakness_hint}")

        print()
        print("  " + "-" * 66)
        print("  CHOOSE YOUR TACTIC:")
        print()
        def _roll_hint(t):
            if not min_rolls:
                return ""
            r = min_rolls.get(t)
            if r is None:
                return "  [cannot win]"
            if r == 2:
                return "  [any roll wins]"
            if r == 12:
                return "  [critical only]"
            return f"  [need {r}+]"

        print(f"    [1] CHARGE        - Aggressive assault. Break their lines.{_roll_hint(1)}")
        print(f"    [2] HOLD THE LINE - Defensive formation. Protect the column.{_roll_hint(2)}")
        print(f"    [3] WICKAN FEINT  - Cavalry draws enemy. Column slips through.{_roll_hint(3)}")
        print(f"    [4] NIGHT ASSAULT - Strike in darkness. High risk, high reward.{_roll_hint(4)}")
        print( "    [5] DISENGAGE     - Retreat. Refugees scatter (chaos), morale drops.")
        print()

        while True:
            choice = input("  > ").strip()
            if choice in ('1', '2', '3', '4', '5'):
                return int(choice)
            print("  Choose 1-5.")

    def get_dice_roll(self, on_roll=None, rerolls=0, dice_mode='simulated'):
        import random

        def _show_prompt():
            clear()
            print()
            print("  +------------------------------------------+")
            print("  |   ROLL 2d6 — the battle's fate awaits   |")
            print("  +------------------------------------------+")
            print()
            print(_two_dice(1, 1).replace("o", "?"))
            print()

        while True:
            _show_prompt()

            if dice_mode == 'physical':
                while True:
                    raw = input("  Roll your dice and enter total (2-12): ").strip()
                    try:
                        total = int(raw)
                        if 2 <= total <= 12:
                            break
                        print("  Must be between 2 and 12.")
                    except ValueError:
                        print("  Enter a number.")
                if on_roll:
                    on_roll()
                # Minimal flash to show entered value
                clear()
                print()
                print("  +------------------------------------------+")
                print(f"  |   You entered: {total:<27}|")
                print("  +------------------------------------------+")
                print()
                print(_two_dice(1, 1).replace("o", "?"))
                print()

            else:
                input("  [Press Enter to roll...]")
                if on_roll:
                    on_roll()
                d1 = random.randint(1, 6)
                d2 = random.randint(1, 6)
                total = d1 + d2

                # Animation: spin fast → slow → land
                schedule = [(0.06, 9), (0.10, 5), (0.17, 3), (0.28, 2), (0.40, 1)]
                for delay, count in schedule:
                    for _ in range(count):
                        clear()
                        print()
                        print("  +------------------------------------------+")
                        print("  |              R O L L I N G ...           |")
                        print("  +------------------------------------------+")
                        print()
                        print(_two_dice(random.randint(1, 6), random.randint(1, 6)))
                        print()
                        time.sleep(delay)

                # Final frame
                clear()
                print()
                print("  +------------------------------------------+")
                print(f"  |   You rolled: {d1} + {d2} = {total:<23}|")
                print("  +------------------------------------------+")
                print()
                print(_two_dice(d1, d2))
                print()

            if rerolls > 0:
                choice = input(f"  [Enter] Accept  |  [R] Reroll ({rerolls} remaining): ").strip().lower()
                if choice == 'r':
                    rerolls -= 1
                    continue
            else:
                input("  [Press Enter to engage...]")
            return total, rerolls

    def render_battle_result(self, state, result, wave=None):
        clear()
        print()
        print("  +" + "=" * 66 + "+")
        if result.get('retreated'):
            print(f"  |{'RETREAT — The column disengages':^66}|")
        elif result.get('critical') == 'win':
            header = f"WAVE {wave} REPELLED!" if wave else "*** CRITICAL VICTORY! ***"
            print(f"  |{header:^66}|")
        elif result.get('critical') == 'loss':
            print(f"  |{'*** CRITICAL FAILURE! ***':^66}|")
        elif result['victory']:
            header = f"WAVE {wave} REPELLED!" if wave else "VICTORY - Enemy Repelled!"
            print(f"  |{header:^66}|")
        else:
            print(f"  |{'The column survives...':^66}|")
        print("  +" + "=" * 66 + "+")
        print()
        print(f"  Tactic used:    {result['tactic_name']}")
        print()
        if result.get('weakness_match'):
            print("  *** Exploited enemy weakness — extra damage dealt! ***")
        if result.get('attrition_penalty'):
            print("  *** Hungry/thirsty soldiers fought at a penalty. ***")
        if result.get('fatigue_penalty'):
            print("  *** Battle fatigue reduced effectiveness. ***")
        if result.get('critical_msg'):
            print(f"  {result['critical_msg']}")
            print()
        if result.get('weakness_match') or result.get('attrition_penalty') or result.get('fatigue_penalty'):
            print()
        print(f"  Your losses:    {result['soldier_losses']:,} soldiers")
        print(f"  Civilian dead:  {result['refugee_losses']:,} refugees")
        print(f"  Enemy killed:   {result['enemy_losses']:,} rebels")
        print()
        if result.get('retreated'):
            print("  The column breaks away. Chaos in the refugee train. We live.")
        elif result['victory']:
            print("  The enemy breaks and retreats. For now, the chain holds.")
        else:
            print("  It was costly. But the column lives. The march continues.")

    def show_event_notification(self, state, message):
        clear()
        self.render(state)
        print(f"\n  >>> {message} <<<")
        input("\n  [Press Enter to continue...]")

    def show_victory(self, state, score, rank, winners, losers, difficulty='normal'):
        clear()
        print(VICTORY_ART)
        print(f"  Days marched:      {state.day}")
        print(f"  Refugees saved:    {state.refugees:,}")
        print(f"  Refugees lost:     {state.total_refugees_lost:,}")
        print(f"  Soldiers lost:     {state.total_soldiers_lost:,}")
        pct = state.refugees / max(1, state.refugees + state.total_refugees_lost) * 100
        print(f"  Survival rate:     {pct:.1f}%")
        print(f"  Score:             {score:,}")
        print()
        if pct > 80:
            print("  A masterful campaign. Coltaine's legend is secure.")
        elif pct > 60:
            print("  A costly victory. But the refugees live.")
        else:
            print("  The gates open. The price was terrible. But they made it.")
        if difficulty == 'custom':
            print("\n  [ CUSTOM DIFFICULTY — UNRANKED ]")
        else:
            d = difficulty.upper()
            self._show_leaderboard(f"VICTORIES [{d}] — THE CHAIN HOLDS", winners, rank)
            self._show_leaderboard(f"LAST STANDS [{d}] — THE CHAIN BREAKS", losers, -1)
        input("\n  [Press Enter...]")

    def show_defeat(self, state, score, rank, winners, losers, difficulty='normal'):
        clear()
        print(DEFEAT_ART)
        print(f"  Days marched:   {state.day}")
        print(f"  Refugees alive: {state.refugees:,}")
        print(f"  Refugees lost:  {state.total_refugees_lost:,}")
        print(f"  Score:          {score:,}")
        print()
        print("  Final log:")
        for entry in state.log[:4]:
            print(f"    {entry}")
        if difficulty == 'custom':
            print("\n  [ CUSTOM DIFFICULTY — UNRANKED ]")
        else:
            d = difficulty.upper()
            self._show_leaderboard(f"VICTORIES [{d}] — THE CHAIN HOLDS", winners, -1)
            self._show_leaderboard(f"LAST STANDS [{d}] — THE CHAIN BREAKS", losers, rank)
        input("\n  [Press Enter...]")

    # ── Animations ──────────────────────────────────────────────────────

    def _play(self, frames, delay=0.13):
        for frame in frames:
            clear()
            print(frame)
            time.sleep(delay)

    def anim_march(self):
        self._play(_MARCH_FRAMES, delay=0.55)

    def anim_forced_march(self):
        self._play(_FORCED_FRAMES, delay=0.45)

    def anim_rest(self):
        self._play(_REST_FRAMES, delay=0.70)

    def anim_forage(self):
        self._play(_FORAGE_FRAMES, delay=0.65)

    def anim_attack_incoming(self, enemy_name, enemy_size, soldiers, intel=True):
        frames = _build_attack_frames(enemy_name, enemy_size, soldiers, intel)
        self._play(frames, delay=0.60)

    def anim_battle_clash(self):
        self._play(_CLASH_FRAMES, delay=0.50)

    def anim_victory(self):
        self._play(_VICTORY_FRAMES, delay=0.90)

    def anim_defeat(self):
        self._play(_DEFEAT_FRAMES, delay=1.10)

    # ── Leaderboard ─────────────────────────────────────────────────────

    def _show_leaderboard(self, title, scores, highlight_rank):
        print()
        print("  " + "-" * 50)
        print(f"  {title}")
        print("  " + "-" * 50)
        for i, entry in enumerate(scores[:10]):
            marker = " <--" if i == highlight_rank else ""
            print(f"  {i+1:>2}. {entry['name']:<20} {entry['score']:>8,}{marker}")
        if not scores:
            print("  (none yet)")
        print("  " + "-" * 50)


# ── ASCII animation frames ───────────────────────────────────────────────────

_MARCH_FRAMES = [
r"""
  THE COLUMN ADVANCES...

       o   o   o   o   o   o   o   o   o   o   o   o
      /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\
      /   /   /   /   /   /   /   /   /   /   /   /

      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
         refugees  refugees  refugees  refugees
      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

                                                  --->
""",
r"""
  THE COLUMN ADVANCES...

       o   o   o   o   o   o   o   o   o   o   o   o
       |\  |\  |\  |\  |\  |\  |\  |\  |\  |\  |\  |\
        \   \   \   \   \   \   \   \   \   \   \   \

      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
         refugees  refugees  refugees  refugees
      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

                                                   --->
""",
r"""
  THE COLUMN ADVANCES...

       o   o   o   o   o   o   o   o   o   o   o   o
      /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\
      /   /   /   /   /   /   /   /   /   /   /   /

      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
         refugees  refugees  refugees  refugees
      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

                                                    --->
""",
]

_FORCED_FRAMES = [
r"""
  FORCED MARCH!  PUSH ON!

       o  o  o  o  o  o  o  o  o  o  o  o  o  o
      /|>/|>/|>/|>/|>/|>/|>/|>/|>/|>/|>/|>/|>/|>
      /  /  /  /  /  /  /  /  /  /  /  /  /  /

     ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~
       refugees stumbling  refugees stumbling
     ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~

                                             ===>===>
""",
r"""
  FORCED MARCH!  PUSH ON!

      o  o  o  o  o  o  o  o  o  o  o  o  o  o
     >|\ >|\ >|\ >|\ >|\ >|\ >|\ >|\ >|\ >|\ >\
       \   \   \   \   \   \   \   \   \   \   \

     ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~
       refugees stumbling  refugees stumbling
     ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~

                                              ===>===>
""",
r"""
  FORCED MARCH!  PUSH ON!

       o  o  o  o  o  o  o  o  o  o  o  o  o  o
      /|>/|>/|>/|>/|>/|>/|>/|>/|>/|>/|>/|>/|>/|>
      /  /  /  /  /  /  /  /  /  /  /  /  /  /

     ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~
       refugees stumbling  refugees stumbling
     ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~ ~~

                                               ===>===>
""",
]

_REST_FRAMES = [
r"""
  THE COLUMN RESTS...

       o   o   o   o   o   o   o   o   o
       |   |   |   |   |   |   |   |   |     z
      /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\
       |   |   |   |   |   |   |   |   |
      / \ / \ / \ / \ / \ / \ / \ / \ / \

      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
           refugees  resting  at  ease
      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
""",
r"""
  THE COLUMN RESTS...

       o   o   o   o   o   o   o   o   o
       |   |   |   |   |   |   |   |   |      z z
      /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\
       |   |   |   |   |   |   |   |   |
      / \ / \ / \ / \ / \ / \ / \ / \ / \

      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
           refugees  resting  at  ease
      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
""",
r"""
  THE COLUMN RESTS...

       o   o   o   o   o   o   o   o   o
       |   |   |   |   |   |   |   |   |    z  Z  z
      /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\
       |   |   |   |   |   |   |   |   |
      / \ / \ / \ / \ / \ / \ / \ / \ / \

      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
           refugees  resting  at  ease
      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
""",
]

_FORAGE_FRAMES = [
r"""
  FORAGING PARTIES SENT OUT...

       o   o   o            o   o   o
       |   |   |            |   |   |
      /|\ /|\ /|\          /|\ /|\ /|\
                \          /
                 \        /
                  \      /
            o      \    /      o
           /|\      \  /      /|\
                   [cache]
""",
r"""
  FORAGING PARTIES RETURN...

       o   o   o            o   o   o
       |   |   |            |   |   |
      /|\ /|\ /|\          /|\ /|\ /|\
              \                /
               \              /
                \            /
          o      \__[FOOD]__/      o
         /|\         [H2O]        /|\
""",
r"""
  SUPPLIES SECURED!

       o   o   o   o   o   o   o   o
       |   |   |   |   |   |   |   |
      /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\

              [FOOD]  [FOOD]  [H2O]
              ~~~~~~  ~~~~~~  ~~~~~

      The column's spirits lift briefly.
""",
]


def _build_attack_frames(enemy_name, enemy_size, soldiers, intel=True):
    bar_e = max(1, min(36, int(enemy_size / max(enemy_size, soldiers, 1) * 36)))
    bar_p = max(1, min(36, int(soldiers   / max(enemy_size, soldiers, 1) * 36)))
    e_bar = '#' * bar_e + '·' * (36 - bar_e)
    p_bar = '+' * bar_p + '·' * (36 - bar_p)
    if intel:
        e_label = f"{enemy_size:,}"
    else:
        low = round(enemy_size * 0.6 / 500) * 500
        high = round(enemy_size * 1.5 / 500) * 500
        e_label = f"~{low:,}–{high:,}?"

    return [
        f"""
  !! ATTACK !!

  {enemy_name}

  ENEMY  [{e_bar}]  {e_label}
  YOURS  [{p_bar}]  {soldiers:,}

  >>>>>>>>                        <<<<<<<<
  >7th  >>           VS           <<rebel<
  >>>>>>>>                        <<<<<<<<

  The desert shakes with the thunder of hooves.
""",
        f"""
  !! ATTACK !!

  {enemy_name}

  ENEMY  [{e_bar}]  {e_label}
  YOURS  [{p_bar}]  {soldiers:,}

       >>>>>>>>              <<<<<<<<
       >7th  >>      VS      <<rebel<
       >>>>>>>>              <<<<<<<<

  Wickan outriders gallop to meet the threat.
""",
        f"""
  !! ATTACK !!

  {enemy_name}

  ENEMY  [{e_bar}]  {e_label}
  YOURS  [{p_bar}]  {soldiers:,}

              >>>>>>>>  <<<<<<<<
              >7th  >>  <<rebel<
              >>>>>>>>  <<<<<<<<

  CHOOSE YOUR TACTIC!
""",
    ]


_CLASH_FRAMES = [
r"""


              >>>>>>>>  <<<<<<<<
              >7th  >>  <<rebel<
              >>>>>>>>  <<<<<<<<


""",
r"""

                  >>X<<
                 >> X <<
                >>> X <<<
                 >> X <<
                  >>X<<

""",
r"""

                    *
                  * | *
                *--\|/--*
                   /|\
                *--/|\--*
                  * | *
                    *

         S  W  O  R  D  S     C L A S H
""",
r"""

             *    *   *    *    *
           *    *    *   *    *   *
         *   *    * * * * *    *    *
           *    *   * X *    *    *
         *   *   *   * *   *   *   *
           *     *   *   *    *   *
             *    *   *    *    *

""",
r"""

            .   .   .   .   .   .
          .   .   .   .   .   .   .
            .   .   .   .   .   .

         The dust begins to settle...

            .   .   .   .   .   .
""",
]

_VICTORY_FRAMES = [
r"""

      THE WALLS OF AREN...

                 |    |
      |          |    |          |
      |   /\     |    |     /\   |
      |  /  \    |    |    /  \  |
      | /    \   |    |   /    \ |
      |/      \  |    |  /      \|
      |        \ |    | /        |
      |____    |\|    |/|    ____|
      |    |   | ==== |   |    |
      |    |   |      |   |    |
""",
r"""

      THE GATES OF AREN...

                 |    |
      |          | !! |          |
      |   /\     |    |     /\   |
      |  /  \    |    |    /  \  |
      | /    \  /|    |\   /    \|
      |/      \/  \  /  \ /      |
      |        \   \/    /       |
      |____     \  /\   /   _____|
      |    |    \/    \/   |    |
      |    |               |    |
""",
r"""

      THE GATES OPEN!

      |          |      |          |
      |   /\     |      |     /\   |
      |  /  \    |      |    /  \  |
      | /    \   |      |   /    \ |
      |/      \  |      |  /      \|
      |________\ |      | /________|
      |    |    \|      |/    |    |
      |    |     \      /     |    |
      |    |      \    /      |    |
""",
r"""

      THE COLUMN ENTERS AREN!

      |          |  >>  |          |
      |   /\     | >>>  |     /\   |
      |  /  \    |>>>   |    /  \  |
      | /    \   |>>    |   /    \ |
      |/      \  |>  >> |  /      \|
      |________\ | >>>> | /________|
      |    |    \|      |/    |    |
      |    |      >>>>>>      |    |
      |    |      >>>>>>      |    |

      T H E   C H A I N   H O L D S .
""",
]

_DEFEAT_FRAMES = [
r"""
  THE CHAIN STRAINS...

       o   o   o   o   o   o   o   o   o   o   o   o
       |   |   |   |   |   |   |   |   |   |   |   |
      /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\ /|\
       |   |   |   |   |   |   |   |   |   |   |   |
      / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \

      ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
""",
r"""
  THE CHAIN BREAKS...

       o       o   o       o   o       o       o
       |       |   |       |   |       |       |
      /|\     /|\ /|\     /|\ /|\     /|\     /|\
                               |
      / \     / \ / \     / \ / \     / \     / \

      ~  ~         ~  ~         ~  ~         ~  ~
""",
r"""
  THE MARCH ENDS...

       o               o               o
       |               |               |
      /|\             /|\             /|\



      ~                   ~                   ~
""",
r"""

         .               .               .


                 .               .


         .               .               .


      The desert swallows all trace of the column.
      Coltaine has failed.
""",
]
