# Deploying to a VPS

One script does everything: installs Docker, generates secrets, builds, and
starts the app behind Caddy with automatic HTTPS.

## Requirements
- A fresh **VPS** (Ubuntu/Debian), with root or a sudo user. (Shared/cloud web
  hosting will NOT work — this needs a real Linux machine.)
- A **domain** pointed at the server's IP (optional but needed for HTTPS).
- Your **OpenRouter API key** (if using the cloud extraction provider).

## Steps

1. Get the project onto the server (either works):
   ```bash
   # Option A — git
   git clone <your-repo-url> lmp-vrinda && cd lmp-vrinda

   # Option B — copy from your Mac
   rsync -av --exclude node_modules --exclude .venv --exclude data \
     ./ user@SERVER_IP:/opt/lmp-vrinda/
   ```

2. If you have a domain, point an **A record** at the server IP first
   (e.g. `finance.example.com -> 203.0.113.10`). HTTPS needs this.

3. Run the one script:
   ```bash
   ./deploy.sh
   ```
   It will:
   - install Docker + Compose if missing,
   - ask for your domain, admin username/password, extraction provider, and
     OpenRouter key (first run only),
   - generate a strong `JWT_SECRET` and bcrypt-hash your password into
     `.env.deploy` (kept at permissions 600, git-ignored),
   - build and start the containers.

4. Open the site:
   - With a domain: `https://your-domain/` (certificate provisions automatically
     on first visit).
   - Without: `http://SERVER_IP/`.
   Log in with the admin username/password you set.

## Day-2 operations

```bash
# Update to the latest code
git pull && ./deploy.sh

# Logs
docker compose --env-file .env.deploy -f deploy/docker-compose.prod.yml logs -f

# Stop / start
docker compose --env-file .env.deploy -f deploy/docker-compose.prod.yml down
docker compose --env-file .env.deploy -f deploy/docker-compose.prod.yml up -d

# Reconfigure (new password/domain/key): delete the env file and re-run
rm .env.deploy && ./deploy.sh
```

## What runs

```
Internet → Caddy (:80/:443, TLS + static React + /api proxy) → FastAPI (:8000)
                                                                     │
                                                         ./data (SQLite + files)
```

- **Two containers:** `lmp-vrinda-web` (Caddy) and `lmp-vrinda-api` (FastAPI).
- **Your data** lives in `./data` on the host — back it up by copying that folder.
- **Secrets** are in `.env.deploy` (never committed). Your real admin password
  lives in the database (`data/`), seeded from this file on first run.

## Security notes
- Auth is always on in production (the compose sets `AUTH_ENABLED=true`).
- Change the password or revoke all sessions anytime from the UI.
- Keep the `data/` folder across updates — it holds your password and statements.
- Open only ports 80/443 on the VPS firewall; the API (8000) is internal only.
