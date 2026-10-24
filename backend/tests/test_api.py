"""Checks for the server's endpoints, with Groq and Gnani replaced by stand-ins. No internet needed."""
import struct

from fastapi.testclient import TestClient

from app import brain, main, voice

client = TestClient(main.app)


def fake_ask(state, text):
    return {"tool": "next_step", "args": {}, "reply": "<sigh> ठीक है बेटा।", "ms": 5, "tokens": 10, "prompt_tokens": 8}


def wav(seconds=1.0):
    frames = int(16000 * seconds)
    header = b"RIFF" + struct.pack("<I", 36 + frames * 2) + b"WAVEfmt " + struct.pack(
        "<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16) + b"data" + struct.pack("<I", frames * 2)
    return header + b"\0\0" * frames


def session(language="hi-en"):
    return client.post("/api/sessions", json={"language": language}).json()["session_id"]


def test_say_runs_a_turn_and_moves_the_step(monkeypatch):
    monkeypatch.setattr(brain, "ask", fake_ask)
    r = client.post(f"/api/sessions/{session()}/say", json={"text": "agla step"}).json()
    assert r["tool"] == "next_step" and r["state"]["step"]["n"] == 2
    assert r["reply_text"] == "ठीक है बेटा।"


def test_listen_hears_then_runs_a_turn(monkeypatch):
    monkeypatch.setattr(brain, "ask", fake_ask)
    monkeypatch.setattr(voice, "stt", lambda audio, lang: ("agla step batao", 42))
    r = client.post(f"/api/sessions/{session()}/listen", content=wav(), headers={"Content-Type": "audio/wav"})
    assert r.status_code == 200
    assert r.json()["heard"] == "agla step batao" and r.json()["timing_ms"]["stt"] == 42


def test_listen_rejects_tiny_recordings_and_empty_transcripts(monkeypatch):
    sid = session()
    assert client.post(f"/api/sessions/{sid}/listen", content=b"x" * 100).status_code == 422
    monkeypatch.setattr(voice, "stt", lambda audio, lang: ("", 40))
    assert client.post(f"/api/sessions/{sid}/listen", content=wav()).status_code == 422


def test_timer_tap_needs_no_ai():
    r = client.post(f"/api/sessions/{session()}/timer", json={"minutes": 5, "label": "simmer"}).json()
    assert r["timers"][0]["label"] == "simmer"


def test_speak_streams_pcm(monkeypatch):
    monkeypatch.setattr(voice, "tts_chunks", lambda text, lang, speed: iter([b"\1\0" * 10, b"\2\0" * 10]))
    r = client.post("/api/speak", json={"text": "नमस्ते", "language": "hi-en"})
    assert r.status_code == 200 and len(r.content) == 40
    assert r.headers["X-Sample-Rate"] == "24000"


def test_missing_session_says_so():
    r = client.post("/api/sessions/nope/say", json={"text": "hi"})
    assert r.status_code == 404 and "ended" in r.json()["detail"]


def test_pantry_hears_ingredients_time_and_no():
    r = client.post("/api/pantry", json={"text": "do aloo, paneer, pyaaz hai, ghee nahi hai. 20 minute", "language": "hi-en"}).json()
    assert [i["id"] for i in r["have"]] == ["potato", "paneer", "onion"]
    assert [i["id"] for i in r["not_have"]] == ["ghee"]
    assert r["minutes"] == 20


def test_suggest_labels_are_honest_and_respect_diet_and_allergies():
    dishes = client.post("/api/suggest", json={"have": ["egg", "onion", "tomato"], "limit": 10}).json()
    assert dishes and all(d["label"] in {"can_make_now", "needs_one_optional", "needs_optional", "missing_essential"}
                          for d in dishes)
    assert all(not d["missing_essential"] for d in dishes if d["label"] != "missing_essential")
    veg = client.post("/api/suggest", json={"have": ["egg", "onion", "tomato", "chicken"], "diet": "veg", "limit": 10}).json()
    assert all(d["diet"] == "veg" for d in veg)
    safe = client.post("/api/suggest", json={"have": ["poha", "potato"], "allergies": ["peanut"], "limit": 10}).json()
    assert all(d["id"] != "BFP044" for d in safe)  # poha has peanuts


def test_recipe_card_and_cooking_a_sheet_dish():
    card = client.get("/api/recipes/BFP044?language=hi").json()
    assert card["name"] == "पोहा" and card["steps"][0].startswith("पोहे") and card["nutrition"]["kcal"] > 0
    state = client.post("/api/sessions", json={"recipe_id": "BFP044", "language": "pa"}).json()
    assert state["recipe_name"] == "ਪੋਹਾ" and state["total_steps"] == 5


def test_finish_sums_up_the_dish_and_how_was_it_gives_tips():
    sid = client.post("/api/sessions", json={"recipe_id": "ASC097", "language": "hi-en"}).json()["session_id"]
    main.SESSIONS[sid]["substitutions"].append({"from": "oil", "to": "ghee"})
    main.SESSIONS[sid]["quantity_changes"].append({"spice": "less", "at_step": 1})
    done = client.post(f"/api/sessions/{sid}/finish").json()
    assert done["recipe_name"] == "Sada paratha" and done["minutes"] >= 1
    assert done["changes"] == ["ghee use kiya, oil ki jagah", "Mirch kam ki"]
    assert done["closing"]["text"].startswith("Shabaash beta!") and "शाबाश" in done["closing"]["speak"]
    assert done["nutrition"]["kcal"] > 0
    assert main.SESSIONS[sid]["completed_steps"] == [1, 2, 3, 4]
    bad = client.post(f"/api/sessions/{sid}/feedback", json={"rating": "bad"}).json()
    assert bad["tips"] and bad["tips"][0]["problem"] and bad["reply"]["text"].startswith("Koi baat nahi")
    assert client.post(f"/api/sessions/{sid}/feedback", json={"rating": "great"}).status_code == 422
