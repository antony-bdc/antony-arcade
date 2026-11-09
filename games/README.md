# games

One folder per game:

```
games/
  my-game/
    index.html     # the game (single file is fine, extra assets allowed)
    game.toml      # metadata, see below
    cover.png      # optional, 16:9, shown in the gallery
```

```toml
title = "My Game"
description = "One or two sentences: what you do and why it's fun."
year = 2026
tags = ["canvas", "physics"]
controls = "Arrow keys to move, space to jump"
```

`python3 -m showcase.build` checks every folder and fails with a clear message if something is missing.
