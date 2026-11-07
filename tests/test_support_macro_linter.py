import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from support_macro_linter import exit_code, format_text, lint_text, report

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "support_macro_linter.py")

CLEAN = "Hi Sarah,\n\nThanks for your message.\n\nYour order is on its way.\n\nThanks,\nAmir\n"


def rules(text):
    return {item["rule"] for item in lint_text(text)}


def severities(text):
    return {item["rule"]: item["severity"] for item in lint_text(text)}


def run_cli(args, stdin_text=None):
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        input=stdin_text, capture_output=True, text=True)


def write_draft(text):
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8")
    handle.write(text)
    handle.close()
    return handle.name


class TestToneRules(unittest.TestCase):
    def test_calm_down(self):
        self.assertIn("tone-calm-down", rules("Hi,\n\nCalm down, please.\n\nThanks,\nAmir\n"))

    def test_already_told_you(self):
        self.assertIn("tone-dismissive",
                      rules("Hi,\n\nAs I already told you, it works.\n\nThanks,\nAmir\n"))

    def test_you_should_have(self):
        self.assertIn("tone-blame",
                      rules("Hi,\n\nYou should have read the email.\n\nThanks,\nAmir\n"))

    def test_your_fault(self):
        self.assertIn("tone-blame",
                      rules("Hi,\n\nIt is your fault it broke.\n\nThanks,\nAmir\n"))

    def test_shouting_run(self):
        text = "Hi,\n\nTHIS IS COMPLETELY UNACCEPTABLE AND MUST BE FIXED NOW.\n\nThanks,\nAmir\n"
        self.assertIn("tone-shouting", rules(text))

    def test_normal_caps_acronym_not_shouting(self):
        text = "Hi,\n\nYour ETA and ID are on file.\n\nThanks,\nAmir\n"
        self.assertNotIn("tone-shouting", rules(text))

    def test_tone_findings_are_warnings(self):
        found = severities("Hi,\n\nCalm down.\n\nThanks,\nAmir\n")
        self.assertEqual(found["tone-calm-down"], "warning")

    def test_line_numbers_reported(self):
        found = lint_text("Hi,\n\nCalm down.\n\nThanks,\nAmir\n")
        calm = [item for item in found if item["rule"] == "tone-calm-down"]
        self.assertEqual(calm[0]["line"], 3)


class TestPlaceholderRules(unittest.TestCase):
    def test_double_brace(self):
        self.assertIn("placeholder-double-brace", rules("Hi {{name}},\n\nThanks,\nAmir\n"))

    def test_double_bracket(self):
        self.assertIn("placeholder-double-bracket", rules("Hi,\n\nSee [[section]] first.\n\nThanks,\nAmir\n"))

    def test_todo_marker(self):
        self.assertIn("placeholder-todo", rules("Hi,\n\n[TODO] add the date.\n\nThanks,\nAmir\n"))

    def test_tbd_marker(self):
        self.assertIn("placeholder-tbd", rules("Hi,\n\nThe refund is TBD.\n\nThanks,\nAmir\n"))

    def test_xxx_marker(self):
        self.assertIn("placeholder-xxx", rules("Hi,\n\nCall XXX for help.\n\nThanks,\nAmir\n"))

    def test_single_brace_token(self):
        self.assertIn("placeholder-brace-token", rules("Hi {first_name},\n\nThanks,\nAmir\n"))

    def test_double_brace_not_double_counted_as_single(self):
        found = [item for item in lint_text("Hi {{name}},\n\nThanks,\nAmir\n")
                 if "placeholder" in item["rule"]]
        self.assertEqual([item["rule"] for item in found],
                         ["placeholder-double-brace"])

    def test_placeholders_are_errors(self):
        found = severities("Hi {{name}},\n\nThanks,\nAmir\n")
        self.assertEqual(found["placeholder-double-brace"], "error")


class TestLinkRules(unittest.TestCase):
    def test_missing_link_promise(self):
        text = "Hi,\n\nSee the guide for the steps.\n\nThanks,\nAmir\n"
        self.assertIn("missing-link", rules(text))

    def test_attached_without_url(self):
        text = "Hi,\n\nThe form is attached.\n\nThanks,\nAmir\n"
        self.assertIn("missing-link", rules(text))

    def test_real_url_satisfies_promise(self):
        text = "Hi,\n\nSee the guide: https://shop.test/guide\n\nThanks,\nAmir\n"
        self.assertNotIn("missing-link", rules(text))

    def test_placeholder_url(self):
        text = "Hi,\n\nSee https://example.com/guide\n\nThanks,\nAmir\n"
        self.assertIn("placeholder-url", rules(text))

    def test_placeholder_url_is_error(self):
        found = severities("Hi,\n\nSee https://example.com/guide\n\nThanks,\nAmir\n")
        self.assertEqual(found["placeholder-url"], "error")


class TestStructuralRules(unittest.TestCase):
    def test_missing_greeting(self):
        self.assertIn("structure-no-greeting", rules("Your order shipped.\n\nThanks,\nAmir\n"))

    def test_missing_closing(self):
        self.assertIn("structure-no-closing", rules("Hi,\n\nYour order shipped.\n"))

    def test_long_paragraph(self):
        long_para = " ".join(["word"] * 160)
        text = "Hi,\n\n%s\n\nThanks,\nAmir\n" % long_para
        self.assertIn("structure-long-paragraph", rules(text))

    def test_short_paragraph_ok(self):
        long_para = " ".join(["word"] * 50)
        text = "Hi,\n\n%s\n\nThanks,\nAmir\n" % long_para
        self.assertNotIn("structure-long-paragraph", rules(text))

    def test_clean_draft_passes(self):
        self.assertEqual(lint_text(CLEAN), [])


class TestCli(unittest.TestCase):
    def test_json_output_shape(self):
        path = write_draft("Hi {{name}},\n\nThanks,\nAmir\n")
        result = run_cli([path, "--json"])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("findings", data)
        self.assertIn("counts", data)
        self.assertIn("total", data)
        finding = data["findings"][0]
        self.assertEqual(set(finding),
                         {"line", "rule", "severity", "message", "suggestion"})
        self.assertEqual(data["counts"]["error"], 1)

    def test_check_fails_on_error(self):
        path = write_draft("Hi {{name}},\n\nThanks,\nAmir\n")
        result = run_cli([path, "--check"])
        self.assertEqual(result.returncode, 1)

    def test_check_passes_on_warning_only(self):
        path = write_draft("Hi,\n\nCalm down.\n\nThanks,\nAmir\n")
        result = run_cli([path, "--check"])
        self.assertEqual(result.returncode, 0)

    def test_check_warnings_as_errors(self):
        path = write_draft("Hi,\n\nCalm down.\n\nThanks,\nAmir\n")
        result = run_cli([path, "--check", "--warnings-as-errors"])
        self.assertEqual(result.returncode, 1)

    def test_check_passes_on_clean(self):
        path = write_draft(CLEAN)
        result = run_cli([path, "--check"])
        self.assertEqual(result.returncode, 0)

    def test_stdin_input(self):
        result = run_cli(["--json"], stdin_text="Hi {{name}},\n\nThanks,\nAmir\n")
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["counts"]["error"], 1)

    def test_stdin_dash_flag(self):
        result = run_cli(["-", "--check"], stdin_text=CLEAN)
        self.assertEqual(result.returncode, 0)

    def test_missing_file_exits_2(self):
        result = run_cli(["/tmp/does-not-exist-support-macro-linter.txt"])
        self.assertEqual(result.returncode, 2)

    def test_text_output_lists_findings(self):
        path = write_draft("Hi {{name}},\n\nThanks,\nAmir\n")
        result = run_cli([path])
        self.assertIn("placeholder-double-brace", result.stdout)
        self.assertIn("L1", result.stdout)

    def test_clean_text_output(self):
        path = write_draft(CLEAN)
        result = run_cli([path])
        self.assertIn("No findings", result.stdout)

    def test_exit_code_helper(self):
        self.assertEqual(exit_code(lint_text(CLEAN), True, False), 0)
        self.assertEqual(exit_code(lint_text("Hi {{x}},\n\nThanks,\nAmir\n"),
                                   True, False), 1)


if __name__ == "__main__":
    unittest.main()
