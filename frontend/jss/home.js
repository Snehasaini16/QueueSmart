const serviceSelect = document.getElementById("service-select");
const joinForm = document.getElementById("join-form");
const nameInput = document.getElementById("name-input");
const errorText = document.getElementById("error-text");
const joinBtn = document.getElementById("join-btn");

// Load available services into the dropdown on page load.
async function loadServices() {
  try {
    const services = await apiGet("/services");
    serviceSelect.innerHTML = services
      .map((s) => `<option value="${s.id}">${s.name}</option>`)
      .join("");
  } catch (err) {
    errorText.textContent = "Couldn't load services. Is the backend running on port 5000?";
    errorText.hidden = false;
  }
}

joinForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorText.hidden = true;

  const name = nameInput.value.trim();
  const serviceId = serviceSelect.value;
  if (!name || !serviceId) return;

  joinBtn.disabled = true;
  joinBtn.textContent = "Joining...";

  try {
    const res = await apiPost("/queue/join", {
      service_id: Number(serviceId),
      name: name,
    });
    // Redirect to the live queue view, carrying service + entry ids in the URL.
    window.location.href = `queue.html?service=${serviceId}&entry=${res.entry.id}`;
  } catch (err) {
    errorText.textContent = "Couldn't join the queue. Please try again.";
    errorText.hidden = false;
    joinBtn.disabled = false;
    joinBtn.textContent = "Join queue";
  }
});

loadServices();
