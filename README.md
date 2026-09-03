# 都道府県クイズ — Japan Prefecture Quiz

An interactive map game for learning the 47 prefectures of Japan. Click the
prefecture you're asked for; the map tells you how you did.

**Play it: https://jpy-git.github.io/japan_map_game/**

## Repo layout

- `index.html` — the whole game, self-contained (no build step needed to play).
- `build/build_paths.py` — generates `build/paths.json` (prefecture SVG paths,
  canvas dimensions, Okinawa inset box) from source geodata.
- `build/game.template.html` — the game source, with `__PLACEHOLDER__` slots for
  the map data.
- `build/build.py` — injects `paths.json` into the template and writes `index.html`.

## Rebuilding

```sh
python3 build/build.py
```

Edit `build/game.template.html` (not `index.html`) and re-run the build —
`index.html` is generated and gets overwritten.
