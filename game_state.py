DIFFICULTIES = {
    'easy': {
        'soldiers':           3200,
        'food':               22,
        'water':              7,
        'morale':             80,
        'march_r_loss':       0.001,
        'forced_r_loss':      0.004,
        'forced_s_loss':      0.007,
        'min_refugees':       200,
        'attack_weight':      14,
        'attack_day_bonus':   4,
        'attack_min':         0.05,
        'attack_max':         0.18,
        'disease_min':        50,
        'disease_max':        300,
        'betrayal_morale':    -8,
        'threshold_mod':      -0.07,
    },
    'normal': {
        'soldiers':           3200,
        'food':               20,
        'water':              5,
        'morale':             75,
        'march_r_loss':       0.002,
        'forced_r_loss':      0.006,
        'forced_s_loss':      0.01,
        'min_refugees':       500,
        'attack_weight':      20,
        'attack_day_bonus':   8,
        'attack_min':         0.08,
        'attack_max':         0.25,
        'disease_min':        100,
        'disease_max':        600,
        'betrayal_morale':    -12,
        'threshold_mod':      0.0,
    },
    'hard': {
        'soldiers':           2800,
        'food':               14,
        'water':              3,
        'morale':             72,
        'march_r_loss':       0.003,
        'forced_r_loss':      0.009,
        'forced_s_loss':      0.015,
        'min_refugees':       5000,
        'attack_weight':      24,
        'attack_day_bonus':   12,
        'attack_min':         0.12,
        'attack_max':         0.35,
        'disease_min':        300,
        'disease_max':        1200,
        'betrayal_morale':    -14,
        'threshold_mod':      0.05,
    },
}

WAYPOINTS = [
    {"name": "Hissar",          "short": "HISSAR",  "dist": 0},
    {"name": "Ubaryd",          "short": "Ubaryd",  "dist": 12},
    {"name": "Vathar Forest",   "short": "Vathar",  "dist": 18},
    {"name": "Sekala Crossing", "short": "Sekala",  "dist": 14},
    {"name": "G'danisban",      "short": "G'dan",   "dist": 20},
    {"name": "Sanimon",         "short": "Sanimon", "dist": 16},
    {"name": "Aren",            "short": "AREN",    "dist": 12},
]

TOTAL_DIST = sum(wp["dist"] for wp in WAYPOINTS[1:])  # 92 march-days


class GameState:
    def __init__(self, difficulty='normal', custom_diff=None):
        self.difficulty = difficulty
        self.custom_diff = custom_diff  # only set when difficulty == 'custom'
        d = self.diff
        self.day = 1
        self.soldiers = d['soldiers']
        self.refugees = 50000
        self.food = d['food']
        self.water = d['water']
        self.morale = d['morale']
        self.waypoint_idx = 0
        self.days_traveled = 0   # march-days since last waypoint
        self.enemy_strength = 28000
        self.game_over = False
        self.won = False
        self.log = []
        self.total_refugees_lost = 0
        self.total_soldiers_lost = 0
        self.pending_battle = None   # {'enemy_size': int, 'name': str, 'intel': bool} when awaiting tactic
        self.last_battle_result = None  # shown once after battle resolves
        self.scout_intel = False     # True if scouts event preceded the next battle

    @property
    def diff(self):
        if self.difficulty == 'custom' and self.custom_diff:
            return self.custom_diff
        return DIFFICULTIES.get(self.difficulty, DIFFICULTIES['normal'])

    def to_dict(self):
        return {
            'difficulty': self.difficulty,
            'custom_diff': self.custom_diff,
            'day': self.day,
            'soldiers': self.soldiers,
            'refugees': self.refugees,
            'food': self.food,
            'water': self.water,
            'morale': self.morale,
            'waypoint_idx': self.waypoint_idx,
            'days_traveled': self.days_traveled,
            'enemy_strength': self.enemy_strength,
            'game_over': self.game_over,
            'won': self.won,
            'log': self.log,
            'total_refugees_lost': self.total_refugees_lost,
            'total_soldiers_lost': self.total_soldiers_lost,
            'pending_battle': self.pending_battle,
            'last_battle_result': self.last_battle_result,
            'scout_intel': self.scout_intel,
        }

    @classmethod
    def from_dict(cls, d):
        obj = cls.__new__(cls)
        for k, v in d.items():
            setattr(obj, k, v)
        return obj

    @property
    def current_waypoint(self):
        return WAYPOINTS[self.waypoint_idx]

    @property
    def next_waypoint(self):
        idx = self.waypoint_idx + 1
        return WAYPOINTS[idx] if idx < len(WAYPOINTS) else None

    @property
    def segment_progress(self):
        """0.0-1.0 progress toward next waypoint"""
        nxt = self.next_waypoint
        if nxt is None:
            return 1.0
        return min(1.0, self.days_traveled / nxt["dist"]) if nxt["dist"] > 0 else 1.0

    @property
    def overall_progress(self):
        """0.0-1.0 overall journey progress"""
        done = sum(WAYPOINTS[i]["dist"] for i in range(1, self.waypoint_idx + 1))
        done += self.days_traveled
        return min(1.0, done / TOTAL_DIST)

    def add_log(self, message):
        self.log.insert(0, f"Day {self.day}: {message}")
        self.log = self.log[:8]

    def _advance_waypoint(self):
        nxt = WAYPOINTS[self.waypoint_idx + 1]
        overflow = self.days_traveled - nxt["dist"]
        self.waypoint_idx += 1
        self.days_traveled = max(0, overflow)
        self.add_log(f"The column reaches {WAYPOINTS[self.waypoint_idx]['name']}!")
        self.morale = min(100, self.morale + 5)

    def _check_waypoint(self):
        while self.waypoint_idx < len(WAYPOINTS) - 1:
            nxt = WAYPOINTS[self.waypoint_idx + 1]
            if nxt["dist"] > 0 and self.days_traveled >= nxt["dist"]:
                self._advance_waypoint()
            else:
                break

    def march(self):
        self.days_traveled += 1
        self.day += 1
        self.food = max(0, self.food - 1)
        self.water = max(0, self.water - 1)
        deaths = max(0, int(self.refugees * self.diff['march_r_loss']))
        self.refugees = max(0, self.refugees - deaths)
        self.total_refugees_lost += deaths
        self._check_waypoint()
        if deaths:
            self.add_log(f"{deaths:,} refugees die from exhaustion and thirst.")

    def forced_march(self):
        self.days_traveled += 2
        self.day += 1
        self.food = max(0, self.food - 1)
        self.water = max(0, self.water - 2)
        self.morale = max(0, self.morale - 5)
        r = max(0, int(self.refugees * self.diff['forced_r_loss']))
        s = max(0, int(self.soldiers * self.diff['forced_s_loss']))
        self.refugees = max(0, self.refugees - r)
        self.soldiers = max(0, self.soldiers - s)
        self.total_refugees_lost += r
        self.total_soldiers_lost += s
        self._check_waypoint()
        self.add_log(f"Forced march! {r:,} refugees, {s:,} soldiers lost.")

    def rest(self):
        self.day += 1
        self.food = max(0, self.food - 1)
        self.water = max(0, self.water - 1)
        self.morale = min(100, self.morale + 10)
        deaths = max(0, int(self.refugees * 0.0005))
        self.refugees = max(0, self.refugees - deaths)
        self.total_refugees_lost += deaths
        self.add_log("The column rests. Morale improves.")

    def forage(self):
        self.day += 1
        self.food = min(20, self.food + 4)
        self.water = min(10, self.water + 2)
        deaths = max(0, int(self.refugees * 0.001))
        self.refugees = max(0, self.refugees - deaths)
        self.total_refugees_lost += deaths
        self.add_log("Foraging parties return with supplies.")

    def check_win(self):
        if self.game_over:
            return self.won
        if self.waypoint_idx >= len(WAYPOINTS) - 1:
            self.game_over = True
            self.won = True
            return True
        return False

    def check_loss(self):
        if self.game_over:
            return not self.won
        reasons = []
        if self.soldiers <= 0:
            reasons.append("The 7th Army is destroyed. No one remains to guard the column.")
        if self.refugees <= self.diff['min_refugees']:
            reasons.append("The refugees are no more. The chain breaks.")
        if self.morale <= 0:
            reasons.append("Morale has collapsed. The army dissolves into the desert.")
        if reasons:
            for r in reasons:
                self.add_log(r)
            self.game_over = True
            return True
        return False

    def calc_score(self):
        bonus = 50000 if self.won else 0
        return max(0, self.refugees + self.soldiers * 5 - self.day * 20 + bonus)
