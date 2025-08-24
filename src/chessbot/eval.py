from __future__ import annotations

from typing import Tuple

from .board import (
    BISHOP,
    BLACK,
    EMPTY,
    KING,
    KNIGHT,
    PAWN,
    QUEEN,
    ROOK,
    WHITE,
    Board,
    idx_to_rf,
    on_board,
    piece_color,
    piece_type,
)

PIECE_VALUE = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 2000,
}

CENTER_FILES = {3, 4}
CENTER_RANKS = {3, 4}

# All this stuff from google


def _file_rank(idx: int) -> Tuple[int, int]:
    return idx & 7, idx >> 4


def _is_center(idx: int) -> bool:
    f, r = _file_rank(idx)
    return (f in CENTER_FILES) and (r in CENTER_RANKS)


def _open_file_info(board: Board, file_idx: int) -> tuple[bool, bool]:
    seen_w = seen_b = False
    for r in range(8):
        sq = (r << 4) | file_idx
        p = board.squares[sq]
        if p != EMPTY and piece_type(p) == PAWN:
            if piece_color(p) == WHITE:
                seen_w = True
            else:
                seen_b = True
    return seen_w, seen_b


# positive = good for white, negative = good for black
def evaluate(board: Board) -> int:
    score = 0

    for idx in range(128):
        if not on_board(idx):
            continue
        p = board.squares[idx]
        if p == EMPTY:
            continue

        col = piece_color(p)
        typ = piece_type(p)
        val = PIECE_VALUE[typ]

        score += val if col == WHITE else -val

        # Positional bonuses
        f, r = _file_rank(idx)
        if typ == PAWN:
            advance = r if col == WHITE else (7 - r)
            score += (advance * 3) if col == WHITE else -(advance * 3)
        elif typ == KNIGHT:
            if _is_center(idx):
                score += 10 if col == WHITE else -10
        elif typ == BISHOP:
            if _is_center(idx):
                score += 5 if col == WHITE else -5
        elif typ == ROOK:
            has_w, has_b = _open_file_info(board, f)
            if (not has_w) and (not has_b):  # open
                score += 12 if col == WHITE else -12
            elif (col == WHITE and not has_w) or (
                col == BLACK and not has_b
            ):  # semi-open
                score += 6 if col == WHITE else -6
        elif typ == QUEEN:
            if _is_center(idx):
                score += 3 if col == WHITE else -3

    return score
