# Remembered Realms Character Builder

A lore-and-identity character builder for The Remembered Realms campaign on Kanka.

Players choose a species, class, subclass and background, answer five sections of prompts, and get a finished profile card. "Copy for Kanka" produces HTML to paste into a new article on their Kanka character (the matching styles live in the campaign CSS as "Character profile cards").

## Files

- `index.html`: the whole builder.
- `data.js`: the campaign's species, classes, subclasses, backgrounds and deities, with blurbs and wiki links. **Built automatically; don't edit by hand.**
- `sheets.js`: each species' statblock, cleaned up to plain formatting. **Built automatically.**
- `img/`: square copies of the species, class, subclass and background art. **Built automatically.**
- `blurbs.json`: the short blurbs for species, backgrounds and deities. **Edit these freely.**
- `builder-config.json`: which Kanka families appear and in what order, and a few special cases.
- `tools/snapshot.py` and `.github/workflows/kanka-sync.yml`: the automation.

## How updating works

Every night, GitHub runs `tools/snapshot.py`. It reads the wiki through Kanka's API, rebuilds `data.js`, `sheets.js` and `img/`, and commits only if something changed. The site updates about a minute after that.

To update right away: open the repo's **Actions** tab → **Sync from Kanka** → **Run workflow**. This works from the GitHub phone app too.

Each run's summary lists new entries that got starter blurbs and species still missing a statblock.

### What the snapshot picks up from Kanka

- **Species**: races directly under one of the families in `builder-config.json`. Races under Homo and Goblinkin count as part of the family above them. A race is left out if it has the **Not Playable** tag or is listed under `skip_species`.
- **Statblocks**: the Species Stats ability attached to the species under In-Game Features. If there isn't one, the species' "In-Game Stats" post is used instead.
- **Classes, subclasses, backgrounds**: abilities tagged **Class**, **Subclass** or **Background**. A subclass goes under the class that's its parent.
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
