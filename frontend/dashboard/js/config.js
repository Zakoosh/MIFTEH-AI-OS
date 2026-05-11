(function() {
    const isStaticDevServer = window.location.port === "3000";

    window.MIFTEH_CONFIG = {
        apiBaseUrl: window.MIFTEH_API_BASE_URL || (isStaticDevServer ? "http://127.0.0.1:8000" : window.location.origin),
        refreshMs: 15000,
        improvementAreas: [
            "UI/UX",
            "SEO",
            "performance",
            "branding",
            "security",
            "analytics",
            "conversion",
            "monetization",
            "automation",
            "scalability"
        ],
        optionalEndpoints: [
            "automation",
            "git"
        ]
    };
})();
