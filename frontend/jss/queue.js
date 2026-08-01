const params = new URLSearchParams(window.location.search);
const serviceId = Number(params.get("service"));
const entryId = params.get("entry");

const content = document.getElementById("content");
const socket = io(SOCKET_URL, { transports: ["websocket", "polling"] });

function render(state) {
  const serviceName = state.service.name;

  // Being served right now?
  if (state.serving && String(state.serving.id) === String(entryId)) {
    content.innerHTML = `
      <p class="muted">${serviceName}</p>
      <p class="status-serving">It's your turn!</p>
      <p class="muted">Please proceed to the counter.</p>
      <a href="index.html" class="small-link">Join another queue</a>
    `;
    return;
  }

  // Still waiting?
  const mine = state.waiting.find((e) => String(e.id) === String(entryId));
  if (mine) {
    content.innerHTML = `
      <p class="muted">${serviceName}</p>
      <p class="muted" style="margin-bottom:0">Your position</p>
      <p class="position-number">#${mine.position}</p>
      <p class="muted">Estimated wait: <strong>${formatSeconds(mine.estimated_wait_seconds)}</strong></p>
      <p class="muted" style="font-size:0.75rem;margin-top:24px;">This page updates live — no need to refresh.</p>
      <a href="index.html" class="small-link">Join another queue</a>
    `;
    return;
  }

  // Not serving, not waiting -> already done or marked no-show.
  content.innerHTML = `
    <p class="muted">${serviceName}</p>
    <p style="font-size:1.4rem;font-weight:700;">You've been served</p>
    <p class="muted">Thanks for using QueueSmart.</p>
    <a href="index.html" class="small-link">Join another queue</a>
  `;
}

async function loadInitial() {
  try {
    const state = await apiGet(`/queue/${serviceId}`);
    render(state);
  } catch (err) {
    content.innerHTML = `<p class="error-text">Couldn't load your queue status.</p>`;
  }
}

socket.on("connect", () => {
  socket.emit("join_room", { service_id: serviceId });
});

socket.on("queue_update", (state) => {
  if (state.service.id === serviceId) render(state);
});

loadInitial();
