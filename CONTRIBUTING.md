## Contributing to VaultVote

Thanks for helping improve this campus e-voting prototype.

### Before you start

1. Read the README and `SECURITY.md`.
2. Open an issue for substantial behavior changes.
3. Never commit credentials, voter data, database files, or production secrets.

### Local workflow

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Use a separate local database and test with sample data only. Before opening a pull request, verify registration, login, one-vote enforcement, vote verification, and admin authorization.

### Pull requests

Keep changes focused, explain the security or user-facing impact, and include manual test steps. Do not claim cryptographic guarantees beyond what the implementation actually provides.
