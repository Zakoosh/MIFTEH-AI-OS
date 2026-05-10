async function loadJSON(url) {
    const response = await fetch(url, { cache: "no-store" });

    if (!response.ok) {
        throw new Error(Request failed: );
    }

    return response.json();
}


function setText(id, value) {
    document.getElementById(id).innerText = value;
}


async function loadDashboard() {
    const feed = document.getElementById("activity-feed");

    try {
        const reports = await loadJSON("http://127.0.0.1:8000/reports/summary");
        const missions = await loadJSON("http://127.0.0.1:8000/missions");

        const projectsCount = reports.by_project
            ? Object.keys(reports.by_project).length
            : 0;

        const agentsCount = reports.by_agent
            ? Object.keys(reports.by_agent).length
            : 0;

        let missionCount = 0;

        Object.values(missions.projects || {}).forEach(project => {
            missionCount += project.active_missions.length;
        });

        setText("projects-count", projectsCount);
        setText("reports-count", reports.total_reports || 0);
        setText("agents-count", agentsCount);
        setText("missions-count", missionCount);

        feed.innerHTML = "";

        if (!reports.latest_reports || reports.latest_reports.length === 0) {
            feed.innerHTML = "<div class='activity-item'>No reports yet</div>";
            return;
        }

        reports.latest_reports.forEach(report => {
            const item = document.createElement("div");
            item.className = "activity-item";

            const status = report.success ? "SUCCESS" : "FAILED / OFFLINE";

            item.innerHTML = 
                <strong></strong>
                › 
                <br/>
                <small> ·  · </small>
            ;

            feed.appendChild(item);
        });

    } catch (error) {
        console.error(error);

        feed.innerHTML = 
            <div class='activity-item'>
                Backend connection error. Make sure FastAPI is running on port 8000.
            </div>
        ;
    }
}

loadDashboard();

setInterval(loadDashboard, 10000);
