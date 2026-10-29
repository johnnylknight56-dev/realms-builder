# Remembered Realms Character Builder

A lore-and-identity character builder for The Remembered Realms campaign on Kanka.

Players choose a species, class, subclass and background, answer five sections of prompts, and get a finished profile card. "Copy for Kanka" produces HTML to paste into a new article on their Kanka character (the matching styles live in the campaign CSS as "Character profile cards").

## Files

- `index.html`: the whole builder.
- `data.js`: a snapshot of the campaign's species, classes, subclasses, backgrounds and deities, with blurbs and wiki links.
- `sheets.js`: each species' statblock from its "[Species] Stats" ability, sanitized to plain formatting.
- `img/`: square copies of the species, class and background art.

## Updating

When species, classes, subclasses, backgrounds or deities change in Kanka, take a new snapshot and replace `data.js`, `sheets.js` and `img/`. Nothing else needs to change.

Answers are saved in each player's own browser. Nothing is sent anywhere.
