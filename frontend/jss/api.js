// Shared config + tiny fetch helper used by every page.
const API_BASE = "http://localhost:5000/api";
const SOCKET_URL = "http://localhost:5000";

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed`);
  return res.json();
}

function formatSeconds(seconds) {
  const mins = Math.round(seconds / 60);
  if (mins <= 0) return "less than a minute";
  if (mins === 1) return "about 1 minute";
  return `about ${mins} minutes`;
}
