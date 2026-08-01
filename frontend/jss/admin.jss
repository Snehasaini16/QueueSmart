const serviceSelect = document.getElementById("service-select");
const avgTimeLabel = document.getElementById("avg-time-label");
const servingContent = document.getElementById("serving-content");
const waitingList = document.getElementById("waiting-list");
const waitingTitle = document.getElementById("waiting-title");
const callNextBtn = document.getElementById("call-next-btn");

const socket = io(SOCKET_URL, { transports: ["websocket", "polling"] });
let currentServiceId = null;

function render(state) {
  avgTimeLabel.textContent = `avg. service time: ${Math.round(state.service.avg_service_time)}s`;

  if (state.serving) {
    servingContent.innerHTML = `
      <p class="token-badge">#${state.serving.token_number}</p>
      <p class="muted" style="margin:0;">${state.serving.name}</p>
    `;
  } else {
    servingContent.innerHTML = `<p class="muted">No one is being served right now.</p>`;
  }

  waitingTitle.textContent = `Waiting (${state.waiting.length})`;

  if (state.waiting.length === 0) {
    waitingList.innerHTML = `<li class="muted">Queue is empty.</li>`;
  } else {
    waitingList.innerHTML = state.waiting
      .map(
        (e) => `
        <li>
          <span><strong>#${e.token_number}</strong> ${e.name}</span>
          <button class="no-show-btn" data-entry-id="${e.id}">No-show</button>
        </li>
      `
      )
      .join("");
  }
}

async function loadServices() {
  const services = await apiGet("/services");
  serviceSelect.innerHTML = services.map((s) => `<option value="${s.id}">${s.name}</option>`).join("");
  currentServiceId = Number(serviceSelect.value);
  await loadQueue();
  socket.emit("join_room", { service_id: currentServiceId });
}

async function loadQueue() {
  const state = await apiGet(`/queue/${currentServiceId}`);
  render(state);
}

serviceSelect.addEventListener("change", async () => {
  currentServiceId = Number(serviceSelect.value);
  await loadQueue();
  socket.emit("join_room", { service_id: currentServiceId });
});

callNextBtn.addEventListener("click", async () => {
  callNextBtn.disabled = true;
  try {
    const state = await apiPost("/queue/call-next", { service_id: currentServiceId });
    render(state);
  } finally {
    callNextBtn.disabled = false;
  }
});

// Event delegation for dynamically-created "No-show" buttons.
waitingList.addEventListener("click", async (e) => {
  if (!e.target.classList.contains("no-show-btn")) return;
  const entryId = e.target.dataset.entryId;
  const state = await apiPost("/queue/no-show", { entry_id: Number(entryId) });
  render(state);
});

socket.on("queue_update", (state) => {
  if (state.service.id === currentServiceId) render(state);
});

loadServices();
