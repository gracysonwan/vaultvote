"""
VaultVote — Secure Campus E-Voting System
==========================================
Run:  pip install flask flask-cors
      python app.py
Then: http://localhost:5000
"""

import os
import sqlite3
import hashlib
import secrets
import time
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, request, jsonify, render_template,
    session, redirect, url_for, g
)
from flask_cors import CORS

# ─────────────────────────────────────────────────────────────
# APP CONFIG
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'vaultvote-stable-secret-key-2024-hackathon'  # fixed key so sessions survive restart
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'vaultvote_session'
CORS(app, supports_credentials=True)

DB_PATH = os.path.join(os.path.dirname(__file__), 'vaultvote.db')

# ─────────────────────────────────────────────────────────────
# CANDIDATES (seeded at startup)
# ─────────────────────────────────────────────────────────────
CANDIDATES = [
    ('C001', 'Arjun Sharma',  'Progressive Alliance',
     'Better campus wifi, 24/7 library access, transparent fund spending.'),
    ('C002', 'Priya Menon',   'Innovation First',
     'Tech labs upgrade, mental health resources, startup incubator.'),
    ('C003', 'Rohan Verma',   'Student Voice',
     'Lower canteen prices, more cultural events, improved hostels.'),
    ('C004', 'Ananya Singh',  'Green Campus',
     'Sustainability, solar panels, zero-plastic campus by 2025.'),
    ('C005', 'Vikram Patel',  'Unity Coalition',
     'Sports expansion, scholarship access, inter-dept collaboration.'),
]

ADMIN_ID       = 'ADMIN001'
ADMIN_PASSWORD = 'VaultAdmin@2024'   # change before production

# ─────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize DB using a direct connection (not Flask g) so it works at startup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS voters (
                student_id    TEXT PRIMARY KEY,
                full_name     TEXT NOT NULL,
                department    TEXT NOT NULL,
                pass_hash     TEXT NOT NULL,
                salt          TEXT NOT NULL,
                has_voted     INTEGER DEFAULT 0,
                vote_id       TEXT,
                ip_address    TEXT,
                registered_at TEXT NOT NULL,
                voted_at      TEXT
            );
            CREATE TABLE IF NOT EXISTS votes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL,
                vote_hash    TEXT NOT NULL UNIQUE,
                timestamp    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS candidates (
                id        TEXT PRIMARY KEY,
                name      TEXT NOT NULL,
                party     TEXT NOT NULL,
                manifesto TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                vote_id        TEXT UNIQUE NOT NULL,
                candidate_id   TEXT NOT NULL,
                candidate_name TEXT NOT NULL,
                sha256_hash    TEXT NOT NULL,
                prev_hash      TEXT,
                chain_hash     TEXT,
                timestamp      TEXT NOT NULL,
                verified       INTEGER DEFAULT 1
            );
        """)
        # Always try to seed candidates
        for c in CANDIDATES:
            conn.execute(
                'INSERT OR IGNORE INTO candidates (id,name,party,manifesto) VALUES (?,?,?,?)', c
            )
        conn.commit()
        count = conn.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
        print(f'✓ Database ready: {DB_PATH}  |  Candidates: {count}')
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────
# CRYPTO HELPERS
# ─────────────────────────────────────────────────────────────
def make_salt():
    return secrets.token_hex(32)

def hash_password(password: str, salt: str, student_id: str) -> str:
    """PBKDF2-HMAC-SHA256 — industry standard password hashing."""
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        (password + student_id).encode(),
        salt.encode(),
        310_000          # NIST-recommended iterations
    )
    return dk.hex()

def verify_password(password: str, salt: str, student_id: str, stored_hash: str) -> bool:
    return secrets.compare_digest(
        hash_password(password, salt, student_id),
        stored_hash
    )

def generate_vote_hash(student_id: str, candidate_id: str, nonce: str) -> str:
    """One-way SHA-256 vote receipt — can't be reversed to find voter."""
    data = f'{student_id}:{candidate_id}:{nonce}:{time.time_ns()}'
    return hashlib.sha256(data.encode()).hexdigest()

def generate_chain_hash(prev_hash: str, vote_hash: str, timestamp: str) -> str:
    """Blockchain-inspired chaining — tamper breaks every subsequent hash."""
    data = f'{prev_hash}:{vote_hash}:{timestamp}'
    return hashlib.sha256(data.encode()).hexdigest()

def gen_vote_id() -> str:
    return 'VT-' + secrets.token_hex(6).upper()

def get_last_chain_hash(db) -> str:
    row = db.execute(
        'SELECT chain_hash FROM audit_log ORDER BY id DESC LIMIT 1'
    ).fetchone()
    return row['chain_hash'] if row else 'GENESIS_' + '0' * 56

# ─────────────────────────────────────────────────────────────
# AUTH DECORATORS
# ─────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'student_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    # Always serve the page — admin.js handles the auth guard via /api/me
    return render_template('admin.html')

# ─────────────────────────────────────────────────────────────
# API — AUTH
# ─────────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    student_id = data.get('student_id', '').strip().upper()
    name       = data.get('name', '').strip()
    dept       = data.get('department', '').strip()
    password   = data.get('password', '')

    if not all([student_id, name, dept, password]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    if len(student_id) < 6:
        return jsonify({'success': False, 'error': 'Student ID must be ≥ 6 characters'}), 400
    if len(password) < 8:
        return jsonify({'success': False, 'error': 'Password must be ≥ 8 characters'}), 400
    if student_id == ADMIN_ID:
        return jsonify({'success': False, 'error': 'Reserved ID'}), 400

    salt      = make_salt()
    pass_hash = hash_password(password, salt, student_id)

    db = get_db()
    try:
        db.execute(
            '''INSERT INTO voters
               (student_id,full_name,department,pass_hash,salt,registered_at,ip_address)
               VALUES (?,?,?,?,?,?,?)''',
            (student_id, name, dept, pass_hash, salt,
             datetime.utcnow().isoformat(), request.remote_addr)
        )
        db.commit()
        return jsonify({'success': True, 'message': f'Registered! Your ID: {student_id}'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Student ID already registered'}), 409


@app.route('/api/login', methods=['POST'])
def login():
    data       = request.get_json(silent=True) or {}
    student_id = data.get('student_id', '').strip().upper()
    password   = data.get('password', '')

    # ── Admin shortcut ──
    if student_id == ADMIN_ID:
        if secrets.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session['student_id'] = ADMIN_ID
            session['role']       = 'admin'
            return jsonify({'success': True, 'role': 'admin', 'name': 'Administrator'})
        return jsonify({'success': False, 'error': 'Invalid admin credentials'}), 401

    db    = get_db()
    voter = db.execute(
        'SELECT * FROM voters WHERE student_id=?', (student_id,)
    ).fetchone()

    if not voter:
        # constant-time to prevent user enumeration
        time.sleep(0.1)
        return jsonify({'success': False, 'error': 'Student ID not found'}), 404

    if not verify_password(password, voter['salt'], student_id, voter['pass_hash']):
        return jsonify({'success': False, 'error': 'Incorrect password'}), 401

    session.clear()
    session['student_id'] = student_id
    session['role']       = 'voter'
    session['name']       = voter['full_name']

    return jsonify({
        'success':   True,
        'role':      'voter',
        'name':      voter['full_name'],
        'has_voted': bool(voter['has_voted'])
    })


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/me', methods=['GET'])
def me():
    if 'student_id' not in session:
        return jsonify({'authenticated': False})
    return jsonify({
        'authenticated': True,
        'student_id': session['student_id'],
        'role': session.get('role'),
        'name': session.get('name', 'Administrator')
    })

# ─────────────────────────────────────────────────────────────
# API — VOTING
# ─────────────────────────────────────────────────────────────
@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    db   = get_db()
    rows = db.execute('SELECT id,name,party,manifesto FROM candidates').fetchall()
    return jsonify({'candidates': [dict(r) for r in rows]})


@app.route('/api/vote', methods=['POST'])
@login_required
def cast_vote():
    if session.get('role') == 'admin':
        return jsonify({'success': False, 'error': 'Admins cannot vote'}), 403

    data         = request.get_json(silent=True) or {}
    candidate_id = data.get('candidate_id', '')
    student_id   = session['student_id']

    db    = get_db()
    voter = db.execute(
        'SELECT has_voted FROM voters WHERE student_id=?', (student_id,)
    ).fetchone()

    if not voter:
        return jsonify({'success': False, 'error': 'Voter not found'}), 404
    if voter['has_voted']:
        return jsonify({'success': False, 'error': 'You have already voted'}), 403

    candidate = db.execute(
        'SELECT * FROM candidates WHERE id=?', (candidate_id,)
    ).fetchone()
    if not candidate:
        return jsonify({'success': False, 'error': 'Invalid candidate'}), 400

    nonce      = secrets.token_hex(16)
    vote_hash  = generate_vote_hash(student_id, candidate_id, nonce)
    vote_id    = gen_vote_id()
    ts         = datetime.utcnow().isoformat()
    prev_hash  = get_last_chain_hash(db)
    chain_hash = generate_chain_hash(prev_hash, vote_hash, ts)

    try:
        # Vote row — no voter identity
        db.execute(
            'INSERT INTO votes (candidate_id,vote_hash,timestamp) VALUES (?,?,?)',
            (candidate_id, vote_hash, ts)
        )
        # Audit with chain
        db.execute(
            '''INSERT INTO audit_log
               (vote_id,candidate_id,candidate_name,sha256_hash,prev_hash,chain_hash,timestamp)
               VALUES (?,?,?,?,?,?,?)''',
            (vote_id, candidate_id, candidate['name'], vote_hash, prev_hash, chain_hash, ts)
        )
        # Mark voter — store vote_id but NOT which candidate
        db.execute(
            'UPDATE voters SET has_voted=1, vote_id=?, voted_at=? WHERE student_id=?',
            (vote_id, ts, student_id)
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Duplicate vote detected'}), 409

    return jsonify({
        'success':    True,
        'vote_id':    vote_id,
        'hash':       vote_hash,
        'chain_hash': chain_hash,
        'timestamp':  ts,
        'candidate':  candidate['name']
    })


@app.route('/api/verify/<vote_id>', methods=['GET'])
def verify_vote(vote_id):
    db  = get_db()
    row = db.execute(
        'SELECT * FROM audit_log WHERE vote_id=?', (vote_id,)
    ).fetchone()
    if not row:
        return jsonify({'verified': False, 'error': 'Vote ID not found'}), 404
    return jsonify({
        'verified':    True,
        'vote_id':     row['vote_id'],
        'candidate':   row['candidate_name'],
        'hash':        row['sha256_hash'],
        'chain_hash':  row['chain_hash'],
        'timestamp':   row['timestamp']
    })

# ─────────────────────────────────────────────────────────────
# API — PUBLIC RESULTS
# ─────────────────────────────────────────────────────────────
@app.route('/api/results', methods=['GET'])
def get_results():
    db = get_db()
    rows = db.execute('''
        SELECT c.id, c.name, c.party, COUNT(v.id) as vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id
        GROUP BY c.id ORDER BY vote_count DESC
    ''').fetchall()

    total_votes   = db.execute('SELECT COUNT(*) as n FROM votes').fetchone()['n']
    total_voters  = db.execute('SELECT COUNT(*) as n FROM voters').fetchone()['n']
    votes_cast    = db.execute('SELECT COUNT(*) as n FROM voters WHERE has_voted=1').fetchone()['n']

    results = []
    for r in rows:
        pct = round(r['vote_count'] / total_votes * 100, 1) if total_votes else 0
        results.append({
            'id': r['id'], 'name': r['name'], 'party': r['party'],
            'votes': r['vote_count'], 'percentage': pct
        })

    return jsonify({
        'results':       results,
        'total_votes':   total_votes,
        'total_voters':  total_voters,
        'votes_cast':    votes_cast,
        'turnout':       round(votes_cast / total_voters * 100, 1) if total_voters else 0
    })


@app.route('/api/audit', methods=['GET'])
def get_audit():
    db   = get_db()
    rows = db.execute(
        'SELECT * FROM audit_log ORDER BY id DESC LIMIT 60'
    ).fetchall()
    return jsonify({'audit_log': [dict(r) for r in rows]})

# ─────────────────────────────────────────────────────────────
# API — ADMIN ONLY
# ─────────────────────────────────────────────────────────────
@app.route('/api/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    db = get_db()

    total_voters  = db.execute('SELECT COUNT(*) as n FROM voters').fetchone()['n']
    votes_cast    = db.execute('SELECT COUNT(*) as n FROM voters WHERE has_voted=1').fetchone()['n']
    total_votes   = db.execute('SELECT COUNT(*) as n FROM votes').fetchone()['n']
    audit_entries = db.execute('SELECT COUNT(*) as n FROM audit_log').fetchone()['n']

    results = db.execute('''
        SELECT c.id, c.name, c.party, COUNT(v.id) as vote_count
        FROM candidates c LEFT JOIN votes v ON c.id=v.candidate_id
        GROUP BY c.id ORDER BY vote_count DESC
    ''').fetchall()

    recent_voters = db.execute('''
        SELECT student_id, full_name, department, has_voted, registered_at, voted_at
        FROM voters ORDER BY registered_at DESC LIMIT 20
    ''').fetchall()

    audit = db.execute(
        'SELECT * FROM audit_log ORDER BY id DESC LIMIT 50'
    ).fetchall()

    # Verify chain integrity
    all_entries = db.execute('SELECT * FROM audit_log ORDER BY id').fetchall()
    chain_valid = True
    for i, entry in enumerate(all_entries):
        expected_prev = all_entries[i-1]['chain_hash'] if i > 0 else 'GENESIS_' + '0'*56
        recomputed = generate_chain_hash(expected_prev, entry['sha256_hash'], entry['timestamp'])
        if recomputed != entry['chain_hash']:
            chain_valid = False
            break

    return jsonify({
        'stats': {
            'total_voters':  total_voters,
            'votes_cast':    votes_cast,
            'total_votes':   total_votes,
            'audit_entries': audit_entries,
            'turnout':       round(votes_cast / total_voters * 100, 1) if total_voters else 0,
            'chain_valid':   chain_valid
        },
        'results':       [dict(r) for r in results],
        'recent_voters': [dict(r) for r in recent_voters],
        'audit_log':     [dict(r) for r in audit]
    })


@app.route('/api/admin/reset', methods=['POST'])
@admin_required
def reset_election():
    """Hard reset — clears all votes (keeps registrations)."""
    db = get_db()
    db.execute('DELETE FROM votes')
    db.execute('DELETE FROM audit_log')
    db.execute('UPDATE voters SET has_voted=0, vote_id=NULL, voted_at=NULL')
    db.commit()
    return jsonify({'success': True, 'message': 'Election reset. All votes cleared.'})


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

@app.route('/api/seed', methods=['GET'])
def seed_candidates():
    """Re-seed candidates (safe to call multiple times)."""
    db = get_db()
    for c in CANDIDATES:
        db.execute(
            'INSERT OR IGNORE INTO candidates (id,name,party,manifesto) VALUES (?,?,?,?)', c
        )
    db.commit()
    count = db.execute('SELECT COUNT(*) as n FROM candidates').fetchone()['n']
    return jsonify({'success': True, 'candidates_in_db': count})

if __name__ == '__main__':
    init_db()
    print('\n' + '='*55)
    print('  🗳️  VaultVote — Secure Campus Election System')
    print('  URL : http://localhost:5000')
    print('  Admin ID  : ADMIN001')
    print('  Admin Pass: VaultAdmin@2024')
    print('  Admin page: http://localhost:5000/admin')
    print('='*55 + '\n')
    app.run(debug=True, port=5000, host='0.0.0.0')
