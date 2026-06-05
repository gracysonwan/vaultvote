# 🗳️ VaultVote — Secure Campus E-Voting System

A cryptographically secure campus e-voting system with a 3D cinematic intro,
glassmorphism UI, blockchain-inspired audit trail, and full admin dashboard.

---

## 📁 Project Structure

```
vaultvote/
├── app.py                  ← Flask backend (run this)
├── requirements.txt        ← pip dependencies
├── vaultvote.db            ← SQLite DB (auto-created on first run)
├── templates/
│   ├── index.html          ← Main voting site
│   └── admin.html          ← Admin dashboard
└── static/
    ├── css/
    │   └── style.css       ← Full stylesheet
    └── js/
        ├── intro.js        ← Three.js cinematic intro scene
        ├── site.js         ← Site background + transitions
        ├── app.js          ← Voting app logic
        └── admin.js        ← Admin dashboard logic
```

---

## 🚀 Setup & Run

### 1. Install Python dependencies
```bash
pip install flask flask-cors
```

### 2. Run the server
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000          ← Voting site
http://localhost:5000/admin    ← Admin dashboard
```

---

## 🔐 Admin Login
| Field      | Value              |
|------------|--------------------|
| Student ID | `ADMIN001`         |
| Password   | `VaultAdmin@2024`  |

---

## 🗳️ Demo Flow

1. Open `http://localhost:5000`
2. Watch the 3D cinematic intro (or scroll to skip)
3. Click **Login / Register** → Register a voter account
4. Login and vote for a candidate
5. See your cryptographic receipt with SHA-256 hash
6. View live results and audit log
7. Login as admin to see full dashboard

---

## 🔒 Security Features

| Feature | Implementation |
|---------|---------------|
| Password Hashing | PBKDF2-HMAC-SHA256 (310,000 iterations) |
| Vote Anonymity | Votes stored in separate table from voter identity |
| Double-Vote Prevention | DB flag + session check |
| Vote Integrity | SHA-256 hash per vote |
| Audit Chain | Blockchain-inspired chain hash (tamper-evident) |
| Timing Attack Prevention | `secrets.compare_digest` for password comparison |
| Session Security | HTTPOnly cookies, SameSite=Lax |

---

## 🎨 Tech Stack

- **Backend**: Python 3 + Flask + SQLite (RDBMS)
- **Frontend**: Vanilla HTML/CSS/JS
- **3D Graphics**: Three.js r128 (CDN)
- **Fonts**: Bebas Neue + Syne + DM Sans (Google Fonts)
- **Crypto**: `hashlib` (PBKDF2, SHA-256) + `secrets` module
