# Changelog

## 1.0.0 (2026-11-01)

- First release.
- Zero-dependency Python CLI: lint a support reply draft from a
  file argument or stdin, with no AI and no network calls.
- Tone checks: dismissive and blame phrases (including "calm
  down", "as I already told you", and "you should have") and
  long all-caps shouting runs.
- Placeholder checks: {{...}}, [[...]], [TODO], TBD, XXX, and
  unfilled {name}-style tokens.
- Link checks: sentences promising a link, guide, or attachment
  with no URL in the draft, and placeholder URLs such as
  example.com.
- Structural checks: missing greeting, missing closing or
  sign-off, and a single paragraph over 150 words.
- Every finding reports line number, rule id, severity (error or
  warning), and a short suggestion.
- Flags: --json for machine output, --check as a CI gate (exits
  1 on any error, warnings alone pass), and
  --warnings-as-errors.
- 37 passing tests.
