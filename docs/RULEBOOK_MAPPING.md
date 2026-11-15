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

## Approved amendment audit (2026-11-14)
These are new design amendments, not text from the original rulebook. Audit completed before implementation. Conflict means a more specific amended behavior supersedes the source; extension fills a gap.

| ID | Original reference | Comparison and approved behavior |
|---|---|---|
| A1 | §9, §25 | Extension: exact named card repayment; lender-approved peso substitution |
| A2 | §18, §25 | Compatible clarification: completed shared-round checkpoint after every mini-round |
| A3 | §9, §25 | Extension: immediate 2-peso overdue charge at due checkpoint, +2 each later completed round; lender receives penalties |
| A4 | §25 | Extension: borrower chooses debt repayment order |
| A5 | §2, §25 | Extension to exit cleanup: repayments to exited lender retained in escrow instead of returning to bank |
| A6 | §2 | Original rule reaffirmed; ranked placement does not force debtor exit |
| A7 | §§15–16, §25 | Extension/restriction of permitted chains: optional activation, immediate consume, round expiry, one redirect/player/attack |
| A8 | §§15–16 | Compatible Storage/Goggles/Backup/Insurance priorities; fills unspecified Counter priority |
| A9 | §15, §25 | Original coexistence reaffirmed; individual activation conditions retained |
| A10 | §14, §25 | Extension: Equipment Theft chosen by attacker |
| A11 | §17, §25 | Extension adopts suggested sequential reversals; next-round effective date retained |
| A12 | §17, §25 | Extension: outgoing selections simultaneous, empty hands skip only their own pass |
| A13 | §13, §25 | Supersedes fixed five-card keep-2/discard-3 for short supply; full supply unchanged |
| A14 | §§10,19,25 | Explicit temporary exception to exactly-one-active-task invariant when no task available |
| A15 | §10, §25 | Restriction: once per opportunity; escalating lifetime fee retained |
| A16 | §§7–8, §25 | Compatible first-creation cutoff; adds last-opportunity cutoff for all-pass phases |
| A17 | §5 | Extension: explicit unlimited bank, net-flow accounting retained |
| D1 | no original rule | New Ranking Points separate from pesos/Match Points; 30/15/5/0 by placement |
| D2 | no original rule | New UTC calendar-month standings, historical seasons retained |
| D3 | no original rule | New accepted request requirement for friends |
| D4 | no original rule | New unique username and device credential authentication, ID alone insufficient |
| D5 | no original rule | New 90-second reconnect window |
| D6 | no original rule | New three-missed-regular-turn forfeit; conflicts with normal §2 exit requirements on forfeit debt remain unresolved |
| D7 | no original rule | New configurable turn and negotiation deadlines |
| D8 | no original rule | New transactional authoritative persistence after accepted commands |

Implementation and amendment-specific tests are indexed in docs/AMENDMENT_STATUS.md. Do not treat rulebook extracts or workbook rows as amended source documents.

## Full mobile specification amendments
| Amendment | Original rulebook relationship | Implementation |
|---|---|---|
| F1 bottom-ranked forfeits, stable ordering, zero ranking award | New digital exit exception to §2; secured placements preserved | Match.forfeit, Store._save |
| F2 settle available forfeit assets and record defaults | New digital exception to §9 continuing unpaid debt; insufficient multiple-lender priority remains blocked | Match.forfeit and loan_history |
| F3 deterministic legal mandatory selections on timeout | New digital selection fallback, preserves original legal choice sets | Match.tick/choose; automatic history event |
| F4 expired proposals persist with no transfers | Technical extension of mutual consent in §§8–9; no reservation invented | offer.status, accept/decline/tick |
| F5 recovery after grace without automatic immediate forfeit | Digital clarification; 90-second protection followed by missed-turn rules | reconnect/tick/end_turn |
| Card instance scanner and expiring sessions | Technical protocol additions, no recipe or scoring change | scan, private instances/task_id, SQLite sessions |

## Explicit oldest-first forfeit settlement approval
F6: the user subsequently approved settling insufficient forfeit resources in ascending server-issued loan sequence. This supersedes the former blocked multiple-lender priority question. Exact card repayment, payable pesos, recorded defaults and closed obligations are retained; no negative inventories are permitted. Test: test_multiple_lender_shortfall_settles_oldest_server_sequence_first. Normal §9 voluntary repayment still follows A4 borrower choice.
