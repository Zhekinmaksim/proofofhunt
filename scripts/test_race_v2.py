"""Deterministic v2 security/liveness regressions, not consensus simulation.

Uses the same fake SDK as test_race.py, with transaction timestamps controlled
explicitly. Private guard tests inject unreachable storage to verify defense in
depth; normal game tests use only public contract entry points.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'contracts'))
import fake_genlayer as fx
import proof_of_hunt as poh

OWNER = '0x' + '11' * 20
ALICE = '0x' + '22' * 20
BOB = '0x' + '33' * 20
CARA = '0x' + '44' * 20
START = 1790985600
PAGE = 'SPEC SECTION 4.2 The protocol was specified in 1974. ' + 'filler text. ' * 60


class RaceV2(unittest.TestCase):
    def setUp(self):
        fx.set_time(START)
        fx.set_page(PAGE)
        fx.set_verdicts()
        fx.clear_events()

    def race(self, count=2, players=(ALICE, BOB, CARA)):
        fx.set_sender(OWNER)
        c = fx.instantiate(poh.ProofOfHunt, 'V2 security regression')
        for i in range(count):
            c.add_clue(str(i), 'What year?', 'https://example.org/spec',
                       'spec section 4.2', 600, 'four digits', r'\d{4}', 'Read it')
            c.pin_clue(i)
        c.open_race()
        for who in players:
            fx.set_sender(who)
            c.join(who)
        return c

    def commit(self, c, who=ALICE, answer='1974', reveal=True):
        fx.set_sender(who)
        idx = c.player(fx.Address(who))['position']
        cid = len(c.commits)
        c.commit(idx, poh.commitment_of(answer, 'salt', who, idx))
        if reveal:
            c.reveal(cid, answer, 'salt')
        return cid

    def judge(self, c, cid, verdict='correct'):
        fx.set_verdicts(fx.verdict(verdict))
        c.judge(cid)

    def final_ready(self):
        c = self.race()
        for who in (ALICE, BOB, CARA):
            self.judge(c, self.commit(c, who))
        return c

    def test_duplicate_pending_cannot_bypass_six_attempts(self):
        c = self.race()
        for _ in range(6):
            cid = self.commit(c, reveal=False)
            with self.assertRaisesRegex(Exception, 'pending'):
                self.commit(c)
            c.reveal(cid, '1974', 'salt')
            with self.assertRaisesRegex(Exception, 'pending'):
                self.commit(c)
            self.judge(c, cid, 'incorrect')
            self.assertEqual(c.player(fx.Address(ALICE))['pending_cid'], -1)
        with self.assertRaisesRegex(Exception, 'no attempts left'):
            self.commit(c)
        self.assertEqual(len(c.commits), 6)
        self.assertEqual(c.player(fx.Address(ALICE))['total_attempts'], 6)

    def test_once_only_advancement_and_stale_storage_defense(self):
        c = self.race(3)
        cid = self.commit(c)
        old = copy.copy(c.commits[cid])
        self.judge(c, cid)
        for action in (lambda: c.judge(cid), lambda: c._stage_c_apply(old, poh.V_CORRECT, '', '')):
            with self.assertRaises(Exception):
                action()
        p = c.player(fx.Address(ALICE))
        self.assertEqual((p['position'], p['cleared'], p['total_attempts']), (1, 1, 1))
        self.assertEqual(p['pending_cid'], -1)
        next_cid = self.commit(c)
        self.judge(c, next_cid)
        self.assertEqual(c.player(fx.Address(ALICE))['position'], 2)

    def test_inactive_attempt_guard(self):
        c = self.race()
        cid = self.commit(c)
        c.players[fx.Address(ALICE)].pending_plus_one = 0
        with self.assertRaisesRegex(Exception, 'active attempt'):
            c._stage_c_apply(c.commits[cid], poh.V_CORRECT, '', '')
        self.assertEqual(c.player(fx.Address(ALICE))['position'], 0)

    def test_reverse_verdict_order_preserves_first_commit_winner(self):
        c = self.final_ready()
        ids = [self.commit(c, who) for who in (BOB, ALICE, CARA)]
        for cid, who in zip(reversed(ids), (CARA, ALICE, BOB)):
            self.judge(c, cid)
            self.assertEqual(c.race()['winner'], who)
        self.assertEqual(c.state, poh.STATE_FINAL)
        self.assertEqual(c.winner_cid, ids[0])
        self.assertEqual(len(fx.events('RaceFinalized')), 1)

    def test_earlier_incorrect_and_bad_form_finalize(self):
        for bad_form in (False, True):
            with self.subTest(bad_form=bad_form):
                c = self.final_ready()
                earlier = self.commit(c, BOB, 'bad' if bad_form else '1981', reveal=not bad_form)
                later = self.commit(c, ALICE)
                self.judge(c, later)
                self.assertEqual(c.state, poh.STATE_WON)
                if bad_form:
                    fx.set_sender(BOB)
                    c.reveal(earlier, 'bad', 'salt')
                else:
                    self.judge(c, earlier, 'incorrect')
                self.assertEqual(c.state, poh.STATE_FINAL)
                self.assertEqual(c.winner.as_hex, ALICE)
                self.assertEqual(c.player(fx.Address(BOB))['pending_cid'], -1)

    def test_reveal_expiration_boundary_charges_once(self):
        c = self.race()
        cid = self.commit(c, reveal=False)
        deadline = c.commit_at(cid)['reveal_deadline']
        self.assertEqual(deadline, START + 86400)
        fx.set_time(deadline - 1)
        with self.assertRaisesRegex(Exception, 'not expired'):
            c.expire(cid)
        fx.set_time(deadline)
        with self.assertRaisesRegex(Exception, 'deadline'):
            c.reveal(cid, '1974', 'salt')
        fx.set_sender(CARA)
        c.expire(cid)
        p = c.player(fx.Address(ALICE))
        self.assertEqual((p['attempts_used'], p['total_attempts'], p['pending_cid']), (1, 1, -1))
        with self.assertRaisesRegex(Exception, 'settled'):
            c.expire(cid)
        self.assertEqual(c.commit_at(cid)['verdict'], poh.V_EXPIRED)
        self.commit(c)

    def test_reveal_one_second_before_deadline_allowed(self):
        c = self.race()
        cid = self.commit(c, reveal=False)
        fx.set_time(START + 86400 - 1)
        c.reveal(cid, '1974', 'salt')
        self.assertTrue(c.commit_at(cid)['revealed'])

    def test_revealed_expiration_is_free_and_pending_released(self):
        for verdict in ('pending', 'undetermined'):
            with self.subTest(verdict=verdict):
                fx.set_time(START)
                c = self.race()
                cid = self.commit(c)
                if verdict == 'undetermined':
                    fx.set_page('', fail=True)
                    c.judge(cid)
                    fx.set_page(PAGE)
                deadline = c.commit_at(cid)['judge_deadline']
                self.assertEqual(deadline, START + 7 * 86400)
                fx.set_time(deadline - 1)
                with self.assertRaisesRegex(Exception, 'not expired'):
                    c.expire(cid)
                fx.set_time(deadline)
                with self.assertRaisesRegex(Exception, 'deadline'):
                    c.judge(cid)
                fx.set_sender(CARA)
                c.expire(cid)
                p = c.player(fx.Address(ALICE))
                self.assertEqual((p['position'], p['attempts_used'], p['total_attempts'], p['pending_cid']), (0, 0, 0, -1))
                self.commit(c)

    def test_judge_one_second_before_deadline_allowed(self):
        c = self.race()
        cid = self.commit(c)
        fx.set_time(START + 7 * 86400 - 1)
        self.judge(c, cid)
        self.assertEqual(c.player(fx.Address(ALICE))['position'], 1)

    def test_undetermined_keeps_pending_and_retry_order_without_charging(self):
        c = self.race()
        cid = self.commit(c)
        fx.set_page('', fail=True)
        c.judge(cid)
        with self.assertRaisesRegex(Exception, 'pending'):
            self.commit(c)
        p = c.player(fx.Address(ALICE))
        self.assertEqual((p['pending_cid'], p['total_attempts']), (cid, 0))
        fx.set_page(PAGE)
        self.judge(c, cid)
        p = c.player(fx.Address(ALICE))
        self.assertEqual((p['pending_cid'], p['position'], p['total_attempts']), (-1, 1, 1))

    def test_non_object_model_json_is_free_undetermined(self):
        for response in (None, [], 'null', '["correct"]', '"correct"', 'broken json'):
            with self.subTest(response=response):
                c = self.race()
                cid = self.commit(c)
                fx.set_verdicts(response)
                c.judge(cid)
                self.assertEqual(c.commit_at(cid)['verdict'], poh.V_UNDETERMINED)
                p = c.player(fx.Address(ALICE))
                self.assertEqual((p['position'], p['total_attempts'], p['pending_cid']), (0, 0, cid))

    def test_six_unrevealed_expirations_cannot_evade_attempt_limit(self):
        c = self.race()
        for _ in range(6):
            cid = self.commit(c, reveal=False)
            fx.set_time(c.commit_at(cid)['reveal_deadline'])
            fx.set_sender(CARA)
            c.expire(cid)
        with self.assertRaisesRegex(Exception, 'no attempts left'):
            self.commit(c)
        p = c.player(fx.Address(ALICE))
        self.assertEqual((p['attempts_used'], p['total_attempts']), (6, 6))

    def test_leaderboard_tie_uses_commit_order_not_judge_order(self):
        c = self.race(3)
        early = self.commit(c, BOB)
        late = self.commit(c, ALICE)
        self.judge(c, late)
        self.judge(c, early)
        rows = c.leaderboard()
        self.assertEqual([row['addr'] for row in rows[:2]], [BOB, ALICE])
        self.assertEqual([row['last_correct_cid'] for row in rows[:2]], [early, late])

    def test_expired_earlier_claim_finalizes_provisional_winner(self):
        c = self.final_ready()
        early = self.commit(c, BOB, reveal=False)
        late = self.commit(c, ALICE)
        self.judge(c, late)
        fx.set_time(c.commit_at(early)['reveal_deadline'])
        fx.set_sender(CARA)
        c.expire(early)
        self.assertEqual((c.state, c.winner.as_hex), (poh.STATE_FINAL, ALICE))

    def test_race_expiration_no_owner_discretion(self):
        c = self.race()
        for who in (OWNER, CARA):
            fx.set_sender(who)
            with self.assertRaisesRegex(Exception, 'not expired'):
                c.cancel_expired_race()
        close = c.race()['closes_at']
        self.assertEqual(close, START + 30 * 86400)
        fx.set_time(close - 10)
        cid = self.commit(c)
        self.assertEqual(c.commit_at(cid)['judge_deadline'], close)
        self.assertEqual(c.commit_at(cid)['reveal_deadline'], close)
        fx.set_time(close)
        fx.set_sender('0x' + '55' * 20)
        c.cancel_expired_race()
        self.assertEqual(c.state, poh.STATE_CANCELLED)
        with self.assertRaises(Exception):
            c.judge(cid)
        with self.assertRaises(Exception):
            c.join('late')
        c.expire(cid)
        self.assertEqual(c.player(fx.Address(ALICE))['total_attempts'], 0)

    def test_race_expiration_finalizes_winner_instead_of_cancelling(self):
        c = self.final_ready()
        fx.set_time(c.closes_at - 60)
        early = self.commit(c, BOB)
        late = self.commit(c, ALICE)
        self.judge(c, late)
        fx.set_time(c.closes_at)
        fx.set_sender(CARA)
        c.cancel_expired_race()
        self.assertEqual((c.state, c.winner.as_hex), (poh.STATE_FINAL, ALICE))
        self.assertEqual(c.commit_at(early)['verdict'], poh.V_EXPIRED)
        self.assertEqual(c.player(fx.Address(BOB))['total_attempts'], 1)

    def test_final_event_emitted_once_when_other_pending_attempt_settles(self):
        c = self.race()
        pending = self.commit(c, BOB)
        for _ in range(2):
            self.judge(c, self.commit(c, ALICE))
        self.judge(c, pending, 'incorrect')
        self.assertEqual(len(fx.events('RaceFinalized')), 1)
        self.assertEqual(c.winner.as_hex, ALICE)

    def test_preexisting_unrevealed_attempt_can_settle_after_final(self):
        c = self.race()
        pending = self.commit(c, BOB, reveal=False)
        for _ in range(2):
            self.judge(c, self.commit(c, ALICE))
        fx.set_sender(BOB)
        c.reveal(pending, '1974', 'salt')
        self.judge(c, pending)
        self.assertEqual(c.player(fx.Address(BOB))['position'], 1)
        self.assertEqual(c.winner.as_hex, ALICE)

    def test_player_cap_and_linear_leaderboard_without_commit_scan(self):
        c = self.race(players=())
        for i in range(poh.MAX_PLAYERS):
            fx.set_sender('0x' + f'{i + 1:040x}')
            c.join('player')
        fx.set_sender(CARA)
        with self.assertRaisesRegex(Exception, 'full'):
            c.join('overflow')
        class NoCommitScan(list):
            def __iter__(self):
                raise AssertionError('leaderboard scans historical commits')
            def __getitem__(self, key):
                raise AssertionError('leaderboard reads historical commits')
        c.commits = NoCommitScan()
        self.assertEqual(len(c.leaderboard()), poh.MAX_PLAYERS)

    def test_commit_cap_rejects_without_mutation(self):
        c = self.race()
        class FullCommits(list):
            def __len__(self):
                return poh.MAX_COMMITS
        c.commits = FullCommits()
        with self.assertRaisesRegex(Exception, 'capacity'):
            self.commit(c)
        self.assertEqual(c.player(fx.Address(ALICE))['pending_cid'], -1)

    def test_clue_cap_and_hex_commitment_validation(self):
        c = self.race()
        fx.set_sender(ALICE)
        for bad in ('g' * 64, '0' * 63, '0' * 65):
            with self.assertRaisesRegex(Exception, 'hex digest'):
                c.commit(0, bad)
        self.assertEqual(len(c.commits), 0)
        fx.set_sender(OWNER)
        draft = fx.instantiate(poh.ProofOfHunt, 'cap')
        for i in range(poh.MAX_CLUES):
            draft.add_clue(str(i), 'r', 'https://example.org', '', 600, 'form', r'.+', '')
        with self.assertRaisesRegex(Exception, 'too many clues'):
            draft.add_clue('overflow', 'r', 'https://example.org', '', 600, 'form', r'.+', '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
