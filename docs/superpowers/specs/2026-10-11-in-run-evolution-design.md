# In-run evolution, level 1-100 and family upgrades

Date: 2026-10-11 · Status: draft for review · Branch: `evolucion-en-run` (cut from `mejoras-post-14`, which equals the head of PR #14)

## 1. Goal

Make the small Pokémon worth playing: a run is the story of a Pokémon growing
from its first form, evolving at the levels the real games use, with a level
cap of 100 like Pokémon Mystery Dungeon. A 20 to 30 minute run reaches the
evolutions comfortably; level 100 needs the XP upgrades and a long run.

Alongside, two menu fixes the author asked for: the upgrades screen stops
listing every owned Pokémon and works on the chosen partner, and the Pokémon
menu marks which families already have upgrades.

Decisions taken with the author:

| Question | Decision |
|---|---|
| What owning an evolved Pokémon means | You start as the form you chose; starting small grants an XP bonus for the run |
| Level vs cards | Level 1-100 drives stats and evolution; cards come on a schedule dense enough to max every attack |
| Non-level evolutions | Trade at 50; stones, friendship and everything else at 36 |
| Upgrades screen | Partner only, with a button to the Pokémon menu; that menu marks families with upgrades |

## 2. Current state (what changes)

- `G.DEX` (generated `js/data/pokedex.js`) has stats, types, rarity and
  generation per species but no evolution data. `tools/fetch_pokedex.py`
  downloads species and stats once from PokeAPI and does not cache raw JSON.
- `Player.xpFor(level)` = `floor((8 + 6L + 1.6·L^1.75) × 4)`; a card pick
  happens at every level; typical runs end around level 15 to 30.
- `pl.mon` is fixed for the run: sprites (`G.Sprites.Animator(mon.dex)`),
  stats (`mon.hp/atk/spd`), types (type chart, weather, liquids, move pool).
- Permanent upgrades are keyed by species (`save.pupg[dex]`). The upgrades
  screen has a `<select>` listing every owned Pokémon.
- Level is read by: missions (`level` goals 8/12/15), achievements (`level15`,
  `level30` style goals in `js/data/achievements.js`), the ranking mark
  (`lv`), run summary and coop. Three damage formulas use it: burn tick
  (`1 + level × 0.06` in `enemy.js`), Casco Dentado (`15 + level × 4` in
  `combat.js`) and the bomb pickup (`60 + level × 14` in `game.js`).
- Coop puppets are built from the member's `dex` at `Coop.begin` and never
  change species.

## 3. Design

### 3.1 Evolution data (`js/data/evolutions.js`)

A new generated file, produced once by a new script `tools/fetch_evolutions.py`
from PokeAPI's `pokemon-species` (for the chain URL) and `evolution-chain`
endpoints, with raw JSON cached under `tools/cache/pokeapi/` so re-runs are
free. It defines:

```js
G.EVOS = {
  4:  { fam: 4, evo: [{ to: 5, lvl: 16 }] },
  5:  { fam: 4, evo: [{ to: 6, lvl: 36 }] },
  6:  { fam: 4, evo: [] },
  133: { fam: 133, evo: [{ to: 134, lvl: 36 }, { to: 135, lvl: 36 }, …] },
  …
};
```

Rules for `lvl`:

| PokeAPI trigger | Level used |
|---|---|
| `level-up` with `min_level` | that level |
| `level-up` without `min_level` (friendship, time of day, held item, known move, location, affection…) | 36 |
| `use-item` (stones) | 36 |
| `trade` (with or without item) | 50 |
| any other trigger (`shed`, `spin`, `tower-of-darkness`, `three-critical-hits`…) | 36 |

Targets that are not in `G.DEX` (regional and special forms) are dropped;
a stage with no remaining targets gets `evo: []`. Every species in `G.DEX`
gets an entry; species outside any chain are their own family. The game never
contacts PokeAPI at runtime.

Helpers in the same file: `G.Evos.family(dex)`, `G.Evos.next(dex)` (the
`evo` list), `G.Evos.stage(dex)` (0 base, 1 middle, 2 final, counted along
the chain from the family base), `G.Evos.lineOf(dex)` (all species in the
family, for the menus).

### 3.2 Level 1-100 and XP

`Player.MAX_LEVEL = 100`. XP needed to leave level L:

```
xpFor(L) = floor((3 + 1.2·L + 0.25·L^1.5) × 4.19)
```

Calibration: the XP to reach level 60 equals the XP today's curve needs for
level 24, the end of a typical 25 minute run. Level 100 needs about 3.2× the
XP of level 60. XP multipliers available today stack to about ×2.2
(Sabiduría +40%, Aprendizaje +60%, Huevo Suerte +30%), so 100 is reachable
with upgrades and a long or strong run, and not otherwise. Rough checkpoints
assuming XP income grows over the run: level 16 near minute 3, 36 near
minute 9, 50 near minute 17, 60 near minute 25. These are starting values to
tune after playtesting; the test pins the formula, not the minutes.

`gainXp` stops at 100 (XP past the cap is discarded; the bar shows full).

Per-level growth, applied on top of the species stats and before passives:
max HP +1% of the species base per level, attack +0.5% per level (level 100:
+100% HP, +50% attack). Speed does not grow. On level up the HP gain is also
healed. Enemy HP scaling stays time- and attack-based (`powerK`), unchanged.

### 3.3 Cards on a schedule

A card pick is offered when the level reaches: every level from 2 to 20,
every second level from 22 to 50, every third level from 53 to 98, and 100.
`G.LevelUp.picksAt(level)` returns true for those levels; `pendingLevels`
in `game.js` only increments for them (several levels gained at once still
queue one pick per scheduled level). Picks per run: 37 by level 60, 51 by
level 100. Maxing six attacks needs 6 new + 24 ups = 30 picks and four
passives 4 + 16 = 20, so a normal run maxes its attacks and a great run maxes
everything. The level-up screen title shows the Pokémon level as today.

Level-based numbers are rescaled so the game plays the same at the new
levels (the old level ≈ new level × 0.4):

| Place | Before | After |
|---|---|---|
| Burn tick (`enemy.js`) | `1 + level × 0.06` | `1 + level × 0.024` |
| Casco Dentado (`combat.js`) | `15 + level × 4` | `15 + level × 1.6` |
| Bomb pickup (`game.js`) | `60 + level × 14` | `60 + level × 5.6` |
| Reactions `lvlK` (`reactions.js`) | `1 + level × 0.06` | `1 + level × 0.024` |
| Daily mission "level" goals | 8 / 12 / 15 | 20 / 30 / 38 |
| Achievements level goals | as in `achievements.js` (e.g. 15, 30) | × 2.5, rounded (38, 75) |
| Ranking `lv` | raw level | raw level (old marks stay; a note in the ranking UI is not needed, levels only go up) |

### 3.4 Evolving mid-run

`Player.evolveTo(dex)` switches the species in place:

- `this.mon = G.DEX_BY[dex]`, `this.dex = dex`; new `Animator` (shiny if the
  run is shiny and the new species has a shiny sheet), new body radius and
  height; `G.Sprites.preload([dex])`.
- Stats: `baseAtk`, `baseSpd` and the species HP base switch to the new
  species; max HP is recomputed from the new base, the level growth and the
  passives taken (`addMaxHp` deltas are tracked in `this.hpBonus` so they
  survive the recompute); current HP keeps its ratio.
- Types switch, which changes the type chart, weather, liquid privileges
  and the pool used for later "new move" cards. Moves, passives, item,
  focus, bonds, coins, level and XP are untouched.
- Presentation: `G.Game.flash('#fff', 0.5)`, a ring and burst, sfx
  `legend`, banner "¡Charmander evolucionó en Charmeleon!" through
  `G.Spawner.say`, and `G.Progress.event('evolvePartner', { from, to })`.

Trigger: in `gainXp`, after each level, `G.Evos.next(this.dex)` is checked;
if exactly one stage has `lvl <= level`, `evolveTo` runs immediately (even
mid-horde; the flash and a 1 s invulnerability cover the swap). If several
stages qualify (branches), the next card pick is replaced by a **choice
card screen** listing every branch (icon, name, types); choosing evolves.
Branches that are not owned still appear; evolving is the only way to see
them in a run. Picking happens through the existing level-up screen with
card type `evo-branch`.

Unlock: evolving grants the evolved species to the collection
(`G.DB.grant(to, 'evolution')`, normal form only). Shiny evolved forms still
come from the gacha or the wild. A run started as a shiny shows the shiny
evolved sprite during the run but does not grant the shiny form.

Coop: the player state array gains the current `dex` (the puppet rebuilds
its animator when it changes, like it rebuilds moves). The host's
`enemyAdded`-style events are not involved; evolution is client-side state.

### 3.5 Starting stage and XP bonus

The partner is whatever form the player chose in the Pokémon menu, as today.
`G.Evos.stage(dex)` decides the run's XP bonus: stage 0 (base form) +30%,
stage 1 +15%, stage 2 or a single-stage species 0%. The bonus multiplies
`xpMul` at run start and is shown on the Pokémon menu card as "+30% de
experiencia por empezar pequeño" with the next evolution level ("Evoluciona
al nivel 16 en Charmeleon"). The Pokémon detail view in the Pokédex shows
the family line with its levels.

### 3.6 Upgrades by family

`save.pupg` is keyed by family base dex. `G.DB.upgradesOf(dex)` resolves
`G.Evos.family(dex)` first, so every caller keeps working and Charmander,
Charmeleon and Charizard share one ladder. Migration on load (`migrate`,
save version 3 → 4): for each species key, merge into its family key taking
the highest level per upgrade, then delete the species key. Guest saves
start clean.

Upgrades screen: the `<select>` goes away. The screen shows the partner's
current form sprite, the family name ("Línea de Charmander" when the family
has more than one member, else the name), the upgrade list, and a button
"Cambiar compañero" that opens the Pokémon menu. The Pokémon menu grid
shows a small `up` icon badge on every cell whose family has at least one
upgrade level, and the detail view lists "Mejoras de la línea: N niveles".

### 3.7 Texts and docs

New strings get English entries (banner, bonus text, family label, badge
title, branch card tag). GDD §2.2, §3 and §7.2 are updated: level cap, curve,
card schedule, evolution rules, family upgrades. README gets two sentences.
`memory.md` gets the new rules and the data file.

## 4. Error handling

- A species with no entry in `G.EVOS` behaves as a single-stage family
  (`family(dex) === dex`, `next` empty, stage 0, +30% XP).
- `evolveTo` ignores a target not in `G.DEX` or without sprite metadata.
- Migration tolerates malformed `pupg` entries (non-object values are
  dropped) and runs once, guarded by the save version.
- Coop puppets ignore a `dex` they cannot resolve and keep the old one.
- The fetch script skips species whose chain request fails and logs them; the
  test fails if any species is missing from the generated file.

## 5. Testing

- Data tests (`tools/test.js`): every `G.DEX` species has an `EVOS` entry;
  every `to` exists in `G.DEX`; no level outside 1..100; trade evolutions are
  50 (Kadabra → Alakazam), stone evolutions 36 (Pikachu → Raichu), level
  evolutions keep their level (Charmander 16, Charmeleon 36); Eevee has at
  least 5 branches; `stage` returns 0/1/2 along a three-stage line.
- Curve tests: `xpFor` matches the formula; cumulative XP to 60 equals the
  old cumulative to 24 within 1%; `picksAt` yields 37 picks by 60 and 51 by
  100; `gainXp` caps at 100.
- Player tests with the sandbox stubs: `evolveTo` swaps species, keeps the HP
  ratio, moves and passives, grows types; stage bonus multiplies `xpMul`;
  per-level growth values at level 100.
- Save tests: `upgradesOf` resolves to the family; migration merges two
  species of one family taking the max per upgrade.
- Browser check: a run as Charmander reaches 16 (dev console can add XP),
  shows the banner and the Charmeleon sprite; upgrades screen without the
  selector; Pokémon menu badge.

## 6. Out of scope

Mega evolution, regional forms, evolution items as pickups, changing the
gacha pools, a Pokédex entry for evolution chains beyond the detail view
line, and rebalancing enemy scaling for the new growth (watch it in play).
