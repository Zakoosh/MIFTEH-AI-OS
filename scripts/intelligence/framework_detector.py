"""
Framework Detection Engine — auto-detects Next.js, Nuxt, Astro, Vite, Laravel, static HTML.
Returns build command, deploy strategy, patch strategy, and source directories.
"""
import json
import os
from pathlib import Path
from typing import Optional

SIGNATURES: dict[str, dict] = {
    "nextjs": {
        "config_files": ["next.config.ts", "next.config.js", "next.config.mjs"],
        "package_deps": ["next"],
        "build_command": "npm run build",
        "dev_command": "npm run dev",
        "output_dir": "out",
        "deploy_strategy": "github-pages-static-export",
        "patch_strategy": "nextjs-app-router",
        "source_dirs": ["src/app", "src/pages", "app", "pages"],
        "component_dirs": ["src/components", "components"],
        "static_dir": "public",
    },
    "nuxt": {
        "config_files": ["nuxt.config.ts", "nuxt.config.js"],
        "package_deps": ["nuxt"],
        "build_command": "npm run generate",
        "dev_command": "npm run dev",
        "output_dir": ".output/public",
        "deploy_strategy": "github-pages-nuxt",
        "patch_strategy": "nuxt-pages",
        "source_dirs": ["pages", "layouts", "components"],
        "component_dirs": ["components"],
        "static_dir": "public",
    },
    "astro": {
        "config_files": ["astro.config.mjs", "astro.config.ts", "astro.config.js"],
        "package_deps": ["astro"],
        "build_command": "npm run build",
        "dev_command": "npm run dev",
        "output_dir": "dist",
        "deploy_strategy": "github-pages-dist",
        "patch_strategy": "astro-pages",
        "source_dirs": ["src/pages", "src/layouts", "src/components"],
        "component_dirs": ["src/components"],
        "static_dir": "public",
    },
    "vite": {
        "config_files": ["vite.config.ts", "vite.config.js", "vite.config.mts"],
        "package_deps": ["vite"],
        "build_command": "npm run build",
        "dev_command": "npm run dev",
        "output_dir": "dist",
        "deploy_strategy": "github-pages-dist",
        "patch_strategy": "vite-src",
        "source_dirs": ["src"],
        "component_dirs": ["src/components"],
        "static_dir": "public",
    },
    "laravel": {
        "config_files": ["artisan", "composer.json"],
        "package_deps": [],
        "build_command": "php artisan config:cache && npm run build",
        "dev_command": "php artisan serve",
        "output_dir": "public",
        "deploy_strategy": "server-deploy",
        "patch_strategy": "laravel-blade",
        "source_dirs": ["resources/views", "app/Http/Controllers"],
        "component_dirs": ["resources/views/components"],
        "static_dir": "public",
    },
    "static": {
        "config_files": ["index.html"],
        "package_deps": [],
        "build_command": None,
        "dev_command": None,
        "output_dir": ".",
        "deploy_strategy": "github-pages-static",
        "patch_strategy": "static-html",
        "source_dirs": ["."],
        "component_dirs": [],
        "static_dir": ".",
    },
}


def detect_framework(project_path: Path | str) -> dict:
    """
    Detect the framework used in a project directory.
    Returns full metadata dict including framework name, build command, etc.
    """
    path = Path(project_path)

    if not path.exists():
        return _unknown(str(project_path), "directory does not exist")

    # Check for package.json to read dependencies
    pkg_deps: set[str] = set()
    pkg_path = path / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text())
            all_deps = {
                **pkg.get("dependencies", {}),
                **pkg.get("devDependencies", {}),
            }
            pkg_deps = set(all_deps.keys())
        except (json.JSONDecodeError, OSError):
            pass

    # Score each framework candidate
    scores: dict[str, int] = {}
    for fw, sig in SIGNATURES.items():
        score = 0
        # Config file presence (strong signal)
        for cf in sig["config_files"]:
            if (path / cf).exists():
                score += 3
        # Package dependency presence (very strong signal)
        for dep in sig["package_deps"]:
            if dep in pkg_deps:
                score += 5
        scores[fw] = score

    # Pick highest score; require > 0
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        # Last fallback: look for index.html
        if (path / "index.html").exists():
            best = "static"
        else:
            return _unknown(str(project_path), "no framework signals found")

    sig = SIGNATURES[best]
    resolved_source_dirs = _resolve_dirs(path, sig["source_dirs"])
    resolved_component_dirs = _resolve_dirs(path, sig["component_dirs"])

    # Detect if Next.js uses App Router vs Pages Router
    router_type = None
    if best == "nextjs":
        if (path / "src" / "app").exists() or (path / "app").exists():
            router_type = "app-router"
        elif (path / "src" / "pages").exists() or (path / "pages").exists():
            router_type = "pages-router"
        else:
            router_type = "app-router"  # default for Next.js 15

    return {
        "framework": best,
        "router_type": router_type,
        "build_command": sig["build_command"],
        "dev_command": sig["dev_command"],
        "output_dir": str(path / sig["output_dir"]),
        "deploy_strategy": sig["deploy_strategy"],
        "patch_strategy": sig["patch_strategy"],
        "source_dirs": resolved_source_dirs,
        "component_dirs": resolved_component_dirs,
        "static_dir": str(path / sig["static_dir"]),
        "project_path": str(path),
        "detection_scores": scores,
        "confidence": _confidence(scores[best]),
    }


def _resolve_dirs(base: Path, dirs: list[str]) -> list[str]:
    return [str(base / d) for d in dirs if (base / d).exists()]


def _confidence(score: int) -> str:
    if score >= 8:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def _unknown(path: str, reason: str) -> dict:
    return {
        "framework": "unknown",
        "router_type": None,
        "build_command": None,
        "dev_command": None,
        "output_dir": None,
        "deploy_strategy": "unknown",
        "patch_strategy": "unknown",
        "source_dirs": [],
        "component_dirs": [],
        "static_dir": path,
        "project_path": path,
        "detection_scores": {},
        "confidence": "none",
        "error": reason,
    }
