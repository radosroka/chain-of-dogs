```
 ██████╗██╗  ██╗ █████╗ ██╗███╗  ██╗     ██████╗ ███████╗
██╔════╝██║  ██║██╔══██╗██║████╗ ██║    ██╔═══██╗██╔════╝
██║     ███████║███████║██║██╔██╗██║    ██║   ██║█████╗
██║     ██╔══██║██╔══██║██║██║╚████║    ██║   ██║██╔══╝
╚██████╗██║  ██║██║  ██║██║██║ ╚███║    ╚██████╔╝██║
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚══╝    ╚═════╝ ╚═╝

██████╗  ██████╗  ██████╗ ███████╗
██╔══██╗██╔═══██╗██╔════╝ ██╔════╝
██║  ██║██║   ██║██║  ███╗███████╗
██║  ██║██║   ██║██║   ██║╚════██║
██████╔╝╚██████╔╝╚██████╔╝███████║
╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝

                   T H E   M A R C H   T O   A R E N
```

---

> *"They said that Coltaine of the Crow Clan, Fist of the 7th Army, led his charge  
> with fifty thousand civilians at his back — and the Whirlwind at his throat."*

---

## The Story

**Seven Cities has risen.**

The Whirlwind goddess stirs in the sands of Raraku. A hundred thousand rebels march
under the banner of Sha'ik. The Malazan garrisons are overrun, their soldiers slaughtered,
their cities burning.

You are **Coltaine of the Crow Clan** — newly appointed Fist of the battered 7th Malazan
Army. From the coast of Hissar, fifty thousand civilians beg for your protection: merchants,
servants, camp followers, children. They cannot fight. They cannot run. They can only
follow — a chain around your neck as you drag them across three hundred leagues of
hostile desert toward the fortress city of Aren.

Korbolo Dom's armies shadow your every step. Kamist Reloe's mage-killers probe your
flanks. The desert itself is your enemy: no water, no shade, no mercy.

History will remember this as **the Chain of Dogs.**

The refugees are the chain.

*You are the dog.*

---

## Screenshots

```
========================================================================
  CHAIN OF DOGS - THE MARCH TO AREN                           Day 23
========================================================================

  *===^---------o----------o----------o----------o----------o---------o
HISSAR        Ubaryd     Vathar      Sekala      G'dan    Sanimon   AREN
  Segment: Hissar  -->  Ubaryd  (6 days away)

  --------------------------------------------------------------------
  Soldiers   [█████████████████░░░]    2,800
  Refugees   [██████████████████░░]   45,230
  Food       [█████░░░░░░░░░░░░░░░]        8     days
  Water      [████░░░░░░░░░░░░░░░░]        2 (!) days
  Morale     [████████████░░░░░░░░]       62
  --------------------------------------------------------------------
  Enemy strength: ~26,400

  RECENT EVENTS:
    Day 23: 94 refugees die from exhaustion and thirst.
    Day 22: Supply cache found! +4 days food, +2 days water.
    Day 21: Disease sweeps the column. 287 refugees perish.
    Day 20: The column rests. Morale improves.

  ACTIONS:
    [1] March        - Advance the column (normal pace)
    [2] Forced March - Push hard (2x speed, costs morale & lives)
    [3] Rest         - Rest the column (recover morale)
    [4] Forage       - Gather supplies (gain food & water)
    [q] Quit
```

```
  +==================================================================+
  |                        !! BATTLE !!                              |
  +==================================================================+

  Korbolo Dom's Army of the Apocalypse
  strikes with 6,200 warriors!

  ENEMY  (  6,200):  ########################################
  YOURS  (  2,800):  ######################

  REFUGEE COLUMN: ~~~~~~~~~~~~~~~~~~~ (45,230)

  ------------------------------------------------------------------
  CHOOSE YOUR TACTIC:

    [1] CHARGE        - Aggressive assault. Break their lines.
    [2] HOLD THE LINE - Defensive formation. Protect the column.
    [3] WICKAN FEINT  - Cavalry draws enemy. Column slips through.
    [4] NIGHT ASSAULT - Strike in darkness. High risk, high reward.
```

---

## Gameplay

### The March

Each turn is one day. You choose how to advance:

| Action | Speed | Cost | Best When |
|---|---|---|---|
| **March** | 1 day progress | Food, water, attrition | Steady state |
| **Forced March** | 2 days progress | Morale, extra lives, double water | Enemy closing in, need distance |
| **Rest** | No progress | Food, water | Morale is collapsing |
| **Forage** | No progress | Nothing (risky) | Food or water near zero |

### The Column

You manage five critical resources:

- **Soldiers** — Your 7th Army and Wickan warriors. They fight. When they're gone, the column dies.
- **Refugees** — Fifty thousand souls. They die every day from heat, thirst, disease, and battle. Getting enough of them to Aren is your only true victory condition.
- **Food** — Days of rations remaining. Hits zero and people start dying faster.
- **Water** — Days of water remaining. More critical than food. The desert is not forgiving.
- **Morale** — The army's will to continue. Let it collapse and your soldiers melt away into the sands.

### Random Events

The desert and the rebels conspire against you:

| Event | Effect |
|---|---|
| **Attack** | Rebel forces strike — triggers battle |
| **Heat Wave** | -2 water immediately |
| **Disease** | Hundreds of refugees die, morale drops |
| **Supply Cache** | Food and water found |
| **Betrayal** | Local guides lead part of column astray, morale crashes |
| **Scouts Report** | Warning: battle coming |
| **New Refugees** | More civilians join, +people -food |
| **Atrocity News** | Word of rebel massacres, morale drops |

### Battles

When the rebels strike, you must choose a tactic:

| Tactic | Style | Risk | Best When |
|---|---|---|---|
| **Charge** | Aggressive assault | High losses, both sides | You're outnumbered and need to break them fast |
| **Hold the Line** | Defensive wall | Lower losses | Protecting the column is the priority |
| **Wickan Feint** | Cavalry misdirection | Variable | You need the column to slip past |
| **Night Assault** | Strike in darkness | Highest risk, highest reward | Desperate times |

Outcome depends on your **force ratio**, **morale**, and luck. Winning a battle boosts morale. Losing one costs it.

### The Route

```
HISSAR --> Ubaryd --> Vathar Forest --> Sekala Crossing --> G'danisban --> Sanimon --> AREN
           12 days      18 days           14 days            20 days       16 days    12 days
                                                                               (92 march-days total)
```

Each waypoint reached boosts morale. Vathar Forest and Sekala Crossing are the bloodiest legs.

### Victory & Defeat

**You win** when the column reaches Aren. The percentage of refugees who survive determines your rating:

| Survival Rate | Rating |
|---|---|
| > 80% | A masterful campaign. Coltaine's legend is secure. |
| 60–80% | A costly victory. But the refugees live. |
| < 60% | The gates open. The price was terrible. |

**You lose** if:
- Your soldiers are destroyed
- Fewer than 500 refugees survive
- Morale collapses to zero

---

## Installation & Running

Requires **Python 3.6+**, no dependencies.

```bash
git clone https://github.com/yourname/chain-of-dogs
cd chain-of-dogs
python3 main.py
```

---

## Lore & Inspiration

This game is based on events from **Deadhouse Gates** (Book 2 of the *Malazan Book of the Fallen*) by Steven Erikson — one of the most brutal and emotionally devastating military campaigns in fantasy literature.

The real Chain of Dogs spans roughly the second half of the novel and runs parallel to another storyline told through the eyes of civilians witnessing it from outside. Reading their perspective — watching Coltaine's army described as a "chain of dogs" dragging the refugees across the continent — is one of the most striking structural choices in modern fantasy.

Key figures of the historical campaign (not yet implemented in the game but part of the lore):
- **Coltaine** — Fist, Crow Clan, relentless
- **Duiker** — Imperial Historian, the witness
- **Lull** — Captain of the Sialk Marines
- **Bult** — Coltaine's second, veteran Wickan
- **Sormo E'nath** — Wickan warlock
- **Korbolo Dom** — Renegade Fist, leads the rebel armies
- **Kamist Reloe** — High Mage, commands the Whirlwind's sorcery

---

## License

MIT — see `LICENSE`.

*"They are the chain. He is the dog. And the Apocalypse howls at his heels."*
