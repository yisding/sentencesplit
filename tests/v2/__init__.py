# -*- coding: utf-8 -*-
"""V2 abbreviation-engine acceptance harness.

This package holds the curated English correctness corpus (``corpus_en.py``) and
the 26-language ``segment()`` snapshot gate (``segment_snapshot.py``). The gate
is the Golden Rules + the curated correctness corpus + the snapshot + the full
suite.

The differential oracle (``oracle.py`` / ``test_oracle.py``) was retired once the
legacy engine it froze a snapshot of was deleted: its load-bearing parity
assertions were re-homed as direct ``segment()`` cases — English/en_legal into
``corpus_en.py`` and Kazakh into ``tests/lang/test_kazakh.py``.
"""
