# Good first issues

Small, testable tasks for first-time contributors. No network access needed.

1. Add a --rules flag that prints the full rule list (rule id,
   severity, and one-line description) and exits 0. Scope: build
   the list from the existing rule definitions, add CLI tests,
   document the flag in the README.
2. Add a --ignore flag that takes a comma separated list of rule
   ids to suppress from the output and from the --check exit
   code. Scope: filter findings after linting, add tests for a
   suppressed error and a suppressed warning, document the flag.
3. Add a severity override file: read a JSON file of rule id to
   severity mappings (error or warning) and apply it before
   reporting. Scope: add a --severity-file flag, validate unknown
   rule ids and bad severities with exit 2, add tests, document
   the file format in the README.
4. Add a word list file for tone phrases: let users pass a text
   file with one extra phrase per line, checked the same way as
   the built-in tone phrases. Scope: add a --tone-file flag,
   ignore blank lines and lines starting with #, add tests for a
   custom phrase firing and a clean draft staying clean, document
   the flag.
