#!/usr/bin/env python3
import os
import sqlite3

from flask import Flask, session, redirect, url_for, render_template, request

from game_state import GameState, WAYPOINTS, TOTAL_DIST
from events import EventSystem, min_roll_for_victory
from ui import (_MARCH_FRAMES, _FORCED_FRAMES, _REST_FRAMES, _FORAGE_FRAMES,
                _CLASH_FRAMES, _VICTORY_FRAMES, _DEFEAT_FRAMES, _build_attack_frames)
import music

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chain-of-dogs-local-secret')

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


def get_state():
    return GameState.from_dict(session['state'])


def save_state(state):
    session['state'] = state.to_dict()


@app.route('/music/<track>.ogg')
def serve_music(track):
    from flask import send_file
    paths = {'ambient': music.AMBIENT_OGG, 'battle': music.BATTLE_OGG}
    path = paths.get(track)
    if not path or not os.path.exists(path):
        return '', 404
    return send_file(path, mimetype='audio/ogg')


@app.route('/sounds/dice_roll.ogg')
def serve_dice_roll():
    from flask import send_file
    path = os.path.join(os.path.dirname(__file__), 'dice_roll.ogg')
    if not os.path.exists(path):
        return '', 404
    return send_file(path, mimetype='audio/ogg')


@app.route('/')
def index():
    scores = load_scores()
    return render_template('index.html', scores=scores)


@app.route('/start', methods=['POST'])
def start():
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('index'))
    difficulty = request.form.get('difficulty', 'normal')

    custom_diff = None
    if difficulty == 'custom':
        from game_state import DIFFICULTIES
        base = DIFFICULTIES['normal']

        def _fi(key, default, lo, hi):
            try:
                return max(lo, min(hi, int(request.form.get(key, default))))
            except (ValueError, TypeError):
                return default

        def _ff(key, default, lo, hi):
            try:
                return max(lo, min(hi, float(request.form.get(key, default))))
            except (ValueError, TypeError):
                return default

        custom_diff = {
            'soldiers':         _fi('c_soldiers',    base['soldiers'],    1600, 3600),
            'food':             _fi('c_food',         base['food'],        8,    25),
            'water':            _fi('c_water',        base['water'],       2,    8),
            'morale':           _fi('c_morale',       base['morale'],      40,   90),
            'march_r_loss':     base['march_r_loss'],
            'forced_r_loss':    base['forced_r_loss'],
            'forced_s_loss':    base['forced_s_loss'],
            'min_refugees':     _fi('c_min_refugees', base['min_refugees'], 100, 8000),
            'attack_weight':    _fi('c_attack_weight', base['attack_weight'], 8, 35),
            'attack_day_bonus': base['attack_day_bonus'],
            'attack_min':       base['attack_min'],
            'attack_max':       base['attack_max'],
            'disease_min':      base['disease_min'],
            'disease_max':      _fi('c_disease_max',  base['disease_max'], 200, 1500),
            'betrayal_morale':  base['betrayal_morale'],
            'threshold_mod':    _fi('c_threshold_mod', 0, -10, 10) / 100.0,
        }
    elif difficulty not in ('easy', 'normal', 'hard'):
        difficulty = 'normal'

    dice_mode = request.form.get('dice_mode', 'simulated')
    if dice_mode not in ('simulated', 'physical'):
        dice_mode = 'simulated'

    session.clear()
    session['name'] = name
    state = GameState(difficulty, custom_diff)
    state.dice_mode = dice_mode
    save_state(state)
    return redirect(url_for('game'))


@app.route('/game')
def game():
    if 'state' not in session:
        return redirect(url_for('index'))
    state = get_state()
    if state.game_over:
        return redirect(url_for('end'))

    page_anim_frames = None
    page_anim_delay = 600
    battle_min_rolls = None
    if state.pending_battle:
        pb = state.pending_battle
        page_anim_frames = _build_attack_frames(pb['name'], pb['enemy_size'], state.soldiers, pb.get('intel', True))
        battle_min_rolls = {t: min_roll_for_victory(state, t, pb['enemy_size']) for t in range(1, 5)}

    return render_template('game.html', state=state, name=session.get('name', ''),
                           battle_rerolls=state.rerolls,
                           waypoints=WAYPOINTS, total_dist=TOTAL_DIST,
                           march_frames=_MARCH_FRAMES,
                           forced_frames=_FORCED_FRAMES,
                           rest_frames=_REST_FRAMES,
                           forage_frames=_FORAGE_FRAMES,
                           clash_frames=_CLASH_FRAMES,
                           page_anim_frames=page_anim_frames,
                           page_anim_delay=page_anim_delay,
                           battle_min_rolls=battle_min_rolls)


@app.route('/action', methods=['POST'])
def action():
    if 'state' not in session:
        return redirect(url_for('index'))
    state = get_state()
    if state.pending_battle or state.game_over:
        return redirect(url_for('game'))

    act = request.form.get('action')
    if act not in ('march', 'forced', 'rest', 'forage'):
        return redirect(url_for('game'))

    state.last_battle_result = None
    events = EventSystem(state)
    event = events.process_day(act)

    if state.game_over:
        save_state(state)
        return redirect(url_for('end'))

    if event and event.type == 'attack':
        state.pending_battle = event.data

    save_state(state)
    return redirect(url_for('game'))


@app.route('/battle', methods=['POST'])
def battle():
    if 'state' not in session:
        return redirect(url_for('index'))
    state = get_state()
    if not state.pending_battle:
        return redirect(url_for('game'))

    tactic = request.form.get('tactic', '2')
    if tactic not in ('1', '2', '3', '4', '5'):
        return redirect(url_for('game'))

    dice_roll = None
    try:
        dr = int(request.form.get('dice_roll', ''))
        if 2 <= dr <= 12:
            dice_roll = dr
    except (ValueError, TypeError):
        pass

    try:
        rerolls_used = max(0, int(request.form.get('rerolls_used', 0)))
        state.rerolls = max(0, state.rerolls - rerolls_used)
    except (ValueError, TypeError):
        pass

    pb = state.pending_battle
    ev = EventSystem(state)
    result = ev.resolve_battle(int(tactic), pb['enemy_size'], pb.get('name'), dice_roll=dice_roll)
    state.check_loss()

    # Multi-wave: if wave 1 won (not retreated), queue wave 2
    if (pb.get('multi_wave') and result['victory'] and not result.get('retreated')
            and not state.game_over):
        wave2_size = int(pb['enemy_size'] * 0.5)
        state.pending_battle = {
            'enemy_size': wave2_size,
            'name': pb['name'],
            'intel': pb.get('intel', False),
            'multi_wave': False,
            'wave': 2,
        }
        state.last_battle_result = {**result, 'wave': 1, 'has_wave2': True}
    else:
        state.pending_battle = None
        state.last_battle_result = {**result, 'wave': pb.get('wave'), 'has_wave2': False}

    save_state(state)
    if state.game_over:
        return redirect(url_for('end'))
    return redirect(url_for('game'))


@app.route('/end')
def end():
    if 'state' not in session:
        return redirect(url_for('index'))
    state = get_state()
    if not state.game_over:
        return redirect(url_for('game'))
    name = session.get('name', 'Unknown')
    score = state.calc_score()
    end_anim = _VICTORY_FRAMES if state.won else _DEFEAT_FRAMES
    end_delay = 900 if state.won else 1100
    session.clear()

    if state.difficulty == 'custom':
        return render_template('end.html', state=state, name=name,
                               score=score, rank=-1,
                               winners=[], losers=[],
                               page_anim_frames=end_anim,
                               page_anim_delay=end_delay)

    rank, all_scores = save_score(name, score, state.won, state.difficulty)
    diff_scores = all_scores[state.difficulty]
    return render_template('end.html', state=state, name=name,
                           score=score, rank=rank,
                           winners=diff_scores['winners'],
                           losers=diff_scores['losers'],
                           page_anim_frames=end_anim,
                           page_anim_delay=end_delay)


if __name__ == '__main__':
    import threading
    threading.Thread(target=music.generate_all, daemon=True).start()
    app.run(debug=True, port=5000, use_reloader=False)
