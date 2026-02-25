# 🛠️ Development Setup Guide

This project offers **three different development approaches** depending on your needs:

## 🚀 Quick Start Options

### 1. **LOCAL Development** (⚡ Fastest - Frontend Only)
**Perfect for:** HTML, CSS, JS, and template changes with instant hot reload

```bash
# All platforms (run from project root)
python z_extras/dev_local.py
```

**Benefits:**
- ✅ Instant hot reload (no rebuilds)
- ✅ Native Flask debug mode
- ✅ Direct file system access
- ✅ Fastest development cycle for UI work

**Limitations:**
- ❌ No OBS WebSocket integration
- ❌ No scene watchers or file trigger watchers
- ❌ No raw WebSocket server (StreamerBot)
- ❌ Use Docker for full-stack testing

**Access:** http://localhost:5000

---

### 2. **Docker Development** (🐳 Containerized with Hot Reload)
**Perfect for:** Testing Docker setup while developing

```bash
# First move dev compose file to root (only needed once)
mv z_extras/docker-compose.dev.yml ./docker-compose.dev.yml

# Then run development container
docker-compose -f docker-compose.dev.yml up --build
```

**Benefits:**
- ✅ Matches production environment
- ✅ Volume mounts for live changes
- ✅ Flask debug mode in container
- ✅ Network isolation testing

**Access:** http://localhost:8081

---

### 3. **Production** (🚀 Full Production Setup)
**Perfect for:** Final testing and deployment

```bash
# All platforms
docker-compose up -d --build
```

**Benefits:**
- ✅ Production-ready configuration
- ✅ Optimized for performance
- ✅ Health checks enabled
- ✅ Proper logging

**Access:** http://localhost:8080

---

## 🔄 Development Workflow

### Frontend Development (HTML/CSS/JS)
1. **Use LOCAL development** for fastest feedback
2. Run `python z_extras/dev_local.py` from project root
3. Edit files in `templates/`, `static/css/`, `static/js/`
4. Refresh browser to see changes instantly
5. **Note:** OBS, scene watchers, and StreamerBot integration are not available in local mode — use Docker for those

### Backend Development (Python)
1. **Use Docker development** for realistic environment
2. Edit Python files — volume mounts will pick up changes
3. Check container logs for error messages
4. Rebuild with `docker compose up --build` if dependencies change

### Full Stack Testing
1. **Use Docker development** to test integration
2. Move `z_extras/docker-compose.dev.yml` to root if not already done
3. Run `docker-compose -f docker-compose.dev.yml up --build` to start containerized version
4. Test both frontend and backend changes
5. Verify everything works in containerized environment

### Production Validation
1. **Use Production setup** for final testing
2. Run `docker-compose up -d --build` to test production config
3. Verify performance and stability
4. Test with actual Smart TV devices

---

## 📁 File Change Detection

### What triggers hot reload:

#### LOCAL Development (frontend only):
- ✅ `templates/*.html` - Immediate on refresh  
- ✅ `static/css/*.css` - Immediate on refresh
- ✅ `static/js/*.js` - Immediate on refresh
- ✅ `routes/*.py` - Flask auto-reloads
- ❌ OBS / watcher / WebSocket changes — use Docker

#### Docker Development:
- ✅ `app.py` - Flask reloads in container
- ✅ `templates/*.html` - Volume mounted, immediate
- ✅ `static/css/*.css` - Volume mounted, immediate  
- ✅ `static/js/*.js` - Volume mounted, immediate
- ❌ `requirements.txt` - Requires rebuild
- ❌ `Dockerfile` changes - Requires rebuild

#### Production:
- ❌ All changes require `docker-compose up --build`

---

## 🎯 Which Setup to Use When

| Task | Recommended Setup | Why |
|------|------------------|-----|
| **HTML/CSS tweaks** | LOCAL | Instant refresh, no containers |
| **JavaScript changes** | LOCAL | Debug tools, instant feedback |
| **Python/Flask changes** | Docker Dev | Full-stack environment |
| **Testing integrations** | Docker Dev | OBS, StreamerBot, watchers |
| **Smart TV testing** | Docker Dev/Prod | Network accessibility |
| **Final validation** | Production | Real deployment conditions |

---

## � Logging

All server output uses Python's `logging` module with both **console** and **file** handlers.

### Log Files
- **Location:** `data/logs/ata.log`
- **Rotation:** 5 MB max per file, 3 backup files kept (`ata.log.1`, `ata.log.2`, `ata.log.3`)
- **Format:** `2026-02-25 15:04:15  INFO      [module_name]  Message text`

### Changing Log Verbosity
Set the `LOG_LEVEL` environment variable to get more (or less) verbose output:

```bash
# Local development — see everything (very verbose)
LOG_LEVEL=DEBUG python z_extras/dev_local.py

# Docker — add to docker-compose.yml environment section
environment:
  - LOG_LEVEL=DEBUG

# Production default is INFO (no env var needed)
```

**Available levels** (from most to least verbose):
| Level | What it shows |
|-------|--------------|
| `DEBUG` | All messages — connection timing, internal state, file watcher ticks, etc. |
| `INFO` | Normal operation — startup, connections, animation changes, scene events |
| `WARNING` | Potential issues — failed reconnections, missing configs, fallback behavior |
| `ERROR` | Failures — connection errors, file read failures, exception details |

> **Tip:** Use `DEBUG` when troubleshooting OBS connection issues or scene mapping problems. The OBS manager and scene watcher modules log detailed connection/timing info at DEBUG level.

---

## �🔧 Troubleshooting

### Port Conflicts
- **LOCAL:** Uses port 5000 (Flask default, frontend only — no raw WebSocket port)
- **Docker Dev:** Uses port 8081 (external) → 8080 (internal) + 8081 (Raw WebSocket) 
- **Production:** Uses port 8080 (main) + 8081 (Raw WebSocket)

**Note:** Docker setups use 2 ports — main port and main port + 1 for raw WebSocket connections. Local dev uses only 1 port.

### Volume Mount Issues (Docker)
```bash
# If changes aren't reflected, rebuild:
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up --build
```

### Python Dependencies
```bash
# Install/update requirements for local development:
pip install -r requirements.txt
```

### File Permissions (macOS/Linux)
```bash
# Make dev_local.py executable if needed:
chmod +x z_extras/dev_local.py
```

---

## 💡 Pro Tips

1. **Use LOCAL for frontend work** — it's the fastest for UI changes
2. **Use Docker for backend/integration work** — it matches production
3. **Use browser dev tools** — they work great with LOCAL setup
4. **Test on real Smart TV** regularly with Docker setups
5. **Check both setups** before committing changes

---
