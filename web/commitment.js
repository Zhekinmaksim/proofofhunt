/*
 * The commitment a player publishes before revealing their answer.
 *
 * This file exists so there is exactly one implementation of the rule on the
 * client side, and so it can be tested against the contract rather than
 * assumed to match it. scripts/test_commitment_parity.py runs this under node
 * and compares its output to contracts/proof_of_hunt.py across a set of awkward
 * inputs.
 *
 * That test is not ceremony. If the client normalises an answer even slightly
 * differently from the contract, reveal() rejects the answer the player
 * actually meant, the commit is spent, and the player loses their place in the
 * race for a reason they cannot see. The rule is duplicated because an
 * Intelligent Contract is a single file and cannot export a module; the test is
 * what keeps the duplicate honest.
 *
 * Mirrors, exactly:
 *
 *     normalise_answer(a)                a.strip().lower(), runs of whitespace
 *                                        collapsed to one space
 *     commitment_of(a, salt, who, idx)   sha256(norm | salt | who.lower() | idx)
 */

export function normaliseAnswer(answer) {
  return String(answer).trim().toLowerCase().replace(/\s+/g, " ");
}

export async function commitmentOf(answer, salt, player, clueIdx) {
  const payload = [
    normaliseAnswer(answer),
    String(salt),
    String(player).toLowerCase(),
    String(clueIdx),
  ].join("|");
  const bytes = new TextEncoder().encode(payload);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/*
 * A salt the player must keep.
 *
 * Losing it means the commitment can never be revealed: the answer is right,
 * the commit holds its place in the race, and it can never be redeemed. That is
 * why the play view makes saving it a step rather than a footnote.
 */
export function newSalt() {
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
}
