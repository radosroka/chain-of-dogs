import os

from game_state import WAYPOINTS, TOTAL_DIST


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


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
        print(row("Food",      state.food,     30,   " days"))
        print(row("Water",     state.water,    10,   " days"))
        print(row("Morale",    state.morale,   100))
        print("  " + "-" * 68)
        print(f"  Enemy strength: ~{state.enemy_strength:,}")

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

    def render_battle(self, state, enemy_size, enemy_name):
        clear()
        print()
        print("  +" + "=" * 66 + "+")
        print(f"  |{'!! BATTLE !!':^66}|")
        print("  +" + "=" * 66 + "+")
        print()
        print(f"  {enemy_name}")
        print(f"  strikes with {enemy_size:,} warriors!")
        print()

        max_force = max(enemy_size, state.soldiers, 1)
        enemy_bars = max(1, int(enemy_size / max_force * 40))
        player_bars = max(1, int(state.soldiers / max_force * 40))

        print(f"  ENEMY  ({enemy_size:>7,}):  " + "#" * enemy_bars)
        print(f"  YOURS  ({state.soldiers:>7,}):  " + "+" * player_bars)
        print()
        print(f"  REFUGEE COLUMN: ~~~~~~~~~~~~~~~~~~~ ({state.refugees:,})")
        print()
        print("  " + "-" * 66)
        print("  CHOOSE YOUR TACTIC:")
        print()
        print("    [1] CHARGE        - Aggressive assault. Break their lines.")
        print("    [2] HOLD THE LINE - Defensive formation. Protect the column.")
        print("    [3] WICKAN FEINT  - Cavalry draws enemy. Column slips through.")
        print("    [4] NIGHT ASSAULT - Strike in darkness. High risk, high reward.")
        print()

        while True:
            choice = input("  > ").strip()
            if choice in ('1', '2', '3', '4'):
                return int(choice)
            print("  Choose 1-4.")

    def render_battle_result(self, state, result):
        clear()
        print()
        print("  +" + "=" * 66 + "+")
        if result['victory']:
            print(f"  |{'VICTORY - Enemy Repelled!':^66}|")
        else:
            print(f"  |{'The column survives...':^66}|")
        print("  +" + "=" * 66 + "+")
        print()
        print(f"  Tactic used:    {result['tactic_name']}")
        print()
        print(f"  Your losses:    {result['soldier_losses']:,} soldiers")
        print(f"  Civilian dead:  {result['refugee_losses']:,} refugees")
        print(f"  Enemy killed:   {result['enemy_losses']:,} rebels")
        print()
        if result['victory']:
            print("  The enemy breaks and retreats. For now, the chain holds.")
        else:
            print("  It was costly. But the column lives. The march continues.")

    def show_event_notification(self, state, message):
        clear()
        self.render(state)
        print(f"\n  >>> {message} <<<")
        input("\n  [Press Enter to continue...]")

    def show_victory(self, state, score, rank, scores):
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
        self._show_leaderboard(scores, rank)
        input("\n  [Press Enter...]")

    def show_defeat(self, state, score, rank, scores):
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
        self._show_leaderboard(scores, rank)
        input("\n  [Press Enter...]")

    def _show_leaderboard(self, scores, highlight_rank):
        print()
        print("  " + "-" * 50)
        print("  HIGH SCORES")
        print("  " + "-" * 50)
        for i, entry in enumerate(scores[:10]):
            marker = " <--" if i == highlight_rank else ""
            outcome = "WIN" if entry.get('won') else "   "
            print(f"  {i+1:>2}. {outcome} {entry['name']:<20} {entry['score']:>8,}{marker}")
        print("  " + "-" * 50)
