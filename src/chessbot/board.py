from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

WHITE = 0
BLACK = 1

# (low 3 bits)
EMPTY = 0
PAWN = 1
KNIGHT = 2
BISHOP = 3
ROOK = 4
QUEEN = 5
KING = 6

# Castling rights mask bits
WHITE_OO = 1 << 0
WHITE_OOO = 1 << 1
BLACK_OO = 1 << 2
BLACK_OOO = 1 << 3

PROMO_MAP = {"q": 5, "r": 4, "b": 3, "n": 2}
PROMO_LETTER = {v: k for k, v in PROMO_MAP.items()}


def on_board(idx: int) -> bool:
    return (idx & 0x88) == 0


def rf_to_idx(file: int, rank: int) -> int:
    return (rank << 4) | file


def idx_to_rf(idx: int) -> tuple[int, int]:
    return (idx & 0x7, idx >> 4)


def idx_to_uci(idx: int) -> str:
    f, r = idx_to_rf(idx)
    return f"{chr(ord('a') + f)}{r + 1}"


def uci_to_idx(sq: str) -> int:
    f = ord(sq[0]) - ord("a")
    r = int(sq[1]) - 1
    return rf_to_idx(f, r)


def promo_suffix(ptype: int) -> str:
    return PROMO_LETTER.get(ptype, "")


def make_piece_idx(color: int, ptype: int) -> int:
    return (color << 3) | ptype


def piece_type(piece: int) -> int:
    return piece & 0b111


def piece_color(piece: int) -> int:
    return (piece >> 3) & 1


PIECE_CHARS = {
    make_piece_idx(WHITE, PAWN): "P",
    make_piece_idx(WHITE, KNIGHT): "N",
    make_piece_idx(WHITE, BISHOP): "B",
    make_piece_idx(WHITE, ROOK): "R",
    make_piece_idx(WHITE, QUEEN): "Q",
    make_piece_idx(WHITE, KING): "K",
    make_piece_idx(BLACK, PAWN): "p",
    make_piece_idx(BLACK, KNIGHT): "n",
    make_piece_idx(BLACK, BISHOP): "b",
    make_piece_idx(BLACK, ROOK): "r",
    make_piece_idx(BLACK, QUEEN): "q",
    make_piece_idx(BLACK, KING): "k",
    EMPTY: ".",
}

START_BACK_RANK = [ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK]


# practice with immutable type here, so i can fuck up less, but the logic got annoying so i fucked up more. maybe revert
@dataclass(frozen=True, slots=True)
class UndoSnapshot:
    frm: int
    to: int
    moved: int
    captured: int

    ep_square: int
    castling_rights: int
    # google says 50 move limit is a required rule
    halfmove_clock: int
    fullmove_number: int

    captured_square: int = -1
    rook_from: int = -1
    rook_to: int = -1


class Board:
    def __init__(self) -> None:
        # 0x88 board
        self.squares: List[int] = [EMPTY] * 128
        self.side_to_move: int = WHITE
        self.castling_rights: int = WHITE_OO | WHITE_OOO | BLACK_OO | BLACK_OOO
        # current en passant square
        self.ep_square: int = -1
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1
        self.reset()

    def reset(self) -> None:
        self.squares = [EMPTY] * 128
        for f, p in enumerate(START_BACK_RANK):
            self.squares[rf_to_idx(f, 0)] = make_piece_idx(WHITE, p)
        for f, p in enumerate(START_BACK_RANK):
            self.squares[rf_to_idx(f, 7)] = make_piece_idx(BLACK, p)
        for f in range(8):
            self.squares[rf_to_idx(f, 1)] = make_piece_idx(WHITE, PAWN)
            self.squares[rf_to_idx(f, 6)] = make_piece_idx(BLACK, PAWN)
        self.side_to_move = WHITE
        self.castling_rights = WHITE_OO | WHITE_OOO | BLACK_OO | BLACK_OOO
        self.ep_square = -1
        self.halfmove_clock = 0
        self.fullmove_number = 1

    def copy(self) -> "Board":
        b = Board()
        b.squares = self.squares.copy()
        b.side_to_move = self.side_to_move
        b.castling_rights = self.castling_rights
        b.ep_square = self.ep_square
        b.halfmove_clock = self.halfmove_clock
        b.fullmove_number = self.fullmove_number
        return b

    # text-based board (chat gpt wrote this)
    def ascii(self) -> str:
        rows: list[str] = []
        for r in range(7, -1, -1):
            row: list[str] = []
            for f in range(8):
                idx = rf_to_idx(f, r)
                row.append(PIECE_CHARS.get(self.squares[idx], "."))
            rows.append(f"{r+1}  " + " ".join(row))
        footer = "\n   " + " ".join(chr(ord("a") + f) for f in range(8))
        return "\n".join(rows) + "\n" + footer

    def __str__(self) -> str:
        return self.ascii()

    def make_move(
        self, frm: int, to: int, promo_type: int | None = None
    ) -> UndoSnapshot:
        moved = self.squares[frm]
        captured = self.squares[to]

        side = self.side_to_move
        ptype = piece_type(moved)

        is_pawn = ptype == PAWN
        is_double_push = is_pawn and abs((to - frm)) == 32 and (frm >> 4 in (1, 6))
        # google says king moves two spaces iff castles
        is_castle = (ptype == KING) and abs((to & 0b00000111) - (frm & 0b00000111)) == 2

        # google says en passant iff pawn moves to last valid ep square and capture is empty. im not sure how it could ever not be empty, but w/e
        is_ep_capture = is_pawn and (to == self.ep_square) and (captured == EMPTY)
        captured_square = -1
        if is_ep_capture:
            captured_square = to - 16 if side == WHITE else to + 16
            captured = self.squares[captured_square]

        rook_from = -1
        rook_to = -1
        if is_castle:
            rank = 0 if side == WHITE else 7
            # kingside if file is 6, queenside if 2
            if (to & 0x7) == 6:
                rook_from = rf_to_idx(7, rank)
                rook_to = rf_to_idx(5, rank)
            else:
                rook_from = rf_to_idx(0, rank)
                rook_to = rf_to_idx(3, rank)

        # snapshot state
        prev = UndoSnapshot(
            frm=frm,
            to=to,
            moved=moved,
            captured=captured,
            ep_square=self.ep_square,
            castling_rights=self.castling_rights,
            halfmove_clock=self.halfmove_clock,
            fullmove_number=self.fullmove_number,
            captured_square=captured_square,
            rook_from=rook_from,
            rook_to=rook_to,
        )

        # apply move
        if is_pawn or captured != EMPTY:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # clear en passant capture square
        if is_ep_capture:
            self.squares[captured_square] = EMPTY

        # move rook if castling
        if rook_from != -1:
            self.squares[rook_to] = self.squares[rook_from]
            self.squares[rook_from] = EMPTY

        # normal move
        self.squares[to] = moved
        self.squares[frm] = EMPTY

        # promotion (overwrite the moved piece on destination)
        if promo_type:
            color = piece_color(moved)
            self.squares[to] = make_piece_idx(color, promo_type)

        # update castling rights (clear bits if king/rook moved or rook captured)
        self._update_castling_rights(frm, to, moved, captured)

        # set new ep square
        if is_double_push:
            self.ep_square = frm + 16 if side == WHITE else frm - 16
        else:
            self.ep_square = -1

        if side == BLACK:
            self.fullmove_number += 1
        self.side_to_move ^= 1

        return prev

    def undo_move(self, prev: UndoSnapshot) -> None:
        self.side_to_move ^= 1

        # restore rook if castling
        if prev.rook_from != -1:
            self.squares[prev.rook_from] = self.squares[prev.rook_to]
            self.squares[prev.rook_to] = EMPTY

        # restore captured pawn square for en passant
        if prev.captured_square != -1:
            self.squares[prev.captured_square] = prev.captured
            self.squares[prev.to] = EMPTY
        else:
            # restore destination square to normal capture
            self.squares[prev.to] = prev.captured

        # restore normal move
        self.squares[prev.frm] = prev.moved
        self.ep_square = prev.ep_square
        self.castling_rights = prev.castling_rights
        self.halfmove_clock = prev.halfmove_clock
        self.fullmove_number = prev.fullmove_number

    # helpers
    def piece_at(self, idx: int) -> int:
        return self.squares[idx]

    # google says _ means "private"
    def _update_castling_rights(
        self,
        frm: int,
        to: int,
        moved: int,
        captured: int,
        captured_square: int = -1,
    ) -> None:

        rights = self.castling_rights

        a1 = rf_to_idx(0, 0)
        h1 = rf_to_idx(7, 0)
        a8 = rf_to_idx(0, 7)
        h8 = rf_to_idx(7, 7)

        mtype = piece_type(moved)
        mcol = piece_color(moved)

        # no if king moves
        if mtype == KING:
            if mcol == WHITE:
                rights &= ~(WHITE_OO | WHITE_OOO)
            else:
                rights &= ~(BLACK_OO | BLACK_OOO)

        # no if rook moves
        if mtype == ROOK:
            if mcol == WHITE:
                if frm == h1:
                    rights &= ~WHITE_OO
                elif frm == a1:
                    rights &= ~WHITE_OOO
            else:
                if frm == h8:
                    rights &= ~BLACK_OO
                elif frm == a8:
                    rights &= ~BLACK_OOO

        # no if rook captured
        if captured != EMPTY and piece_type(captured) == ROOK:
            cap_col = piece_color(captured)
            cap_sq = captured_square if captured_square != -1 else to

            if cap_col == WHITE:
                if cap_sq == h1:
                    rights &= ~WHITE_OO
                elif cap_sq == a1:
                    rights &= ~WHITE_OOO
            else:
                if cap_sq == h8:
                    rights &= ~BLACK_OO
                elif cap_sq == a8:
                    rights &= ~BLACK_OOO

        self.castling_rights = rights
