async function loadDashboard() {
    try {
        const reports = await fetch("http://127.0.0.1:8000/reports/dashboard")
            .then(res => res.json());

        const missions = await fetch("http://127.0.0.1:8000/missions")
            .then(res => res.json());

        document.getElementById("projects-count").innerText =
            reports.by_project ? Object.keys(reports.by_project).length : 0;

        document.getElementById("reports-count").innerText =
            reports.total_reports || 0;

        document.getElementById("agents-count").innerText =
            reports.by_agent ? Object.keys(reports.by_agent).length : 0;

        let missionCount = 0;

        Object.values(missions.projects || {}).forEach(project => {
            missionCount += project.active_missions.length;
        });

        document.getElementById("missions-count").innerText = missionCount;

        const feed = document.getElementById("activity-feed");
        feed.innerHTML = "";

        (reports.latest_reports || []).forEach(report => {
            const item = document.createElement("div");
            item.className = "activity-item";

            item.innerHTML = 
                <strong></strong>
                › 
                <br/>
                <small></small>
            ;

            feed.appendChild(item);
        });

    } catch (error) {
        console.error(error);
        document.getElementById("activity-feed").innerHTML =
            "<div class='activity-item'>Backend connection error</div>";
    }
}

loadDashboard();
