# Remembered Realms Character Builder

A lore-and-identity character builder for The Remembered Realms campaign on Kanka.

Players pick a level (1–20, default 20), choose a species, background, class and subclass (each with its statblock), set ability scores (standard array or point buy) and skills, answer five sections of prompts, and finish with:

- a **character sheet** (PDF) at that level, built in their browser from `character-sheet-template.pdf` and downloaded straight to their device. Nothing is stored on the site. Every class and subclass feature up to that level is listed, with the full feature text on the notes pages (extra copies of the notes page are added as needed). No general feats, ASIs, epic boons or spells are added.
- a profile card. "Copy for Kanka" produces HTML to paste into a new article on their Kanka character (the matching styles live in the campaign CSS as "Character profile cards").

## Files

- `index.html`: the builder's screens.
- `sheet.js`: the sheet math for any level (scores, HP, AC, skills, scaling class values…) and the PDF filling.
- `character-sheet-template.pdf`: MPMB's 2024 printer-friendly sheet with its scripts and control buttons removed (`tools/clean_sheet.py`).
- `vendor/pdf-lib.min.js`: the library that fills the PDF in the browser (MIT licence alongside it).
- `rules.js`: mechanics read from the wiki: hit die, saves, skills, feature blurbs and full text, uses, and each class's level 1–20 table. **Built automatically.**
- `data.js`: the campaign's species, classes, subclasses, backgrounds and deities, with blurbs and wiki links. **Built automatically; don't edit by hand.**
- `sheets.js`: each species' statblock and each class, subclass and background's In-Game Stats post, cleaned up to plain formatting. **Built automatically.**
- `img/`: square copies of the species, class, subclass and background art. **Built automatically.**
- `blurbs.json`: the short blurbs for species, backgrounds and deities. **Edit these freely.**
- `builder-config.json`: which Kanka families appear and in what order, and a few special cases.
- `tools/snapshot.py`, `tools/rules.py` and `.github/workflows/kanka-sync.yml`: the automation.

## How updating works

Every night, GitHub runs `tools/snapshot.py`. It reads the wiki through Kanka's API, rebuilds `data.js`, `sheets.js` and `img/`, and commits only if something changed. The site updates about a minute after that.

To update right away: open the repo's **Actions** tab → **Sync from Kanka** → **Run workflow**. This works from the GitHub phone app too.

Each run's summary lists new entries that got starter blurbs and species still missing a statblock.

### What the snapshot picks up from Kanka

- **Species**: races directly under one of the families in `builder-config.json`. Races under Homo and Goblinkin count as part of the family above them. A race is left out if it has the **Not Playable** tag or is listed under `skip_species`.
- **Statblocks**: the Species Stats ability attached to the species under In-Game Features. If there isn't one, the species' "In-Game Stats" post is used instead.
- **Classes, subclasses, backgrounds**: abilities tagged **Class**, **Subclass** or **Background**. A subclass goes under the class that's its parent. Each needs a post named **In-Game Stats** written in the format in the project doc "Kanka format for the character builder"; until it has one it shows as greyed-out "Coming soon". Full feature text and the class table (a table whose first column runs 1–20) are read from any public post on the entry, matched to the blurbs by level and name.
- **Species mechanics** (size, speed, darkvision, trait names, skills) are read from the species statblock as well as possible. Players can adjust species skills in the builder because statblock wording varies.
- **Deities**: characters whose type is "Primordial", "Deity", or starts with "Deity, ".
- **Art**: each entry's main image, cropped square.
- Private entries are always left out.

### Blurbs

The automation never changes a blurb once it's in `blurbs.json`. When a new species, background or deity appears, it gets a starter blurb taken from the first sentence of its Kanka entry. Rewrite that blurb whenever you like. If the entry has no text yet, it's skipped until it does.

### Common changes to `builder-config.json`

- **Rename a family in the builder**: change its `name`. `kanka_name` is just a reminder of the Kanka name.
- **Add a new family**: add `{"id": <Kanka entity id>, "name": "Display name"}` to `families`, in the position you want it to appear.
- **Show a species under a different family**: add it to `move_species`.

The entity id is the number at the end of an entry's Kanka address: `.../entities/9465423`.

## Kanka token

The automation signs in to Kanka with a personal access token saved as the repository secret `KANKA_TOKEN` (Settings → Secrets and variables → Actions). Kanka tokens expire after a year. When a run fails with "Kanka rejected the token", make a new token in Kanka (Settings → API) and paste it into that secret.

Answers are saved in each player's own browser. Nothing is sent anywhere.
