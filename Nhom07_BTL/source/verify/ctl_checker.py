# -*- coding: utf-8 -*-
"""
ctl_checker.py — Model checker CTL bằng thuật toán gán nhãn (labeling algorithm, giáo trình mục 1.9.2).

Khác với phần mềm của giảng viên (chỉ nhận 1 toán tử + 1 nhãn), bộ kiểm tra này nhận công thức
GHÉP và LỒNG NHAU, để kiểm chứng các thuộc tính dạng "nếu ... thì cuối cùng ...":
    AG(allocated -> AF(mem_clean))       AG(!(cb_locked & to_locked))      EF(payment_done | input_rejected)

Cú pháp:  atom | true | false | !f | f & g | f | g | f -> g | (f)
          AX(f) EX(f) AF(f) EF(f) AG(f) EG(f)
Ngữ nghĩa: K |= f  khi và chỉ khi  S0 ⊆ Sat(f)  (giống phần mềm của giảng viên).
"""
from __future__ import annotations

import re
from typing import Set, Tuple

TOKEN = re.compile(r"\s*(->|AX|EX|AF|EF|AG|EG|[A-Za-z_][A-Za-z0-9_]*|[!&|()])")
TEMPORAL = {"AX", "EX", "AF", "EF", "AG", "EG"}


def _tokens(text: str):
    pos, out = 0, []
    text = text.strip()
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"Ký tự không hợp lệ tại vị trí {pos}: {text[pos:]!r}")
        out.append(m.group(1))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, text):
        self.t, self.i = _tokens(text), 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def eat(self, tok=None):
        cur = self.peek()
        if tok is not None and cur != tok:
            raise ValueError(f"Mong đợi '{tok}', gặp '{cur}'")
        self.i += 1
        return cur

    def parse(self):
        node = self.implication()
        if self.peek() is not None:
            raise ValueError(f"Thừa ký hiệu: {self.t[self.i:]}")
        return node

    def implication(self):
        left = self.disj()
        if self.peek() == "->":
            self.eat()
            return ("->", left, self.implication())
        return left

    def disj(self):
        node = self.conj()
        while self.peek() == "|":
            self.eat()
            node = ("|", node, self.conj())
        return node

    def conj(self):
        node = self.unary()
        while self.peek() == "&":
            self.eat()
            node = ("&", node, self.unary())
        return node

    def unary(self):
        tok = self.peek()
        if tok == "!":
            self.eat()
            return ("!", self.unary())
        if tok in TEMPORAL:
            self.eat()
            self.eat("(")
            sub = self.implication()
            self.eat(")")
            return (tok, sub)
        if tok == "(":
            self.eat()
            sub = self.implication()
            self.eat(")")
            return sub
        if tok is None or not re.match(r"[A-Za-z_]", tok):
            raise ValueError(f"Mong đợi mệnh đề, gặp '{tok}'")
        self.eat()
        return ("atom", tok)


def parse(formula: str):
    return _Parser(formula).parse()


def is_tool_syntax(formula: str) -> bool:
    """True nếu công thức thuộc dạng phần mềm của giảng viên hiểu đúng: OP(p) hoặc OP(!p)."""
    return re.fullmatch(r"\s*(AX|EX|AF|EF|AG|EG)\(\s*!?\s*[A-Za-z_][A-Za-z0-9_]*\s*\)\s*", formula) is not None


class CTLChecker:
    def __init__(self, model):
        self.m = model
        self.S = set(model.states)

    def sat(self, node) -> Set[str]:
        op = node[0]
        m, S = self.m, self.S
        if op == "atom":
            if node[1] == "true":
                return set(S)
            if node[1] == "false":
                return set()
            return {s for s in S if node[1] in m.labels.get(s, set())}
        if op == "!":
            return S - self.sat(node[1])
        if op == "&":
            return self.sat(node[1]) & self.sat(node[2])
        if op == "|":
            return self.sat(node[1]) | self.sat(node[2])
        if op == "->":
            return (S - self.sat(node[1])) | self.sat(node[2])
        f = self.sat(node[1])
        if op == "EX":
            return {s for s in S if m.successors(s) & f}
        if op == "AX":
            return {s for s in S if m.successors(s) and m.successors(s) <= f}
        if op == "EF":                              # điểm bất động NHỎ NHẤT: Z = f ∪ EX Z
            z = set(f)
            while True:
                nz = z | {s for s in S if m.successors(s) & z}
                if nz == z:
                    return z
                z = nz
        if op == "AF":                              # điểm bất động NHỎ NHẤT: Z = f ∪ AX Z
            z = set(f)
            while True:
                nz = z | {s for s in S if m.successors(s) and m.successors(s) <= z}
                if nz == z:
                    return z
                z = nz
        if op == "EG":                              # điểm bất động LỚN NHẤT: Z = f ∩ EX Z
            z = set(f)
            while True:
                nz = {s for s in z if m.successors(s) & z}
                if nz == z:
                    return z
                z = nz
        if op == "AG":                              # AG f = ¬EF¬f
            return S - self.sat(("EF", ("!", node[1])))
        raise ValueError(f"Toán tử không hỗ trợ: {op}")

    def check(self, formula: str) -> Tuple[bool, Set[str]]:
        sat = self.sat(parse(formula))
        return set(self.m.initial_states) <= sat, sat

    def counterexample_AG(self, formula: str):
        """Với công thức AG(f) bị vi phạm: trả về đường đi ngắn nhất từ S0 tới 1 trạng thái không thỏa f."""
        node = parse(formula)
        if node[0] != "AG":
            return None
        bad = self.S - self.sat(node[1])
        best = None
        for s in sorted(bad):
            p = self.m.find_path(s)
            if p and (best is None or len(p) < len(best)):
                best = p
        return best
