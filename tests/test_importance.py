import pytest
from app.engine.importance import calculate_importance


def test_importance_goal():
    score = calculate_importance("Goal", replay_count=2, commentary_text="WHAT A SENSATIONAL GOAL BY NEYMAR!")
    assert score >= 0.95


def test_importance_foul():
    score = calculate_importance("Foul", replay_count=0, commentary_text="Minor challenge in midfield.")
    assert 0.35 <= score <= 0.50


def test_replay_multiplier():
    score_no_replay = calculate_importance("Offside", replay_count=0, commentary_text=None)
    score_with_replays = calculate_importance("Offside", replay_count=3, commentary_text=None)
    assert score_with_replays > score_no_replay
