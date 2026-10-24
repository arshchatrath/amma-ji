"""Checks for the code that carries out Amma ji's tools. No internet needed.

Run from the backend folder:  .venv/bin/pytest
"""
from datetime import timedelta

from app import session
from app.brain import note, screen_text, timer_reply, warnings
from app.session import apply_tool, live_timers, new_session, normalise, public


def fresh(**kw):
    return new_session("dal_tadka", **kw)


def test_next_and_previous_stay_inside_the_recipe():
    s = fresh()
    apply_tool(s, "previous_step", {})
    assert s["current_step"] == 1
    for _ in range(20):
        apply_tool(s, "next_step", {})
    assert s["current_step"] == 7
    assert s["completed_steps"] == [1, 2, 3, 4, 5, 6]


def test_finishing_a_step_counts_its_ingredients_as_added():
    s = fresh()
    for _ in range(3):
        apply_tool(s, "next_step", {})
    assert s["current_step"] == 4
    assert s["ingredients_added"] == ["toor_dal", "water", "turmeric", "salt"]


def test_mark_added_only_accepts_real_ingredients_once():
    s = fresh()
    apply_tool(s, "mark_added", {"ingredient": "Turmeric"})
    apply_tool(s, "mark_added", {"ingredient": "turmeric"})
    apply_tool(s, "mark_added", {"ingredient": "chocolate"})
    assert s["ingredients_added"] == ["turmeric"]


def test_timer_runs_on_the_clock_and_rejects_silly_lengths():
    s = fresh()
    assert apply_tool(s, "start_timer", {"minutes": 15, "label": "pressure cook"})["timer_started"]
    apply_tool(s, "start_timer", {"minutes": 0})
    apply_tool(s, "start_timer", {"minutes": "lots"})
    apply_tool(s, "start_timer", {"minutes": 500})
    timers = live_timers(s)
    assert len(timers) == 1 and 14 * 60 < timers[0]["seconds_left"] <= 15 * 60


def test_finished_timers_disappear_after_five_minutes(monkeypatch):
    s = fresh()
    apply_tool(s, "start_timer", {"minutes": 1, "label": "x"})
    later = session.now() + timedelta(minutes=7)
    monkeypatch.setattr(session, "now", lambda: later)
    assert live_timers(s) == []


def test_slow_repeat_asks_for_a_slower_voice():
    assert apply_tool(fresh(), "repeat_step", {"slow": True}) == {"tts_speed": 0.85}


def test_note_hides_substitutes_the_user_is_allergic_to():
    s = fresh(allergies=["butter"])
    text = note(s)
    assert "घी [ghee] 1 tbsp (or तेल [oil])" in text
    assert "Allergies (never suggest these): butter" in text


def test_allergy_groups_from_the_screen_block_every_ingredient_in_them():
    s = fresh(allergies=["dairy"])  # the screen sends groups, not ingredient ids
    assert {"butter", "ghee", "milk", "paneer"} <= set(s["blocked"])
    text = note(s)
    assert "(or तेल [oil])" in text and "मक्खन [butter])" not in text
    assert "warn them gently: घी [ghee]" in text
    apply_tool(s, "substitute", {"ingredient": "ghee", "to": "butter"})
    assert s["substitutions"] == []


def test_note_shows_only_steps_around_the_current_one():
    s = fresh(language="hi")
    s["current_step"] = 4
    text = note(s)
    assert "Previous step 3" in text and "Current step 4" in text and "Next step 5" in text
    assert "step 1:" not in text and "step 7:" not in text
    assert "कुकर खोलो" in text


def test_public_state_has_the_step_ready_to_show():
    p = public(fresh(language="pa"))
    assert p["step"]["n"] == 1 and p["total_steps"] == 7
    assert p["recipe_name"] == "ਦਾਲ ਤੜਕਾ"


def test_screen_text_drops_audio_tags():
    assert screen_text("<sigh> कोई बात नहीं बेटा।") == "कोई बात नहीं बेटा।"


def test_timer_reply_comes_from_the_clock():
    s = fresh(language="hi-en")
    assert timer_reply(s) == "बेटा, अभी कोई timer नहीं चल रहा।"
    apply_tool(s, "start_timer", {"minutes": 15, "label": "dal"})
    assert timer_reply(s) == "बेटा, dal में 15 मिनट बचे हैं।"
    s["language"] = "en"
    assert timer_reply(s) == "बेटा, 15 minutes left on dal."


def test_substitute_only_records_listed_and_safe_swaps():
    s = fresh(allergies=["butter"])
    apply_tool(s, "substitute", {"ingredient": "ghee", "to": "butter"})
    apply_tool(s, "substitute", {"ingredient": "ghee", "to": "coconut oil"})
    assert s["substitutions"] == []
    apply_tool(s, "substitute", {"ingredient": "ghee", "to": "oil"})
    assert s["substitutions"] == [{"from": "ghee", "to": "oil"}]
    assert "घी [ghee] -> तेल [oil]" in note(s)


def test_warnings_catch_known_slips():
    assert warnings("गhee की जगह तेल डालो") == ["a word mixes two scripts"]
    assert warnings("<sigh> ठीक है <laugh>") == ["more than one audio tag"]
    assert warnings("टाइमर लगा रहा हूँ") == ["masculine verb form for Amma ji"]
    assert warnings("बेटा, 15 मिनट का timer लगा देती हूँ।") == []


def test_normalise_writes_ingredients_in_the_reply_script():
    assert normalise("ghee khatam ho gaya, kya use karun?", "hi-en") == "घी khatam ho gaya, kya use karun?"
    assert normalise("Desi Ghee aur jeera", "pa") == "ਘਿਓ aur ਜੀਰਾ"
    assert normalise("haldi daal di", "en") == "haldi daal di"
    assert normalise("teliya", "hi") == "teliya"  # only whole words


def test_hinglish_steps_are_spoken_in_devanagari():
    p = public(fresh(language="hi-en"))
    assert p["step"]["text"].startswith("Toor dal")
    assert p["step"]["speak"].startswith("तूर दाल")


def test_timer_labels_read_like_words():
    s = fresh()
    apply_tool(s, "start_timer", {"minutes": 5, "label": "dal_tadka_step3"})
    assert live_timers(s)[0]["label"] == "dal tadka step3"


def test_pantry_reads_all_three_scripts():
    from app.pantry import hear
    assert hear("मेरे पास आलू, प्याज़ और टमाटर हैं, पनीर नहीं है")["not_have"] == ["paneer"]
    assert hear("ਆਂਡੇ, ਪਿਆਜ਼ ਤੇ ਟਮਾਟਰ ਨੇ")["have"] == ["egg", "onion", "tomato"]
    assert hear("I have eggs, onions and bread, no butter")["have"] == ["egg", "onion", "bread"]
    assert hear("aadha ghanta hai")["minutes"] == 30
