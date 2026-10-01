# Debugging Runbook — LMP Vrinda Finance Engine

A layer-by-layer guide to diagnosing issues yourself, from the browser all the
way down to the extraction engine. Work **top to bottom**: each layer depends on
the ones below it, so fix the lowest failing layer first.

> Golden rule: **isolate the layer.** A request passes through many layers
> (Browser → Network/DNS → Caddy → FastAPI → DB / Extraction engine → OpenRouter).
> Test each layer independently to find exactly where it breaks, instead of
> guessing from the symptom.

---

## 0. The request path (memorize this)

```
Your Browser
   │  (DNS resolves finance.infinitelab.tech → VPS IP)
   │  (your local network / corporate proxy may interfere here)
   ▼
Caddy container  (ports 80/443, TLS, serves React, proxies /api)
   │
   ▼
FastAPI container  (uvicorn :8000)
   │
   ├── SQLite  (./data/database/finance.db)
   │
   └── Extraction engine  →  OpenRouter (cloud)  /  Ollama (local)  /  Tesseract
```

Common failure-to-layer mapping:

| Symptom | Most likely layer |
|---|---|
| Page won't load at all (ERR_EMPTY_RESPONSE, timeout) | DNS or Network/Firewall |
| Wrong site / "hcdn" / parking page | DNS (A record wrong / CDN alias) |
| Cert warning / not secure | Caddy TLS / DNS not pointing to VPS |
| Page loads but "Failed to fetch" on actions | Network (corporate proxy) OR Caddy→API |
| "Invalid username or password" | Auth / DB password hash |
| Extraction fails only in browser, works on server | **Corporate network blocking** |
| Extraction fails on server too | Backend / provider / OpenRouter key |

---

## Quick reference: the compose command

Every container command uses this prefix (run from `/opt/lmp-vrinda-finance-engine`):

```bash
DC="docker compose --env-file .env.deploy -f deploy/docker-compose.prod.yml"
# then e.g.:  $DC ps   /   $DC logs -f api
```

Set that once per SSH session and the rest of this doc's `$DC ...` commands work directly.

---

## Layer 1 — DNS & Domain

**What it does:** maps `finance.infinitelab.tech` to your VPS's public IP.

### 1.1 Find your VPS's REAL public IP
Do NOT trust `curl ifconfig.me` (it can show a proxy/NAT IP). The authoritative
source is Hostinger hPanel → VPS → **IP address** page.

```bash
# On the VPS — but cross-check against hPanel, which is authoritative:
curl -s ifconfig.me ; echo
```

> In our deployment the real IP was `187.126.117.45`, while `ifconfig.me` once
> reported a different (proxy) IP. Always confirm in hPanel.

### 1.2 Check what the domain resolves to
```bash
dig +short finance.infinitelab.tech
```
- **Must print ONLY your VPS IP** (one line).
- **Rotating / multiple IPs** = a CDN alias or wildcard is interfering (see 1.4).
- **An IP that isn't your VPS** = wrong A record.

From your Mac you can also use an external resolver:
```bash
dig +short finance.infinitelab.tech @8.8.8.8
nslookup finance.infinitelab.tech 1.1.1.1
```

### 1.3 Correct DNS setup (Hostinger → Domain → DNS Zone / Subdomains)
```
Type: A    Name: finance (or @ in the subdomain zone)    Value: <VPS IP>    TTL: 300
```
Leave MX / SPF / autodiscover / autoconfig records alone (those are email).

### 1.4 The CDN-alias trap (we hit this)
If the subdomain was auto-created as a Hostinger "website", it gets:
```
ALIAS @   → finance.infinitelab.tech.cdn.hstgr.net      ← CDN, hijacks the domain
CNAME www → ...cdn.hstgr.net
```
A `.cdn.hstgr.net` ALIAS/CNAME **overrides** your A record and serves Hostinger's
CDN (`Server: hcdn`) instead of your VPS. **Delete those** and keep only
`A @ → <VPS IP>`. You cannot have both.

### 1.5 Confirm you're hitting YOUR server, not a CDN
```bash
curl -s -I http://finance.infinitelab.tech/ | grep -i server
```
- `Server: Caddy` → good, reaching your VPS.
- `Server: hcdn` → still hitting Hostinger CDN; fix DNS (1.4).

### 1.6 Which IP does a request actually connect to?
```bash
curl -s -o /dev/null -w "connected to: %{remote_ip}\n" http://finance.infinitelab.tech/
```
Must equal your VPS IP.

> DNS changes take up to the TTL (300s = 5 min) to propagate. Re-check with `dig`
> until it's stable before concluding anything.

---

## Layer 2 — Network & Firewall

**What it does:** allows inbound traffic to reach ports 80/443 on the VPS, and
outbound traffic from the VPS to the internet (for OpenRouter + Let's Encrypt).

### 2.1 Is anything listening on 80/443 inside the VPS?
```bash
ss -tlnp | grep -E ':80|:443'
```
Expect `docker-proxy` on `0.0.0.0:80` and `0.0.0.0:443`. If missing → the Caddy
container isn't running (see Layer 4).

### 2.2 Is the local OS firewall blocking?
```bash
ufw status verbose
```
- `Status: inactive` → ufw not blocking.
- If active, ensure: `ufw allow 80`, `ufw allow 443`, `ufw allow 22` (SSH!).

### 2.3 THE KEY TEST — can the VPS reach its own public IP?
```bash
curl -s -m 5 -o /dev/null -w "self via public IP: %{http_code}\n" http://<VPS_PUBLIC_IP>/
```
- `200` (or a redirect) → inbound traffic reaches the server. Good.
- `000` → **inbound 80 is blocked upstream** (not by ufw if that's inactive).
  This means the **Hostinger panel firewall** (hPanel → VPS → Firewall) is
  dropping it. Either no firewall should be attached, or it must have inbound
  Accept rules for TCP 80, 443 (and 22 for SSH).

> We saw `self via public IP: 000` with ufw inactive and Caddy listening — that
> isolated the block to the Hostinger upstream layer. In our case there was NO
> panel firewall and the real issue was we were testing the WRONG IP (Layer 1).

### 2.4 Corporate network / proxy blocking the BROWSER (we hit this — important)
If the app works when tested **on the server** (Layers 3-6 all pass) but the
**browser** shows "Failed to fetch" / "ERR_EMPTY_RESPONSE" / a cert from an
unexpected issuer:

- Your **office/VPN network** (e.g. Netskope, Zscaler, corporate proxy) is
  intercepting or blocking the connection to your site.
- **Tell-tale signs:** the TLS cert issuer is `*.goskope.com` / `netskope` /
  your company CA; browser DevTools → Network shows a failed request to a
  company domain with an injected `Content-Security-Policy`.
- **Confirm:** open the site on your **phone over mobile data** (not office WiFi).
  If it works there → it's the corporate network, not the app.

### 2.5 Outbound from the VPS (needed for OpenRouter + HTTPS certs)
```bash
# From inside the api container — can it reach OpenRouter?
$DC exec api python -c "import httpx; print(httpx.get('https://openrouter.ai/api/v1/models', timeout=15).status_code)"
```
Expect `200`. If it errors, the VPS has no outbound internet / DNS, and both
extraction and Let's Encrypt cert issuance will fail.

---

## Layer 3 — Caddy (TLS + reverse proxy + static React)

**What it does:** terminates HTTPS (auto Let's Encrypt cert), serves the built
React app, and proxies `/api/*` to the FastAPI container.

### 3.1 Is Caddy running?
```bash
$DC ps          # lmp-vrinda-web should be Up, ports 0.0.0.0:80 and :443
```

### 3.2 Caddy logs (TLS + routing)
```bash
$DC logs caddy | tail -40
```
Look for:
- `"server is listening only on the HTTP port"` → **no domain was set**
  (deployed with blank domain) → no HTTPS. Re-run deploy with the domain.
- TLS/ACME errors (`obtaining certificate`, `challenge failed`) → Let's Encrypt
  couldn't validate the domain. Cause is almost always **DNS not pointing to the
  VPS yet** (Layer 1) or **port 80 blocked** (Layer 2) — ACME uses port 80.
- `certificate obtained successfully` → HTTPS is good.

### 3.3 Is HTTPS actually working?
```bash
curl -s -o /dev/null -w "HTTPS %{http_code}\n" https://finance.infinitelab.tech/
curl -s -o /dev/null -w "HTTP -> %{redirect_url} (%{http_code})\n" http://finance.infinitelab.tech/
```
Expect HTTPS `200` and HTTP a `308` redirect to https.

### 3.4 Does Caddy correctly proxy /api to the backend?
```bash
curl -s https://finance.infinitelab.tech/api/health ; echo
```
Expect `{"status":"ok",...}`. If the static site loads but `/api/health` fails,
the proxy block or the api container is the problem (Layer 4).

### 3.5 Caddy config reference
File: `deploy/Caddyfile`. Key points:
- `{$SITE_ADDRESS}` is set from `.env.deploy` — a domain enables HTTPS, `:80`
  serves plain HTTP on the IP.
- `/api/*` → `reverse_proxy api:8000` (with 300s timeouts for slow vision calls).
- everything else → static SPA (`try_files {path} /index.html`).

To change it: edit `deploy/Caddyfile`, then rebuild caddy:
```bash
$DC up -d --build caddy
```

---

## Layer 4 — Docker & Containers

**What it does:** runs the two containers (`lmp-vrinda-api`, `lmp-vrinda-web`),
injects env vars from `.env.deploy`, and mounts `./data` + `extraction-engine`.

### 4.1 Container status & health
```bash
$DC ps                 # both should be "Up"
docker ps -a           # includes stopped/crashed containers
```
If a container is restarting or exited, read its logs (4.3).

### 4.2 Did the images build with the latest code?
```bash
cd /opt/lmp-vrinda-finance-engine
git pull                                   # get latest code
$DC up -d --build                          # rebuild + restart
```
> Common mistake: pulling code but forgetting `--build`, so old images keep
> running. Always `--build` after `git pull`.

### 4.3 Container logs
```bash
$DC logs api    | tail -60      # backend
$DC logs caddy  | tail -60      # proxy
$DC logs -f                     # live tail BOTH (great while reproducing a bug)
```

### 4.4 Are the env vars actually inside the container?
The authoritative values the app runs with (not just the file):
```bash
$DC exec api printenv EXTRACTION_PROVIDER
$DC exec api printenv OPENROUTER_API_KEY        # should be your key
$DC exec api printenv AUTH_USERNAME
$DC exec api printenv JWT_SECRET | cut -c1-6     # just confirm it's non-empty
```
> The "variable is not set" warnings during build mean a `$` in `.env.deploy`
> was interpreted by Compose. bcrypt hashes contain `$` and are escaped as `$$`
> in the generated file — if you hand-edit `.env.deploy`, keep that escaping.

### 4.5 Open a shell inside a container
```bash
$DC exec api sh         # poke around /app, run python, etc.
```

### 4.6 Data & persistence
- Host data lives in `./data` (mounted to `/app/data` in the api container):
  `data/database/finance.db`, `data/sources/`, `data/reports/`.
- **Back up** = copy the `data/` folder. It survives rebuilds and redeploys.
- The extraction engine is mounted read-only at `/opt/extraction-engine`.

### 4.7 Full restart / clean rebuild
```bash
$DC down                 # stop & remove containers (data/ is preserved)
$DC up -d --build        # rebuild and start
```

---

## Layer 5 — Backend (FastAPI) & Auth

**What it does:** the API — months, sources, validation, reports, auth.

### 5.1 Health & config (no auth needed)
```bash
curl -s http://localhost/api/health ; echo
curl -s http://localhost/api/config ; echo    # shows auth_enabled, provider, etc.
```

### 5.2 Request logging (added for diagnosis)
Every request logs `METHOD path -> status (duration)`. Watch it live:
```bash
$DC logs -f api
```
Then reproduce the action in the browser. You will see e.g.:
```
GET /api/dashboard -> 200 (12ms)
POST /api/test/extract -> 200 (3660ms)
```
- **A line appears** → request reached the backend; the status/duration tells you more.
- **No line at all** → the request never arrived → it died at the network/proxy
  (Layer 2/3), typically the **corporate network** (2.4).

### 5.3 Auth: "Invalid username or password"
The password is stored **in the database** (`app_state` table), seeded from
`AUTH_PASSWORD_HASH` **only on first run**. Re-running deploy with a new password
does NOT change it — the DB keeps the original. To check / reset:

```bash
# See the stored hash (first chars only)
$DC exec api python -c "
from app.db import SessionLocal; from app.auth import get_app_state
db=SessionLocal(); print('hash starts:', get_app_state(db).password_hash[:12]); db.close()"

# RESET the password directly in the DB (authoritative; also revokes old tokens)
$DC exec api python -c "
import getpass; from app.db import SessionLocal; from app.auth import set_password
db=SessionLocal(); set_password(db, getpass.getpass('New admin password: ')); db.close(); print('updated')"
```

> Boot guard: if the password is empty or a known demo value, login returns
> `503` with a message to set a real password. Reset it as above.

### 5.4 Testing a protected endpoint from the CLI (quoting-safe)
Passwords with `$ ! " '` break inline shell JSON. Use a file to avoid quoting:
```bash
read -s -p "pw: " PW; echo
printf '{"username":"admin","password":"%s"}' "$PW" > /tmp/login.json
TOKEN=$(curl -s -X POST http://localhost/api/auth/login -H 'Content-Type: application/json' --data @/tmp/login.json | python3 -c "import sys,json;print(json.load(sys.stdin).get('token',''))")
rm -f /tmp/login.json
echo "token len: ${#TOKEN}"      # >0 means login worked
```

---

## Layer 6 — Extraction Engine & Providers

**What it does:** reads a scan → structured rows, via a configured provider.

### 6.1 Engine status
```bash
curl -s http://localhost/api/config | python3 -m json.tool    # see "extraction" block
```
`providers_loaded` lists what imported. `provider` is the active default.

### 6.2 THE definitive extraction test (bypasses browser, proxy, login)
Runs the engine directly inside the container against a real scan:
```bash
docker cp output-validation/input/<scan>.jpeg lmp-vrinda-api:/tmp/scan.jpeg
$DC exec api python -c "
import os; os.environ['EXTRACTION_PROVIDER']='openrouter'
from pathlib import Path; from app.services import extraction_service as es
try:
    r,_=es.extract_file(Path('/tmp/scan.jpeg'))
    print('SUCCESS receipts=',len(r.receipts),'payments=',len(r.payments),'period=',r.period)
except Exception as e:
    import traceback; traceback.print_exc(); print('FAILED:',e)
"
```
- `SUCCESS ...` → the engine works. Any browser failure is Layer 2 (network).
- `FAILED ... traceback` → the real error (SSL / key / timeout / parse).

The step logs also show in `$DC logs api`:
```
extract: start provider=openrouter file=scan.jpeg size=392406B
extract: done  provider=openrouter model=google/gemini-2.5-flash receipts=1 payments=3 (3660ms)
```

### 6.3 Provider notes
| Provider | Needs | Works on this VPS? |
|---|---|---|
| `openrouter` | `OPENROUTER_API_KEY`, outbound HTTPS | ✅ (default) |
| `ollama` | Ollama server + model (~6GB) + RAM | ❌ not installed on VPS |
| `tesseract` | tesseract binary + pytesseract | ✅ but weak on handwriting |
| `stub` | nothing (fixed demo data) | ✅ (for testing offline) |

Switch provider: edit `EXTRACTION_PROVIDER` in `.env.deploy`, then `$DC up -d`.

### 6.4 Common extraction errors
- `CERTIFICATE_VERIFY_FAILED` → TLS to OpenRouter blocked (corporate proxy on the
  machine running it; the VPS itself is clean — see 2.5).
- `OPENROUTER_API_KEY is not set` → key missing/typoed in `.env.deploy` (4.4).
- `Could not parse model output as JSON` → model returned non-JSON; retry.
- Nothing logged + browser "Failed to fetch" → **network block** (2.4), not the app.

---

## Decision tree — start here when "something is broken"

```
Can you load https://finance.infinitelab.tech/ at all?
│
├─ NO (timeout / ERR_EMPTY_RESPONSE / can't connect)
│   ├─ dig shows correct VPS IP?            → NO: fix DNS (Layer 1)
│   ├─ `self via public IP` returns 000?    → YES: inbound port blocked (Layer 2.3)
│   ├─ works on phone mobile-data?          → YES: corporate network block (Layer 2.4)
│   └─ `$DC ps` shows caddy Up?             → NO: start containers (Layer 4)
│
├─ Loads but cert warning / "not secure"
│   ├─ caddy logs show ACME failure?        → DNS (L1) or port 80 (L2) — ACME needs them
│   └─ "listening only on HTTP port"?       → deployed with blank domain; redeploy w/ domain
│
├─ Loads, but login fails ("Invalid username or password")
│   └─ reset password in DB (Layer 5.3) — the DB keeps the FIRST password set
│
├─ Logged in, but an action shows "Failed to fetch"
│   ├─ `$DC logs -f api` shows the request? → NO: network/proxy block (L2.4) — test on mobile
│   │                                         → YES: read the status/error in the log
│   └─ extraction specifically?             → run the direct engine test (Layer 6.2)
│
└─ Extraction fails
    ├─ direct engine test (6.2) SUCCESS?    → app is fine; browser issue is network (L2.4)
    └─ direct engine test FAILED?           → read traceback: key? SSL? timeout? (6.4)
```

---

## One-shot health check

Run this on the VPS to snapshot every layer at once:

```bash
cd /opt/lmp-vrinda-finance-engine
DC="docker compose --env-file .env.deploy -f deploy/docker-compose.prod.yml"

echo "== containers =="; $DC ps
echo "== listening ports =="; ss -tlnp | grep -E ':80|:443'
echo "== DNS =="; dig +short finance.infinitelab.tech
echo "== local health =="; curl -s http://localhost/api/health; echo
echo "== https health =="; curl -s https://finance.infinitelab.tech/api/health; echo
echo "== provider env =="; $DC exec -T api printenv EXTRACTION_PROVIDER
echo "== outbound to openrouter =="; $DC exec -T api python -c "import httpx;print(httpx.get('https://openrouter.ai/api/v1/models',timeout=15).status_code)"
echo "== recent api logs =="; $DC logs api | tail -15
```

Each line maps to a layer above. The first one that looks wrong is where to dig in.

---

## Day-2 cheat sheet

```bash
cd /opt/lmp-vrinda-finance-engine
DC="docker compose --env-file .env.deploy -f deploy/docker-compose.prod.yml"

$DC ps                      # status
$DC logs -f api             # live backend logs
$DC logs -f caddy           # live proxy/TLS logs
$DC restart api             # restart just the backend
$DC up -d --build           # rebuild + restart after `git pull`
$DC down                    # stop everything (data/ preserved)

git pull && $DC up -d --build         # deploy latest code
./deploy.sh                           # reconfigure (reuses .env.deploy if present)
rm .env.deploy && ./deploy.sh         # full reconfigure (new secrets/password/domain)
```

### Backups
```bash
tar czf lmp-backup-$(date +%F).tar.gz data/      # the DB + scans + reports
```

### Where things live
| What | Path |
|---|---|
| Generated secrets/config | `/opt/lmp-vrinda-finance-engine/.env.deploy` |
| Database | `data/database/finance.db` |
| Uploaded scans | `data/sources/<year>/<month>/` |
| Generated statements | `data/reports/<year>/<month>/revision-NN/` |
| Caddy / proxy config | `deploy/Caddyfile` |
| Compose file | `deploy/docker-compose.prod.yml` |
| Deploy script | `deploy.sh` |

---

## The one lesson from this deployment

Most of our pain was **not** the app — it was the layers around it:
1. **Wrong IP** — `ifconfig.me` lied; hPanel had the real IP.
2. **DNS CDN alias** — Hostinger's `.cdn.hstgr.net` hijacked the subdomain.
3. **Corporate network** — Netskope blocked the browser, so it "failed" even
   though the server was perfect.

When a symptom appears, **isolate the layer** with the tests above before changing
code. The app being healthy on the server (Layer 6.2 SUCCESS) while the browser
fails almost always means the problem is **above** the server — DNS or network.
