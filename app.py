"""
VaultVote — Secure Campus E-Voting System
==========================================
Local:   python app.py  →  http://localhost:5000
Deploy:  gunicorn app:app
"""

import os, sqlite3, hashlib, secrets, time
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, g
from flask_cors import CORS

# ── App ──────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'vaultvote-hackathon-2026-secret-xK9pL2mN'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
CORS(app, supports_credentials=True)

# ── Database path (works locally + Railway + Render) ─────────
_BASE = os.path.dirname(os.path.abspath(__file__))
_VOL  = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '')
if _VOL:
    DB_PATH = os.path.join(_VOL, 'vaultvote.db')      # Railway persistent disk
elif os.environ.get('RENDER'):
    DB_PATH = '/tmp/vaultvote.db'                      # Render ephemeral
else:
    DB_PATH = os.path.join(_BASE, 'vaultvote.db')      # Local dev

# ── Admin credentials ─────────────────────────────────────────
ADMIN_ID       = 'ADMIN001'
ADMIN_PASSWORD = 'VaultAdmin@2026'

# ── Candidates (seeded at startup) ───────────────────────────
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

# ── DB helpers ────────────────────────────────────────────────
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
    if db: db.close()

def init_db():
    """Create tables + seed candidates using a direct connection."""
    conn = sqlite3.connect(DB_PATH)
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
            CREATE TABLE IF NOT EXISTS candidates (
                id        TEXT PRIMARY KEY,
                name      TEXT NOT NULL,
                party     TEXT NOT NULL,
                manifesto TEXT
            );
            CREATE TABLE IF NOT EXISTS votes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL,
                vote_hash    TEXT NOT NULL UNIQUE,
                timestamp    TEXT NOT NULL
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
        for c in CANDIDATES:
            conn.execute(
                'INSERT OR IGNORE INTO candidates (id,name,party,manifesto) VALUES (?,?,?,?)', c
            )
        conn.commit()
        n = conn.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
        print(f'✓ DB ready → {DB_PATH}  |  candidates: {n}')
    finally:
        conn.close()

# ── Crypto helpers ────────────────────────────────────────────
def make_salt():   return secrets.token_hex(32)

def hash_password(pwd, salt, uid):
    return hashlib.pbkdf2_hmac('sha256', (pwd+uid).encode(), salt.encode(), 310_000).hex()

def verify_password(pwd, salt, uid, stored):
    return secrets.compare_digest(hash_password(pwd, salt, uid), stored)

def vote_hash(uid, cid, nonce):
    return hashlib.sha256(f'{uid}:{cid}:{nonce}:{time.time_ns()}'.encode()).hexdigest()

def chain_hash(prev, vh, ts):
    return hashlib.sha256(f'{prev}:{vh}:{ts}'.encode()).hexdigest()

def gen_vote_id():   return 'VT-' + secrets.token_hex(6).upper()

def last_chain_hash(db):
    r = db.execute('SELECT chain_hash FROM audit_log ORDER BY id DESC LIMIT 1').fetchone()
    return r['chain_hash'] if r else 'GENESIS_' + '0'*56

# ── Auth decorators ───────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'student_id' not in session:
            return jsonify({'success':False,'error':'Not authenticated'}), 401
        return f(*a, **kw)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **kw):
        if session.get('role') != 'admin':
            return jsonify({'success':False,'error':'Admin only'}), 403
        return f(*a, **kw)
    return d

# ── Page routes ───────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# ── API: seed (always safe to call) ──────────────────────────
@app.route('/api/seed')
def seed():
    db = get_db()
    for c in CANDIDATES:
        db.execute('INSERT OR IGNORE INTO candidates (id,name,party,manifesto) VALUES (?,?,?,?)', c)
    db.commit()
    n = db.execute('SELECT COUNT(*) as n FROM candidates').fetchone()['n']
    return jsonify({'success':True, 'candidates':n})

# ── API: auth ─────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    d = request.get_json(silent=True) or {}
    sid  = d.get('student_id','').strip().upper()
    name = d.get('name','').strip()
    dept = d.get('department','').strip()
    pwd  = d.get('password','')

    if not all([sid,name,dept,pwd]):
        return jsonify({'success':False,'error':'All fields required'}), 400
    if len(sid) < 6:
        return jsonify({'success':False,'error':'Student ID must be 6+ characters'}), 400
    if len(pwd) < 8:
        return jsonify({'success':False,'error':'Password must be 8+ characters'}), 400
    if sid == ADMIN_ID:
        return jsonify({'success':False,'error':'Reserved ID'}), 400

    salt = make_salt()
    ph   = hash_password(pwd, salt, sid)
    db   = get_db()
    try:
        db.execute(
            'INSERT INTO voters (student_id,full_name,department,pass_hash,salt,registered_at,ip_address) VALUES (?,?,?,?,?,?,?)',
            (sid, name, dept, ph, salt, datetime.utcnow().isoformat(), request.remote_addr)
        )
        db.commit()
        return jsonify({'success':True,'message':f'Registered! ID: {sid}'})
    except sqlite3.IntegrityError:
        return jsonify({'success':False,'error':'Student ID already registered'}), 409

@app.route('/api/login', methods=['POST'])
def login():
    d   = request.get_json(silent=True) or {}
    sid = d.get('student_id','').strip().upper()
    pwd = d.get('password','')

    if sid == ADMIN_ID:
        if secrets.compare_digest(pwd, ADMIN_PASSWORD):
            session.clear()
            session['student_id'] = ADMIN_ID
            session['role']       = 'admin'
            return jsonify({'success':True,'role':'admin','name':'Administrator'})
        return jsonify({'success':False,'error':'Wrong admin password'}), 401

    db    = get_db()
    voter = db.execute('SELECT * FROM voters WHERE student_id=?',(sid,)).fetchone()
    if not voter:
        time.sleep(0.1)
        return jsonify({'success':False,'error':'Student ID not found'}), 404
    if not verify_password(pwd, voter['salt'], sid, voter['pass_hash']):
        return jsonify({'success':False,'error':'Incorrect password'}), 401

    session.clear()
    session['student_id'] = sid
    session['role']       = 'voter'
    session['name']       = voter['full_name']
    return jsonify({'success':True,'role':'voter','name':voter['full_name'],'has_voted':bool(voter['has_voted'])})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success':True})

@app.route('/api/me')
def me():
    if 'student_id' not in session:
        return jsonify({'authenticated':False})
    return jsonify({'authenticated':True,'student_id':session['student_id'],'role':session.get('role'),'name':session.get('name','Administrator')})

# ── API: candidates ───────────────────────────────────────────
@app.route('/api/candidates')
def get_candidates():
    db   = get_db()
    rows = db.execute('SELECT id,name,party,manifesto FROM candidates ORDER BY id').fetchall()
    return jsonify({'candidates':[dict(r) for r in rows]})

# ── API: vote ─────────────────────────────────────────────────
@app.route('/api/vote', methods=['POST'])
@login_required
def cast_vote():
    if session.get('role') == 'admin':
        return jsonify({'success':False,'error':'Admins cannot vote'}), 403

    d    = request.get_json(silent=True) or {}
    cid  = d.get('candidate_id','')
    sid  = session['student_id']
    db   = get_db()

    voter = db.execute('SELECT has_voted FROM voters WHERE student_id=?',(sid,)).fetchone()
    if not voter:
        return jsonify({'success':False,'error':'Voter not found'}), 404
    if voter['has_voted']:
        return jsonify({'success':False,'error':'Already voted'}), 403

    cand = db.execute('SELECT * FROM candidates WHERE id=?',(cid,)).fetchone()
    if not cand:
        return jsonify({'success':False,'error':'Invalid candidate'}), 400

    nonce  = secrets.token_hex(16)
    vh     = vote_hash(sid, cid, nonce)
    vid    = gen_vote_id()
    ts     = datetime.utcnow().isoformat()
    prev   = last_chain_hash(db)
    ch     = chain_hash(prev, vh, ts)

    try:
        db.execute('INSERT INTO votes (candidate_id,vote_hash,timestamp) VALUES (?,?,?)', (cid,vh,ts))
        db.execute('INSERT INTO audit_log (vote_id,candidate_id,candidate_name,sha256_hash,prev_hash,chain_hash,timestamp) VALUES (?,?,?,?,?,?,?)',
                   (vid, cid, cand['name'], vh, prev, ch, ts))
        db.execute('UPDATE voters SET has_voted=1,vote_id=?,voted_at=? WHERE student_id=?', (vid,ts,sid))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'success':False,'error':'Duplicate vote detected'}), 409

    return jsonify({'success':True,'vote_id':vid,'hash':vh,'chain_hash':ch,'timestamp':ts,'candidate':cand['name']})

@app.route('/api/verify/<vote_id>')
def verify_vote(vote_id):
    db  = get_db()
    row = db.execute('SELECT * FROM audit_log WHERE vote_id=?',(vote_id,)).fetchone()
    if not row:
        return jsonify({'verified':False,'error':'Vote ID not found'}), 404
    return jsonify({'verified':True,'vote_id':row['vote_id'],'candidate':row['candidate_name'],'hash':row['sha256_hash'],'chain_hash':row['chain_hash'],'timestamp':row['timestamp']})

# ── API: results ──────────────────────────────────────────────
@app.route('/api/results')
def get_results():
    db   = get_db()
    rows = db.execute('''
        SELECT c.id,c.name,c.party,COUNT(v.id) as vote_count
        FROM candidates c LEFT JOIN votes v ON c.id=v.candidate_id
        GROUP BY c.id ORDER BY vote_count DESC
    ''').fetchall()
    total  = db.execute('SELECT COUNT(*) as n FROM votes').fetchone()['n']
    treg   = db.execute('SELECT COUNT(*) as n FROM voters').fetchone()['n']
    tcast  = db.execute('SELECT COUNT(*) as n FROM voters WHERE has_voted=1').fetchone()['n']
    results = []
    for r in rows:
        results.append({'id':r['id'],'name':r['name'],'party':r['party'],
                        'votes':r['vote_count'],
                        'percentage':round(r['vote_count']/total*100,1) if total else 0})
    return jsonify({'results':results,'total_votes':total,'total_voters':treg,'votes_cast':tcast,
                    'turnout':round(tcast/treg*100,1) if treg else 0})

@app.route('/api/audit')
def get_audit():
    db   = get_db()
    rows = db.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 60').fetchall()
    return jsonify({'audit_log':[dict(r) for r in rows]})

# ── API: admin ────────────────────────────────────────────────
@app.route('/api/admin/dashboard')
@admin_required
def admin_dashboard():
    db      = get_db()
    treg    = db.execute('SELECT COUNT(*) as n FROM voters').fetchone()['n']
    tcast   = db.execute('SELECT COUNT(*) as n FROM voters WHERE has_voted=1').fetchone()['n']
    total   = db.execute('SELECT COUNT(*) as n FROM votes').fetchone()['n']
    nlog    = db.execute('SELECT COUNT(*) as n FROM audit_log').fetchone()['n']
    results = db.execute('''
        SELECT c.id,c.name,c.party,COUNT(v.id) as vote_count
        FROM candidates c LEFT JOIN votes v ON c.id=v.candidate_id
        GROUP BY c.id ORDER BY vote_count DESC
    ''').fetchall()
    voters  = db.execute('''
        SELECT student_id,full_name,department,has_voted,registered_at,voted_at
        FROM voters ORDER BY registered_at DESC LIMIT 50
    ''').fetchall()
    audit   = db.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 60').fetchall()

    # Verify chain integrity
    entries = db.execute('SELECT * FROM audit_log ORDER BY id').fetchall()
    valid   = True
    for i, e in enumerate(entries):
        prev = entries[i-1]['chain_hash'] if i > 0 else 'GENESIS_' + '0'*56
        if chain_hash(prev, e['sha256_hash'], e['timestamp']) != e['chain_hash']:
            valid = False; break

    return jsonify({
        'stats':{'total_voters':treg,'votes_cast':tcast,'total_votes':total,
                 'audit_entries':nlog,'turnout':round(tcast/treg*100,1) if treg else 0,'chain_valid':valid},
        'results':[dict(r) for r in results],
        'recent_voters':[dict(r) for r in voters],
        'audit_log':[dict(r) for r in audit]
    })

@app.route('/api/admin/reset', methods=['POST'])
@admin_required
def reset_election():
    db = get_db()
    db.execute('DELETE FROM votes')
    db.execute('DELETE FROM audit_log')
    db.execute('UPDATE voters SET has_voted=0,vote_id=NULL,voted_at=NULL')
    db.commit()
    return jsonify({'success':True,'message':'Election reset.'})

# ── Startup ───────────────────────────────────────────────────
init_db()

if __name__ == '__main__':
    print('\n' + '='*50)
    print('  VaultVote — http://localhost:5000')
    print('  Admin     — http://localhost:5000/admin')
    print('  ID: ADMIN001  |  Pass: VaultAdmin@2024')
    print('='*50 + '\n')
    app.run(debug=True, port=5000, host='0.0.0.0')
