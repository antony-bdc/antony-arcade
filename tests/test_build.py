from pathlib import Path

import pytest

from showcase import build

FIXTURES = Path(__file__).parent / "fixtures" / "games"


def make_game(root: Path, slug: str, toml: str | None = 'title="T"\ndescription="D"\nyear=2026', html: bool = True):
    d = root / slug
    d.mkdir(parents=True)
    if html:
        (d / "index.html").write_text("<!DOCTYPE html><title>x</title>")
    if toml is not None:
        (d / "game.toml").write_text(toml)
    return d


def test_builds_fixture(tmp_path):
    games = build.build(FIXTURES, tmp_path / "site", "https://github.com/x/antony-arcade")
    assert [g.slug for g in games] == ["orbit-demo"]
    html = (tmp_path / "site" / "index.html").read_text()
    assert "Orbit demo" in html and 'href="orbit-demo/"' in html and "{{" not in html
    assert (tmp_path / "site" / "orbit-demo" / "index.html").exists()
    assert not (tmp_path / "site" / "orbit-demo" / "game.toml").exists()  # metadata isn't published
    assert (tmp_path / "site" / "assets" / "inter-tight-latin-400-normal.woff2").exists()


def test_empty_gallery(tmp_path):
    (tmp_path / "games").mkdir()
    assert build.build(tmp_path / "games", tmp_path / "site") == []
    assert "No games yet" in (tmp_path / "site" / "index.html").read_text()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"html": False}, "index.html is missing"),
        ({"toml": None}, "game.toml is missing"),
        ({"toml": 'title="T"'}, "missing description, year"),
        ({"toml": "title = "}, "game.toml is invalid"),
    ],
)
def test_invalid_games_fail_with_clear_message(tmp_path, kwargs, message):
    make_game(tmp_path, "broken", **kwargs)
    with pytest.raises(build.GameError, match=message):
        build.load_games(tmp_path)


def test_all_errors_are_reported_at_once(tmp_path):
    make_game(tmp_path, "one", html=False)
    make_game(tmp_path, "two", toml=None)
    with pytest.raises(build.GameError) as exc:
        build.load_games(tmp_path)
    assert "one:" in str(exc.value) and "two:" in str(exc.value)


def test_bad_folder_name(tmp_path):
    make_game(tmp_path, "My Game")
    with pytest.raises(build.GameError, match="folder name"):
        build.load_games(tmp_path)


def test_size_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "MAX_GAME_BYTES", 10)
    make_game(tmp_path, "big")
    with pytest.raises(build.GameError, match="budget"):
        build.load_games(tmp_path)


def test_titles_are_escaped_and_sorted_newest_first(tmp_path):
    make_game(tmp_path / "g", "old", toml='title="<Old>"\ndescription="d"\nyear=2024')
    make_game(tmp_path / "g", "new", toml='title="New"\ndescription="d"\nyear=2026')
    games = build.build(tmp_path / "g", tmp_path / "site")
    assert [g.slug for g in games] == ["new", "old"]
    assert "&lt;Old&gt;" in (tmp_path / "site" / "index.html").read_text()


def test_cover_is_used(tmp_path):
    d = make_game(tmp_path / "g", "cov")
    (d / "cover.png").write_bytes(b"\x89PNG")
    build.build(tmp_path / "g", tmp_path / "site")
    assert 'src="cov/cover.png"' in (tmp_path / "site" / "index.html").read_text()
