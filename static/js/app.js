let spots = [];
let selectedMinutes = 3;

const statusLabel = {
    available: "Available now",
    occupied: "Occupied",
    leaving_soon: "Leaving soon"
};

async function loadAll() {
    await Promise.all([loadSpots(), loadProfile()]);
}

async function loadSpots() {
    const response = await fetch("/api/spots");
    spots = await response.json();
    renderSpots();
    renderMap();
    populateSpotSelect();

    document.getElementById("availableCount").textContent =
        spots.filter(s => s.status === "available").length;

    document.getElementById("leavingCount").textContent =
        spots.filter(s => s.status === "leaving_soon").length;
}

async function loadProfile() {
    const response = await fetch("/api/profile");
    const profile = await response.json();
    document.getElementById("pointsSidebar").textContent = `${profile.points} ParkPoints`;
    document.getElementById("helpedCount").textContent = profile.helped_drivers;
}

function renderMap() {
    const map = document.getElementById("map");
    map.querySelectorAll(".map-pin").forEach(el => el.remove());

    spots.forEach(spot => {
        const pin = document.createElement("button");
        pin.className = `map-pin ${spot.status}`;
        pin.style.left = `${spot.x}%`;
        pin.style.top = `${spot.y}%`;
        pin.title = `${spot.id} — ${spot.street}`;
        pin.innerHTML = `<span>${spot.status === "leaving_soon" ? spot.minutes + "m" : "P"}</span>`;
        map.appendChild(pin);
    });
}

function renderSpots() {
    const list = document.getElementById("spotList");
    const priority = { leaving_soon: 0, available: 1, occupied: 2 };

    list.innerHTML = [...spots]
        .sort((a, b) => priority[a.status] - priority[b.status])
        .map(spot => `
            <div class="spot">
                <i class="status-icon ${spot.status === "leaving_soon" ? "leaving" : spot.status}"></i>
                <div>
                    <strong>${spot.street}</strong>
                    <small>${spot.id} · ${spot.section}</small>
                </div>
                <span class="status-text ${spot.status}">
                    ${spot.status === "leaving_soon" ? `${spot.minutes} min` : statusLabel[spot.status]}
                </span>
                ${spot.status === "leaving_soon" ? `
                    <button class="secondary-button" onclick="completePing(${spot.ping_id})">Confirm left</button>
                ` : ""}
            </div>
        `).join("");
}

function populateSpotSelect() {
    const select = document.getElementById("spotSelect");
    const usable = spots.filter(s => s.status === "occupied");
    select.innerHTML = usable.map(s =>
        `<option value="${s.id}">${s.id} — ${s.street}</option>`
    ).join("");
}

async function createPing() {
    const spotId = document.getElementById("spotSelect").value;
    if (!spotId) {
        alert("Choose an occupied parking bay first.");
        return;
    }

    const response = await fetch("/api/pings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spot_id: spotId, minutes: selectedMinutes })
    });

    const data = await response.json();
    if (!response.ok) {
        alert(data.error || "Could not create ping");
        return;
    }

    closeModal();
    await loadSpots();
}

async function completePing(pingId) {
    const response = await fetch(`/api/pings/${pingId}/complete`, { method: "PATCH" });
    const data = await response.json();
    if (!response.ok) {
        alert(data.error || "Could not complete ping");
        return;
    }
    await loadAll();
}

async function runPrediction() {
    const hour = Number(document.getElementById("predictionHour").value);
    const day = Number(document.getElementById("predictionDay").value);

    // The backend only uses fields that exist in model_meta.json.
    // Extra JSON fields are harmless and ignored.
    const payload = {
        hour: hour,
        day_of_week: day,
        is_weekend: day >= 5 ? 1 : 0,
        parking_lot_section: "Zone A",
        parking_section: "Zone A",
        section: "Zone A",
        traffic_conditions: "Moderate",
        nearby_traffic_conditions: "Moderate",
        weather_conditions: "Clear",
        weather_condition: "Clear",
        user_type: "Registered",
        vehicle_type: "Car",
        parking_spot_size: "Standard",
        reserved_status: "No"
    };

    const resultBox = document.getElementById("predictionResult");
    resultBox.textContent = "Checking historical parking patterns…";

    const response = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    const data = await response.json();

    if (!data.trained) {
        resultBox.textContent = data.message;
        return;
    }

    const percent = Math.round(data.availability_probability * 100);
    resultBox.innerHTML = `
        <strong>${percent}% estimated availability</strong><br>
        ${data.recommendation}
    `;
}

function openModal() {
    document.getElementById("leaveModal").classList.remove("hidden");
}
function closeModal() {
    document.getElementById("leaveModal").classList.add("hidden");
}

document.getElementById("openLeaveModal").addEventListener("click", openModal);
document.getElementById("closeLeaveModal").addEventListener("click", closeModal);
document.getElementById("sendPing").addEventListener("click", createPing);
document.getElementById("predictButton").addEventListener("click", runPrediction);

document.querySelectorAll(".time-options button").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".time-options button").forEach(b => b.classList.remove("selected"));
        button.classList.add("selected");
        selectedMinutes = Number(button.dataset.minutes);
    });
});

loadAll();
