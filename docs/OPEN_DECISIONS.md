# Approved decisions and remaining release questions

## Authority
The original Complete Rulebook and preserved workbook are reference sources. Explicit user amendments take precedence only for the behaviors listed here and in RULEBOOK_MAPPING.md. Recipes and the 211-card inventory are unchanged.

## Previously approved amendments
A1 exact named card repayment, or lender-approved peso substitution. A2 shared rounds complete after all mini-rounds. A3 unpaid loans gain 2 pesos immediately at their due round's completion and 2 each later overdue shared round, payable to the lender. A4 borrowers choose normal repayment order. A5 exited-lender repayments enter match escrow. A6 secured placements do not release borrowers from unpaid debt. A7 Counter-Reaction is optional, consumed on activation, expires at round end, and each player may redirect an attack only once. A8 relevant priority: Secure Storage, Counter-Reaction, Safety Goggles, Emergency Backup, Lab Insurance. A9 multiple defences coexist under individual conditions. A10 attacker selects Equipment Theft. A11 sequential reversals affect next shared round. A12 simultaneous Formula Shuffle, empty hands pass nothing. A13 Research keeps min(2, available draw) and discards the remainder. A14 players without a Task wait for available supply; existing Task holders may still complete. A15 one replacement per opportunity with lifetime fee escalation. A16 trade/bank closes at first creation or last opportunity when all pass. A17 unlimited bank.

D1 ranking awards 30/15/5/0. D2 UTC calendar-month seasons, historical awards retained. D3 friendships require acceptance. D4 unique case-insensitive authenticated identities. D5 reconnect grace 90 seconds. D6 three consecutive missed regular turns cause forfeit. D7 configurable positive turn/negotiation timers. D8 transactional authoritative state after accepted commands.

## Final mobile specification amendments
F1 forfeits receive the lowest available placement; earlier forfeits rank lower. Already secured placements remain intact. Record reason, server timestamp and stable sequence. Forfeit Ranking Points are zero.
F2 repay available same-type cards and payable pesos (including liquidated savings), record remaining defaults, write off and close obligations. Loans to exited lenders use escrow.
F3 mandatory selections time out to stable legal choices and are recorded as automatic. Optional redirection declines. Choice sets remain server-owned.
F4 proposals expire without transfers; pending/accepted/declined/expired status remains visible to participants. No resources are reserved, so none need release.
F5 after grace expiry a player can still recover authenticated state; overdue turns count as missed. Grace expiry alone does not forfeit a player.
F6 explicitly approved follow-up: insufficient resources across multiple lenders settle **oldest server-issued loan sequence first**. Normal voluntary repayment remains borrower-selected. This resolves the earlier blocked arbitration question.

## Technical decisions, not physical game rules
- Loan due round = creation round + agreed positive shared-round duration - 1.
- Card IDs represent unique references within current possession, not authentication; a trade can issue new references. The scanner verifies exact owned IDs plus the current Task reference against the authoritative revision.
- Server enrollment issues the permanent player ID as required by the latest mobile specification. Device credentials are high-entropy random secrets; only verifiers are stored server-side. Mobile SQLite contains metadata/pending command intents; secure storage contains the device credential; short-lived access tokens stay in memory.
- Expiring 15-minute sessions can be renewed with the device credential. Revocation invalidates both. The legacy device-credential HTTP header remains compatible with existing clients/tests.
- Snapshots are revisioned and private per viewer; reconnect fetches the latest snapshot rather than historical event replay.
- One server worker; process-local socket broadcasts. SQLite transactions serialize accepted commands.
- Open lobby lifetime: 30 minutes. Explicit host leave transfers host to the earliest remaining member; absent hosts may reconnect, or the lobby expires. A faster automatic host-disconnect transfer policy is not specified.

## Remaining release questions and verification gates
- Broader ranked anti-collusion/point-farming eligibility has no approved scoring penalty. Implemented safeguards are authenticated server results, unique awards and enrollment/session throttling; no arbitrary point penalty is introduced.
- Account recovery and multiple-device enrollment are not implemented. Reset warns that access may be permanently lost.
- Android build, launch, real platform secure storage and device networking require an installed Android SDK/device or emulator and sufficient disk space. iOS builds require macOS/Xcode. Docker runtime verification requires Docker.
- Scientific accuracy audit before printing; recipes are game-card requirements, not synthesis instructions.

### Existing lobby host lease clarification
The implemented schema-v4 lobby presence lease is renewed by authenticated lobby polling. After a host is absent for 90 seconds, the earliest remaining member with fresh presence becomes host. If nobody has fresh presence, the existing lobby expiration applies. This is a multiplayer lifecycle technical decision, not a physical game-rule change; regression: test_disconnected_lobby_host_lease_transfers_after_grace.
