# Map Quiz — 都道府県 and the counties of the UK

Two interactive map games in one page. Click the country chip to swap between them.

**Play it: https://jpy-git.github.io/japan_map_game/**

- **都道府県クイズ** — the 47 prefectures of Japan, in kanji, kana or romaji, with
  the eight 地方 as both a scope filter and a quiz of their own.
- **UK County Quiz** — 107 counties and council areas, filterable to England,
  Scotland, Wales or Northern Ireland, plus a region quiz over the nine English
  regions and the other three nations.

Each question highlights one area on the map. You get two tries, three hints, and
a card telling you what it is when you run out. Zoom, pan and a "show names" mode
work the same in both.

## What counts as a "prefecture" in the UK

Nothing does, exactly — the four nations reorganised separately and no single
uniform layer covers all of them. The game uses the layer each nation actually
recognises:

| | Unit | Count |
|---|---|---|
| England | Ceremonial counties (Lieutenancies Act 1997) | 47 |
| Scotland | Council areas | 32 |
| Wales | Principal areas | 22 |
| Northern Ireland | Traditional counties | 6 |

England has 48 ceremonial counties on paper. The 48th is the City of London — a
square mile you could not click — so it is folded into Greater London.

Ceremonial counties do not nest perfectly inside the nine statistical regions of
England (ceremonial Lincolnshire has a foot in Yorkshire and the Humber, for
instance). For the region quiz each county is assigned to whichever region it sits
in most naturally, and the whole county goes with it.

## Repo layout

- `index.html` — the whole game, self-contained (no build step needed to play).
- `build/game.template.html` — the game source, with `__JP_DATA__` and `__UK_DATA__`
  slots for the two maps. Everything country-specific — names, readings, accepted
  spellings, hints and every line of UI text — lives in a pack near the top; the
  engine below it is country-agnostic.
- `build/build.py` — injects both map files into the template and writes `index.html`.
- `build/paths.json`, `build/build_paths.py` — the Japan map: prefecture SVG paths,
  canvas dimensions, and the Okinawa inset box.
- `build/paths_uk.json`, `build/build_uk_paths.py` — the UK map, generated from the
  sources below. Shetland goes in an inset box, as it does on every printed UK map,
  and the Republic of Ireland is drawn greyed out behind the six counties so that
  Northern Ireland is not left floating in open sea. It is scenery: it takes no
  clicks, is never a question, and is not counted among the 107.

## Rebuilding

```sh
python3 build/build_uk_paths.py   # only when the UK map data changes
python3 build/build.py
```

Edit `build/game.template.html` (not `index.html`) and re-run `build.py` —
`index.html` is generated and gets overwritten.

`build_uk_paths.py` downloads its sources once into `build/cache/` (gitignored) and
reuses them after that. It prints the district-to-county assignment it derived, so
that can be read back and checked.

## Where the UK boundaries come from

England's ceremonial counties are not published as boundaries anywhere, so they are
built by dissolving the 326 ONS local authority districts. The dissolve happens in
TopoJSON arc space rather than on coordinates, which makes internal borders vanish
exactly instead of leaving hairlines. Scotland and Wales come from the same shared
topology, so the borders between the three line up. Northern Ireland is an island,
so its counties can safely come from a different source.

- [martinjc/UK-GeoJSON](https://github.com/martinjc/UK-GeoJSON) — 2013 local
  authority districts for England, Scotland and Wales.
- [evansd/uk-ceremonial-counties](https://github.com/evansd/uk-ceremonial-counties) —
  ceremonial county outlines, used to decide which district belongs to which county,
  and directly for the six counties of Northern Ireland and the greyed-out Republic
  of Ireland behind them (its one unnamed feature).

Both are derived from official boundary data published under the
[Open Government Licence](http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
Contains OS data © Crown copyright and database right; contains National Statistics
data © Crown copyright and database right; contains OSNI data © Crown copyright.
