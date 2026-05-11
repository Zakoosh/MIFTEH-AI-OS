(function() {
    const ui = window.MIFTEH_UI;

    function countActiveMissions(missions) {
        return Object.values((missions && missions.projects) || {}).reduce(function(total, project) {
            return total + ((project.active_missions || []).length);
        }, 0);
    }

    function flattenMissions(missions) {
        const result = [];
        Object.entries((missions && missions.projects) || {}).forEach(function(entry) {
            const projectId = entry[0];
            const project = entry[1];
            (project.active_missions || []).forEach(function(mission) {
                result.push({
                    projectId,
                    projectName: project.project,
                    goal: project.goal,
                    mission
                });
            });
        });
        return result;
    }

    function renderOverview(data) {
        const reports = data.reports || {};
        const intelligence = data.intelligenceOverview || {};
        const decisions = data.decisionOverview || {};
        const automation = data.automationTasks.data || {};
        const reportCount = reports.total_reports || 0;
        const missionCount = countActiveMissions(data.missions);

        ui.setText(
            "hero-recommendation",
            decisions.recommended_mission
                ? "Next best mission: " + decisions.recommended_mission + " for " + decisions.recommended_project
                : "Command intelligence is online"
        );
        ui.setText(
            "hero-subtitle",
            "Overall health " + (intelligence.overall_health || 0)
                + " | Automation readiness " + (intelligence.automation_readiness || 0)
                + " | Priority " + (decisions.priority || "medium")
        );

        ui.setHTML("improvement-areas", window.MIFTEH_CONFIG.improvementAreas.map(function(area) {
            return ui.chip(area);
        }).join(""));

        ui.setHTML("overview-metrics", [
            ui.metricCard("Overall Health", intelligence.overall_health || 0, "Rule-based project score"),
            ui.metricCard("Automation Ready", intelligence.automation_readiness || 0, "Average readiness"),
            ui.metricCard("Active Missions", missionCount, "Mission registry"),
            ui.metricCard("Queued Tasks", automation.pending || 0, data.automationTasks.ok ? "Scheduler queue" : "Automation API offline"),
            ui.metricCard("Failed Tasks", automation.failed || 0, data.automationTasks.ok ? "Needs review" : "Automation API offline"),
            ui.metricCard("Reports", reportCount, "Structured reports")
        ].join(""));

        const insights = (data.decisionRecommendations.recommendations || []).slice(0, 5).map(function(decision) {
            return ui.listItem(
                decision.project_id + " -> " + decision.mission_id,
                "Urgency " + decision.urgency_score + " | Impact " + decision.impact_score + " | Effort " + decision.effort_score,
                ui.badge(decision.priority, ui.priorityTone(decision.priority))
                    + " " + (decision.reasons || []).slice(0, 2).map(function(reason) {
                        return ui.chip(reason);
                    }).join(" ")
            );
        }).join("");

        ui.setHTML("insights-feed", insights || ui.empty("No decision recommendations yet."));

        const activity = (reports.latest_reports || []).slice(0, 8).map(function(report) {
            return ui.listItem(
                report.project_id + " -> " + report.agent,
                ui.formatDate(report.created_at),
                ui.badge(report.success ? "success" : "offline / failed", report.success ? "success" : "warning")
                    + " " + ui.chip(report.mode || "unknown")
            );
        }).join("");

        ui.setHTML("activity-feed", activity || ui.empty("No report activity yet."));
    }

    function renderProjects(data) {
        const projects = (data.intelligenceProjects.projects || []);
        const html = projects.map(function(project) {
            const git = data.gitStatuses[project.project_id];
            const gitData = git && git.data ? git.data : {};
            const gitBadge = git && git.ok
                ? ui.badge(gitData.is_clean ? "git clean" : "git changes", gitData.is_clean ? "success" : "warning")
                : ui.badge("git unavailable", "warning");
            const recommendation = (project.recommendations || [])[0];

            return [
                "<article class='project-card'>",
                "<div class='panel-title'><h3>" + ui.escapeHTML(project.name || project.project_id) + "</h3>" + gitBadge + "</div>",
                "<div class='metric-row'><span>Health</span><strong>" + ui.escapeHTML(project.health.overall_health) + "</strong></div>",
                ui.progress(project.health.overall_health),
                "<div class='metric-row'><span>Risk</span><strong>" + ui.escapeHTML(project.health.risk_score) + "</strong></div>",
                ui.progress(100 - project.health.risk_score),
                "<div class='metric-row'><span>Automation readiness</span><strong>" + ui.escapeHTML(project.health.automation_readiness) + "</strong></div>",
                ui.progress(project.health.automation_readiness),
                "<div class='chip-row'>",
                (project.priorities || []).slice(0, 3).map(function(priority) {
                    return ui.chip(priority);
                }).join(""),
                "</div>",
                recommendation ? ui.listItem("Recommended", recommendation.mission_id, ui.badge(recommendation.priority, ui.priorityTone(recommendation.priority))) : ui.empty("No recommendation"),
                "<div class='muted'>Last activity: " + ui.escapeHTML(project.signals.days_since_last_activity === null ? "unknown" : project.signals.days_since_last_activity + " days ago") + "</div>",
                "</article>"
            ].join("");
        }).join("");

        ui.setHTML("projects-grid", html || ui.empty("No projects available."));
    }

    function renderMissions(data) {
        const priorities = data.decisionPriorities || {};
        const allPriorityItems = []
            .concat(priorities.critical || [])
            .concat(priorities.high || [])
            .concat(priorities.medium || [])
            .concat(priorities.low || []);
        const missionPriorityHTML = allPriorityItems.slice(0, 10).map(function(decision) {
            return ui.listItem(
                decision.project_id + " -> " + decision.mission_id,
                "Decision score " + decision.decision_score + " | Automation " + decision.automation_readiness,
                ui.badge(decision.priority, ui.priorityTone(decision.priority))
                    + " " + (decision.improvement_areas || []).slice(0, 3).map(function(area) {
                        return ui.chip(area);
                    }).join(" ")
            );
        }).join("");

        ui.setHTML("mission-priorities", missionPriorityHTML || ui.empty("No mission priorities available."));

        const history = (data.missionHistory.executions || []).slice(0, 8).map(function(entry) {
            return ui.listItem(
                entry.project_id + " -> " + entry.mission_id,
                ui.formatDate(entry.completed_at || entry.started_at),
                ui.badge(entry.status || "unknown", String(entry.status || "").includes("fail") ? "warning" : "success")
            );
        }).join("");

        const scheduled = data.automationTasks.ok
            ? (data.automationTasks.data.tasks || []).slice(0, 5).map(function(task) {
                return ui.listItem(
                    "Scheduled: " + task.project_id + " -> " + task.mission_id,
                    "Every " + task.interval_minutes + " min | status " + task.status,
                    ui.badge(task.enabled ? "enabled" : "disabled", task.enabled ? "success" : "warning")
                );
            }).join("")
            : ui.empty("Automation API unavailable; scheduled missions will appear here when the Automation Layer is active.");

        ui.setHTML("mission-history", scheduled + (history || ui.empty("No mission history yet.")));
    }

    function renderDecisions(data) {
        const html = (data.decisionRecommendations.recommendations || []).slice(0, 12).map(function(decision) {
            const constraints = (decision.constraints || []).slice(0, 3).map(function(constraint) {
                return ui.chip(constraint.name, constraint.allowed ? "success" : "warning");
            }).join("");

            return [
                "<article class='decision-card'>",
                "<div class='panel-title'><h3>" + ui.escapeHTML(decision.project_id + " -> " + decision.mission_id) + "</h3>",
                ui.badge(decision.priority, ui.priorityTone(decision.priority)),
                "</div>",
                "<div class='score-grid'>",
                "<div class='score-tile'><span>Urgency</span><strong>" + ui.escapeHTML(decision.urgency_score) + "</strong></div>",
                "<div class='score-tile'><span>Impact</span><strong>" + ui.escapeHTML(decision.impact_score) + "</strong></div>",
                "<div class='score-tile'><span>Effort</span><strong>" + ui.escapeHTML(decision.effort_score) + "</strong></div>",
                "</div>",
                "<div class='chip-row'>" + (decision.recommended_agents || []).slice(0, 4).map(function(agent) { return ui.chip(agent); }).join("") + "</div>",
                "<div class='muted'>" + ui.escapeHTML((decision.reasons || []).slice(0, 2).join(" | ")) + "</div>",
                constraints ? "<div class='chip-row'>" + constraints + "</div>" : "",
                "</article>"
            ].join("");
        }).join("");

        ui.setHTML("decisions-list", html || ui.empty("No decisions available."));
    }

    function renderReports(data) {
        const reports = data.reports || {};
        const latest = (reports.latest_reports || []).slice(0, 14).map(function(report) {
            return ui.listItem(
                report.file,
                report.project_id + " | " + report.agent + " | " + report.mode,
                ui.escapeHTML(report.content_preview || "")
            );
        }).join("");

        ui.setHTML("reports-list", latest || ui.empty("No reports found."));

        const failed = (reports.latest_reports || []).filter(function(report) {
            return !report.success;
        }).slice(0, 10).map(function(report) {
            return ui.listItem(
                report.project_id + " -> " + report.agent,
                ui.formatDate(report.created_at),
                ui.badge(report.error ? "error" : "offline fallback", "warning")
            );
        }).join("");

        const broken = (reports.broken_files || []).map(function(file) {
            return ui.listItem(file.file, "Broken report file", ui.escapeHTML(file.error), "error");
        }).join("");

        ui.setHTML("risk-actions-list", broken + (failed || ui.empty("No failed reports or broken files.")));
    }

    function renderGit(data) {
        const projectStatuses = Object.entries(data.gitStatuses || {}).map(function(entry) {
            const projectId = entry[0];
            const result = entry[1];

            if (!result.ok) {
                return ui.listItem(projectId, "Git status unavailable", ui.badge(result.error || "offline", "warning"));
            }

            const status = result.data || {};
            return ui.listItem(
                projectId,
                "Branch " + (status.branch || "unknown") + " | clean " + Boolean(status.is_clean),
                ui.badge(status.is_clean ? "clean" : "changes", status.is_clean ? "success" : "warning")
                    + " " + ui.chip((status.files || []).length + " changed files")
            );
        }).join("");

        ui.setHTML("git-status-list", projectStatuses || ui.empty("No git status data yet."));

        const patchesResult = data.gitPatches;
        const patches = patchesResult.ok
            ? (patchesResult.data.patches || []).slice(0, 8).map(function(patch) {
                return ui.listItem(patch.name, patch.project_id + " | " + patch.size_bytes + " bytes", ui.formatDate(patch.created_at));
            }).join("")
            : ui.empty("Git patch endpoint unavailable; patches and diffs will appear when the Git Automation Layer is active.");

        ui.setHTML("git-activity-list", patches || ui.empty("No patches generated yet."));
    }

    function renderAutomation(data) {
        const tasksResult = data.automationTasks;
        const historyResult = data.automationHistory;

        if (!tasksResult.ok) {
            ui.setHTML("automation-status", ui.empty("Automation API unavailable; scheduler state will appear when the Automation Layer is active."));
        } else {
            const tasks = tasksResult.data;
            const summary = [
                ui.metricCard("Pending", tasks.pending || 0, "Queue"),
                ui.metricCard("Running", tasks.running || 0, "Workers"),
                ui.metricCard("Completed", tasks.completed || 0, "Finished"),
                ui.metricCard("Failed", tasks.failed || 0, "Retry needed")
            ].join("");
            const rows = (tasks.tasks || []).slice(0, 8).map(function(task) {
                return ui.listItem(
                    task.project_id + " -> " + task.mission_id,
                    "Retry " + task.retry_count + "/" + task.max_retries + " | cooldown " + task.cooldown_minutes + " min",
                    ui.badge(task.status, task.status === "failed" ? "warning" : "success")
                );
            }).join("");
            ui.setHTML("automation-status", "<div class='cards'>" + summary + "</div>" + (rows || ui.empty("No scheduled tasks.")));
        }

        if (!historyResult.ok) {
            ui.setHTML("automation-history", ui.empty("Automation history unavailable."));
            return;
        }

        const history = (historyResult.data.entries || []).slice(0, 8).map(function(entry) {
            return ui.listItem(
                entry.project_id + " -> " + entry.mission_id,
                ui.formatDate(entry.completed_at || entry.started_at),
                ui.badge(entry.status, entry.status === "failed" ? "warning" : "success")
                    + " " + ui.chip("attempt " + entry.attempt)
            );
        }).join("");

        ui.setHTML("automation-history", history || ui.empty("No automation history yet."));
    }

    function renderOrchestrator(data) {
        const status = data.orchestratorStatus || {};
        const recommendations = data.orchestratorRecommendations || {};
        const cycles = data.orchestratorCycles || {};
        const telemetry = data.orchestratorTelemetry || {};

        const statusCards = [
            ui.metricCard("Mode", status.mode || "advisory", "No autonomous execution"),
            ui.metricCard("Projects", status.projects_monitored || 0, "Monitored"),
            ui.metricCard("Recommendations", status.recommendations_count || 0, "Cycle output"),
            ui.metricCard("Blocked", status.blocked_count || 0, "Needs review")
        ].join("");

        const recommendationRows = (recommendations.recommendations || []).slice(0, 8).map(function(item) {
            return ui.listItem(
                item.project_id + " -> " + item.mission_id,
                "Optimization " + item.optimization_score + " | " + item.scheduler_action,
                ui.badge(item.priority, ui.priorityTone(item.priority))
                    + " " + (item.improvement_areas || []).slice(0, 3).map(function(area) {
                        return ui.chip(area);
                    }).join(" ")
            );
        }).join("");

        const cycleRows = (cycles.cycles || []).slice(0, 4).map(function(cycle) {
            return ui.listItem(
                cycle.cycle_id,
                ui.formatDate(cycle.completed_at || cycle.started_at),
                ui.badge(cycle.status, cycle.status === "blocked" ? "warning" : "success")
                    + " " + ui.chip(cycle.recommendations_count + " recommendations")
            );
        }).join("");

        ui.setHTML(
            "orchestrator-status",
            "<div class='cards'>" + statusCards + "</div>"
                + (recommendationRows || ui.empty("No orchestrator recommendations yet."))
                + (cycleRows || "")
        );

        const telemetryCards = [
            ui.metricCard("Cycles", telemetry.cycles_total || 0, "Recorded"),
            ui.metricCard("Avg Score", telemetry.average_optimization_score || 0, "Optimization"),
            ui.metricCard("Total Recs", telemetry.recommendations_total || 0, "All cycles"),
            ui.metricCard("Blocked", telemetry.blocked_total || 0, "Safeguards")
        ].join("");

        const areaRows = Object.entries(telemetry.by_area || {}).map(function(entry) {
            return ui.listItem(entry[0], entry[1] + " recommendations", ui.chip("continuous improvement"));
        }).join("");

        ui.setHTML(
            "orchestrator-telemetry",
            "<div class='cards'>" + telemetryCards + "</div>"
                + (areaRows || ui.empty("Telemetry will populate after orchestration cycles run."))
        );
    }

    function renderMemoryAI(data) {
        const patterns = data.memoryPatterns || {};
        const successes = data.memorySuccesses || {};
        const failures = data.memoryFailures || {};
        const recommendations = data.memoryRecommendations || {};
        const heuristics = data.memoryHeuristics || {};

        const patternRows = (patterns.patterns || []).slice(0, 8).map(function(pattern) {
            return ui.listItem(
                pattern.pattern,
                pattern.project_id + " | " + pattern.mission_id + " | confidence " + pattern.confidence,
                ui.badge(pattern.pattern_type, pattern.pattern_type === "failure" ? "warning" : "success")
                    + " " + ui.chip(pattern.recommended_frequency)
            );
        }).join("");

        const successRows = (successes.successes || []).slice(0, 4).map(function(success) {
            return ui.listItem(
                "Success: " + success.project_id + " -> " + success.mission_id,
                "success rate " + success.success_rate + " | confidence " + success.confidence,
                ui.chip(success.successes + " success signals", "success")
            );
        }).join("");

        const failureRows = (failures.failures || []).slice(0, 4).map(function(failure) {
            return ui.listItem(
                "Failure: " + failure.project_id + " -> " + failure.mission_id,
                "failure rate " + failure.failure_rate + " | retry after " + failure.retry_after_hours + "h",
                ui.badge(failure.cooldown_recommended ? "cooldown recommended" : "watch", "warning")
            );
        }).join("");

        ui.setHTML(
            "memory-patterns",
            "<div class='section-label'>Detected Patterns</div>"
                + (patternRows || ui.empty("No adaptive patterns detected yet."))
                + "<div class='section-label'>Success Memory</div>"
                + (successRows || ui.empty("No success memory yet."))
                + "<div class='section-label'>Failure Memory</div>"
                + (failureRows || ui.empty("No failure memory yet."))
        );

        const recommendationRows = (recommendations.recommendations || []).slice(0, 8).map(function(item) {
            return ui.listItem(
                item.project_id + " -> " + item.mission_id,
                "confidence " + item.confidence + " | priority " + item.priority,
                ui.badge(item.cooldown_recommended ? "cooldown" : "optimize", item.cooldown_recommended ? "warning" : "success")
                    + " " + ui.escapeHTML(item.recommendation)
            );
        }).join("");

        const heuristicRows = (heuristics.heuristics || []).slice(0, 5).map(function(heuristic) {
            return ui.listItem(
                heuristic.name,
                "weight " + heuristic.weight,
                ui.escapeHTML(heuristic.description)
            );
        }).join("");

        ui.setHTML(
            "memory-recommendations",
            "<div class='section-label'>Heuristics</div>"
                + (heuristicRows || ui.empty("No heuristics available."))
                + "<div class='section-label'>Adaptive Recommendations</div>"
                + (recommendationRows || ui.empty("No adaptive recommendations yet."))
        );
    }

    function renderStrategy(data) {
        const overview = data.strategyOverview || {};
        const projects = data.strategyProjects || {};
        const roadmaps = data.strategyRoadmaps || {};
        const opportunities = data.strategyOpportunities || {};

        const portfolioCards = [
            ui.metricCard("Projects", overview.projects_count || 0, "Portfolio"),
            ui.metricCard("Opportunities", overview.opportunities_count || 0, "Detected"),
            ui.metricCard("Priority", overview.highest_priority_project || "none", "Project"),
            ui.metricCard("Focus", (overview.portfolio_focus || []).length, "Strategic themes")
        ].join("");

        const projectRows = (projects.projects || []).slice(0, 6).map(function(project) {
            return ui.listItem(
                project.project_id + " -> " + project.portfolio_role,
                "alignment " + project.business_alignment.alignment_score + " | " + project.project_type,
                (project.strategy_focus || []).slice(0, 4).map(function(focus) {
                    return ui.chip(focus);
                }).join(" ")
            );
        }).join("");

        const focusRows = (overview.portfolio_focus || []).slice(0, 5).map(function(focus) {
            return ui.listItem(focus, "portfolio priority", ui.chip("strategy"));
        }).join("");

        ui.setHTML(
            "strategy-overview",
            "<div class='cards'>" + portfolioCards + "</div>"
                + "<div class='section-label'>Project Strategies</div>"
                + (projectRows || ui.empty("No project strategies available."))
                + "<div class='section-label'>Portfolio Focus</div>"
                + (focusRows || ui.empty("No portfolio focus available."))
        );

        const roadmapRows = (roadmaps.roadmap_30_day || []).slice(0, 6).map(function(item) {
            return ui.listItem(
                item.project_id + " -> " + item.title,
                "30 day | " + item.focus,
                ui.badge(item.priority, ui.priorityTone(item.priority))
            );
        }).join("");

        const roadmap90Rows = (roadmaps.roadmap_90_day || []).slice(0, 4).map(function(item) {
            return ui.listItem(
                item.project_id + " -> " + item.title,
                "90 day | " + item.focus,
                ui.badge(item.priority, ui.priorityTone(item.priority))
            );
        }).join("");

        const opportunityRows = (opportunities.opportunities || []).slice(0, 6).map(function(item) {
            return ui.listItem(
                item.project_id + " -> " + item.opportunity,
                item.domain + " | confidence " + item.confidence,
                ui.badge(item.priority, ui.priorityTone(item.priority))
            );
        }).join("");

        ui.setHTML(
            "strategy-roadmaps",
            "<div class='section-label'>30-Day Roadmap</div>"
                + (roadmapRows || ui.empty("No 30-day roadmap items."))
                + "<div class='section-label'>90-Day Roadmap</div>"
                + (roadmap90Rows || ui.empty("No 90-day roadmap items."))
                + "<div class='section-label'>Strategic Opportunities</div>"
                + (opportunityRows || ui.empty("No strategic opportunities."))
        );
    }

    function renderAll(data) {
        renderOverview(data);
        renderProjects(data);
        renderMissions(data);
        renderDecisions(data);
        renderReports(data);
        renderGit(data);
        renderAutomation(data);
        renderOrchestrator(data);
        renderMemoryAI(data);
        renderStrategy(data);
    }

    window.MIFTEH_RENDERERS = {
        renderAll,
        flattenMissions
    };
})();
