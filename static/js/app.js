const REFRESH_MS = 3000;   // how often the street re-checks the server

let bays = [];             // [{id, status}] from /api/bays
let mode = "look";         // "look" or "leave"
let selectedId = null;     // the bay the user tapped
let myBayId = null;        // the bay this user parked in
let notice = "";           // one-off message shown in the sheet
let lastDrawn = "";

const $ = id => document.getElementById(id);

async function post(path) {
    const response = await fetch(path, { method: "POST" });
    const data = await response.json();
    return response.ok ? "" : data.error;
}

/* ---------- data ---------- */

async function loadBays() {
    const response = await fetch("/api/bays");
    const latest = await response.json();

    // The "ping": a bay that was taken a moment ago is free now. Point the looking driver at it.
    const opened = latest.find(bay =>
        bay.status === "free" && bays.some(old => old.id === bay.id && old.status === "occupied"));
    if (opened && mode === "look") {
        selectedId = opened.id;
        notice = `Bay ${opened.id} just opened up`;
    }

    bays = latest;
    render();
}

async function parkHere(bayId) {
    notice = await post(`/api/bays/${bayId}/park`);
    if (!notice) myBayId = bayId;
    await loadBays();
}

async function leaveBay(bayId) {
    const error = await post(`/api/bays/${bayId}/leave`);
    notice = error || `Bay ${bayId} is now free for other drivers`;
    if (!error && myBayId === bayId) myBayId = null;
    selectedId = null;
    await loadBays();
}

/* ---------- drawing ---------- */

function bayButton(bay) {
    const classes = ["bay", bay.status];
    if (bay.id === selectedId) classes.push("selected");
    if (bay.id === myBayId) classes.push("mine");
    return `<button class="${classes.join(" ")}" data-bay="${bay.id}">${bay.id}</button>`;
}

function sheetHtml() {
    const bay = bays.find(b => b.id === selectedId);
    const freeCount = bays.filter(b => b.status === "free").length;

    if (!bays.length) return `<h2>No parking data yet</h2><p>Put the Kaggle CSV in the data folder and restart.</p>`;

    if (mode === "look") {
        if (!bay) {
            return freeCount
                ? `<h2>${freeCount} bays free</h2><p>Tap a green bay to take it.</p>`
                : `<h2>No free bays right now</h2><p>This screen updates the moment someone leaves.</p>`;
        }
        if (bay.status === "free") {
            return `<span class="badge free">FREE</span><h2>Bay ${bay.id}</h2>
                    <button class="button" data-action="park">I parked here</button>`;
        }
        return `<span class="badge">TAKEN</span><h2>Bay ${bay.id}</h2><p>Someone is parked here.</p>`;
    }

    // mode === "leave"
    if (!bay) return `<h2>Which bay are you in?</h2><p>Tap your bay on the street.</p>`;
    if (bay.status === "free") return `<h2>Bay ${bay.id} is already free</h2><p>Tap the bay you are parked in.</p>`;
    return `<span class="badge">YOUR BAY</span><h2>Leaving bay ${bay.id}?</h2>
            <p>Drivers who are looking will see it turn green.</p>
            <button class="button" data-action="leave">I'm leaving</button>`;
}

function render() {
    const html = {
        // First half of the bays above the road, second half below it.
        topRow: bays.slice(0, Math.ceil(bays.length / 2)).map(bayButton).join(""),
        bottomRow: bays.slice(Math.ceil(bays.length / 2)).map(bayButton).join(""),
        legend: `<span><i class="free"></i>${bays.filter(b => b.status === "free").length} free</span>
                 <span><i class="occupied"></i>${bays.filter(b => b.status === "occupied").length} taken</span>`,
        sheet: (notice ? `<p class="notice">${notice}</p>` : "") + sheetHtml()
    };

    // Skip the redraw when nothing changed, so a button is never replaced mid-tap.
    const drawing = JSON.stringify(html) + mode;
    if (drawing === lastDrawn) return;
    lastDrawn = drawing;

    for (const id in html) $(id).innerHTML = html[id];
    document.querySelectorAll("#modeSwitch button").forEach(button =>
        button.classList.toggle("on", button.dataset.mode === mode));
}

async function loadOutlook() {
    const response = await fetch("/api/outlook");
    const hours = await response.json();
    if (!hours.length) return;

    const now = new Date().getHours();
    const current = hours.find(h => h.hour === now) || hours[0];
    const quietest = hours.reduce((a, b) => (b.occupied_pct < a.occupied_pct ? b : a));

    $("outlook").innerHTML = `
        <div class="chips">
            <span class="chip">Usually ${current.occupied_pct}% full at ${current.hour}:00</span>
            <span class="chip">Quietest at ${quietest.hour}:00</span>
        </div>
        <div class="bars">${hours.map(h => `
            <i class="${h.hour === current.hour ? "on" : ""}" style="height:${h.occupied_pct}%"
               title="${h.hour}:00 - ${h.occupied_pct}% full"></i>`).join("")}
        </div>
        <p>How full parking usually is at each hour of the day, from the dataset.</p>`;
}

/* ---------- clicks ---------- */

document.querySelector(".street").addEventListener("click", event => {
    const button = event.target.closest("[data-bay]");
    if (!button) return;
    selectedId = Number(button.dataset.bay);
    notice = "";
    render();
});

$("sheet").addEventListener("click", event => {
    const action = event.target.dataset.action;
    if (action === "park") parkHere(selectedId);
    if (action === "leave") leaveBay(selectedId);
});

document.querySelectorAll("#modeSwitch button").forEach(button =>
    button.addEventListener("click", () => {
        mode = button.dataset.mode;
        selectedId = mode === "leave" ? myBayId : null;   // leaving starts from the bay you parked in
        notice = "";
        render();
    }));

$("resetButton").addEventListener("click", async () => {
    await post("/api/reset");
    selectedId = myBayId = null;
    notice = "";
    bays = [];
    await loadBays();
});

setInterval(loadBays, REFRESH_MS);
loadBays();
loadOutlook();
