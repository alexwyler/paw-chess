from __future__ import annotations

from typing import List

from .board import (
    BISHOP,
    BLACK,
    BLACK_OO,
    BLACK_OOO,
    EMPTY,
    KING,
    KNIGHT,
    PAWN,
    QUEEN,
    ROOK,
    WHITE,
    WHITE_OO,
    WHITE_OOO,
    Board,
    on_board,
    piece_color,
    piece_type,
    rf_to_idx,
)
from .move import FLAG_CASTLE, FLAG_DOUBLE_PAWN, FLAG_EN_PASSANT, FLAG_PROMOTION, Move

_rank_dist = 16

KING_DELTAS = (
    +1,
    -1,
    +_rank_dist,
    -_rank_dist,
    +_rank_dist + 1,
    +_rank_dist - 1,
    -_rank_dist + 1,
    -_rank_dist - 1,
)
BISHOP_DELTAS = (
    +_rank_dist + 1,
    +_rank_dist - 1,
    -_rank_dist + 1,
    -_rank_dist - 1,
)

KNIGHT_DELTAS = (
    +2 * _rank_dist + 1,
    +2 * _rank_dist - 1,
    +_rank_dist + 2,
    +_rank_dist - 2,
    -2 * _rank_dist + 1,
    -2 * _rank_dist - 1,
    -_rank_dist + 2,
    -_rank_dist - 2,
)

ROOK_DELTAS = (+1, -1, +_rank_dist, -_rank_dist)
QUEEN_DELTAS = BISHOP_DELTAS + ROOK_DELTAS


def generate_pseudo_legal(board: Board) -> List[Move]:
    """Return pseudo-legal moves for the side to move."""
    side = board.side_to_move
    out: List[Move] = []

    for idx in range(128):
        if not on_board(idx):
            continue
        piece = board.squares[idx]
        if piece == EMPTY or piece_color(piece) != side:
            continue

        p = piece_type(piece)
        if p == PAWN:
            out.extend(pawn_moves(board, idx))
        elif p == KNIGHT:
            out.extend(leaper_moves(board, idx, KNIGHT_DELTAS))
        elif p == BISHOP:
            out.extend(slider_moves(board, idx, BISHOP_DELTAS))
        elif p == ROOK:
            out.extend(slider_moves(board, idx, ROOK_DELTAS))
        elif p == QUEEN:
            out.extend(slider_moves(board, idx, QUEEN_DELTAS))
        elif p == KING:
            out.extend(leaper_moves(board, idx, KING_DELTAS))
            out.extend(castle_candidates(board, idx))

    return out


def leaper_moves(board: Board, frm: int, deltas: tuple[int, ...]) -> List[Move]:
    side = board.side_to_move
    squares = board.squares
    moves: List[Move] = []
    for d in deltas:
        to = frm + d
        if not on_board(to):
            continue
        dst = squares[to]
        if dst == EMPTY or piece_color(dst) != side:
            moves.append(Move(frm, to))
    return moves


def slider_moves(board: Board, frm: int, deltas: tuple[int, ...]) -> List[Move]:
    side = board.side_to_move
    squares = board.squares
    moves: List[Move] = []
    for d in deltas:
        to = frm + d
        while on_board(to):
            dst = squares[to]
            if dst == EMPTY:
                moves.append(Move(frm, to))
                to += d
                continue
            # stop on first occupied
            if piece_color(dst) != side:
                moves.append(Move(frm, to))
            break
    return moves


def pawn_moves(board: Board, frm: int) -> List[Move]:
    side = board.side_to_move
    squares = board.squares
    moves: List[Move] = []

    forward = _rank_dist if side == WHITE else -_rank_dist
    start_rank = 1 if side == WHITE else 6
    last_rank = 7 if side == WHITE else 0

    one = frm + forward
    if on_board(one) and squares[one] == EMPTY:
        moves.extend(_promotions_or_single(frm, one, last_rank))

        # double push from start
        if (frm >> 4) == start_rank:
            two = one + forward
            if on_board(two) and squares[two] == EMPTY:
                moves.append(Move(frm, two, flags=FLAG_DOUBLE_PAWN))

    # captures
    for df in (-1, 1):
        to = one + df
        if not on_board(to):
            continue
        dst = squares[to]
        if dst != EMPTY and piece_color(dst) != side:
            moves.extend(_promotions_or_single(frm, to, last_rank, capture=True))

    # en passant
    ep = board.ep_square
    if ep != -1:
        file_delta = (ep & 7) - (frm & 7)
        rank_delta = (ep >> 4) - (frm >> 4)
        forward_step = 1 if side == WHITE else -1
        if abs(file_delta) == 1 and rank_delta == forward_step:
            # ensure the pawn behind ep square is enemy pawn (google sugges this but i dont understand why)
            behind = ep - _rank_dist if side == WHITE else ep + _rank_dist
            if on_board(behind):
                bp = squares[behind]
                if bp != EMPTY and piece_color(bp) != side and piece_type(bp) == PAWN:
                    moves.append(Move(frm, ep, flags=FLAG_EN_PASSANT))

    return moves


def _promotions_or_single(
    frm: int, to: int, last_rank: int, *, capture: bool = False
) -> List[Move]:
    to_rank = to >> 4
    if to_rank == last_rank:
        return [
            Move(frm, to, promo=QUEEN, flags=FLAG_PROMOTION),
            Move(frm, to, promo=ROOK, flags=FLAG_PROMOTION),
            Move(frm, to, promo=BISHOP, flags=FLAG_PROMOTION),
            Move(frm, to, promo=KNIGHT, flags=FLAG_PROMOTION),
        ]
    return [Move(frm, to)]


def castle_candidates(board: Board, king_from: int) -> List[Move]:
    side = board.side_to_move
    rights = board.castling_rights
    squares = board.squares
    moves: List[Move] = []

    # Squares
    e1, f1, g1, d1, c1, b1 = (
        rf_to_idx(4, 0),
        rf_to_idx(5, 0),
        rf_to_idx(6, 0),
        rf_to_idx(3, 0),
        rf_to_idx(2, 0),
        rf_to_idx(1, 0),
    )
    e8, f8, g8, d8, c8, b8 = (
        rf_to_idx(4, 7),
        rf_to_idx(5, 7),
        rf_to_idx(6, 7),
        rf_to_idx(3, 7),
        rf_to_idx(2, 7),
        rf_to_idx(1, 7),
    )

    if side == WHITE and king_from == e1:
        if (rights & WHITE_OO) and squares[f1] == EMPTY and squares[g1] == EMPTY:
            moves.append(Move(e1, g1, flags=FLAG_CASTLE))
        if (
            (rights & WHITE_OOO)
            and squares[d1] == EMPTY
            and squares[c1] == EMPTY
            and squares[b1] == EMPTY
        ):
            moves.append(Move(e1, c1, flags=FLAG_CASTLE))

    if side == BLACK and king_from == e8:
        if (rights & BLACK_OO) and squares[f8] == EMPTY and squares[g8] == EMPTY:
            moves.append(Move(e8, g8, flags=FLAG_CASTLE))
        if (
            (rights & BLACK_OOO)
            and squares[d8] == EMPTY
            and squares[c8] == EMPTY
            and squares[b8] == EMPTY
        ):
            moves.append(Move(e8, c8, flags=FLAG_CASTLE))

    return moves
