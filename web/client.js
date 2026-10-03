import {canCommit,unresolvedTransaction} from "./lifecycle.js";
import { createClient, abi } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { CalldataAddress } from "genlayer-js/types";
import { verifyWalletIdentity, singleSendProvider } from "./wallet.js";
import { CONTRACT, NETWORKS } from "./config.js";
import { commitmentOf, newSalt, normaliseAnswer } from "./commitment.js";
import { addressOK, scopeKey, validateRecovery, mergeRecovery, transactionOutcome, safeSource } from "./recovery.js";
const $ = (id) => document.getElementById(id);
const json = (v) => JSON.stringify(v, (_, x) => typeof x === "bigint" ? x.toString() : x, 2);
let client, account = "", race, player, clue, pending, backup, busy = false, actionLock = false, refreshing = false, lastRefresh = 0, lastReadOK = false, generation = 0, unresolved = null;
const clueCache = new Map();
const isPlay = Boolean($("network"));
const network = () => NETWORKS[isPlay ? $("network").value : "studionet"];
const address = () => isPlay ? $("contract").value.trim() : CONTRACT;
function status(message) {
  if ($("status")) $("status").textContent = message;
}
function freshClient(provider) {
  const n = network();
  return createClient({ chain: { ...studionet, id: n.chainId, rpcUrls: { default: { http: [n.endpoint] } } }, endpoint: n.endpoint, ...account ? { account } : {}, ...provider ? { provider } : {} });
}
async function read(method, kwargs = {}) {
  return client.readContract({ address: address(), functionName: method, kwargs, transactionHashVariant: "latest-final" });
}
const addrValue = (v) => new CalldataAddress(Uint8Array.from(v.slice(2).match(/../g), (h) => parseInt(h, 16)));
function save(data = backup) {
  localStorage.setItem(data.scope, json(data));
  if (localStorage.getItem(data.scope) !== json(data)) throw Error("Recovery storage verification failed.");
}
async function load() {
  backup=null;
  unresolved=null;
  const key = scopeKey(network().endpoint, address(), account);
  const raw = localStorage.getItem(key);
  backup = raw ? await validateRecovery(raw, key) : { version: 2, scope: key, records: [] };
  const journal = JSON.parse(localStorage.getItem(backup.scope + ":transaction") || "null");
  unresolved = unresolvedTransaction(backup,journal);
}
function buttons() {
  if (!isPlay) return;
  const active = Boolean(account && backup && lastReadOK && backup.scope===scopeKey(network().endpoint,address(),account) && race?.protocol_version === 2 && !busy && !actionLock && !unresolved);
  $("join").disabled = !active || player?.joined || race.state !== 1;
  $("commit").disabled = !active || !canCommit(race,player);
  $("reveal").disabled = !active || !pending || pending.revealed;
  $("judge").disabled = !active || !pending?.revealed || ![0, 3].includes(Number(pending.verdict));
  $("expire").disabled = !active || !pending;
  $("cancel").disabled = !active || ![1, 2].includes(Number(race?.state));
  $("connect").disabled = busy || actionLock || refreshing;
  $("network").disabled = busy || actionLock || refreshing;
  $("contract").disabled = busy || actionLock || refreshing;
}
function board(rows) {
  const b = $("board");
  if (!b) return;
  b.replaceChildren();
  if (!rows.length) {
    b.textContent = "No runners yet. Join the race to take the first place on the board.";
    return;
  }
  for (const [i, r] of rows.entries()) {
    const row = document.createElement("div");
    row.className = "row" + (i === 0 ? " top" : "");
    for (const [tag, text] of [["i", String(i + 1).padStart(2, "0")], ["b", r.handle || r.addr], ["span", `${r.cleared} controls \xB7 ${r.total_attempts} attempts`], ["em", `commit #${r.last_correct_cid}`]]) {
      const e = document.createElement(tag);
      e.textContent = text;
      row.append(e);
    }
    b.append(row);
  }
}
function draw() {
  if (!isPlay) return;
  $("addr-out").textContent = address();
  $("net-out").textContent = network().name;
  $("race-state").textContent = race ? `${["DRAFT", "OPEN", "WON \u2014 pending earlier commits", "FINAL", "CANCELLED"][race.state] ?? race.state} \xB7 ${race.player_count} runners \xB7 ${race.clue_count} clues` : "Not loaded";
  $("player-state").textContent = player?.joined ? `Position ${player.position}/${race.clue_count} \xB7 ${player.attempts_left} attempts left at this clue${player.finished ? " \xB7 Finished" : ""}` : "Join to start";
  $("deadlines").textContent = race ? `Reveal within 24 hours of commit; resolve within 7 days. Race ends ${race.closes_at ? new Date(Number(race.closes_at) * 1e3).toUTCString() : "30 days after opening"}. Expiring an unrevealed commit spends an attempt; a revealed expiry does not.` : "";
  if (clue) {
    $("n-out").textContent = `Clue ${clue.idx + 1}`;
    $("clue-out").textContent = `${clue.idx + 1} of ${race.clue_count}`;
    $("title-out").textContent = clue.title;
    $("q-out").textContent = clue.riddle;
    $("form-out").textContent = `Answer form: ${clue.answer_form}. Read the source before committing.`;
    const url = safeSource(clue.source_url);
    $("src-out").textContent = url || "Invalid source URL";
    if (url) $("src-out").href = url;
    else $("src-out").removeAttribute("href");
  }
  $("pending-state").textContent = pending ? json(pending) : "No active commitment.";
  $("log").replaceChildren();
  for (const r of backup?.records ?? []) {
    const tr = document.createElement("tr");
    for (const v of [r.clue + 1, r.answer, r.salt, r.commitment]) {
      const td = document.createElement("td");
      td.textContent = String(v);
      tr.append(td);
    }
    $("log").append(tr);
  }
  buttons();
}
async function refresh(force = false) {
  if (force && lastReadOK && Date.now()-lastRefresh<5000) return;
  if (refreshing || busy || !force && Date.now() - lastRefresh < 3e4) return;
  if (!addressOK(address())) {
    status("Set a deployed protocol-v2 contract address.");
    if (!isPlay && $("board")) $("board").textContent = "The next beta race is being prepared.";
    return;
  }
  refreshing = true;
  lastReadOK = false;
  lastRefresh = Date.now();
  const g = generation;
  try {
    client = freshClient();
    const nextRace = await read("race");
    if (g !== generation) return;
    race = nextRace;
    if($("landing-state")) $("landing-state").textContent=`Studionet · ${["Draft","Open","Winner pending","Finished","Cancelled"][Number(race.state)]??"Unknown state"}`;
    board(await read("leaderboard"));
    if (!isPlay) return;
    player = account ? await read("player", { addr: addrValue(account) }) : null;
    pending = player?.joined && Number(player.pending_cid) >= 0 ? await read("commit_at", { cid: Number(player.pending_cid) }) : null;
    const idx = player?.joined ? Number(player.position) : 0;
    const clueKey = `${network().endpoint}:${address()}:${race.chain_version}:${idx}`;
    if(idx < race.clue_count && !clueCache.has(clueKey)) clueCache.set(clueKey, await read("clue", {idx}));
    clue = idx < race.clue_count ? clueCache.get(clueKey) : null;
    if(g!==generation) return;
    if (backup && pending) {
      const match = backup.records.find((r) => r.commitment === pending.commitment);
      if (match) {
        match.cid = Number(pending.cid);
        match.submitting = false;
        if (unresolved === "unknown" && localStorage.getItem(backup.scope + ":transaction") === null) unresolved = null;
        save();
      }
    }
    if (unresolved && unresolved !== "unknown") {
      const tx = await client.request({ method: "eth_getTransactionByHash", params: [unresolved] });
      const outcome = transactionOutcome(tx);
      $("tx-state").textContent = `${unresolved}
${outcome}`;
      if (["FINALIZED", "FAILED", "CANCELED", "UNDETERMINED"].includes(outcome)) {
        for (const r of backup.records) if (r.tx === unresolved) {
          r.settled = true;
          r.submitting = false;
          r.outcome = outcome;
        }
        const journal = JSON.parse(localStorage.getItem(backup.scope + ":transaction") || "null");
        if (journal?.cid !== void 0) {
          const result = await read("commit_at", { cid: Number(journal.cid) });
          $("tx-state").textContent += `
${["PENDING", "CORRECT", "INCORRECT", "UNDETERMINED", "EXPIRED"][Number(result.verdict)] ?? result.verdict} \xB7 source ${["OK", "DRIFTED", "UNREACHABLE"][Number(result.pin_status)] ?? result.pin_status}`;
        }
        unresolved = null;
        localStorage.removeItem(backup.scope + ":transaction");
        save();
      }
    }
    lastReadOK = true;
    status(race.protocol_version === 2 ? "Connected to finalized contract state." : "Legacy contract: writes disabled. Use a protocol-v2 race.");
    draw();
  } catch (e) {
    status("Read failed: " + (e.shortMessage || e.message));
    if (!isPlay && $("board")) $("board").textContent = "Live positions are unavailable. Open the play view to check the network.";
  } finally {
    refreshing = false;
    buttons();
  }
}
async function verifyWallet() {
  if (!window.ethereum) throw Error("Install an EIP-1193 wallet or use the manual payload below.");
  const n = network();
  const params = [{ type: "read", to: address(), from: account, data: abi.transactions.serialize([abi.calldata.encode(abi.calldata.makeCalldataObject("race", [], {})), false]), transaction_hash_variant: "latest-final" }];
  await verifyWalletIdentity(window.ethereum, client, { account, chainId: n.chainId, endpoint: n.endpoint, params });
}
async function write(method, kwargs, record) {
  if (busy || unresolved) throw Error("Resolve the pending transaction before sending another.");
  if (refreshing) throw Error("A state refresh is in progress. Wait a moment.");
  await refresh(true);
  if (!lastReadOK) throw Error("Refresh the contract state before sending.");
  if (race?.protocol_version !== 2) throw Error("Only protocol v2 is supported for writes.");
  const operationBackup = backup;
  const journalKey = operationBackup.scope + ":transaction";
  busy = true;
  buttons();
  try {
    const currentGeneration = generation;
    const provider = singleSendProvider(window.ethereum, async () => {
      if (currentGeneration !== generation) throw Error("Wallet context changed before signing.");
      await verifyWallet();
      if(currentGeneration!==generation)throw Error("Wallet context changed while verifying.");
      if(record){record.submitting=true;save(operationBackup);}
      localStorage.setItem(journalKey, json({ method, startedAt: (/* @__PURE__ */ new Date()).toISOString(), state: "awaiting-wallet" }));
    });
    const hash = await freshClient(provider).writeContract({ address: address(), functionName: method, kwargs });
    localStorage.setItem(journalKey, json({ method, cid: kwargs.cid, hash, state: "submitted" }));
    unresolved = hash;
    if (record && operationBackup.records.includes(record)) {
      record.tx = hash;
      record.submitting = false;
      save(operationBackup);
    }
    $("tx-state").textContent = `${method}: ${hash}
Submitted; waiting for consensus. No automatic resubmission.`;
    status("Transaction submitted. Wait for FINALIZED before the next step.");
  } catch (e) {
    const rejected = e.code === 4001 || e.cause?.code === 4001;
    if (rejected || !localStorage.getItem(journalKey)) {
      localStorage.removeItem(journalKey);
      if (record) {
        record.submitting = false;
        save(operationBackup);
      }
    } else if (localStorage.getItem(journalKey)) {
      unresolved = "unknown";
    }
    status(e.shortMessage || e.message);
    throw e;
  } finally {
    busy = false;
    buttons();
  }
}
function handle(fn) {
  return async () => {
    if (actionLock) return;
    actionLock = true;
    buttons();
    try {
      await fn();
    } catch (e) {
      status(e.shortMessage || e.message);
    } finally {
      actionLock = false;
      buttons();
    }
  };
}
if (isPlay) {
  $("contract").value = CONTRACT;
  $("salt").value = newSalt();
  $("who").readOnly = false;
  $("watch").onclick = handle(async () => {
    if (!addressOK($("who").value)) throw Error("Enter a valid public account address.");
    generation++;
    account = $("who").value;
    lastReadOK=false;
    await load();
    await refresh(true);
  });
  $("network").onchange = $("contract").onchange = handle(async () => {
    generation++;
    lastReadOK=false;
    lastRefresh=0;
    account = "";
    backup = null;
    player = null;
    pending = null;
    race = null;
    unresolved = null;
    $("who").value = "";
    await refresh(true);
  });
  $("connect").onclick = handle(async () => {
    if (!window.ethereum) throw Error("No browser wallet found. Install an EIP-1193 wallet; no private key is requested.");
    if (!addressOK(address())) throw Error("Set a valid protocol-v2 contract first.");
    generation++;
    account = (await window.ethereum.request({ method: "eth_requestAccounts" }))[0];
    $("who").value = account;
    lastReadOK=false;
    await load();
    await refresh(true);
  });
  $("refresh").onclick = handle(() => refresh(true));
  $("recover").onclick = handle(async () => {
    const hash = $("recover-hash").value.trim();
    if (!backup || !/^0x[\da-f]{64}$/i.test(hash)) throw Error("Connect and enter the transaction hash from your wallet.");
    const tx = await client.request({ method: "eth_getTransactionByHash", params: [hash] });
    const sender = tx?.from_address ?? tx?.from;
    const target = tx?.to_address ?? tx?.to;
    if (sender?.toLowerCase() !== account.toLowerCase() || target?.toLowerCase() !== address().toLowerCase()) throw Error("Transaction does not belong to this account and contract.");
    unresolved = hash;
    localStorage.setItem(backup.scope + ":transaction", json({ hash, state: "submitted" }));
    await refresh(true);
  });
  $("roll").onclick = () => {
    $("salt").value = newSalt();
  };
  $("join").onclick = handle(() => write("join", { handle: $("handle").value.trim() }));
  $("commit").onclick = handle(async () => {
    await refresh(true);
    if (Number(player?.pending_cid) >= 0) throw Error("An active commitment already exists.");
    const answer = $("ans").value, salt = $("salt").value;
    if (!normaliseAnswer(answer) || answer.length > 240 || !/^[a-f0-9]{32}$/.test(salt)) throw Error("Enter an answer and a generated 32-character salt.");
    if (!new RegExp("^(?:" + clue.answer_pattern + ")$", "u").test(normaliseAnswer(answer))) throw Error("Answer does not match the required form.");
    const r = { clue: Number(player.position), answer, salt, account, commitment: await commitmentOf(answer, salt, account, Number(player.position)), createdAt: (/* @__PURE__ */ new Date()).toISOString(), submitting: false };
    const existing = backup.records.find((x) => x.commitment === r.commitment);
    if (existing) {
      Object.assign(existing, r, { tx: void 0, settled: false });
    } else backup.records.push(r);
    save();
    await write("commit", { clue_idx: r.clue, commitment: r.commitment }, existing ?? r);
    $("salt").value = newSalt();
  });
  $("reveal").onclick = handle(async () => {
    await refresh(true);
    const r = backup.records.find((r2) => r2.commitment === pending?.commitment);
    if (!r) throw Error("Import the saved backup for this commitment before revealing.");
    await write("reveal", { cid: Number(pending.cid), answer: r.answer, salt: r.salt });
  });
  $("judge").onclick = handle(() => write("judge", { cid: Number(pending.cid) }));
  $("expire").onclick = handle(() => write("expire", { cid: Number(pending.cid) }));
  $("cancel").onclick = handle(() => write("cancel_expired_race", {}));
  $("export").onclick = handle(async () => {
    if (!backup) throw Error("Connect your wallet first.");
    const blob = new Blob([json(backup)], { type: "application/json" }), a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `proof-of-hunt-${account.slice(2, 10)}-backup.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1e3);
  });
  $("import").onchange = handle(async () => {
    if (!backup) throw Error("Connect the matching account and race first.");
    const file = $("import").files[0];
    if (!file || file.size > 8 * 1024 * 1024) throw Error("Choose a recovery JSON file under 8 MB.");
    backup = mergeRecovery(backup, await validateRecovery(await file.text(), backup.scope));
    save();
    draw();
  });
  $("manual").onclick = handle(async () => {
    if (!clue) throw Error("Load a clue first.");
    const a = $("ans").value, s = $("salt").value, who = $("who").value;
    if (!addressOK(who)) throw Error("Enter an account address first.");
    if (!normaliseAnswer(a) || a.length > 240 || !/^[a-f0-9]{32}$/.test(s)) throw Error("Enter an answer and generate a valid salt.");
    const key = scopeKey(network().endpoint, address(), who);
    if (!backup || backup.scope !== key) throw Error("Use this address to load recovery storage first.");
    const commitment = await commitmentOf(a, s, who, clue.idx);
    if (!backup.records.some((r) => r.commitment === commitment)) {
      backup.records.push({ clue: clue.idx, answer: a, salt: s, account: who, commitment });
      save();
      draw();
    }
    $("calls").textContent = json({ network: network().endpoint, contract: address(), commit: { clue_idx: clue.idx, commitment: await commitmentOf(a, s, who, clue.idx) }, reveal: { cid: pending?.cid ?? "<commit id>", answer: a, salt: s }, judge: { cid: pending?.cid ?? "<commit id>" } });
  });
  window.ethereum?.on?.("accountsChanged", () => {
    generation++;
    account = "";
    lastReadOK=false;
    backup = null;
    unresolved = null;
    status("Wallet account changed. Connect again.");
    buttons();
  });
  window.ethereum?.on?.("chainChanged", () => {
    generation++;
    account = "";
    lastReadOK=false;
    backup=null;
    unresolved=null;
    status("Wallet network changed. Connect again.");
    buttons();
  });
}
await refresh(true);
setInterval(() => {
  if (document.visibilityState === "visible") refresh();
}, 3e4);
