from pathlib import Path


CONTENT_EXTENSIONS = {".html", ".md", ".txt", ".json", ".js", ".ts", ".tsx", ".jsx", ".vue"}


def relative_paths(root: Path, files: list[Path]) -> list[str]:
    paths = []
    for file_path in files:
        try:
            paths.append(file_path.relative_to(root).as_posix())
        except ValueError:
            paths.append(file_path.name)
    return paths


def text_files(files: list[Path], max_size: int = 300000) -> list[Path]:
    return [
        file_path for file_path in files
        if file_path.suffix.lower() in CONTENT_EXTENSIONS and file_path.stat().st_size <= max_size
    ]


def read_text_preview(file_path: Path, limit: int = 1000) -> str:
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""
