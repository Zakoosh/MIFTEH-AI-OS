from pathlib import Path

from app.integration.file_scanner import read_text_preview, text_files
from app.integration.models import SeoGap


def analyze_seo_gaps(project_id: str, files: list[Path]) -> list[SeoGap]:
    gaps: list[SeoGap] = []

    for file_path in text_files(files[:500]):
        content = read_text_preview(file_path, limit=5000).lower()
        name = file_path.name
        if file_path.suffix.lower() not in {".html", ".tsx", ".jsx", ".vue", ".md"}:
            continue

        if "<title" not in content and "seo_title" not in content and "title:" not in content:
            gaps.append(SeoGap(
                project_id=project_id,
                page=name,
                issue="Missing explicit SEO title",
                priority="high",
                recommendation="Add page-specific SEO title metadata",
            ))

        if "meta name=\"description\"" not in content and "meta_description" not in content and "description:" not in content:
            gaps.append(SeoGap(
                project_id=project_id,
                page=name,
                issue="Missing meta description",
                priority="medium",
                recommendation="Add conversion-focused meta description",
            ))

        if len(gaps) >= 50:
            break

    if not files:
        gaps.append(SeoGap(
            project_id=project_id,
            page="repository",
            issue="Repository unavailable for SEO scan",
            priority="medium",
            recommendation="Connect repository path to enable SEO analysis",
        ))

    return gaps
