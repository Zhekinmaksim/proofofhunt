import { commitmentOf } from "./commitment.js";
const addressOK = (v) => /^0x[\da-f]{40}$/i.test(v ?? "");
function scopeKey(endpoint, contract, account) {
  if (!addressOK(contract) || !addressOK(account)) throw Error("Invalid recovery address");
  return `poh:v2:${new URL(endpoint).href}:${contract.toLowerCase()}:${account.toLowerCase()}`;
}
async function validateRecovery(value, expectedScope) {
  const data = typeof value === "string" ? JSON.parse(value) : value;
  if (!data || data.version !== 2 || data.scope !== expectedScope || !Array.isArray(data.records) || data.records.length > 8192) throw Error("Backup belongs to another network, contract or account, or is invalid.");
  for (const r of data.records) {
    if (!Number.isSafeInteger(r.clue) || r.clue < 0 || r.clue > 63 || typeof r.answer !== "string" || r.answer.length > 240 || typeof r.salt !== "string" || !/^[\da-f]{32}$/.test(r.salt) || !addressOK(r.account) || !expectedScope.endsWith(":" + r.account.toLowerCase()) || !/^[\da-f]{64}$/.test(r.commitment)) throw Error("Invalid recovery record");
    if (await commitmentOf(r.answer, r.salt, r.account, r.clue) !== r.commitment) throw Error("Recovery commitment does not match its answer and salt");
    if (r.tx && !/^0x[\da-f]{64}$/i.test(r.tx)) throw Error("Invalid transaction hash");
  }
  if (new Set(data.records.map((r) => r.commitment)).size !== data.records.length) throw Error("Duplicate recovery records");
  return data;
}
function mergeRecovery(a, b) {
  const m = new Map(a.records.map((r) => [r.commitment, r]));
  for (const r of b.records) m.set(r.commitment, { ...r, ...m.get(r.commitment) });
  return { ...a, records: [...m.values()] };
}
function transactionOutcome(tx) {
  if (!tx) return "UNKNOWN";
  const status = String(tx.statusName ?? tx.status).toUpperCase();
  if (status !== "FINALIZED") return status;
  const last = tx.consensus_history?.consensus_results?.at(-1);
  const phases = last?.status_changes;
  if (phases && !phases.includes("ACCEPTED")) return "FAILED";
  const result = tx.consensus_data?.leader_receipt?.[0]?.execution_result ?? tx.leader_receipt?.[0]?.execution_result;
  if(result === "ERROR") return "FAILED";
  return result === "SUCCESS" && phases?.includes("ACCEPTED") ? "FINALIZED" : "UNVERIFIED_FINALIZED";
}
function safeSource(url) {
  try {
    const u = new URL(url);
    return ["https:", "http:"].includes(u.protocol) ? u.href : null;
  } catch {
    return null;
  }
}
export {
  addressOK,
  mergeRecovery,
  safeSource,
  scopeKey,
  transactionOutcome,
  validateRecovery
};
