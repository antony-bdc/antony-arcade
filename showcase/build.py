"""Validates games/* and renders the gallery into site/."""

from __future__ import annotations

import re
import shutil
import sys
import tomllib
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

REQUIRED = ("title", "description", "year")
MAX_GAME_BYTES = 25 * 1024 * 1024  # GitHub Pages is not a CDN: keep games light
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
TEMPLATE = Path(__file__).with_name("template.html")


class GameError(Exception):
    pass


@dataclass
class Game:
    slug: str
    path: Path
    title: str
    description: str
    year: int
    tags: list[str] = field(default_factory=list)
    controls: str = ""
    cover: str | None = None
    size: int = 0


def folder_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def load_game(path: Path) -> Game:
    slug = path.name
    if not SLUG.match(slug):
        raise GameError(f"{slug}: folder name must be lowercase letters, digits and '-'")
    if not (path / "index.html").is_file():
        raise GameError(f"{slug}: index.html is missing")
    meta_file = path / "game.toml"
    if not meta_file.is_file():
        raise GameError(f"{slug}: game.toml is missing")
    try:
        meta = tomllib.loads(meta_file.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise GameError(f"{slug}: game.toml is invalid: {exc}") from exc
    missing = [k for k in REQUIRED if not meta.get(k)]
    if missing:
        raise GameError(f"{slug}: game.toml is missing {', '.join(missing)}")
    size = folder_size(path)
    if size > MAX_GAME_BYTES:
        raise GameError(f"{slug}: {size / 1e6:.1f} MB is over the {MAX_GAME_BYTES / 1e6:.0f} MB budget")
    cover = next((c.name for c in (path / "cover.png", path / "cover.jpg", path / "cover.webp") if c.is_file()), None)
    return Game(
        slug=slug,
        path=path,
        title=str(meta["title"]),
        description=str(meta["description"]),
        year=int(meta["year"]),
        tags=[str(t) for t in meta.get("tags", [])],
        controls=str(meta.get("controls", "")),
        cover=cover,
        size=size,
    )


def load_games(root: Path) -> list[Game]:
    games, errors = [], []
    for path in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        try:
            games.append(load_game(path))
        except GameError as exc:
            errors.append(str(exc))
    if errors:
        raise GameError("\n".join(errors))
    return sorted(games, key=lambda g: (-g.year, g.title.lower()))


def render_game(g: Game, index: int) -> str:
    tags = "".join(f"<li>{escape(t)}</li>" for t in g.tags)
    if g.cover:
        visual = f'<img src="{g.slug}/{escape(g.cover)}" alt="" loading="lazy" width="1600" height="900">'
    else:
        visual = f'<span class="initial" aria-hidden="true">{escape(g.title[:1].upper())}</span>'
    controls = f'<p class="controls">{escape(g.controls)}</p>' if g.controls else ""
    return f"""
    <article class="game">
      <a class="visual" href="{g.slug}/" tabindex="-1" aria-hidden="true">{visual}</a>
      <div class="text">
        <p class="meta"><span>{index:02d}</span><span>{g.year}</span></p>
        <h2><a href="{g.slug}/">{escape(g.title)}</a></h2>
        <p class="desc">{escape(g.description)}</p>
        {controls}
        <ul class="tags">{tags}</ul>
        <a class="play" href="{g.slug}/">Play in the browser<span aria-hidden="true"> &rarr;</span></a>
      </div>
    </article>"""


def build(games_dir: Path, out: Path, repo_url: str = "") -> list[Game]:
    games = load_games(games_dir)
    body = (
        "".join(render_game(g, i + 1) for i, g in enumerate(games))
        or '<p class="empty">No games yet. Add a folder to <code>games/</code>.</p>'
    )
    html = TEMPLATE.read_text()
    for key, value in {
        "{{GAMES}}": body,
        "{{COUNT}}": str(len(games)),
        "{{REPO_URL}}": escape(repo_url or "#"),
    }.items():
        html = html.replace(key, value)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "index.html").write_text(html)
    (out / ".nojekyll").write_text("")
    shutil.copytree(TEMPLATE.with_name("assets"), out / "assets")
    for g in games:
        shutil.copytree(g.path, out / g.slug, ignore=shutil.ignore_patterns("game.toml"))
    return games


def main() -> int:
    import os

    games_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "games")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "site")
    try:
        games = build(games_dir, out, os.environ.get("REPO_URL", ""))
    except GameError as exc:
        print(f"build failed:\n{exc}", file=sys.stderr)
        return 1
    for g in games:
        print(f"  {g.slug:<24} {g.size / 1e6:6.2f} MB  {g.title}")
    print(f"built {len(games)} game(s) into {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
