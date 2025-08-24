from __future__ import annotations

import random

from .board import Board
from .move import Move
from .movegen import generate_pseudo_legal


def select_move(board: Board, depth: int = 2) -> Move:
    moves = generate_pseudo_legal(board)
    if not moves:
        raise ValueError("No moves available.")
    return random.choice(moves)
