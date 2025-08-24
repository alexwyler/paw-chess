from __future__ import annotations

import random

from .board import Board
from .move import Move
from .movegen import generate_legal


def select_move(board: Board, *, depth: int = 2) -> Move:
    moves = generate_legal(board)
    if not moves:
        raise ValueError("No legal moves.")
    return random.choice(moves)
