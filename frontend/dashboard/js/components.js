(function() {
    function escapeHTML(value) {
        return String(value === undefined || value === null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function byId(id) {
        return document.getElementById(id);
    }

    function setHTML(id, html) {
        const element = byId(id);
        if (element) {
            element.innerHTML = html;
        }
    }

    function setText(id, value) {
        const element = byId(id);
        if (element) {
            element.innerText = value;
        }
    }

    function badge(text, tone) {
        return "<span class='badge " + escapeHTML(tone || "") + "'>" + escapeHTML(text) + "</span>";
    }

    function chip(text, tone) {
        return "<span class='chip " + escapeHTML(tone || "") + "'>" + escapeHTML(text) + "</span>";
    }

    function progress(value) {
        const safeValue = Math.max(0, Math.min(100, Number(value || 0)));
        return "<div class='progress'><span style='width:" + safeValue + "%'></span></div>";
    }

    function empty(message) {
        return "<div class='empty'>" + escapeHTML(message) + "</div>";
    }

    function metricCard(label, value, helper) {
        return [
            "<div class='card'>",
            "<h3>" + escapeHTML(label) + "</h3>",
            "<p>" + escapeHTML(value) + "</p>",
            helper ? "<small>" + escapeHTML(helper) + "</small>" : "",
            "</div>"
        ].join("");
    }

    function listItem(title, meta, body, tone) {
        return [
            "<div class='list-item " + escapeHTML(tone || "") + "'>",
            "<strong>" + escapeHTML(title) + "</strong>",
            meta ? "<div class='muted'>" + escapeHTML(meta) + "</div>" : "",
            body ? "<div>" + body + "</div>" : "",
            "</div>"
        ].join("");
    }

    function priorityTone(priority) {
        if (priority === "critical") {
            return "danger";
        }

        if (priority === "high") {
            return "warning";
        }

        if (priority === "low") {
            return "success";
        }

        return "";
    }

    function formatDate(value) {
        if (!value) {
            return "No activity yet";
        }

        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }

        return date.toLocaleString();
    }

    window.MIFTEH_UI = {
        byId,
        setHTML,
        setText,
        escapeHTML,
        badge,
        chip,
        progress,
        empty,
        metricCard,
        listItem,
        priorityTone,
        formatDate
    };
})();
