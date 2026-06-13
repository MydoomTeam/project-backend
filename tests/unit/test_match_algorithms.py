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
        nuevo_g, nuevo_p = MatchService._compute_new_elo(1000, 1000)
        self.assertEqual(nuevo_g - 1000, -(nuevo_p - 1000))

    def test_lower_elo_winner_gains_more_than_favorite(self):
        nuevo_g_debil, _ = MatchService._compute_new_elo(800, 1600)
        nuevo_g_fuerte, _ = MatchService._compute_new_elo(1600, 800)
        self.assertGreater(nuevo_g_debil - 800, nuevo_g_fuerte - 1600)


class TestBuildCompleteBracket(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_four_players_generates_all_rounds(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_full_bracket(1, participantes)

        self.assertEqual({m.ronda for m in matches}, {1, 2})
        self.assertEqual(len(matches), 3)

    def test_five_players_byes_assigned_to_top_seeds(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = self._service()._build_full_bracket(1, participantes)

        byes = [m for m in matches if m.ronda == 1 and m.jugador2_id is None]
        self.assertEqual(len(byes), 3)
        self.assertEqual({m.jugador1_id for m in byes}, {1, 2, 3})

    def test_future_rounds_start_without_assigned_players(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_full_bracket(1, participantes)

        ronda2 = [m for m in matches if m.ronda == 2]
        self.assertTrue(all(m.jugador1_id is None and m.jugador2_id is None for m in ronda2))


class TestBuildRoundRobin(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_three_players_generate_three_matches(self):
        participantes = [(1, 1500), (2, 1300), (3, 1100)]
        matches = self._service()._build_round_robin(1, participantes)

        self.assertEqual(len(matches), 3)
        pares = {(m.jugador1_id, m.jugador2_id) for m in matches}
        self.assertEqual(pares, {(1, 2), (1, 3), (2, 3)})


class TestBuildDoubleElimination(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_four_players_generates_winners_losers_and_grand_final_brackets(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participantes)

        tipos = {m.bracket_tipo for m in matches}
        self.assertIn("ganadores", tipos)
        self.assertIn("perdedores", tipos)
        self.assertIn("gran_final", tipos)

    def test_four_players_winners_bracket_has_three_matches(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participantes)

        ganadores = [m for m in matches if m.bracket_tipo == "ganadores"]
        self.assertEqual(len(ganadores), 3)

    def test_four_players_losers_bracket_has_two_matches(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participantes)

        perdedores = [m for m in matches if m.bracket_tipo == "perdedores"]
        self.assertEqual(len(perdedores), 2)

    def test_exactly_one_grand_final_match(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participantes)

        gran_final = [m for m in matches if m.bracket_tipo == "gran_final"]
        self.assertEqual(len(gran_final), 1)

    def test_grand_final_starts_without_players(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_double_elimination(1, participantes)

        gf = next(m for m in matches if m.bracket_tipo == "gran_final")
        self.assertIsNone(gf.jugador1_id)
        self.assertIsNone(gf.jugador2_id)

    def test_loser_path_first_round_first_position(self):
        lb_ronda, lb_pos, lb_slot = MatchService._loser_route_to_losers(1, 0)
        self.assertEqual(lb_ronda, 1)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 0)

    def test_loser_path_first_round_second_position(self):
        lb_ronda, lb_pos, lb_slot = MatchService._loser_route_to_losers(1, 1)
        self.assertEqual(lb_ronda, 1)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 1)

    def test_loser_path_second_round_goes_to_lb_round_two(self):
        lb_ronda, lb_pos, lb_slot = MatchService._loser_route_to_losers(2, 0)
        self.assertEqual(lb_ronda, 2)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 1)

    def test_loser_path_third_round_goes_to_lb_round_four(self):
        lb_ronda, lb_pos, lb_slot = MatchService._loser_route_to_losers(3, 0)
        self.assertEqual(lb_ronda, 4)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 1)


class TestBuildSwiss(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_four_players_generates_two_matches_in_round_one(self):
        participantes = [(1, 1600), (2, 1500), (3, 1400), (4, 1300)]
        matches = self._service()._build_swiss_round1(1, participantes)

        self.assertEqual(len(matches), 2)

    def test_higher_elo_players_paired_first(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._build_swiss_round1(1, participantes)

        primer_match = matches[0]
        self.assertIn(1, (primer_match.jugador1_id, primer_match.jugador2_id))
        self.assertIn(2, (primer_match.jugador1_id, primer_match.jugador2_id))

    def test_five_players_generates_bye_for_last(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = self._service()._build_swiss_round1(1, participantes)

        byes = [m for m in matches if m.jugador2_id is None]
        self.assertEqual(len(byes), 1)
        self.assertEqual(byes[0].estado, "Finalizado")

    def test_pairing_avoids_rematches(self):
        pares_jugados = {(1, 2)}
        jugadores = [1, 2, 3, 4]
        matches = MatchService._pair_swiss(1, ronda=2, jugadores=jugadores, pares_jugados=pares_jugados)

        for m in matches:
            if m.jugador2_id is not None:
                par = (min(m.jugador1_id, m.jugador2_id), max(m.jugador1_id, m.jugador2_id))
                self.assertNotIn(par, pares_jugados)

    def test_all_swiss_matches_start_in_progress(self):
        participantes = [(1, 1600), (2, 1500), (3, 1400), (4, 1300)]
        matches = self._service()._build_swiss_round1(1, participantes)

        for m in matches:
            if m.jugador2_id is not None:
                self.assertEqual(m.estado, "En curso")


if __name__ == "__main__":
    unittest.main()
