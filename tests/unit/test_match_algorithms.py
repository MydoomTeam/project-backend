import unittest

from app.services.match_service import MatchService


class TestNextPowerOfTwo(unittest.TestCase):
    def test_value_already_power_of_two(self):
        self.assertEqual(MatchService._next_power_of_two(8), 8)

    def test_value_between_powers_rounds_up(self):
        self.assertEqual(MatchService._next_power_of_two(5), 8)

    def test_minimum_value_returns_one(self):
        self.assertEqual(MatchService._next_power_of_two(1), 1)


class TestComputeNewElo(unittest.TestCase):
    def test_equal_skill_symmetric_change(self):
        new_winner_elo, new_loser_elo = MatchService._compute_new_elo(1000, 1000)
        self.assertEqual(new_winner_elo - 1000, -(new_loser_elo - 1000))

    def test_lower_elo_winner_gains_more_than_favorite(self):
        underdog_new_elo, _ = MatchService._compute_new_elo(800, 1600)
        favorite_new_elo, _ = MatchService._compute_new_elo(1600, 800)
        self.assertGreater(underdog_new_elo - 800, favorite_new_elo - 1600)


class TestBuildCompleteBracket(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_four_players_generates_all_rounds(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_full_bracket(1, participants)

        self.assertEqual({m.round for m in matches}, {1, 2})
        self.assertEqual(len(matches), 3)

    def test_five_players_byes_assigned_to_top_seeds(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = self._service()._build_full_bracket(1, participants)

        byes = [m for m in matches if m.round == 1 and m.player2_id is None]
        self.assertEqual(len(byes), 3)
        self.assertEqual({m.player1_id for m in byes}, {1, 2, 3})

    def test_future_rounds_start_without_assigned_players(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_full_bracket(1, participants)

        round2 = [m for m in matches if m.round == 2]
        self.assertTrue(all(m.player1_id is None and m.player2_id is None for m in round2))


class TestBuildRoundRobin(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_three_players_generate_three_matches(self):
        participants = [(1, 1500), (2, 1300), (3, 1100)]
        matches = self._service()._build_round_robin(1, participants)

        self.assertEqual(len(matches), 3)
        pairs = {(m.player1_id, m.player2_id) for m in matches}
        self.assertEqual(pairs, {(1, 2), (1, 3), (2, 3)})


class TestBuildDoubleElimination(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_four_players_generates_winners_losers_and_grand_final_brackets(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participants)

        types = {m.bracket_type for m in matches}
        self.assertIn("ganadores", types)
        self.assertIn("perdedores", types)
        self.assertIn("gran_final", types)

    def test_four_players_winners_bracket_has_three_matches(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participants)

        winners = [m for m in matches if m.bracket_type == "ganadores"]
        self.assertEqual(len(winners), 3)

    def test_four_players_losers_bracket_has_two_matches(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participants)

        losers = [m for m in matches if m.bracket_type == "perdedores"]
        self.assertEqual(len(losers), 2)

    def test_exactly_one_grand_final_match(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participants)

        grand_final = [m for m in matches if m.bracket_type == "gran_final"]
        self.assertEqual(len(grand_final), 1)

    def test_grand_final_starts_without_players(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participants)

        gf = next(m for m in matches if m.bracket_type == "gran_final")
        self.assertIsNone(gf.player1_id)
        self.assertIsNone(gf.player2_id)

    def test_loser_path_first_round_first_position(self):
        lb_round, lb_pos, lb_slot = MatchService._loser_route_to_losers(1, 0)
        self.assertEqual(lb_round, 1)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 0)

    def test_loser_path_first_round_second_position(self):
        lb_round, lb_pos, lb_slot = MatchService._loser_route_to_losers(1, 1)
        self.assertEqual(lb_round, 1)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 1)

    def test_loser_path_second_round_goes_to_lb_round_two(self):
        lb_round, lb_pos, lb_slot = MatchService._loser_route_to_losers(2, 0)
        self.assertEqual(lb_round, 2)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 1)

    def test_loser_path_third_round_goes_to_lb_round_four(self):
        lb_round, lb_pos, lb_slot = MatchService._loser_route_to_losers(3, 0)
        self.assertEqual(lb_round, 4)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 1)


class TestBuildSwiss(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_four_players_generates_two_matches_in_round_one(self):
        participants = [(1, 1600), (2, 1500), (3, 1400), (4, 1300)]
        matches = self._service()._build_swiss_round1(1, participants)

        self.assertEqual(len(matches), 2)

    def test_higher_elo_players_paired_first(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_swiss_round1(1, participants)

        first_match = matches[0]
        self.assertIn(1, (first_match.player1_id, first_match.player2_id))
        self.assertIn(2, (first_match.player1_id, first_match.player2_id))

    def test_five_players_generates_bye_for_last(self):
        participants = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = self._service()._build_swiss_round1(1, participants)

        byes = [m for m in matches if m.player2_id is None]
        self.assertEqual(len(byes), 1)
        self.assertEqual(byes[0].status, "Finalizado")

    def test_pairing_avoids_rematches(self):
        played_pairs = {(1, 2)}
        players = [1, 2, 3, 4]
        matches = MatchService._pair_swiss(1, round=2, players=players, played_pairs=played_pairs)

        for m in matches:
            if m.player2_id is not None:
                pair = (min(m.player1_id, m.player2_id), max(m.player1_id, m.player2_id))
                self.assertNotIn(pair, played_pairs)

    def test_all_swiss_matches_start_in_progress(self):
        participants = [(1, 1600), (2, 1500), (3, 1400), (4, 1300)]
        matches = self._service()._build_swiss_round1(1, participants)

        for m in matches:
            if m.player2_id is not None:
                self.assertEqual(m.status, "En curso")


if __name__ == "__main__":
    unittest.main()
