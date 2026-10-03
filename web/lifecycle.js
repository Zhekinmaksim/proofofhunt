export function canCommit(race, player) {
  return Boolean(race && player?.joined && !player.finished && Number(player.pending_cid)<0 && [1,2].includes(Number(race.state)) && !(Number(race.state)===2 && Number(player.position)===Number(race.clue_count)-1));
}
export function unresolvedTransaction(backup,journal) {
  if(journal?.state==='submitted') return journal.hash;
  if(journal?.state==='awaiting-wallet') return 'unknown';
  const record=backup.records.find(r=>r.submitting || r.tx && !r.settled);
  return record?.tx ?? (record?.submitting ? 'unknown' : null);
}
