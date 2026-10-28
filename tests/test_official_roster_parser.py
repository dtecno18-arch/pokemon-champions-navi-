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


if __name__ == "__main__":
    unittest.main()
