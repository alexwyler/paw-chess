from __future__ import annotations

from typing import List, Tuple

from .board import (
    BLACK,
    EMPTY,
    PAWN,
    WHITE,
    Board,
    on_board,
    piece_color,
    piece_type,
    rf_to_idx,
)
from .eval import PIECE_VALUE, evaluate
from .move import FLAG_EN_PASSANT, Move
from .movegen import generate_legal, in_check

INF = 10_000_000
MATE_SCORE = 1_000_000  # big value for checkmates

def select_move(board: Board, *, depth: int = 3) -> Move:
    side = board.side_to_move
    best_score = -INF
    best_move: Move | None = None

    moves = generate_legal(board)
    if not moves:
        if in_check(board, side):
            raise ValueError("Checkmated: no legal moves.")
        raise ValueError("Stalemate: no legal moves.")

    # captures first
    moves.sort(key=lambda m: _move_order_key(board, m), reverse=True)

    alpha, beta = -INF, INF
    for m in moves:
        prev = board.make_move(m.frm, m.to, m.promo or None)
        score = -_negamax(board, depth - 1, -beta, -alpha, ply=1)
        board.undo_move(prev)

        if score > best_score:
            best_score = score
            best_move = m
        if score > alpha:
            alpha = score

    assert best_move is not None
    return best_move

def _negamax(board: Board, depth: int, alpha: int, beta: int, *, ply: int) -> int:
    side = board.side_to_move

    if depth == 0:
        # Static evaluation is always from White's POV.
        # Negamax convention: flip by side to move.
        s = evaluate(board)
        return s if side == WHITE else -s

    moves = generate_legal(board)
    if not moves:
        # terminal: mate or stalemate
        if in_check(board, side):
            # side to move is checkmated -> very bad for side
            # prefer quicker mates (distance-to-mate)
            return -MATE_SCORE + ply
        else:
            return 0  # stalemate

    moves.sort(key=lambda m: _move_order_key(board, m), reverse=True)

    best = -INF
    for m in moves:
        prev = board.make_move(m.frm, m.to, m.promo or None)
        score = -_negamax(board, depth - 1, -beta, -alpha, ply=ply + 1)
        board.undo_move(prev)

        if score > best:
            best = score
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break  # alpha-beta cutoff
    return best

def _move_order_key(board: Board, m: Move) -> int:
    att_val = PIECE_VALUE.get(piece_type(board.squares[m.frm]), 0)
    cap_val = _captured_value(board, m)
    promo_bonus = 800 if m.promo else 0
    return cap_val - att_val + promo_bonus

def _captured_value(board: Board, m: Move) -> int:
    if m.flags & FLAG_EN_PASSANT:
        behind = m.to - 16 if board.side_to_move == WHITE else m.to + 16
        if on_board(behind):
            p = board.squares[behind]
            if p != EMPTY and piece_type(p) == PAWN:
                return PIECE_VALUE[PAWN]
        return 0
    dst = board.squares[m.to]
    if dst == EMPTY:
        return 0
    return PIECE_VALUE.get(piece_type(dst), 0)