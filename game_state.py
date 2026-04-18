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
    def __init__(self):
        self.day = 1
        self.soldiers = 3200
        self.refugees = 50000
        self.food = 20
        self.water = 5
        self.morale = 75
        self.waypoint_idx = 0
        self.days_traveled = 0   # march-days since last waypoint
        self.enemy_strength = 28000
        self.game_over = False
        self.won = False
        self.log = []
        self.total_refugees_lost = 0
        self.total_soldiers_lost = 0

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
        deaths = max(0, int(self.refugees * 0.002))
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
        r = max(0, int(self.refugees * 0.006))
        s = max(0, int(self.soldiers * 0.01))
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
        self.food = min(30, self.food + 4)
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
        if self.refugees <= 500:
            reasons.append("The refugees are no more. The chain breaks.")
        if self.morale <= 0:
            reasons.append("Morale has collapsed. The army dissolves into the desert.")
        if reasons:
            for r in reasons:
                self.add_log(r)
            self.game_over = True
            return True
        return False
