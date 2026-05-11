(function() {
    const config = window.MIFTEH_CONFIG;

    function endpoint(path) {
        return config.apiBaseUrl + path;
    }

    async function fetchJSON(path, options) {
        const response = await fetch(endpoint(path), {
            cache: "no-store",
            ...(options || {})
        });

        if (!response.ok) {
            throw new Error("Request failed: " + path + " (" + response.status + ")");
        }

        return response.json();
    }

    async function fetchOptional(path, fallback) {
        try {
            return {
                ok: true,
                data: await fetchJSON(path)
            };
        } catch (error) {
            return {
                ok: false,
                data: fallback,
                error: error.message
            };
        }
    }

    async function loadProjectGit(projects) {
        const statuses = {};

        await Promise.all((projects || []).map(async function(project) {
            const projectId = project.project_id;
            const result = await fetchOptional("/git/status/" + encodeURIComponent(projectId), null);
            statuses[projectId] = result;
        }));

        return statuses;
    }

    async function loadCommandCenterData() {
        const coreRequests = {
            reports: fetchJSON("/reports/summary"),
            missions: fetchJSON("/missions"),
            missionHistory: fetchJSON("/missions/history"),
            intelligenceOverview: fetchJSON("/intelligence/overview"),
            intelligenceProjects: fetchJSON("/intelligence/projects"),
            intelligenceRecommendations: fetchJSON("/intelligence/recommendations"),
            intelligenceTrends: fetchJSON("/intelligence/trends"),
            decisionOverview: fetchJSON("/decision/overview"),
            decisionPlans: fetchJSON("/decision/plans"),
            decisionRecommendations: fetchJSON("/decision/recommendations"),
            decisionPriorities: fetchJSON("/decision/priorities")
        };

        const data = {};
        const entries = await Promise.all(Object.entries(coreRequests).map(async function(entry) {
            return [entry[0], await entry[1]];
        }));

        entries.forEach(function(entry) {
            data[entry[0]] = entry[1];
        });

        const projectList = (data.intelligenceProjects.projects || []);
        const optional = await Promise.all([
            fetchOptional("/automation/tasks", { tasks: [], pending: 0, running: 0, completed: 0, failed: 0 }),
            fetchOptional("/automation/history", { total: 0, entries: [] }),
            fetchOptional("/git/patches", { patches: [] }),
            loadProjectGit(projectList)
        ]);

        data.automationTasks = optional[0];
        data.automationHistory = optional[1];
        data.gitPatches = optional[2];
        data.gitStatuses = optional[3];

        return data;
    }

    window.MIFTEH_API = {
        loadCommandCenterData,
        fetchJSON,
        fetchOptional
    };
})();
