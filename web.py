#!/usr/bin/env python3
import os
import sqlite3

from flask import Flask, session, redirect, url_for, render_template, request

from game_state import GameState, WAYPOINTS, TOTAL_DIST
from events import EventSystem
from ui import (_MARCH_FRAMES, _FORCED_FRAMES, _REST_FRAMES, _FORAGE_FRAMES,
                _CLASH_FRAMES, _VICTORY_FRAMES, _DEFEAT_FRAMES, _build_attack_frames)
import music

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chain-of-dogs-local-secret')

DB_FILE = os.path.join(os.path.dirname(__file__), 'scores.db')


def _get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            score INTEGER NOT NULL,
            won   INTEGER NOT NULL
        )
    """)
    conn.commit()
    return conn


def load_scores():
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT name, score, won FROM scores ORDER BY score DESC LIMIT 100"
        ).fetchall()
    return [{'name': r[0], 'score': r[1], 'won': bool(r[2])} for r in rows]


def save_score(name, score, won):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO scores (name, score, won) VALUES (?, ?, ?)",
            (name, score, int(won))
        )
        conn.commit()
    scores = load_scores()
    rank = next(
        i for i, e in enumerate(scores)
        if e['name'] == name and e['score'] == score
    )
    return rank, scores


def calc_score(state):
    score = state.refugees + state.soldiers * 5 - state.day * 20
    if state.won:
        score += 10000
    return max(0, score)


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


@app.route('/')
def index():
    scores = load_scores()
    return render_template('index.html', scores=scores[:10])


@app.route('/start', methods=['POST'])
def start():
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('index'))
    session.clear()
    session['name'] = name
    state = GameState()
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
    if state.pending_battle:
        pb = state.pending_battle
        page_anim_frames = _build_attack_frames(pb['name'], pb['enemy_size'], state.soldiers)

    return render_template('game.html', state=state, name=session.get('name', ''),
                           waypoints=WAYPOINTS, total_dist=TOTAL_DIST,
                           march_frames=_MARCH_FRAMES,
                           forced_frames=_FORCED_FRAMES,
                           rest_frames=_REST_FRAMES,
                           forage_frames=_FORAGE_FRAMES,
                           clash_frames=_CLASH_FRAMES,
                           page_anim_frames=page_anim_frames,
                           page_anim_delay=page_anim_delay)


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
    if tactic not in ('1', '2', '3', '4'):
        return redirect(url_for('game'))

    events = EventSystem(state)
    result = events.resolve_battle(int(tactic), state.pending_battle['enemy_size'])
    state.check_loss()
    state.pending_battle = None
    state.last_battle_result = result

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
    score = calc_score(state)
    rank, scores = save_score(name, score, state.won)
    end_anim = _VICTORY_FRAMES if state.won else _DEFEAT_FRAMES
    end_delay = 900 if state.won else 1100
    session.clear()
    return render_template('end.html', state=state, name=name,
                           score=score, rank=rank, scores=scores[:10],
                           page_anim_frames=end_anim,
                           page_anim_delay=end_delay)


if __name__ == '__main__':
    import threading
    threading.Thread(target=music.generate_all, daemon=True).start()
    app.run(debug=True, port=5000, use_reloader=False)
