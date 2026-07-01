"""Load the sample knowledge documents into the running backend via its API.

Usage (from the backend service or host):
    uv run python scripts/load_sample_docs.py [BASE_URL]

BASE_URL defaults to http://localhost:8000.
"""

import sys
from pathlib import Path

import httpx

DOCS_DIR = Path(__file__).resolve().parent.parent / "sample_docs"


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    files = sorted(DOCS_DIR.glob("*.md"))
    if not files:
        print(f"No .md files found in {DOCS_DIR}")
        return

    for path in files:
        text = path.read_text(encoding="utf-8")
        # First markdown heading (or filename) becomes the title.
        first_line = text.splitlines()[0].lstrip("# ").strip()
        title = first_line or path.stem
        resp = httpx.post(
            f"{base_url}/api/v1/knowledge/documents",
            json={"title": title, "content": text, "source": path.name},
            timeout=180.0,
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"Indexed '{data['title']}' -> {data['chunk_count']} chunks "
              f"(status={data['status']})")


if __name__ == "__main__":
    main()
