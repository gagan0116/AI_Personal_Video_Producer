import pytest
from app.data.player_extractor import PlayerExtractor


def test_player_extraction_barcelona():
    extractor = PlayerExtractor("barcelona_vs_paris_sg")
    text = "Neymar collects the pass on the left and combines with Messi. Luis Suarez makes the overlapping run."
    players = extractor.extract_players(text)
    
    assert "Neymar" in players or any("neymar" in p.lower() for p in players)
    assert any("messi" in p.lower() for p in players)
    assert any("suarez" in p.lower() for p in players)


def test_player_mention_check():
    extractor = PlayerExtractor("barcelona_vs_paris_sg")
    text = "Sensational dribbling by Neymar past two defenders!"
    
    assert extractor.is_player_mentioned(text, "Neymar")
    assert extractor.is_player_mentioned(text, "Neymar Jr")
    assert not extractor.is_player_mentioned(text, "Cristiano Ronaldo")


def test_leicester_arsenal_roster():
    extractor = PlayerExtractor("leicester_vs_arsenal")
    text = "Jamie Vardy breaks past the defense, but Petr Cech makes the point-blank save from Alexis Sanchez's deflection."
    players = extractor.extract_players(text)
    
    assert any("vardy" in p.lower() for p in players)
    assert any("cech" in p.lower() for p in players)
