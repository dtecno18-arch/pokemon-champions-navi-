import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "official_audit", Path(__file__).resolve().parents[1] / "tools" / "audit_official_mc.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class OfficialRosterParserTest(unittest.TestCase):
    def test_hidden_dom_concatenated_entries(self):
        body = "参加できるポケモンNo.0003 フシギバナNo.0006 リザードンNo.0026 ライチュウ (アローラのすがた)"
        self.assertEqual(audit.extract_official(body), [
            (3, "フシギバナ"), (6, "リザードン"),
            (26, "ライチュウ (アローラのすがた)")
        ])

    def test_newline_separated_entries(self):
        body = "No.0003 フシギバナ\nNo.0006 リザードン\n"
        self.assertEqual(audit.extract_official(body), [
            (3, "フシギバナ"), (6, "リザードン")
        ])

    def test_embedded_official_form_codes(self):
        text = 'const pokemons = [["0003-000",1,"フシギバナ"],["0931-000",1,"イキリンコ"],["0931-002",1,"イキリンコ"]];'
        self.assertEqual(audit.extract_official_payload(text), [
            (3, "フシギバナ", "0003-000"),
            (931, "イキリンコ", "0931-000"),
            (931, "イキリンコ", "0931-002"),
        ])

    def test_embedded_duplicate_form_code_rejected(self):
        text = 'const pokemons = [["0931-000",1,"イキリンコ"],["0931-000",1,"イキリンコ"]];'
        with self.assertRaises(ValueError):
            audit.extract_official_payload(text)

    def test_header_only_cannot_pass(self):
        self.assertEqual(audit.extract_official("参加できるポケモン"), [])


    def test_official_mega_section_normalizes_fullwidth_xyz(self):
        text = ("このレギュレーションでメガシンカできるのは、下記のポケモンです。\n"
                "メガリザードンＸ\nメガリザードンＹ\nメガガブリアスＺ\n"
                "ポケモンの持ち物")
        self.assertEqual(audit.extract_official_megas(text), [
            "メガリザードンX", "メガリザードンY", "メガガブリアスZ"
        ])

    def test_official_mega_missing_section_fails_closed(self):
        with self.assertRaises(ValueError):
            audit.extract_official_megas("メガリザードンＸ メガリザードンＹ")

    def test_official_mega_duplicate_fails_closed(self):
        with self.assertRaises(ValueError):
            audit.extract_official_megas(
                "下記のポケモンです。メガリザードンＸ メガリザードンＸ ポケモンの持ち物")

    @staticmethod
    def mega_fixture():
        notices = {
            "M-A": ["メガニャオニクス"] + [f"メガテストA{i}" for i in range(58)],
            "M-B": [f"メガテストB{i}" for i in range(16)],
            "M-C": [f"メガテストC{i}" for i in range(6)],
        }
        expanded = set().union(*[set(v) for v in notices.values()])
        expanded.remove("メガニャオニクス")
        expanded.update(audit.MEGA_SEX_EXPANSIONS["メガニャオニクス"])
        return notices, sorted(expanded)

    def test_mega_exact_match_81_names_82_input_forms(self):
        notices, forms = self.mega_fixture()
        result = audit.reconcile_official_megas(notices, notices, forms, forms)
        self.assertTrue(result["passed"])
        self.assertEqual(result["officialNamed"], 81)
        self.assertEqual(result["officialExpanded"], 82)

    def test_mega_same_count_wrong_name_rejected(self):
        notices, forms = self.mega_fixture()
        app = {k: list(v) for k, v in notices.items()}
        app["M-C"][-1] = "メガ誤登録"
        result = audit.reconcile_official_megas(notices, app, forms, forms)
        self.assertFalse(result["passed"])
        self.assertEqual(result["bucketDiff"]["M-C"]["extra"], ["メガ誤登録"])

    def test_mega_same_count_wrong_input_rejected(self):
        notices, forms = self.mega_fixture()
        bad = forms[:-1] + ["メガ誤登録"]
        result = audit.reconcile_official_megas(notices, notices, bad, bad)
        self.assertFalse(result["passed"])
        self.assertEqual(result["candidateExtra"], ["メガ誤登録"])

    def test_mega_same_count_wrong_candidate_rejected(self):
        notices, forms = self.mega_fixture()
        bad = forms[:-1] + ["メガ誤登録"]
        result = audit.reconcile_official_megas(notices, notices, forms, bad)
        self.assertFalse(result["passed"])
        self.assertEqual(result["candidateExtra"], ["メガ誤登録"])

    def test_mega_duplicate_bucket_rejected(self):
        notices, forms = self.mega_fixture()
        app = {k: list(v) for k, v in notices.items()}
        app["M-C"][-1] = app["M-C"][0]
        with self.assertRaises(ValueError):
            audit.reconcile_official_megas(notices, app, forms, forms)


if __name__ == "__main__":
    unittest.main()
