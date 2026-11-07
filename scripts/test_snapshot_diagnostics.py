"""Isolated diagnostic rule tests, never study observations."""
import unittest
from diagnose_snapshot import presence, proposed_ids


def row(rid, score=.9, name=.9, distance=10):
    return {"record_id": rid, "score": score, "name_similarity": name, "distance_m": distance}


class SnapshotDiagnosticTests(unittest.TestCase):
    def test_all_four_gates_apply(self):
        for r in [row("x", score=.81), row("x", name=.83), row("x", distance=201), row("x", distance=None)]:
            self.assertEqual(proposed_ids({("b", "OSM"): [r]}, .82, .08), {})
        self.assertEqual(proposed_ids({("b", "OSM"): [row("x")]}, .82, .08), {("b", "OSM"): "x"})

    def test_competing_candidate_margin(self):
        self.assertEqual(proposed_ids({("b", "OSM"): [row("x"), row("y", .85)]}, .82, .08), {})

    def test_duplicate_record_is_not_automatic_for_two_branches(self):
        self.assertEqual(proposed_ids({("a", "OSM"): [row("x")], ("b", "OSM"): [row("x")]}, .82, .08), {})

    def test_presence_uses_full_snapshot_population(self):
        result = {r["field"]: r for r in presence([{"aliases": ["A"]}, {"aliases": []}], "OSM")}
        self.assertEqual(result["aliases"]["present_n"], 1)
        self.assertEqual(result["aliases"]["records"], 2)
        self.assertEqual(result["opening_hours"]["present_fraction"], 0)


if __name__ == "__main__":
    unittest.main()
