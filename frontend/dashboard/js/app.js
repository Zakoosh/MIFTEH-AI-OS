let cachedReports = null;
let cachedMissions = null;

async function loadJSON(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
        throw new Error("Request failed: " + url);
    }
    return response.json();
}

function setText(id, value) {
    document.getElementById(id).innerText = value;
}

function showTab(tabId) {
    document.querySelectorAll(".tab").forEach(function(tab) {
        tab.classList.remove("active");
    });

    document.getElementById(tabId).classList.add("active");
}

function renderDashboard(reports, missions) {
    const projectsCount = reports.by_project ? Object.keys(reports.by_project).length : 0;
    const agentsCount = reports.by_agent ? Object.keys(reports.by_agent).length : 0;

    let missionCount = 0;
    Object.values(missions.projects || {}).forEach(function(project) {
        missionCount += project.active_missions.length;
    });

    setText("projects-count", projectsCount);
    setText("reports-count", reports.total_reports || 0);
    setText("agents-count", agentsCount);
    setText("missions-count", missionCount);

    const feed = document.getElementById("activity-feed");
    feed.innerHTML = "";

    (reports.latest_reports || []).slice(0, 10).forEach(function(report) {
        const item = document.createElement("div");
        item.className = "activity-item";

        const status = report.success ? "SUCCESS" : "FAILED / OFFLINE";

        item.innerHTML =
            "<strong>" + report.project_id + "</strong>" +
            " -> " + report.agent +
            "<br/>" +
            "<small>" + status + " | " + report.mode + " | " + report.created_at + "</small>";

        feed.appendChild(item);
    });
}

function renderProjects(reports) {
    const list = document.getElementById("projects-list");
    list.innerHTML = "";

    Object.entries(reports.by_project || {}).forEach(function(entry) {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = "<strong>" + entry[0] + "</strong><span class='badge'>" + entry[1] + " reports</span>";
        list.appendChild(item);
    });
}

function renderMissions(missions) {
    const list = document.getElementById("missions-list");
    list.innerHTML = "";

    Object.entries(missions.projects || {}).forEach(function(entry) {
        const projectId = entry[0];
        const project = entry[1];

        const header = document.createElement("div");
        header.className = "list-item";
        header.innerHTML = "<strong>" + project.project + "</strong><br/><small>" + project.goal + "</small>";
        list.appendChild(header);

        project.active_missions.forEach(function(mission) {
            const item = document.createElement("div");
            item.className = "list-item";
            item.innerHTML =
                "<strong>" + mission.title + "</strong>" +
                "<span class='badge'>" + mission.id + "</span>" +
                "<br/><small>Agents: " + mission.agents.length + " | Project: " + projectId + "</small>";
            list.appendChild(item);
        });
    });
}

function renderAgents(reports) {
    const list = document.getElementById("agents-list");
    list.innerHTML = "";

    Object.entries(reports.by_agent || {}).forEach(function(entry) {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = "<strong>" + entry[0] + "</strong><span class='badge'>" + entry[1] + " runs</span>";
        list.appendChild(item);
    });
}

function renderReports(reports) {
    const list = document.getElementById("reports-list");
    list.innerHTML = "";

    (reports.latest_reports || []).forEach(function(report) {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML =
            "<strong>" + report.file + "</strong>" +
            "<br/><small>" + report.project_id + " | " + report.agent + " | " + report.mode + "</small>";
        list.appendChild(item);
    });
}

function renderErrors(reports) {
    const list = document.getElementById("errors-list");
    list.innerHTML = "";

    if (reports.broken_files_count > 0) {
        reports.broken_files.forEach(function(file) {
            const item = document.createElement("div");
            item.className = "list-item error";
            item.innerHTML = "<strong>" + file.file + "</strong><br/><small>" + file.error + "</small>";
            list.appendChild(item);
        });
    }

    (reports.latest_reports || []).filter(function(report) {
        return !report.success;
    }).forEach(function(report) {
        const item = document.createElement("div");
        item.className = "list-item error";
        item.innerHTML =
            "<strong>" + report.project_id + " -> " + report.agent + "</strong>" +
            "<br/><small>" + report.mode + " | " + report.created_at + "</small>";
        list.appendChild(item);
    });
}

async function loadDashboard() {
    try {
        cachedReports = await loadJSON("http://127.0.0.1:8000/reports/summary");
        cachedMissions = await loadJSON("http://127.0.0.1:8000/missions");

        renderDashboard(cachedReports, cachedMissions);
        renderProjects(cachedReports);
        renderMissions(cachedMissions);
        renderAgents(cachedReports);
        renderReports(cachedReports);
        renderErrors(cachedReports);

    } catch (error) {
        console.error(error);
        document.getElementById("activity-feed").innerHTML =
            "<div class='activity-item'>Backend connection error. Make sure FastAPI is running on port 8000.</div>";
    }
}

loadDashboard();
setInterval(loadDashboard, 10000);
