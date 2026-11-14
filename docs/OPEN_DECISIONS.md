# Open decisions

No unspecified rule below is implemented as a guessed default. The first milestone deliberately avoids these branches. Source conflicts and the explicit complete-rulebook precedence used for M1 appear in RULEBOOK_MAPPING.md.

## Rulebook §25 decisions
- Card loan repayment when equivalent cards are unavailable.
- Loan deadline representation; exact completed-shared-round checkpoint, first penalty checkpoint, and penalty recipient.
- Repayment priority across simultaneous debts.
- Repayment to exited lenders; continued debt play after only one unplaced player remains.
- Multiple Experiment Reversal effects in one resolution (sequential reversal is only a suggestion in the source).
- Formula Shuffle with empty hands and treatment of remaining passes.
- Counter-Reaction consumption, expiry, activation choice, defence priority and chain termination.
- Repeated Defence stacking/consumption.
- Equipment Theft selection owner.
- Restoring an active Task if both task piles are empty.
- Research Breakthrough keep/discard split when fewer than five cards can be drawn.
- Number of voluntary replacements per opportunity; banking/trading closure when nobody creates.
- Chemistry audit before physical printing; game recipes are not synthesis guidance.

## Product decisions absent from sources
- Ranking Points formula, eligibility, anti-collusion policy, ties, monthly timezone and season boundary. No ranking awards until specified.
- Username uniqueness and friend request acceptance/privacy model.
- Disconnect grace, abandonment, forfeits, command timeouts and credential recovery after local reset.
- Treatment of central bank supply: no finite inventory is stated. M1 records net receipts/payments without inventing a starting supply.
- Maximum regular-turn duration and negotiation deadlines for production.

An empty task draw is represented internally as `None`; this does not resolve the rule requiring one active task. Full gameplay must surface a blocked decision rather than invent a task or end condition.
