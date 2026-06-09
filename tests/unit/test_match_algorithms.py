import unittest

from app.services.match_service import MatchService


class TestSiguientePotenciaDeDos(unittest.TestCase):
    def test_valor_ya_es_potencia_de_dos(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(8), 8)

    def test_valor_entre_potencias_sube_a_la_siguiente(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(5), 8)

    def test_valor_minimo_devuelve_uno(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(1), 1)


class TestCalcularNuevoElo(unittest.TestCase):
    def test_igual_habilidad_cambio_simetrico(self):
        nuevo_g, nuevo_p = MatchService._calcular_nuevo_elo(1000, 1000)
        self.assertEqual(nuevo_g - 1000, -(nuevo_p - 1000))

    def test_ganador_con_menor_elo_recibe_mas_puntos_que_favorito(self):
        nuevo_g_debil, _ = MatchService._calcular_nuevo_elo(800, 1600)
        nuevo_g_fuerte, _ = MatchService._calcular_nuevo_elo(1600, 800)
        self.assertGreater(nuevo_g_debil - 800, nuevo_g_fuerte - 1600)


class TestConstruirBracketCompleto(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_cuatro_jugadores_genera_todas_las_rondas(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_bracket_completo(1, participantes)

        self.assertEqual({m.ronda for m in matches}, {1, 2})
        self.assertEqual(len(matches), 3)

    def test_cinco_jugadores_byes_asignados_a_top_seeds(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = self._service()._construir_bracket_completo(1, participantes)

        byes = [m for m in matches if m.ronda == 1 and m.jugador2_id is None]
        self.assertEqual(len(byes), 3)
        self.assertEqual({m.jugador1_id for m in byes}, {1, 2, 3})

    def test_rondas_futuras_inician_sin_jugadores_asignados(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_bracket_completo(1, participantes)

        ronda2 = [m for m in matches if m.ronda == 2]
        self.assertTrue(all(m.jugador1_id is None and m.jugador2_id is None for m in ronda2))


class TestConstruirRoundRobin(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_tres_jugadores_generan_tres_matches(self):
        participantes = [(1, 1500), (2, 1300), (3, 1100)]
        matches = self._service()._construir_round_robin(1, participantes)

        self.assertEqual(len(matches), 3)
        pares = {(m.jugador1_id, m.jugador2_id) for m in matches}
        self.assertEqual(pares, {(1, 2), (1, 3), (2, 3)})


class TestConstruirEliminacionDoble(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_cuatro_jugadores_genera_brackets_ganadores_perdedores_y_gran_final(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_eliminacion_doble(1, participantes)

        tipos = {m.bracket_tipo for m in matches}
        self.assertIn("ganadores", tipos)
        self.assertIn("perdedores", tipos)
        self.assertIn("gran_final", tipos)

    def test_cuatro_jugadores_bracket_ganadores_tiene_tres_matches(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_eliminacion_doble(1, participantes)

        ganadores = [m for m in matches if m.bracket_tipo == "ganadores"]
        self.assertEqual(len(ganadores), 3)

    def test_cuatro_jugadores_bracket_perdedores_tiene_dos_matches(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_eliminacion_doble(1, participantes)

        perdedores = [m for m in matches if m.bracket_tipo == "perdedores"]
        self.assertEqual(len(perdedores), 2)

    def test_exactamente_un_match_gran_final(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_eliminacion_doble(1, participantes)

        gran_final = [m for m in matches if m.bracket_tipo == "gran_final"]
        self.assertEqual(len(gran_final), 1)

    def test_gran_final_inicia_sin_jugadores(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_eliminacion_doble(1, participantes)

        gf = next(m for m in matches if m.bracket_tipo == "gran_final")
        self.assertIsNone(gf.jugador1_id)
        self.assertIsNone(gf.jugador2_id)

    def test_ruta_perdedor_primera_ronda_primera_posicion(self):
        lb_ronda, lb_pos, lb_slot = MatchService._ruta_perdedor_a_perdedores(1, 0)
        self.assertEqual(lb_ronda, 1)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 0)

    def test_ruta_perdedor_primera_ronda_segunda_posicion(self):
        lb_ronda, lb_pos, lb_slot = MatchService._ruta_perdedor_a_perdedores(1, 1)
        self.assertEqual(lb_ronda, 1)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 1)

    def test_ruta_perdedor_segunda_ronda_va_a_lb_ronda_dos(self):
        lb_ronda, lb_pos, lb_slot = MatchService._ruta_perdedor_a_perdedores(2, 0)
        self.assertEqual(lb_ronda, 2)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 1)

    def test_ruta_perdedor_tercera_ronda_va_a_lb_ronda_cuatro(self):
        lb_ronda, lb_pos, lb_slot = MatchService._ruta_perdedor_a_perdedores(3, 0)
        self.assertEqual(lb_ronda, 4)
        self.assertEqual(lb_pos, 0)
        self.assertEqual(lb_slot, 1)


class TestConstruirSwiss(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_cuatro_jugadores_genera_dos_matches_en_ronda_uno(self):
        participantes = [(1, 1600), (2, 1500), (3, 1400), (4, 1300)]
        matches = self._service()._construir_swiss_ronda1(1, participantes)

        self.assertEqual(len(matches), 2)

    def test_jugadores_de_mayor_elo_emparejados_primero(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_swiss_ronda1(1, participantes)

        primer_match = matches[0]
        self.assertIn(1, (primer_match.jugador1_id, primer_match.jugador2_id))
        self.assertIn(2, (primer_match.jugador1_id, primer_match.jugador2_id))

    def test_cinco_jugadores_genera_bye_para_ultimo(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = self._service()._construir_swiss_ronda1(1, participantes)

        byes = [m for m in matches if m.jugador2_id is None]
        self.assertEqual(len(byes), 1)
        self.assertEqual(byes[0].estado, "Finalizado")

    def test_emparejamiento_evita_rematches(self):
        pares_jugados = {(1, 2)}
        jugadores = [1, 2, 3, 4]
        matches = MatchService._emparejar_swiss(1, ronda=2, jugadores=jugadores, pares_jugados=pares_jugados)

        for m in matches:
            if m.jugador2_id is not None:
                par = (min(m.jugador1_id, m.jugador2_id), max(m.jugador1_id, m.jugador2_id))
                self.assertNotIn(par, pares_jugados)

    def test_todos_los_matches_swiss_inician_en_curso(self):
        participantes = [(1, 1600), (2, 1500), (3, 1400), (4, 1300)]
        matches = self._service()._construir_swiss_ronda1(1, participantes)

        for m in matches:
            if m.jugador2_id is not None:
                self.assertEqual(m.estado, "En curso")


if __name__ == "__main__":
    unittest.main()
