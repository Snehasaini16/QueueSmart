# QueueSmart Lite

A real-time queue management system for public services (hospitals, banks, government offices).
Users join a virtual queue and see their live position + estimated wait time. Admins run the
counter from a live dashboard — no more physical lines.

## Tech stack

- **Frontend**: plain HTML, CSS, JavaScript (no framework, no build step) + Socket.IO client (via CDN)
- **Backend**: Flask, Flask-SocketIO, SQLAlchemy (SQLite by default; swappable to MySQL)
- **Real-time**: WebSockets via Socket.IO, one "room" per service so updates only broadcast
  to clients watching that specific queue

## How the wait-time estimate works

Each `Service` (e.g. "OPD") keeps a rolling average of how long it actually takes to serve one
person — `avg_service_time`. Every time an admin clicks **Call next**:

1. The person currently being served is marked `done`, and their actual serve duration
   (`finished_at - serving_started_at`) is measured.
2. That measurement updates the average using an **exponential moving average (EMA)**:

   ```
   new_avg = alpha * actual_duration + (1 - alpha) * old_avg
   ```

   `alpha = 0.3` means recent serve times matter more than old ones, so the estimate adapts if a
   counter suddenly gets slower/faster instead of being dragged down by history from hours ago.
3. Anyone waiting sees `estimated_wait = (people ahead of them) * avg_service_time`, live,
   without refreshing.

This is the piece worth walking through in an interview: why EMA over a plain average (adapts to
recent conditions, O(1) memory instead of storing every past duration), and what you'd add next.

## Project structure

```
queuesmart/
├── backend/
│   ├── app.py          # REST API + Socket.IO events + core queue logic
│   ├── models.py        # Service, QueueEntry (SQLAlchemy models)
│   ├── extensions.py    # db + socketio instances
│   └── requirements.txt
└── frontend/
    ├── index.html        # pick a service, join queue
    ├── queue.html         # live position + wait time (user side)
    ├── admin.html         # call next / no-show (admin side)
    ├── css/style.css
    └── js/
        ├── api.js         # shared fetch helpers + formatSeconds()
        ├── home.js         # logic for index.html
        ├── queue.js        # logic for queue.html (socket listener)
        └── admin.js        # logic for admin.html (socket listener)
```

## Running it locally (Windows / VS Code)

### 1. Backend

Open a terminal in VS Code (`` Ctrl+` ``):
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Runs on `http://localhost:5000`. A SQLite file `queuesmart.db` is created automatically with
three default services (OPD, Billing, Registration).

**If `eventlet` fails to install** (occasional Windows issue), install without it:
```powershell
pip install Flask Flask-SQLAlchemy Flask-SocketIO Flask-Cors python-socketio
```
Flask-SocketIO will fall back to a different mode automatically — fine for local dev.

### 2. Frontend

The frontend is plain static files, but browsers restrict some features (like `fetch`/WebSockets)
on pages opened directly via `file://`. Serve it with a tiny local server instead — open a
**second terminal** (keep the backend running in the first):

```powershell
cd frontend
python -m http.server 5500
```
Then open **http://localhost:5500** in your browser.

(Alternative: install the VS Code extension "Live Server" and click "Go Live" from `index.html`
— does the same thing with one click.)

### 3. Test it
Open `http://localhost:5500` in one tab (join the queue), and `http://localhost:5500/admin.html`
in another. Click **Call next** on the admin tab and watch the first tab update instantly —
no refresh needed.

## What's deliberately left simple (v1 scope)

- No authentication yet (route-based split between user/admin pages)
- Single counter per service (no multi-counter load balancing)
- No priority queue (FCFS only)

## Possible next steps (good to mention in interviews, don't need to build)

- JWT-based auth with separate admin/user roles
- Priority queue for emergency/senior-citizen cases (weighted fairness rule)
- Multi-counter load balancing — route new joiners to whichever counter has the shortest
  predicted wait
- Push notifications when a user is close to the front
