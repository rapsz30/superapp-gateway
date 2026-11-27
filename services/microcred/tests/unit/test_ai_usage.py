"""Logger identity berjalan di latar belakang dan tidak menggagalkan pemanggil."""
from src.libs import ai_usage


def test_gagal_mengirim_catatan_tidak_dilempar(monkeypatch):
    monkeypatch.setenv("AI_CATAT_TOKEN", "token-uji")
    monkeypatch.setenv("IDENTITY_URL", "http://identity.invalid")
    monkeypatch.setattr(ai_usage, "get_settings", lambda: type("S", (), {
        "ai_catat_token": "token-uji", "identity_url": "http://identity.invalid",
    })())

    class ThreadSinkron:
        def __init__(self, target, daemon=True):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(ai_usage.threading, "Thread", ThreadSinkron)
    monkeypatch.setattr(ai_usage.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    ai_usage.catat("gpt-test")
