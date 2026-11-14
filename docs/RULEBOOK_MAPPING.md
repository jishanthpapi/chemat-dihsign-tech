# Rulebook mapping

PDF page numbers are printed page numbers. `rulebook-extracted.txt` preserves all 27 pages; PDF text extraction loses some formula subscripts. Workbook formulas are retained in JSON; recipes are game requirements, not laboratory instructions.

| Reference | Rule | Implementation / milestone |
|---|---|---|
| §1 p3; §§20–23 pp20–25 | 82 reactants, 30 apparatus, 35 tasks, 64 actions | `data/catalog.json`, catalog tests, M1 |
| §2 p4 | 10-point target, ordered placements, exit, debt freeze | M2/M3 deferred |
| §3 p5 | 2–4 players, shuffled separate decks, random first player, setup die, secret task | `Game.__init__`, M1 |
| §4 p6 | regular turns → action resolution → shared reaction → mini-rounds | full scheduler M2 deferred |
| §§5–6 p7 | income, bank payments, top-card purchases | setup/first turn and `Game.buy`, M1; subsequent income M2 |
| §§7–9 pp8–9 | banking, gifts, consensual trades, loans and penalties | M3 deferred, decisions required |
| §10 p10 | one secret task, end-opportunity redraw, escalating replacement | completion/redraw M1; replacement M2 |
| §11 p11 | one successful compound, owned ingredients, consumed apparatus, 5 + card count fee, 1/3/5 base points | `ReactionOpportunity`, all 20 recipes tested M1 |
| §12 p12 | 2 buy + 2 play, queued actions, defence then attack then Good/Chaos | action purchase M1; queue/resolution M2 |
| §13 p13 | eight Good types; Double Yield ×2 stacking and shared-phase expiry | inventory M1; effects M2 |
| §§14–16 pp14–16 | eight Attack, five Defence types and interaction priorities | inventory M1; effects M2, decisions required |
| §17 p17 | eight Chaos types, undefendable | inventory M1; effects M2 |
| §18 p18 | ordered consecutive mini-rounds, delayed actions, no loan-round increment | M2/M3 |
| §19 p19 | independent discards, reshuffle only on exhaustion, partial draws | `Deck.draw` M1; multi-draw effects M2 |
| §24 p26 | consolidated restrictions | regression coverage expanded by milestone |
| §25 p27 | unresolved rules | `OPEN_DECISIONS.md` |

`data/card-table-extracted.json` preserves every workbook row including outdated totals/effects. `scripts/build_catalog.py` generates canonical structured data with explicit corrections. Action names/categories/quantities are structured; authoritative action effect prose remains in extracted rulebook §§13–18 until the resolver milestone. Do not implement effects from outdated workbook descriptions.

## Source conflict ledger
| Field | Workbook | Complete rulebook used |
|---|---|---|
| Medium task copies | 1 each, total tasks 30 | 2 each, tasks 35 |
| Sodium hydroxide copies | 8, reactants 81 | 9, reactants 82 |
| Iron(II) oxalate apparatus | Beaker + Filter funnel | Beaker + Stirring rod |
| Action total label | 62; actual rows sum to 64 | 64 |
| Action category price labels | Good 1, Attack/Defence 2, Chaos 3 | all actions buy 2, play 2 |
| Double Reaction | immediate extra turn | mini-round after shared reaction; queued mini-round actions next shared resolution |
| Double Yield | next compound, no explicit expiry | next current shared-phase compound only, stacks, expires |
| Lucky Reaction | any deck | excludes Tasks |
| Chemical Discovery | generic cards | Reactant Cards |
| Equipment Recall | returns to deck | apparatus discard |
| Lab Lockdown | next turn | upcoming current shared Reaction Phase |
| Defence summaries | abbreviated scopes/expiry | detailed §§15–16, Chaos excluded |

These are disclosed source precedence choices, not silent recipe edits. The complete rulebook is explicitly final and its inventory agrees with the user's 211 requirement. Preserve this ledger if the creator revises precedence.
