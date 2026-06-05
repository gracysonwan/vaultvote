# 🗳️ VaultVote — Secure Campus E-Voting System

> Hackathon Project | Theme: Cybersecurity | Team: Gracy Sonwan

A cryptographically secure, full-stack campus e-voting platform with a cinematic 3D intro,
glassmorphism UI, blockchain-inspired audit trail, and a live admin dashboard.

---

## 🌐 Live Demo

| Page | Link |
|------|------|
| Voting Site | https://vaultvote-production.up.railway.app |
| Admin Panel | https://vaultvote-production.up.railway.app/admin |

**Admin Credentials**
- ID: `ADMIN001`
- Password: `VaultAdmin@2024`

---

## 📸 What It Looks Like

- **Cinematic Intro** — 3D glass bubbles, crystal shards, torus rings floating in baby-blue space. "VaultVote" types itself letter by letter with a 3D flip animation. Scroll to enter.
- **Main Site** — Baby blue glassmorphism, liquid blob follows your mouse, floating 3D cards, smooth scroll animations, scrolling marquee ticker
- **Candidate Cards** — Hover to flip the card and reveal the SHA-256 cryptographic hash. Click to select and vote.
- **Vote Receipt** — Full cryptographic receipt with SHA-256 hash + blockchain chain hash
- **Live Results** — Animated bar chart, live turnout percentage, auto-refreshes every 8 seconds
- **Admin Dashboard** — Full voter list, vote tally, blockchain chain integrity check, reset controls

---

## 📁 Project Structure

```
vaultvote/
├── app.py                  ← Flask backend (run this)
├── requirements.txt        ← pip dependencies
├── Procfile                ← for Railway/Render deployment
├── .gitignore              ← git ignore rules
├── README.md               ← this file
├── vaultvote.db            ← SQLite DB (auto-created on first run)
└── templates/
    ├── index.html          ← Main voting site (CSS + JS all embedded)
    └── admin.html          ← Admin dashboard (CSS + JS all embedded)
```

> Note: All CSS and JavaScript is embedded directly inside the HTML files.
> No separate static folder needed — just templates/ and app.py.

---

## 🚀 Run Locally in VS Code

### Step 1 — Install dependencies
```bash
pip install flask flask-cors gunicorn
```

### Step 2 — Delete old DB if it exists
```bash
# Windows
del vaultvote.db

# Mac/Linux
rm -f vaultvote.db
```

### Step 3 — Run the server
```bash
python app.py
```

You should see:
```
✓ DB ready → vaultvote.db  |  candidates: 5
==================================================
  VaultVote — http://localhost:5000
  Admin     — http://localhost:5000/admin
  ID: ADMIN001  |  Pass: VaultAdmin@2024
==================================================
```

### Step 4 — Open in Chrome (NOT Live Server)
```
http://localhost:5000          ← Voting site
http://localhost:5000/admin    ← Admin dashboard
```

⚠️ **Do NOT open with Live Server or by double-clicking the HTML file.**
**Always use `http://localhost:5000` — Flask must be running.**

---

## 🗳️ How to Use

### As a Voter
1. Open `http://localhost:5000`
2. Watch the 3D cinematic intro (scroll or click to skip)
3. Click **Login / Register** → Register with your Student ID
4. Login and scroll to **Meet the Candidates**
5. Hover a card to flip it and see the cryptographic hash
6. Click a candidate to select → click **Submit Encrypted Vote**
7. Confirm in the modal — see your full cryptographic receipt
8. Your Vote ID and SHA-256 hash prove your vote was counted

### As Admin
1. Open `http://localhost:5000/admin`
2. Login with `ADMIN001` / `VaultAdmin@2024`
3. See live stats, vote tally bars, full voter list
4. View the blockchain audit chain with all SHA-256 hashes
5. Chain integrity is automatically verified — any tampering is detected
6. Use Reset button to clear votes for a fresh demo

---

## 🔐 Security Features

| Feature | Implementation | Why It Matters |
|---------|---------------|----------------|
| Password Hashing | PBKDF2-HMAC-SHA256, 310,000 iterations | NIST standard — brute force resistant |
| Password Salting | 64-char random salt per user | Prevents rainbow table attacks |
| Vote Anonymity | Votes stored in separate table from voter identity | Your name never touches your ballot |
| Double-Vote Prevention | DB flag + session check + IntegrityError catch | Multiple layers of protection |
| Vote Integrity | SHA-256 hash with unique nonce per vote | Each vote is cryptographically unique |
| Audit Chain | Each entry hashed with previous (blockchain-style) | Tamper one entry → all subsequent hashes break |
| Timing Attack Prevention | `secrets.compare_digest` for all comparisons | Prevents password timing side-channels |
| Session Security | HTTPOnly cookies, SameSite=Lax | Prevents XSS/CSRF attacks |
| Admin Protection | Role-based session + separate auth wall | Admin functions completely isolated |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3 + Flask |
| Database | SQLite (RDBMS) |
| Cryptography | `hashlib` (PBKDF2, SHA-256) + `secrets` |
| 3D Graphics | Three.js r128 |
| Frontend | Vanilla HTML5 + CSS3 + JavaScript (ES5) |
| Fonts | Bebas Neue + Syne + DM Sans (Google Fonts) |
| Deployment | Railway / Render / PythonAnywhere |

---

## 🌍 Deploy to Railway (Permanent Always-On Link)

```bash
# 1. Push to GitHub
git init
git add .
git commit -m "VaultVote hackathon"
git branch -M main
git remote add origin https://github.com/YOURUSERNAME/vaultvote.git
git push -u origin main

# 2. Go to railway.app → Login with GitHub
# 3. New Project → Deploy from GitHub → select vaultvote
# 4. Settings → Start Command: gunicorn app:app
# 5. Settings → Networking → Generate Domain
# 6. Done! You get: https://vaultvote-production.up.railway.app
```

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main voting site |
| GET | `/admin` | Admin dashboard |
| POST | `/api/register` | Register a voter |
| POST | `/api/login` | Login (voter or admin) |
| POST | `/api/logout` | Logout |
| GET | `/api/me` | Check current session |
| GET | `/api/candidates` | List all candidates |
| POST | `/api/vote` | Cast a vote |
| GET | `/api/results` | Live election results |
| GET | `/api/audit` | Public audit log |
| GET | `/api/verify/<vote_id>` | Verify a vote by ID |
| GET | `/api/admin/dashboard` | Full admin data |
| POST | `/api/admin/reset` | Reset election |
| GET | `/api/seed` | Re-seed candidates |

---

## 🏆 Hackathon Judging Points

### Cybersecurity Concepts Demonstrated
1. **Hashing** — SHA-256 for votes, PBKDF2 for passwords
2. **Salting** — Unique salt per user prevents pre-computed attacks
3. **Anonymization** — Votes and identities in completely separate DB tables
4. **Blockchain Principle** — Chain hash links every audit entry to the previous
5. **Zero-Knowledge-Like Verification** — Voters can prove their vote exists without revealing who they voted for
6. **Constant-Time Comparison** — Prevents timing attacks on password verification
7. **Session Management** — HTTPOnly, SameSite cookie security

### What Makes This Stand Out
- Full working system — not just a mockup
- Real cryptography (not fake/simulated)
- Beautiful 3D glassmorphism UI that judges actually want to look at
- Live admin dashboard with chain integrity verification
- Deployed with a real URL — click and it works

---

## 👤 Team

Built for Hackathon — Cybersecurity Theme
Developer: Gracy Sonwan
College: VIT/SRM/Manipal tier
Stack: Python + Flask + SQLite + Three.js
