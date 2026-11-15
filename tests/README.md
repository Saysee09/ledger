# Brokeless tests

Headless-browser checks (Playwright + Chromium, phone size 360 px, normal and large text). Run from the repo root:

    python3 tests/test_card.py     # card pay, card bill matched from SMS, limit usage
    python3 tests/test_glitch.py   # page behind a sheet, tab strip, card showing its limit
    python3 tests/test_v91.py      # Google sign-in against a fake Google, switch, backups, bank picker, tour, guides
    python3 tests/test_perm.py     # permissions step with a simulated phone app
    python3 tests/test_rep.py      # monthly report

Each prints PASS/FAIL lines and "FAILED: n". Screenshots go to tests/shots/ (not committed).
The fake Google in test_v91.py rejects locale en_IN like the real one. Real Google and real Android cannot be reached from a sandbox.
