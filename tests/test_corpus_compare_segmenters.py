from types import SimpleNamespace

from benchmarks.corpus_compare import segmenters


def test_probe_import_redacts_absolute_paths(monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stderr=(
                "Traceback (most recent call last):\n"
                "OSError: /tmp/sentencesplit/virtualenv/lib/python3.13/site-packages/blingfire/"
                "libblingfiretokdll.so: cannot open shared object file\n"
            ),
        )

    monkeypatch.setattr(segmenters.subprocess, "run", fake_run)

    ok, reason = segmenters._probe_import("blingfire")

    assert ok is False
    assert "/tmp/sentencesplit" not in reason
    assert "virtualenv" not in reason
    assert "<path>" in reason
    assert "cannot open shared object file" in reason


def test_segmenter_redacts_unavailable_reason_paths():
    adapter = segmenters.Segmenter(
        "fake",
        "rule-based",
        "Fake adapter.",
        available=False,
        unavailable_reason=r"ImportError: C:\\Users\\alice\\sentencesplit\\virtualenv\\pkg.pyd failed",
    )

    assert "C:" not in adapter.unavailable_reason
    assert "alice" not in adapter.unavailable_reason
    assert "<path>" in adapter.unavailable_reason
