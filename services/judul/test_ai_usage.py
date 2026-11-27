"""Kegagalan logger identity tidak mengubah hasil fitur judul."""
from ai_usage import catat


def test_gagal_mengirim_catatan_tidak_dilempar(monkeypatch):
    monkeypatch.setenv("AI_CATAT_TOKEN", "token-uji")
    monkeypatch.setenv("IDENTITY_URL", "http://identity.invalid")

    class ThreadSinkron:
        def __init__(self, target, daemon=True):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr("ai_usage.threading.Thread", ThreadSinkron)
    monkeypatch.setattr("ai_usage.urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    catat("rekomendasi_judul", "gpt-test")
