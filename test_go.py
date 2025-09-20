import pytest
from go_game import GoGame

def test_simple_move():
    game = GoGame(size=5)
    ok, reason = game.play_move(0, 0)  # первый ход
    assert ok
    assert game.board[0][0] == game.BLACK

def test_capture():
    game = GoGame(size=3)
    game.play_move(0, 1)  # B
    game.play_move(0, 0)  # W
    game.play_move(1, 0)  # B
    game.play_move(1, 1)  # W
    game.play_move(2, 0)  # B
    game.play_move(2, 1)  # W захватывает
    assert game.board[0][1] == GoGame.EMPTY
