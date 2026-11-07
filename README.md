# support-macro-linter

Lint a support reply draft before sending it. Deterministic
checks only, no AI, no network, no dependencies. Just Python 3
and the standard library.

A support reply sent with an unfilled placeholder, a promised
link that is not there, or a blame phrase in the first line is
hard to unsend. This tool catches those mistakes while the draft
is still editable, and it works as a CI gate for a macro or
template library.

## Usage

Run from the repository root:

```sh
python3 support_macro_linter.py examples/bad-draft.txt
python3 support_macro_linter.py examples/good-draft.txt --check
python3 support_macro_linter.py examples/good-draft.txt --json
cat examples/good-draft.txt | python3 support_macro_linter.py
python3 support_macro_linter.py - < examples/good-draft.txt
python3 -m support_macro_linter examples/good-draft.txt
```

With no file argument, or with `-` as the file, the draft is
read from stdin. With a file argument, that file is linted.

`--json` prints findings as JSON. `--check` is the CI gate: it
exits 1 when any error-severity finding exists, and exits 0 when
there are only warnings or no findings. `--warnings-as-errors`
only changes `--check` behavior: with both flags, warnings also
exit 1. Without `--check`, the exit code is always 0 for a
readable draft. A missing or unreadable file exits 2.

## Checks

Severity rule: placeholders, missing links, and placeholder URLs
are errors, because the draft is not finished. Tone and
structural problems are warnings, because the draft is sendable
but should be improved.

| Area | Rules | Severity |
| --- | --- | --- |
| Tone | tone-calm-down, tone-dismissive, tone-blame | warning |
| Tone | tone-shouting: a run of 4 or more all-caps words | warning |
| Placeholders | placeholder-double-brace ({{...}}), placeholder-double-bracket ([[...]]) | error |
| Placeholders | placeholder-todo ([TODO]), placeholder-tbd (TBD), placeholder-xxx (XXX) | error |
| Placeholders | placeholder-brace-token (unfilled {name}-style tokens) | error |
| Links | missing-link: a sentence promising a link, guide, or attachment ("see the guide", "attached", "link below") with no URL in the draft | error |
| Links | placeholder-url: example.com, example.org, example.net, placeholder.com, yourdomain.com, and similar placeholder URLs | error |
| Structure | structure-no-greeting: first line is not Hi, Hello, Hey, Dear, or Good morning/afternoon/evening | warning |
| Structure | structure-no-closing: no Thanks, Best regards, or similar sign-off in the last three lines | warning |
| Structure | structure-long-paragraph: a single paragraph over 150 words | warning |

Tone phrases checked include "calm down", "as I already told
you", "you should have", "your fault", "not my problem", and
similar blame language. Matching is case-insensitive, and a
shorter phrase inside a longer matched phrase fires only once.
A double-brace placeholder is not also reported as a single
brace token. A link promise is satisfied by any real URL in the
draft; a placeholder URL alone does not satisfy it, and is
reported as placeholder-url instead.

Every finding reports a line number, a rule id, a severity, and
a short suggestion. Findings are sorted by line, then rule id.

## Real examples

All outputs below were captured by running the CLI on the files
in `examples/` on 2026-11-01.

`examples/bad-draft.txt` is:

```
Calm down, as I already told you, you should have checked this before writing in.
Your order {{order_id}} is delayed and the guide is attached, see the guide for details.
Please fill in [TODO] and confirm with {name} before we proceed. Check https://example.com for updates.
THIS IS COMPLETELY UNACCEPTABLE AND YOU NEED TO FIX IT RIGHT NOW WITHOUT ANY DELAY AT ALL.
```

Linting it:

```sh
python3 support_macro_linter.py examples/bad-draft.txt
```

```
L1 [structure-no-greeting] warning: Draft does not start with a greeting. Suggestion: Start with Hi, Hello, or Dear followed by the name.
L1 [tone-blame] warning: Tone risk: phrase 'you should have' can read as dismissive or blaming. Suggestion: Blames the customer. Describe the next step instead.
L1 [tone-calm-down] warning: Tone risk: phrase 'calm down' can read as dismissive or blaming. Suggestion: Tells the customer how to feel. Replace it with an acknowledgement.
L1 [tone-dismissive] warning: Tone risk: phrase 'as i already told you' can read as dismissive or blaming. Suggestion: Sounds dismissive. Restate the point without referencing repetition.
L2 [placeholder-double-brace] error: Unresolved placeholder '{{order_id}}'. Suggestion: Fill in the value or remove the placeholder.
L3 [placeholder-brace-token] error: Unfilled token '{name}'. Suggestion: Replace the token with the real value.
L3 [placeholder-todo] error: Unresolved [TODO] marker. Suggestion: Finish the item and remove the marker.
L3 [placeholder-url] error: Placeholder URL, not a real link. Suggestion: Replace it with the real URL before sending.
L4 [structure-no-closing] warning: Draft has no closing or sign-off. Suggestion: End with Thanks, Best regards, or a similar sign-off.
L4 [tone-shouting] warning: Long run of all-caps words reads as shouting. Suggestion: Rewrite in normal sentence case, keeping acronyms only.
```

That same draft with `--check` exits 1, because it has
error-severity findings:

```sh
python3 support_macro_linter.py examples/bad-draft.txt --check
echo $?
```

The output is the same finding list as above, and the exit code
is 1.

`examples/good-draft.txt` is:

```
Hi Sarah,

Thanks for reaching out, and sorry for the delay on order 1042.

We have checked your order and it is now on its way. You can track it here: https://shop.test/orders/1042

Please let us know if anything else comes up.

Thanks,
Amir
```

Linting it with `--check` exits 0:

```
No findings. Draft looks ready to send.
```

Linting it with `--json` gives:

```json
{
  "findings": [],
  "counts": {
    "error": 0,
    "warning": 0
  },
  "total": 0
}
```

Linting the bad draft with `--json` gives (counts at the end):

```json
{
  "findings": [
    {
      "line": 1,
      "rule": "structure-no-greeting",
      "severity": "warning",
      "message": "Draft does not start with a greeting.",
      "suggestion": "Start with Hi, Hello, or Dear followed by the name."
    },
    {
      "line": 1,
      "rule": "tone-blame",
      "severity": "warning",
      "message": "Tone risk: phrase 'you should have' can read as dismissive or blaming.",
      "suggestion": "Blames the customer. Describe the next step instead."
    },
    {
      "line": 1,
      "rule": "tone-calm-down",
      "severity": "warning",
      "message": "Tone risk: phrase 'calm down' can read as dismissive or blaming.",
      "suggestion": "Tells the customer how to feel. Replace it with an acknowledgement."
    },
    {
      "line": 1,
      "rule": "tone-dismissive",
      "severity": "warning",
      "message": "Tone risk: phrase 'as i already told you' can read as dismissive or blaming.",
      "suggestion": "Sounds dismissive. Restate the point without referencing repetition."
    },
    {
      "line": 2,
      "rule": "placeholder-double-brace",
      "severity": "error",
      "message": "Unresolved placeholder '{{order_id}}'.",
      "suggestion": "Fill in the value or remove the placeholder."
    },
    {
      "line": 3,
      "rule": "placeholder-brace-token",
      "severity": "error",
      "message": "Unfilled token '{name}'.",
      "suggestion": "Replace the token with the real value."
    },
    {
      "line": 3,
      "rule": "placeholder-todo",
      "severity": "error",
      "message": "Unresolved [TODO] marker.",
      "suggestion": "Finish the item and remove the marker."
    },
    {
      "line": 3,
      "rule": "placeholder-url",
      "severity": "error",
      "message": "Placeholder URL, not a real link.",
      "suggestion": "Replace it with the real URL before sending."
    },
    {
      "line": 4,
      "rule": "structure-no-closing",
      "severity": "warning",
      "message": "Draft has no closing or sign-off.",
      "suggestion": "End with Thanks, Best regards, or a similar sign-off."
    },
    {
      "line": 4,
      "rule": "tone-shouting",
      "severity": "warning",
      "message": "Long run of all-caps words reads as shouting.",
      "suggestion": "Rewrite in normal sentence case, keeping acronyms only."
    }
  ],
  "counts": {
    "error": 4,
    "warning": 6
  },
  "total": 10
}
```

A warning-only draft passes `--check` but fails with
`--warnings-as-errors`:

```sh
printf 'Hi,\nCalm down.\nThanks,\nAmir\n' > /tmp/warning-draft.txt
python3 support_macro_linter.py /tmp/warning-draft.txt --check
echo $?
python3 support_macro_linter.py /tmp/warning-draft.txt --check --warnings-as-errors
echo $?
```

```
L2 [tone-calm-down] warning: Tone risk: phrase 'calm down' can read as dismissive or blaming. Suggestion: Tells the customer how to feel. Replace it with an acknowledgement.
0
L2 [tone-calm-down] warning: Tone risk: phrase 'calm down' can read as dismissive or blaming. Suggestion: Tells the customer how to feel. Replace it with an acknowledgement.
1
```

## Limitations

- Checks are pattern based, not semantic: a polite draft that
  quotes a customer's angry words back to them can still trip a
  tone rule, and a subtly rude draft can pass.
- The greeting and closing checks use a fixed list of common
  openings and sign-offs, so an unusual but polite opening may
  be flagged.
- Link promises are satisfied by any real URL anywhere in the
  draft, not by checking that the URL is the promised guide.
- The tool reads the whole draft into memory, so a very large
  draft may be slow, but support replies are normally short.

## Tests

```sh
python3 -m unittest discover -s tests
```

37 tests, covering each rule firing on a crafted draft, clean
drafts passing, placeholder variants, --json output shape,
--check exit codes (error vs warning-only, plus
--warnings-as-errors), stdin input, and missing file handling.

## License

MIT. See `LICENSE`.
