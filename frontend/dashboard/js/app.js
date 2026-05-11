(function() {
    const api = window.MIFTEH_API;
    const ui = window.MIFTEH_UI;
    const renderers = window.MIFTEH_RENDERERS;
    const config = window.MIFTEH_CONFIG;

    let refreshTimer = null;
    let isLoading = false;

    function showTab(tabId) {
        document.querySelectorAll(".tab").forEach(function(tab) {
            tab.classList.remove("active");
        });

        document.querySelectorAll("[data-tab-target]").forEach(function(button) {
            button.classList.toggle("active", button.dataset.tabTarget === tabId);
        });

        const tab = document.getElementById(tabId);
        if (tab) {
            tab.classList.add("active");
        }

        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function setRefreshState(state, message) {
        const element = ui.byId("refresh-state");
        if (!element) {
            return;
        }

        element.className = "status " + state;
        element.innerText = message;
    }

    function setGlobalError(message) {
        const element = ui.byId("global-error");
        if (!element) {
            return;
        }

        if (!message) {
            element.classList.add("hidden");
            element.innerText = "";
            return;
        }

        element.classList.remove("hidden");
        element.innerText = message;
    }

    function renderSkeletons() {
        [
            "overview-metrics",
            "projects-grid",
            "mission-priorities",
            "decisions-list",
            "reports-list",
            "git-status-list",
            "automation-status",
            "orchestrator-status",
            "memory-patterns",
            "strategy-overview",
            "executive-overview",
            "production-overview",
            "execution-pipelines",
            "integration-projects",
            "improvements-projects"
        ].forEach(function(id) {
            ui.setHTML(id, "<div class='skeleton'></div><div class='skeleton'></div>");
        });
    }

    async function refreshDashboard() {
        if (isLoading) {
            return;
        }

        isLoading = true;
        setRefreshState("loading", "SYNCING");
        setGlobalError("");

        try {
            const data = await api.loadCommandCenterData();
            renderers.renderAll(data);
            setRefreshState("online", "LIVE");
        } catch (error) {
            console.error(error);
            setRefreshState("error", "DEGRADED");
            setGlobalError("Backend connection error. Make sure FastAPI is running on port 8000 and the Intelligence/Decision layers are available.");
        } finally {
            isLoading = false;
        }
    }

    function bindNavigation() {
        document.querySelectorAll("[data-tab-target]").forEach(function(button) {
            button.addEventListener("click", function() {
                showTab(button.dataset.tabTarget);
            });
        });
    }

    function startAutoRefresh() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }

        refreshTimer = setInterval(refreshDashboard, config.refreshMs);
    }

    function initDashboard() {
        bindNavigation();
        ui.byId("refresh-button").addEventListener("click", refreshDashboard);
        renderSkeletons();
        refreshDashboard();
        startAutoRefresh();
    }

    window.showTab = showTab;
    document.addEventListener("DOMContentLoaded", initDashboard);
})();
