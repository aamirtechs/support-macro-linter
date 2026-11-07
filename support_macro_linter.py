"""Lint a support reply draft before sending it.

Zero dependencies, Python 3 standard library only. The checks are
deterministic pattern checks, not AI and not network calls. Run it
on a draft file or pipe a draft on stdin:

    python3 support_macro_linter.py draft.txt
    python3 support_macro_linter.py draft.txt --json
    python3 support_macro_linter.py draft.txt --check
    cat draft.txt | python3 support_macro_linter.py
    python3 -m support_macro_linter draft.txt

Exit codes: 0 normally, and also with --check when there are no
error-severity findings. With --check, exit 1 when at least one
error-severity finding exists, or when --warnings-as-errors is
also given and at least one warning exists. Exit 2 for a missing
or unreadable file, or for bad command line arguments.
"""

import argparse
import json
import re
import sys

__version__ = "1.0.0"

# Each finding is a dict with keys: line, rule, severity, message,
# suggestion. Severities: "error" blocks a send, "warning" is advice.

TONE_PHRASES = [
    ("calm down", "tone-calm-down",
     "Tells the customer how to feel. Replace it with an acknowledgement."),
    ("as i already told you", "tone-dismissive",
     "Sounds dismissive. Restate the point without referencing repetition."),
    ("as i said before", "tone-dismissive",
     "Sounds dismissive. Restate the point without referencing repetition."),
    ("i already told you", "tone-dismissive",
     "Sounds dismissive. Restate the point without referencing repetition."),
    ("you should have", "tone-blame",
     "Blames the customer. Describe the next step instead."),
    ("it is your fault", "tone-blame",
     "Blames the customer. Describe what will happen next instead."),
    ("it's your fault", "tone-blame",
     "Blames the customer. Describe what will happen next instead."),
    ("your fault", "tone-blame",
     "Blames the customer. Describe what will happen next instead."),
    ("not my problem", "tone-blame",
     "Refuses ownership. Say who will handle it and by when."),
    ("you never", "tone-blame",
     "Absolute blame language. Stick to the specific event."),
    ("you always", "tone-blame",
     "Absolute blame language. Stick to the specific event."),
]

LINK_PROMISES = [
    "see the guide",
    "see guide",
    "check the link",
    "link below",
    "link above",
    "follow the link",
    "attached",
    "attachment",
    "see the attachment",
    "i have attached",
    "i've attached",
    "guide attached",
    "document attached",
]

GREETING_RE = re.compile(
    r"^(hi|hello|hey|dear|good morning|good afternoon|good evening)\b",
    re.IGNORECASE)
CLOSING_RE = re.compile(
    r"^(thanks|thank you|regards|best regards|kind regards|warm regards|"
    r"best wishes|sincerely|cheers|take care|best)\b",
    re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s<>\])]+")
PLACEHOLDER_URL_RE = re.compile(
    r"(https?://)?(www\.)?(example\.(com|org|net)|placeholder\.com|"
    r"yourdomain\.com|insert-link-here|your-link-here)\b",
    re.IGNORECASE)
DOUBLE_BRACE_RE = re.compile(r"\{\{[^{}]*\}\}")
DOUBLE_BRACKET_RE = re.compile(r"\[\[[^\]]*\]\]")
SINGLE_BRACE_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
SHOUTING_RUN_RE = re.compile(r"\b[A-Z]{2,}\b(?:[\s,;:]+[A-Z]{2,}\b){3,}")

LONG_PARAGRAPH_WORDS = 150


def _finding(line, rule, severity, message, suggestion):
    return {
        "line": line,
        "rule": rule,
        "severity": severity,
        "message": message,
        "suggestion": suggestion,
    }


def lint_text(text):
    """Return a list of findings for the draft text, in line order."""
    lines = text.splitlines()
    findings = []

    # A URL anywhere in the draft satisfies link promises below.
    has_real_url = bool(URL_RE.search(text))
    has_placeholder_url = bool(PLACEHOLDER_URL_RE.search(text))

    for index, line in enumerate(lines, start=1):
        lowered = line.lower()

        # Tone risks. Drop a shorter phrase when a longer matched phrase
        # already contains it, so "as i already told you" fires once.
        matched_tone = [(p, r, s) for p, r, s in TONE_PHRASES if p in lowered]
        matched_tone = [(p, r, s) for p, r, s in matched_tone
                        if not any(p != q and p in q
                                   for q, _, _ in matched_tone)]
        for phrase, rule, suggestion in matched_tone:
            if phrase in lowered:
                findings.append(_finding(
                    index, rule, "warning",
                    "Tone risk: phrase %r can read as dismissive or blaming."
                    % phrase,
                    suggestion))
        if SHOUTING_RUN_RE.search(line):
            findings.append(_finding(
                index, "tone-shouting", "warning",
                "Long run of all-caps words reads as shouting.",
                "Rewrite in normal sentence case, keeping acronyms only."))

        # Unresolved placeholders.
        for match in DOUBLE_BRACE_RE.finditer(line):
            findings.append(_finding(
                index, "placeholder-double-brace", "error",
                "Unresolved placeholder %r." % match.group(0),
                "Fill in the value or remove the placeholder."))
        for match in DOUBLE_BRACKET_RE.finditer(line):
            findings.append(_finding(
                index, "placeholder-double-bracket", "error",
                "Unresolved placeholder %r." % match.group(0),
                "Fill in the value or remove the placeholder."))
        stripped = DOUBLE_BRACE_RE.sub("", line)
        for match in SINGLE_BRACE_RE.finditer(stripped):
            findings.append(_finding(
                index, "placeholder-brace-token", "error",
                "Unfilled token %r." % match.group(0),
                "Replace the token with the real value."))
        if re.search(r"\[TODO\]", line, re.IGNORECASE):
            findings.append(_finding(
                index, "placeholder-todo", "error",
                "Unresolved [TODO] marker.",
                "Finish the item and remove the marker."))
        if re.search(r"\bTBD\b", line):
            findings.append(_finding(
                index, "placeholder-tbd", "error",
                "Unresolved TBD marker.",
                "Fill in the missing detail or remove the marker."))
        if re.search(r"\bXXX\b", line):
            findings.append(_finding(
                index, "placeholder-xxx", "error",
                "Unresolved XXX marker.",
                "Fill in the missing detail or remove the marker."))

        # Missing links and placeholder URLs.
        for phrase in LINK_PROMISES:
            if phrase in lowered and not has_real_url \
                    and not has_placeholder_url:
                findings.append(_finding(
                    index, "missing-link", "error",
                    "Promises a link, guide, or attachment (%r) but the "
                    "draft contains no URL." % phrase,
                    "Add the real URL, or remove the promise."))
                break
        if PLACEHOLDER_URL_RE.search(line):
            findings.append(_finding(
                index, "placeholder-url", "error",
                "Placeholder URL, not a real link.",
                "Replace it with the real URL before sending."))

    # Structural checks, only for non-empty drafts.
    non_empty = [(i, line) for i, line in enumerate(lines, start=1)
                 if line.strip()]
    if non_empty:
        first_no, first_line = non_empty[0]
        if not GREETING_RE.search(first_line.strip()):
            findings.append(_finding(
                first_no, "structure-no-greeting", "warning",
                "Draft does not start with a greeting.",
                "Start with Hi, Hello, or Dear followed by the name."))
        last_no, _ = non_empty[-1]
        tail = [line.strip() for _, line in non_empty[-3:]]
        if not any(CLOSING_RE.search(line) for line in tail):
            findings.append(_finding(
                last_no, "structure-no-closing", "warning",
                "Draft has no closing or sign-off.",
                "End with Thanks, Best regards, or a similar sign-off."))

    # Very long single paragraph: blank-line separated blocks.
    para_start = None
    para_words = 0
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            if para_words > LONG_PARAGRAPH_WORDS:
                findings.append(_finding(
                    para_start, "structure-long-paragraph", "warning",
                    "Single paragraph has %d words, over the %d word limit."
                    % (para_words, LONG_PARAGRAPH_WORDS),
                    "Split it into shorter paragraphs, one point each."))
            para_start = None
            para_words = 0
        else:
            if para_start is None:
                para_start = index
            para_words += len(line.split())
    if para_words > LONG_PARAGRAPH_WORDS:
        findings.append(_finding(
            para_start, "structure-long-paragraph", "warning",
            "Single paragraph has %d words, over the %d word limit."
            % (para_words, LONG_PARAGRAPH_WORDS),
            "Split it into shorter paragraphs, one point each."))

    findings.sort(key=lambda item: (item["line"], item["rule"]))
    return findings


def format_text(findings):
    if not findings:
        return "No findings. Draft looks ready to send."
    out = []
    for item in findings:
        out.append("L%d [%s] %s: %s Suggestion: %s" % (
            item["line"], item["rule"], item["severity"],
            item["message"], item["suggestion"]))
    return "\n".join(out)


def report(findings):
    counts = {"error": 0, "warning": 0}
    for item in findings:
        counts[item["severity"]] += 1
    return {
        "findings": findings,
        "counts": counts,
        "total": len(findings),
    }


def exit_code(findings, check, warnings_as_errors):
    if not check:
        return 0
    counts = report(findings)["counts"]
    if counts["error"] > 0:
        return 1
    if warnings_as_errors and counts["warning"] > 0:
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lint a support reply draft before sending it.")
    parser.add_argument("file", nargs="?",
                        help="Draft file to lint, or - for stdin. "
                        "Reads stdin when omitted.")
    parser.add_argument("--json", action="store_true",
                        help="Print findings as JSON.")
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 when any error-severity finding exists. "
                        "Warnings alone pass.")
    parser.add_argument("--warnings-as-errors", action="store_true",
                        help="With --check, also exit 1 on warnings.")
    args = parser.parse_args(argv)

    if args.file in (None, "-"):
        text = sys.stdin.read()
    else:
        try:
            with open(args.file, encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            print("Error: cannot read %s: %s" % (args.file, exc),
                  file=sys.stderr)
            return 2

    findings = lint_text(text)
    if args.json:
        print(json.dumps(report(findings), indent=2))
    else:
        print(format_text(findings))
    return exit_code(findings, args.check, args.warnings_as_errors)


if __name__ == "__main__":
    sys.exit(main())
