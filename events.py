import random
from game_state import GameState

ATTACK_NAMES = [
    "Sha'ik's Holy Desert Apocalypse",
    "Korbolo Dom's Army of the Apocalypse",
    "Leoman's Desert Raiders",
    "Kamist Reloe's Mage Host",
    "Tribal Confederation forces",
    "Sha'ik's Regulars",
]

TACTIC_DATA = {
    1: dict(name="CHARGE",        p_loss=0.08, e_loss=0.22, r_loss=0.004, threshold=0.45),
    2: dict(name="HOLD THE LINE", p_loss=0.05, e_loss=0.12, r_loss=0.002, threshold=0.50),
    3: dict(name="WICKAN FEINT",  p_loss=0.06, e_loss=0.18, r_loss=0.001, threshold=0.43),
    4: dict(name="NIGHT ASSAULT", p_loss=0.10, e_loss=0.28, r_loss=0.003, threshold=0.40),
}

# Each faction is vulnerable to one tactic (e_loss bonus ×1.4 when matched)
FACTION_WEAKNESSES = {
    "Sha'ik's Holy Desert Apocalypse":      1,  # CHARGE — direct shock breaks holy fervor
    "Korbolo Dom's Army of the Apocalypse": 4,  # NIGHT ASSAULT — regulars are blind in darkness
    "Leoman's Desert Raiders":              3,  # WICKAN FEINT — Wickan cavalry outmaneuver them
    "Kamist Reloe's Mage Host":             2,  # HOLD THE LINE — outlast the mage reserves
    "Tribal Confederation forces":          1,  # CHARGE — tribes shatter under direct assault
    "Sha'ik's Regulars":                   4,  # NIGHT ASSAULT — discipline crumbles in darkness
}

FACTION_WEAKNESS_HINTS = {
    "Sha'ik's Holy Desert Apocalypse":      "Their fervor falters under a direct, overwhelming assault.",
    "Korbolo Dom's Army of the Apocalypse": "Regulars rely on formation — darkness robs them of it.",
    "Leoman's Desert Raiders":              "Wickan cavalry have faced these desert raiders before.",
    "Kamist Reloe's Mage Host":             "Hold your line. Outlast the mage reserves — do not overextend.",
    "Tribal Confederation forces":          "Tribes shatter when hit hard and fast. Strike like a fist.",
    "Sha'ik's Regulars":                   "Night blinds soldiers who depend on drill and order.",
}


class Event:
    def __init__(self, etype, data=None):
        self.type = etype
        self.data = data or {}


class EventSystem:
    def __init__(self, state: GameState):
        self.state = state

    def _roll_event(self):
        s = self.state
        d = s.diff
        weights = {
            'attack':       d['attack_weight'] + (d['attack_day_bonus'] if s.day > 20 else 0),
            'heat_wave':    8  + (6 if s.water <= 2 else 0),
            'disease':      7  + (3 if s.morale < 50 else 0),
            'supply_cache': 8,
            'betrayal':     4  + (6 if s.morale < 40 else 0),
            'scouts':       8,
            'new_refugees': 7,
            'atrocity':     7,
            'nothing':      20,
        }
        total = sum(weights.values())
        roll = random.randint(1, total)
        cum = 0
        for k, v in weights.items():
            cum += v
            if roll <= cum:
                return k
        return 'nothing'

    def process_day(self, action):
        s = self.state

        if action == 'march':
            s.march()
        elif action == 'forced':
            s.forced_march()
        elif action == 'rest':
            s.rest()
        elif action == 'forage':
            s.forage()

        if s.check_win() or s.check_loss():
            return None

        etype = self._roll_event()

        if etype == 'attack':
            d = s.diff
            size = random.randint(
                int(s.enemy_strength * d['attack_min']),
                int(s.enemy_strength * d['attack_max']),
            )
            name = random.choice(ATTACK_NAMES)
            intel = s.scout_intel
            multi_wave = size >= 12000 and random.random() < 0.5
            if intel:
                s.add_log(f"ATTACK! {name} ({size:,} warriors)!")
            else:
                low = round(size * 0.6 / 500) * 500
                high = round(size * 1.5 / 500) * 500
                s.add_log(f"ATTACK! {name} (estimated {low:,}–{high:,} warriors)!")
            if multi_wave:
                s.add_log("Enemy forces are vast — they will attack in waves!")
            return Event('attack', {'enemy_size': size, 'name': name, 'intel': intel, 'multi_wave': multi_wave})

        elif etype == 'heat_wave':
            s.water = max(0, s.water - 2)
            msg = "A searing heat wave strikes. Water supplies dwindle rapidly."
            s.add_log(msg)
            return Event('heat_wave', {'message': msg})

        elif etype == 'disease':
            deaths = random.randint(s.diff['disease_min'], s.diff['disease_max'])
            s.refugees = max(0, s.refugees - deaths)
            s.total_refugees_lost += deaths
            s.morale = max(0, s.morale - 3)
            msg = f"Disease sweeps the column. {deaths:,} refugees perish."
            s.add_log(msg)
            s.check_loss()
            return Event('disease', {'deaths': deaths, 'message': msg})

        elif etype == 'supply_cache':
            food = random.randint(2, 8)
            water = random.randint(1, 4)
            s.food = min(20, s.food + food)
            s.water = min(10, s.water + water)
            msg = f"Supply cache found! +{food} days food, +{water} days water."
            s.add_log(msg)
            return Event('supply_cache', {'message': msg})

        elif etype == 'betrayal':
            s.morale = max(0, s.morale + s.diff['betrayal_morale'])
            msg = "Treachery! Local guides lead part of the column astray. Morale plummets."
            s.add_log(msg)
            s.check_loss()
            return Event('betrayal', {'message': msg})

        elif etype == 'scouts':
            s.scout_intel = True
            msg = "Wickan scouts report large enemy forces massing ahead. Prepare for battle."
            s.add_log(msg)
            return Event('scouts', {'message': msg})

        elif etype == 'new_refugees':
            n = random.randint(300, 1500)
            s.refugees += n
            s.food = max(0, s.food - 1)
            msg = f"{n:,} refugees fleeing rebel atrocities join the column."
            s.add_log(msg)
            return Event('new_refugees', {'count': n, 'message': msg})

        elif etype == 'atrocity':
            s.morale = max(0, s.morale - 7)
            msg = "Word of rebel massacres reaches the column. Grief and fury grip the soldiers."
            s.add_log(msg)
            s.check_loss()
            return Event('atrocity', {'message': msg})

        return Event('nothing', {'message': 'The march continues without incident.'})

    def resolve_battle(self, tactic, enemy_size, enemy_name=None):
        s = self.state

        # ── Retreat (tactic 5: DISENGAGE) ───────────────────────────────
        if tactic == 5:
            refugee_losses = max(0, int(s.refugees * random.uniform(0.04, 0.09)))
            refugee_losses = min(refugee_losses, int(s.refugees * 0.12))
            s.refugees = max(0, s.refugees - refugee_losses)
            s.total_refugees_lost += refugee_losses
            s.morale = max(0, s.morale - 15)
            s.scout_intel = False
            s.last_battle_day = s.day
            s.add_log(f"Retreat! Stampede and chaos — {refugee_losses:,} refugees lost. Soldiers intact.")
            return {
                'victory': False,
                'retreated': True,
                'tactic_name': 'DISENGAGE',
                'soldier_losses': 0,
                'enemy_losses': 0,
                'refugee_losses': refugee_losses,
                'weakness_match': False,
                'attrition_penalty': False,
                'fatigue_penalty': False,
            }

        td = TACTIC_DATA.get(tactic, TACTIC_DATA[2])

        force_ratio = s.soldiers / max(1, enemy_size)
        morale_mod = s.morale / 100.0

        p_loss = td['p_loss'] * (1.0 / max(0.3, min(2.5, force_ratio * 1.5)))
        e_loss = td['e_loss'] * max(0.4, min(1.8, force_ratio))
        r_loss = td['r_loss'] * (1.5 - morale_mod * 0.5)

        victory_penalty = 0.0

        # ── Faction weakness bonus ───────────────────────────────────────
        weakness_match = bool(enemy_name and FACTION_WEAKNESSES.get(enemy_name) == tactic)
        if weakness_match:
            e_loss *= 1.4

        # ── Pre-battle attrition ─────────────────────────────────────────
        attrition_penalty = s.food == 0 or s.water == 0
        if s.food == 0:
            p_loss *= 1.25
            victory_penalty += 0.08
        if s.water == 0:
            p_loss *= 1.35
            victory_penalty += 0.10

        # ── Consecutive battle fatigue ───────────────────────────────────
        days_gap = s.day - s.last_battle_day
        fatigue_penalty = s.last_battle_day > 0 and days_gap < 3
        if fatigue_penalty:
            mult = 1 + (3 - days_gap) * 0.15  # +15% or +30%
            p_loss *= mult
            victory_penalty += (3 - days_gap) * 0.06

        p_loss *= random.uniform(0.7, 1.3)
        e_loss *= random.uniform(0.7, 1.3)
        r_loss *= random.uniform(0.7, 1.3)

        soldier_losses = max(10, int(s.soldiers * p_loss))
        enemy_losses = max(50, int(enemy_size * e_loss))
        refugee_losses = max(0, int(s.refugees * r_loss))

        soldier_losses = min(soldier_losses, int(s.soldiers * 0.45))
        refugee_losses = min(refugee_losses, int(s.refugees * 0.06))

        victory_score = force_ratio * 0.3 + morale_mod * 0.3 + random.random() * 0.4 - victory_penalty
        victory = victory_score > td['threshold'] + s.diff['threshold_mod']

        s.soldiers = max(0, s.soldiers - soldier_losses)
        s.refugees = max(0, s.refugees - refugee_losses)
        s.total_soldiers_lost += soldier_losses
        s.total_refugees_lost += refugee_losses
        s.enemy_strength = max(0, s.enemy_strength - enemy_losses)

        s.scout_intel = False
        s.last_battle_day = s.day

        if victory:
            s.morale = min(100, s.morale + 8)
        else:
            s.morale = max(0, s.morale - 8)

        msg = (
            f"Battle ({td['name']}): -{soldier_losses:,} soldiers, "
            f"-{refugee_losses:,} refugees. Enemy lost {enemy_losses:,}. "
            f"{'Victory!' if victory else 'We held the line.'}"
        )
        s.add_log(msg)

        return {
            'victory': victory,
            'retreated': False,
            'tactic_name': td['name'],
            'soldier_losses': soldier_losses,
            'enemy_losses': enemy_losses,
            'refugee_losses': refugee_losses,
            'weakness_match': weakness_match,
            'attrition_penalty': attrition_penalty,
            'fatigue_penalty': fatigue_penalty,
        }
