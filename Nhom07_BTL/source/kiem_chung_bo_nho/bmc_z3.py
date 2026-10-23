# -*- coding: utf-8 -*-
"""
bmc_z3.py — Bounded Model Checking bằng Z3 trên mô hình Kripke MỨC BỘ NHỚ (Nhóm 07).

Khác mô hình 35 trạng thái (mỗi trạng thái là một TÌNH HUỐNG do nhóm đặt tên, vd h1_tran_1_byte), ở đây
trạng thái là ẢNH CHỤP MÁY tại một thời điểm:

  K = (S, S0, R, L)
  S  : s = (pc, thanh ghi/biến, các ô nhớ). pc là dòng lệnh CPU sắp chạy; mỗi ô nhớ là một biến bit-vector
       của Z3 đúng độ rộng của máy (1 byte = 8 bit, int32 = 32 bit), nên phép cộng tràn quay vòng như CPU thật.
  S0 : MỌI trạng thái đầu có thể. Đầu vào (mã đơn, giá từng dòng, lịch chạy 2 worker) là biến TỰ DO của Z3:
       nhóm không chọn đầu vào nào cả — đây là chỗ khác function testing.
  R  : T(s, s') = ngữ nghĩa của MỘT lệnh tại s.pc (vòng lặp chép chuỗi: mỗi lần ghi 1 byte).
  L  : mệnh đề nguyên tử được TÍNH từ bộ nhớ, vd total_sai ≡ (4 byte của ô total ≠ 489000).

BMC (giáo trình mục 3.5): với k = 0, 1, 2, ... hỏi Z3 công thức
      I(s0) ∧ T(s0,s1) ∧ ... ∧ T(s(k-1),sk) ∧ Bad(sk)
  SAT   -> Z3 trả về phản ví dụ: đầu vào cụ thể + giá trị của MỌI ô nhớ ở MỌI bước (in ra từng bước).
  UNSAT -> không có lỗi trong k bước. Nếu thêm I ∧ T^k ∧ ¬KetThuc(sk) cũng UNSAT (mọi đường đi đã tới trạng
           thái kết thúc, tự lặp) thì không còn trạng thái mới: kết luận AN TOÀN là đầy đủ (completeness threshold).

Chạy (cần: pip install z3-solver):
    cd source/kiem_chung_bo_nho
    python bmc_z3.py                -> tất cả mô hình
    python bmc_z3.py H1             -> chỉ H1 (H1, H3, H6)
  Kết quả: màn hình + results/logs/bmc_z3.txt + results/xem_trang_thai_bo_nho.html (mở bằng trình duyệt)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

from z3 import (And, BitVecSort, BitVecVal, Bool, BoolSort, Concat, Const, If, Implies, Int, IntSort,
                Not, Or, Solver, SolverFor, UGE, UGT, ULE, ULT, is_true, sat, unsat)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
LOGS = os.path.join(ROOT, "results", "logs")
HTML_OUT = os.path.join(ROOT, "results", "xem_trang_thai_bo_nho.html")

BV8, BV32, BV64 = BitVecSort(8), BitVecSort(32), BitVecSort(64)


def B8(x):
    return BitVecVal(x, 8)


def ev(m, e):
    """Giá trị của biểu thức e trong phản ví dụ m (số nguyên Python)."""
    return m.eval(e, model_completion=True).as_long()


def giu(s, t, tru=()):
    """Các biến không nằm trong 'tru' giữ nguyên giá trị ở bước sau."""
    return And([t[x] == s[x] for x in s if x not in tru])


# =============================================================================================== khung chung
class MoHinh:
    ten = ""          # vd "H1-v0"
    tieu_de = ""
    ma = []           # [(pc, dòng mã C)] — để in và để biết lệnh tại pc
    bien = []         # [(tên, sort)] — biến trạng thái
    ket_thuc_pc = {}  # {pc: tên trạng thái kết thúc}
    thuoc_tinh = []   # các nhãn x cần kiểm AG(!x)
    dinh_nghia = {}   # S, S0, R, L dạng chữ để in
    logic = "QF_BV"   # lý thuyết SMT: bit-vector không lượng từ (H3 thêm mảng: QF_ABV)

    def tao(self, k):
        return {t: Const(f"{t}@{k}", srt) for t, srt in self.bien}

    def rang_buoc_vao(self):
        return []

    def nhan(self):
        """{nhãn: (mô tả, hàm s -> BoolRef)} — L(s) = {x | nhan[x](s) đúng}."""
        raise NotImplementedError

    def ten_pc(self, pc):
        if pc in self.ket_thuc_pc:
            return self.ket_thuc_pc[pc]
        return f"dòng {pc}"

    def lenh(self, pc):
        return dict(self.ma).get(pc, "").strip()

    def ket_thuc(self, s):
        return Or([s["pc"] == p for p in self.ket_thuc_pc])

    def uu_tien(self, x):
        """Các ràng buộc phụ thử thêm khi đã có phản ví dụ (xem chon_phan_vi_du)."""
        return []


# =============================================================================================== H1 — STACK
RET0 = 0x00007FF6A1B2C3D4      # giá trị minh họa của ô địa chỉ trả về
TONG_DON = 489000
KY_TU = "0-9, A-Z, '-'"


def _byte_le(v, n):
    return [(v >> (8 * j)) & 0xFF for j in range(n)]


class H1(MoHinh):
    """parse mã đơn vào OrderRecord {char order_id[N]; int32 total; int32 status;} + ô địa chỉ trả về.
    Bố cục byte giống hệt struct Khung của thanhtoan.c (offsetof in ra khi chạy ca 1)."""
    XONG, TU_CHOI, NHAY_LA = 90, 91, 92

    def __init__(self, v1):
        self.v1 = v1
        self.ten = "H1-v1" if v1 else "H1-v0"
        if v1:
            self.ID, self.OT, self.OS, self.OR, self.SIZE = 17, 20, 24, 32, 40
            self.tieu_de = "H1 — v1: buffer 17 byte + strnlen + từ chối (bản sửa)"
            self.ma = [(11, "size_t len = strnlen(raw, 17);"),
                       (12, "if (len > 16) return -1;      /* từ chối */"),
                       (13, "memcpy(r->order_id, raw, len + 1);"),
                       (14, "return 0;")]
        else:
            self.ID, self.OT, self.OS, self.OR, self.SIZE = 16, 16, 20, 24, 32
            self.tieu_de = "H1 — v0: strcpy(r->order_id, raw) với order_id[16] (CÓ LỖI)"
            self.ma = [(11, "strcpy(r->order_id, raw);"),
                       (12, "return 0;")]
        self.MAXL = self.SIZE - 1                      # mọi lần ghi đều nằm trong khung quan sát
        self.ket_thuc_pc = {self.XONG: "XONG", self.TU_CHOI: "TỪ_CHỐI", self.NHAY_LA: "NHẢY_LẠ"}
        self.bien = ([("pc", BV8), ("i", BV32), ("len", BV32)] +
                     [(f"m{j}", BV8) for j in range(self.SIZE)])
        self.L = Const("L", BV32)                                   # độ dài chuỗi đầu vào
        self.src = [Const(f"raw{j}", BV8) for j in range(self.MAXL + 1)]
        self.m0 = self._bo_nho_dau()
        self.thuoc_tinh = ["tran_bo_dem", "total_sai", "ret_bi_ghi_de", "nhay_la"]
        self.dinh_nghia = {
            "S": f"s = (pc, i, len, m[0..{self.SIZE - 1}]) — m[j] là 1 byte (BitVec 8) của khung stack: "
                 f"order_id[0..{self.ID - 1}] | total[{self.OT}..{self.OT + 3}] | status[{self.OS}..{self.OS + 3}] | "
                 f"ret[{self.OR}..{self.OR + 7}]",
            "S0": f"pc = 11, i = 0, order_id = rác 0xCC, total = 489000 (28 76 07 00), status = 0, ret = 0x{RET0:016X}; "
                  f"đầu vào raw[0..L] TỰ DO: 0 ≤ L ≤ {self.MAXL}, ký tự {KY_TU}, raw[L] = '\\0'",
            "R": ("pc=11: m[i] := raw[i]; nếu raw[i]=0 thì pc:=12 ngược lại i:=i+1   (strcpy = mỗi bước ghi 1 byte)\n"
                  "pc=12: pc := NHẢY_LẠ nếu m[ret] ≠ ret ban đầu, ngược lại XONG") if not self.v1 else
                 ("pc=11: len := min(L, 17); pc:=12      (strnlen chỉ ĐỌC)\n"
                  "pc=12: nếu len > 16 thì pc:=TỪ_CHỐI ngược lại pc:=13\n"
                  "pc=13: m[i] := raw[i]; nếu i = len thì pc:=14 ngược lại i:=i+1   (memcpy len+1 byte)\n"
                  "pc=14: pc := NHẢY_LẠ nếu m[ret] đổi, ngược lại XONG"),
            "L": "tran_bo_dem ≡ ∃ j ngoài order_id: m[j] ≠ m0[j];  total_sai ≡ int32(m[total]) ≠ 489000;  "
                 "ret_bi_ghi_de ≡ m[ret] ≠ ret ban đầu;  nhay_la ≡ pc = NHẢY_LẠ",
        }

    def _bo_nho_dau(self):
        m = [0xCC] * self.SIZE                                      # rác chưa khởi tạo (cả byte đệm)
        m[self.OT:self.OT + 4] = _byte_le(TONG_DON, 4)
        m[self.OS:self.OS + 4] = [0, 0, 0, 0]
        m[self.OR:self.OR + 8] = _byte_le(RET0, 8)
        return m

    def rang_buoc_vao(self):
        rb = [ULE(self.L, self.MAXL)]
        for j, c in enumerate(self.src):
            hop_le = Or(And(UGE(c, ord("0")), ULE(c, ord("9"))), And(UGE(c, ord("A")), ULE(c, ord("Z"))), c == ord("-"))
            rb.append(Implies(ULT(BitVecVal(j, 32), self.L), hop_le))
            rb.append(Implies(self.L == j, c == 0))
        return rb

    def uu_tien(self, x):
        # 1) có phản ví dụ nào mà mã đơn HỢP LỆ theo nghiệp vụ (≤ 16 ký tự) không?
        # 2) cho dễ đọc: ưu tiên chuỗi trùng chuỗi mẫu; bỏ đi thì Z3 chọn chuỗi bất kỳ, kết luận không đổi
        mau = ("DH20261015000123-QUA-DAI-" * 2)[:self.MAXL]
        giong_mau = And([Implies(ULT(j, self.L), self.src[j] == ord(c)) for j, c in enumerate(mau)])
        return [And(ULE(self.L, 16), giong_mau), giong_mau]

    def _doc_raw(self, i):
        e = BitVecVal(0, 8)
        for j in range(self.MAXL, -1, -1):
            e = If(i == j, self.src[j], e)
        return e

    def _ghi(self, s, t, i, c):
        return And([t[f"m{j}"] == If(i == j, c, s[f"m{j}"]) for j in range(self.SIZE)])

    def _ret_doi(self, s):
        return Or([s[f"m{j}"] != self.m0[j] for j in range(self.OR, self.OR + 8)])

    def I(self, s):
        return And([s["pc"] == 11, s["i"] == 0, s["len"] == 0] +
                   [s[f"m{j}"] == self.m0[j] for j in range(self.SIZE)])

    def T(self, s, t, k):
        dung_yen = giu(s, t)
        tra_ve = And(t["pc"] == If(self._ret_doi(s), B8(self.NHAY_LA), B8(self.XONG)), giu(s, t, ["pc"]))
        c = self._doc_raw(s["i"])
        if not self.v1:
            chep = And(self._ghi(s, t, s["i"], c),
                       t["i"] == If(c == 0, s["i"], s["i"] + 1),
                       t["pc"] == If(c == 0, B8(12), B8(11)), t["len"] == s["len"])
            return If(s["pc"] == 11, chep, If(s["pc"] == 12, tra_ve, dung_yen))
        do_dai = And(t["len"] == If(ULE(self.L, 17), self.L, BitVecVal(17, 32)), t["pc"] == 12,
                     giu(s, t, ["len", "pc"]))
        kiem = And(t["pc"] == If(UGT(s["len"], 16), B8(self.TU_CHOI), B8(13)), giu(s, t, ["pc"]))
        chep = And(self._ghi(s, t, s["i"], c),
                   t["i"] == If(s["i"] == s["len"], s["i"], s["i"] + 1),
                   t["pc"] == If(s["i"] == s["len"], B8(14), B8(13)), t["len"] == s["len"])
        return If(s["pc"] == 11, do_dai, If(s["pc"] == 12, kiem, If(s["pc"] == 13, chep,
                  If(s["pc"] == 14, tra_ve, dung_yen))))

    def nhan(self):
        ngoai = [j for j in range(self.SIZE) if j >= self.ID]
        total = lambda s: Concat(*[s[f"m{j}"] for j in range(self.OT + 3, self.OT - 1, -1)])   # noqa: E731
        return {
            "tran_bo_dem": ("có byte NGOÀI order_id bị đổi",
                            lambda s: Or([s[f"m{j}"] != self.m0[j] for j in ngoai])),
            "total_sai": ("ô total (tiền đơn) ≠ 489000 — mất độ chính xác", lambda s: total(s) != TONG_DON),
            "ret_bi_ghi_de": ("ô địa chỉ trả về bị đổi", self._ret_doi),
            "nhay_la": ("CPU return về địa chỉ do đầu vào quyết định", lambda s: s["pc"] == self.NHAY_LA),
            "tu_choi": ("đầu vào bị từ chối", lambda s: s["pc"] == self.TU_CHOI),
            "xong": ("kết thúc bình thường", lambda s: s["pc"] == self.XONG),
        }

    # ---- hiển thị
    def dau_vao(self, m):
        L = ev(m, self.L)
        raw = "".join(chr(ev(m, self.src[j])) for j in range(L))
        return {"chuỗi raw": f'"{raw}" (L = {L} ký tự = {L + 1} byte kể cả \\0)'}, f"tt_{self.ten[-2:]} 1 {raw}"

    def vung(self, gt):
        """gt: list giá trị byte -> các vùng để in."""
        def le(a, n):
            return sum(gt[a + j] << (8 * j) for j in range(n))
        tot = le(self.OT, 4)
        tot = tot - (1 << 32) if tot >= 1 << 31 else tot
        st = le(self.OS, 4)
        st = st - (1 << 32) if st >= 1 << 31 else st
        return [("order_id", 0, self.ID, None),
                ("total", self.OT, 4, f"= {tot:,} VND".replace(",", ".")),
                ("status", self.OS, 4, f"= {st}"),
                ("ret", self.OR, 8, f"= 0x{le(self.OR, 8):016X}")]

    def gia_tri(self, m, s):
        return [ev(m, s[f"m{j}"]) for j in range(self.SIZE)]

    def bien_hien(self, m, s):
        d = {"i": ev(m, s["i"])}
        if self.v1:
            d["len"] = ev(m, s["len"])
        return d


# =============================================================================================== H3 — int32
HAN_MUC = 2_000_000_000
MAX_DONG, MAX_GIA = 100, 50_000_000


def quay_vong(v, W):
    """Phép cộng của CPU trên ô W bit có dấu: kết quả toán học v được đưa về [-2^(W-1), 2^(W-1)) theo mod 2^W."""
    M, H = 2 ** W, 2 ** (W - 1)
    return If(v >= H, v - M, If(v < -H, v + M, v))


class H3(MoHinh):
    """Ô total int32 (v0) / int64 (v1). Giá trị ô nhớ được mô hình bằng số nguyên + phép quay vòng mod 2^W,
    đúng bằng phép cộng bù 2 của CPU (Z3 giải số học tuyến tính nhanh hơn bit-blast 43 phép cộng 32 bit)."""
    XONG, TU_CHOI = 90, 91

    def __init__(self, v1):
        self.v1 = v1
        self.ten = "H3-v1" if v1 else "H3-v0"
        self.logic = None
        self.W = 64 if v1 else 32
        if v1:
            self.tieu_de = "H3 — v1: int64_t total + kiểm tra hạn mức trước khi cộng (bản sửa)"
            self.ma = [(21, "for (i = 0; i < n; i++) { if (total + dong[i] > HAN_MUC) return TU_CHOI; "
                            "total += dong[i]; }"),
                       (24, "return total;")]
        else:
            self.tieu_de = "H3 — v0: int32_t total; total += dong[i] (CÓ LỖI)"
            self.ma = [(21, "for (i = 0; i < n; i++) total += dong[i];"),
                       (24, "return total;")]
        self.ket_thuc_pc = {self.XONG: "XONG", self.TU_CHOI: "TỪ_CHỐI"}
        self.bien = [("pc", IntSort()), ("i", IntSort()), ("total", IntSort()), ("dung", IntSort())]
        self.n = Int("n")
        self.x = []                                       # x[k] = dong[i] đọc ở bước k (đầu vào tự do)
        self.thuoc_tinh = ["mat_chinh_xac", "tong_am"]
        self.dinh_nghia = {
            "S": f"s = (pc, i, total, dung) — total là ô nhớ {self.W} bit có dấu, chỉ chứa được "
                 f"[-2^{self.W - 1}, 2^{self.W - 1} - 1]; dung là BIẾN MA giữ tổng toán học, chỉ để so sánh "
                 "(không có trong chương trình)",
            "S0": f"pc = 21, i = 0, total = 0, dung = 0; đầu vào TỰ DO: 1 ≤ n ≤ {MAX_DONG}, "
                  f"mỗi dong[i] ∈ [0, 50.000.000] (CON-03) — mỗi dòng chỉ đọc 1 lần nên mỗi lần đọc là 1 biến "
                  "tự do của Z3",
            "R": ("pc=21: nếu i < n thì total := (total + dong[i]) quay vòng mod 2^32 (lệnh add của CPU), "
                  "dung := dung + dong[i], i := i + 1; ngược lại pc := 24\npc=24: pc := XONG") if not self.v1 else
                 ("pc=21: nếu i ≥ n thì pc:=24; nếu total + dong[i] > 2.000.000.000 thì pc:=TỪ_CHỐI; ngược lại "
                  "total := (total + dong[i]) mod 2^64, dung := dung + dong[i], i := i + 1\npc=24: pc := XONG"),
            "L": "mat_chinh_xac ≡ giá trị trong ô total ≠ dung (ô nhớ không còn chứa đúng số tiền);  "
                 "tong_am ≡ total < 0",
        }

    def rang_buoc_vao(self):
        return [1 <= self.n, self.n <= MAX_DONG]

    def I(self, s):
        return And(s["pc"] == 21, s["i"] == 0, s["total"] == 0, s["dung"] == 0)

    def T(self, s, t, k):
        x = Int(f"dong_doc@{k}")
        self.x.append(x)
        cong = And(t["total"] == quay_vong(s["total"] + x, self.W), t["dung"] == s["dung"] + x,
                   t["i"] == s["i"] + 1, t["pc"] == 21)
        het = And(t["pc"] == 24, giu(s, t, ["pc"]))
        if self.v1:
            vong = If(s["i"] >= self.n, het,
                      If(s["total"] + x > HAN_MUC, And(t["pc"] == self.TU_CHOI, giu(s, t, ["pc"])), cong))
        else:
            vong = If(s["i"] < self.n, cong, het)
        return And(0 <= x, x <= MAX_GIA,
                   If(s["pc"] == 21, vong, If(s["pc"] == 24, And(t["pc"] == self.XONG, giu(s, t, ["pc"])), giu(s, t))))

    bat_bien_mo_ta = "Inv(s) ≡ total = dung ∧ 0 ≤ total ≤ 2.000.000.000 ∧ i ≥ 0"

    def bat_bien(self, s):
        """Bất biến quy nạp của v1: ô total luôn đúng bằng tổng toán học và không vượt hạn mức."""
        return And(s["total"] == s["dung"], 0 <= s["total"], s["total"] <= HAN_MUC, 0 <= s["i"],
                   Or([s["pc"] == p for p in (21, 24, self.XONG, self.TU_CHOI)]))

    def nhan(self):
        return {
            "mat_chinh_xac": ("ô total không còn chứa đúng tổng tiền", lambda s: s["total"] != s["dung"]),
            "tong_am": ("tổng tiền âm", lambda s: s["total"] < 0),
            "tu_choi": ("đơn bị từ chối", lambda s: s["pc"] == self.TU_CHOI),
            "xong": ("kết thúc bình thường", lambda s: s["pc"] == self.XONG),
        }

    def uu_tien(self, x):
        # đơn có đúng k dòng (k = độ dài phản ví dụ); cho dễ đọc thì ưu tiên mọi dòng cùng giá 50.000.000
        dung_k = self.n == len(self.x)
        return [And(dung_k, *[d == MAX_GIA for d in self.x]), dung_k]

    def dau_vao(self, m):
        g = [ev(m, d) for d in self.x]
        n = len(g)
        if len(set(g)) == 1:
            lenh = f"tt_{self.ten[-2:]} 3 {g[0]} {n}"
        else:
            lenh = f"tt_{self.ten[-2:]} 3 " + ",".join(map(str, g))
        tom = ", ".join(f"{x:,}".replace(",", ".") for x in g[:4]) + (", ..." if n > 4 else "")
        return {"n": str(ev(m, self.n)), f"dong[0..{n - 1}]": tom,
                "tổng toán học": f"{sum(g):,}".replace(",", ".")}, lenh

    def vung(self, gt):
        v = sum(gt[j] << (8 * j) for j in range(self.W // 8))
        v = v - (1 << self.W) if v >= 1 << (self.W - 1) else v
        return [("total", 0, self.W // 8, f"= {v:,}".replace(",", "."))]

    def gia_tri(self, m, s):
        return _byte_le(ev(m, s["total"]) % (1 << self.W), self.W // 8)

    def bien_hien(self, m, s):
        return {"i": ev(m, s["i"]), "dung (biến ma)": f'{ev(m, s["dung"]):,}'.replace(",", ".")}


# =============================================================================================== H6 — heap
TT = ["OPEN", "PAID", "CANCELLED", "CLOSED"]


class H6(MoHinh):
    """2 worker (C = callback, T = timeout) cùng đóng 1 phiên s; mọi thứ tự xen kẽ do Z3 chọn."""

    def __init__(self, v1):
        self.v1 = v1
        self.ten = "H6-v1" if v1 else "H6-v0"
        if v1:
            self.tieu_de = "H6 — v1: mutex + kiểm tra CLOSED + explicit_bzero (bản sửa)"
            self.ops = [("lock", None, "lock(&s->mtx);"), ("if_closed", 7, "if (s->status == CLOSED) goto 7;"),
                        ("status", None, "s->status = V;"), ("bzero", None, "explicit_bzero(s->card, 16);"),
                        ("free_card", None, "free(s->card);"), ("status", 3, "s->status = CLOSED;"),
                        ("unlock", None, "unlock(&s->mtx);")]
            self.vung_gang = set(range(2, 8))          # đang giữ phiên: sau lock, trước unlock
        else:
            self.tieu_de = "H6 — v0: không khóa, memset rồi free 2 lần (CÓ LỖI)"
            self.ops = [("status", None, "s->status = V;"), ("memset", None, "memset(s->card, 0, 16);"),
                        ("free_card", None, "free(s->card);"), ("free_s", None, "free(s);")]
            self.vung_gang = {2, 3, 4}
        self.RET = len(self.ops) + 1
        self.ma = [(j + 1, o[2]) for j, o in enumerate(self.ops)] + [(self.RET, "return;")]
        self.ket_thuc_pc = {}
        self.bien = [("cb", BV8), ("to", BV8), ("khoa", BV8), ("status", BV8),
                     ("s_ok", BoolSort()), ("card_ok", BoolSort()), ("con_the", BoolSort()), ("loi", BV8)]
        self.chon, self.bo = {}, {}
        self.thuoc_tinh = ["race", "double_free", "use_after_free", "secret_residue"]
        self.dinh_nghia = {
            "S": "s = (pcC, pcT, khóa, status, valid_map[s], valid_map[card], card còn số thẻ, lỗi) — "
                 "valid_map[p] = 1 khi vùng heap p đã cấp phát và chưa free (giáo trình mục 3.6)",
            "S0": "pcC = pcT = 1, khóa trống, status = OPEN, valid_map[s] = valid_map[card] = 1, card chứa số thẻ",
            "R": "mỗi bước BỘ LẬP LỊCH chọn C hoặc T (biến tự do chon@k của Z3) chạy MỘT lệnh:\n" +
                 "\n".join(f"  dòng {j + 1}: {o[2]}" for j, o in enumerate(self.ops)) +
                 "\n  free(p) khi valid_map[p] = 0 -> lỗi double_free; đọc/ghi *p khi valid_map[p] = 0 -> use_after_free"
                 + ("\n  memset ngay trước free có thể bị trình biên dịch BỎ (biến tự do bo@k)" if not self.v1 else ""),
            "L": "race ≡ cả C và T cùng ở giữa thao tác trên phiên;  double_free, use_after_free ≡ lệnh vừa chạy vi phạm "
                 "valid_map;  secret_residue ≡ valid_map[card] = 0 ∧ card còn số thẻ",
        }

    def ten_pc(self, pc):
        return "xong" if pc == self.RET else f"dòng {pc}"

    def uu_tien(self, x):
        # phản ví dụ không cần trình biên dịch bỏ memset thì lấy loại đó (giống bản biên dịch -O0 khi phát lại)
        return [] if x == "secret_residue" else [And([Not(b) for b in self.bo.values()])]

    def ket_thuc(self, s):
        return Or(s["loi"] != 0, And(s["cb"] == self.RET, s["to"] == self.RET))

    def I(self, s):
        return And(s["cb"] == 1, s["to"] == 1, s["khoa"] == 0, s["status"] == 0, s["s_ok"], s["card_ok"],
                   s["con_the"], s["loi"] == 0)

    def _buoc(self, s, t, w, wid, V, bo):
        """Worker w chạy lệnh tại pc của nó. Trả về (điều kiện được chạy, ràng buộc trạng thái sau)."""
        pc = s[w]
        nhanh = []
        for j, (op, arg, _) in enumerate(self.ops, 1):
            tiep = t[w] == j + 1
            loi = lambda kieu: And(t["loi"] == kieu, giu(s, t, ["loi"]))   # noqa: E731
            if op == "status":
                hq = If(s["s_ok"], And(tiep, t["status"] == (arg if arg is not None else V),
                                       giu(s, t, [w, "status"])), loi(2))
            elif op == "memset":
                hq = If(Not(s["s_ok"]), loi(2), If(Not(s["card_ok"]), loi(2),
                        And(tiep, t["con_the"] == And(bo, s["con_the"]), giu(s, t, [w, "con_the"]))))
            elif op == "bzero":
                hq = If(Not(s["card_ok"]), loi(2), And(tiep, Not(t["con_the"]), giu(s, t, [w, "con_the"])))
            elif op == "free_card":
                hq = If(Not(s["s_ok"]), loi(2), If(Not(s["card_ok"]), loi(1),
                        And(tiep, Not(t["card_ok"]), giu(s, t, [w, "card_ok"]))))
            elif op == "free_s":
                hq = If(Not(s["s_ok"]), loi(1), And(tiep, Not(t["s_ok"]), giu(s, t, [w, "s_ok"])))
            elif op == "lock":
                hq = And(tiep, t["khoa"] == wid, giu(s, t, [w, "khoa"]))
            elif op == "unlock":
                hq = And(tiep, t["khoa"] == 0, giu(s, t, [w, "khoa"]))
            elif op == "if_closed":
                hq = And(t[w] == If(s["status"] == 3, B8(arg), B8(j + 1)), giu(s, t, [w]))
            else:
                raise ValueError(op)
            nhanh.append((j, op, hq))
        duoc = And(pc != self.RET, Or([And(pc == j, s["khoa"] == 0) if op == "lock" else pc == j
                                       for j, op, _ in nhanh]))
        hq = And([Implies(pc == j, h) for j, _, h in nhanh])
        return duoc, hq

    def T(self, s, t, k):
        self.chon[k] = Bool(f"chon_C@{k}")
        self.bo[k] = Bool(f"bo_memset@{k}")
        dc, hc = self._buoc(s, t, "cb", 1, 1, self.bo[k])
        dt, ht = self._buoc(s, t, "to", 2, 2, self.bo[k])
        return If(self.ket_thuc(s), giu(s, t),
                  Or(And(self.chon[k], dc, hc), And(Not(self.chon[k]), dt, ht)))

    def nhan(self):
        return {
            "race": ("C và T cùng đang thao tác trên phiên",
                     lambda s: And(Or([s["cb"] == j for j in self.vung_gang]), Or([s["to"] == j for j in self.vung_gang]))),
            "double_free": ("free vùng đã free", lambda s: s["loi"] == 1),
            "use_after_free": ("đọc/ghi vùng đã free", lambda s: s["loi"] == 2),
            "secret_residue": ("card đã free nhưng số thẻ còn trong heap", lambda s: And(Not(s["card_ok"]), s["con_the"])),
            "xong": ("2 worker xong", lambda s: And(s["cb"] == self.RET, s["to"] == self.RET, s["loi"] == 0)),
        }

    def dau_vao(self, m):
        return {}, None

    def lich(self, m, k):
        """Chuỗi C/T: worker nào chạy ở từng bước của phản ví dụ."""
        return "".join("C" if is_true(m.eval(self.chon[j], model_completion=True)) else "T" for j in range(k))

    def bien_hien(self, m, s):
        g = lambda x: m.eval(s[x], model_completion=True)   # noqa: E731
        loi = ev(m, s["loi"])
        return {"pcC": self.ten_pc(ev(m, s["cb"])), "pcT": self.ten_pc(ev(m, s["to"])),
                "khóa": {0: "-", 1: "C", 2: "T"}[ev(m, s["khoa"])], "status": TT[ev(m, s["status"])],
                "valid_map[s]": int(is_true(g("s_ok"))), "valid_map[card]": int(is_true(g("card_ok"))),
                "card": "CÒN số thẻ" if is_true(g("con_the")) else "đã xóa",
                "lỗi": {0: "-", 1: "DOUBLE FREE", 2: "USE-AFTER-FREE"}[loi]}


# =============================================================================================== BMC
def bmc(mh, kmax, out):
    """Chạy BMC cho mọi thuộc tính AG(!x) của mô hình. Trả về {x: kết quả}."""
    p = lambda *a: print(*a, file=out)   # noqa: E731
    nhan = mh.nhan()
    sv = SolverFor(mh.logic) if mh.logic else Solver()     # QF_BV: bộ giải chuyên cho bit-vector
    S = [mh.tao(0)]
    sv.add(mh.rang_buoc_vao())
    sv.add(mh.I(S[0]))
    con = list(mh.thuoc_tinh)
    kq = {}
    t0 = time.time()
    for k in range(kmax + 1):
        sv.push()
        sv.add(Or([nhan[x][1](S[k]) for x in con]))          # có thuộc tính nào bị vi phạm ở bước k không?
        co_loi = sv.check() == sat
        sv.pop()
        if co_loi:
            for x in list(con):
                sv.push()
                sv.add(nhan[x][1](S[k]))
                if sv.check() == sat:
                    kq[x] = {"ket_qua": "VI PHẠM", "k": k,
                             "vet": trich_vet(mh, chon_phan_vi_du(sv, mh, x), S, k, nhan)}
                    con.remove(x)
                sv.pop()
        if not con:
            break
        sv.push()
        sv.add(Not(mh.ket_thuc(S[k])))
        het = sv.check() == unsat
        sv.pop()
        if het:
            for x in con:
                kq[x] = {"ket_qua": "AN TOÀN", "k": k,
                         "ly_do": f"k = {k}: I ∧ T^{k} ∧ ¬KếtThúc UNSAT — mọi đường đi đã dừng, không còn trạng thái mới "
                                  f"(completeness threshold), và Bad UNSAT ở mọi k ≤ {k}"}
            con = []
            break
        S.append(mh.tao(k + 1))
        sv.add(mh.T(S[k], S[k + 1], k))
    for x in con:
        kq[x] = {"ket_qua": "CHƯA KẾT LUẬN", "k": kmax}
    p(f"  (Z3 giải xong trong {time.time() - t0:.1f} giây)")
    return kq


def chon_phan_vi_du(sv, mh, x):
    """Đã biết SAT. Thử lần lượt các câu hỏi phụ của mô hình (vd 'có phản ví dụ với mã đơn HỢP LỆ ≤ 16 ký tự
    không?'); câu nào SAT thì lấy phản ví dụ đó. Chỉ chọn trong các phản ví dụ, không đổi kết luận."""
    for rb in mh.uu_tien(x):
        sv.push()
        sv.add(rb)
        if sv.check() == sat:
            m = sv.model()
            sv.pop()
            return m
        sv.pop()
    sv.check()
    return sv.model()


def quy_nap(mh, kq, p):
    """Chứng minh quy nạp (k-induction với k = 1) cho các thuộc tính BMC chưa kết luận:
         (1) I(s) ⇒ Inv(s)    (2) Inv(s) ∧ T(s,t) ⇒ Inv(t)    (3) Inv(s) ⇒ ¬Bad(s)
    Cả 3 đúng thì AG(!Bad) đúng trên MỌI đường đi, không phụ thuộc độ sâu k (kể cả n không giới hạn)."""
    s, t = mh.tao("s"), mh.tao("t")
    nhan = mh.nhan()

    def dung(*f):
        sv = Solver()
        sv.add(mh.rang_buoc_vao())
        sv.add(*f)
        return sv.check() == unsat

    b1 = dung(mh.I(s), Not(mh.bat_bien(s)))
    b2 = dung(mh.bat_bien(s), mh.T(s, t, "quy_nap"), Not(mh.bat_bien(t)))
    dong = [f"Chứng minh quy nạp với bất biến {mh.bat_bien_mo_ta}:",
            f"  (1) I ⇒ Inv            : {'ĐÚNG' if b1 else 'SAI'} (Z3: I ∧ ¬Inv {'UNSAT' if b1 else 'SAT'})",
            f"  (2) Inv ∧ T ⇒ Inv'     : {'ĐÚNG' if b2 else 'SAI'} (Z3: Inv ∧ T ∧ ¬Inv' {'UNSAT' if b2 else 'SAT'})"]
    for x, r in kq.items():
        if r["ket_qua"] != "CHƯA KẾT LUẬN":
            continue
        b3 = dung(mh.bat_bien(s), nhan[x][1](s))
        dong.append(f"  (3) Inv ⇒ ¬{x:13s}: {'ĐÚNG' if b3 else 'SAI'} (Z3: Inv ∧ {x} {'UNSAT' if b3 else 'SAT'})")
        if b1 and b2 and b3:
            r["ket_qua"] = "AN TOÀN"
            r["ly_do"] = (f"BMC không thấy lỗi tới k = {r['k']}; chứng minh quy nạp với {mh.bat_bien_mo_ta} "
                          "cho thấy AG(!" + x + ") đúng với MỌI độ dài đường đi")
    dong.append("  => (1)(2)(3) đều đúng: thuộc tính đúng ở mọi trạng thái đạt tới được, không cần duyệt hết k")
    kq[mh.thuoc_tinh[0]]["quy_nap"] = dong


def trich_vet(mh, m, S, k, nhan):
    """Đọc từ mô hình Z3 giá trị mọi biến ở mọi bước 0..k -> danh sách trạng thái để in/xuất HTML."""
    vet, truoc = [], None
    for j in range(k + 1):
        s = S[j]
        st = {"buoc": j, "nhan": [x for x, (_, f) in nhan.items() if is_true(m.eval(f(s), model_completion=True))]}
        if isinstance(mh, H6):
            st["bien"] = mh.bien_hien(m, s)
            if j > 0:
                w = "C" if is_true(m.eval(mh.chon[j - 1], model_completion=True)) else "T"
                pc_truoc = vet[-1]["_pc_" + w]
                if pc_truoc == mh.RET or vet[-1]["_loi"]:
                    st["canh"] = "(tự lặp)"
                else:
                    st["canh"] = f"{w} chạy {mh.ten_pc(pc_truoc)}: {mh.lenh(pc_truoc)}"
                    if mh.ops[pc_truoc - 1][0] == "memset" and is_true(m.eval(mh.bo[j - 1], model_completion=True)) \
                            and "use_after_free" not in st["nhan"]:
                        st["canh"] += "  ← trình biên dịch đã BỎ lệnh này"
            st["_pc_C"], st["_pc_T"], st["_loi"] = ev(m, s["cb"]), ev(m, s["to"]), ev(m, s["loi"])
            st["pc"] = f'C:{mh.ten_pc(st["_pc_C"])} T:{mh.ten_pc(st["_pc_T"])}'
            # tên của chính trạng thái này trong đồ thị Kripke tường minh (verify/mo_hinh_bo_nho.py)
            ten = (f"cb{st['_pc_C']}_to{st['_pc_T']}_k{['0', 'cb', 'to'][ev(m, s['khoa'])]}_"
                   f"{['mo', 'tt', 'huy', 'dong'][ev(m, s['status'])]}_s{int(is_true(m.eval(s['s_ok'], model_completion=True)))}"
                   f"c{int(is_true(m.eval(s['card_ok'], model_completion=True)))}"
                   f"t{int(is_true(m.eval(s['con_the'], model_completion=True)))}")
            if st["_loi"] and j > 0:
                ten += ("_df_" if st["_loi"] == 1 else "_uaf_") + ("cb" if w == "C" else "to") + str(st["_pc_" + w])
            st["ten_kripke"] = ten
        else:
            pc = ev(m, s["pc"])
            gt = mh.gia_tri(m, s)
            st["pc"] = mh.ten_pc(pc)
            st["lenh"] = mh.lenh(pc)
            st["bien"] = mh.bien_hien(m, s)
            st["vung"] = []
            for ten, a, n, giai in mh.vung(gt):
                st["vung"].append({"ten": ten, "off": a, "o": [f"{gt[a + q]:02X}" for q in range(n)],
                                   "doi": [truoc is not None and gt[a + q] != truoc[a + q] for q in range(n)],
                                   "giai_ma": giai})
            if j > 0:
                pc_truoc = vet[-1]["_pc"]
                doi = [q for q in range(len(gt)) if gt[q] != truoc[q]]
                st["canh"] = f"{mh.ten_pc(pc_truoc)}: {mh.lenh(pc_truoc)}"
                if isinstance(mh, H3) and pc_truoc == 21 and j - 1 < len(mh.x):
                    st["canh"] = f"dòng 21: total += dong[{j - 1}]   (dong[{j - 1}] = {ev(m, mh.x[j - 1]):,})".replace(",", ".")
                    doi = []
                if doi:
                    st["canh"] += "  — ghi " + ", ".join(f"ô [{q}] = {gt[q]:02X}" for q in doi)
            st["_pc"] = pc
            truoc = gt
        vet.append(st)
    vao, lenh = mh.dau_vao(m)
    if isinstance(mh, H6):
        lenh = f"tt_{mh.ten[-2:]} 4 {mh.lich(m, k)}"
    return {"dau_vao": vao, "phat_lai": lenh, "trang_thai": [{x: v for x, v in st.items() if not x.startswith("_")}
                                                              for st in vet]}


# =============================================================================================== in kết quả
def in_mo_hinh(mh, p):
    p(f"\n{'=' * 110}\n{mh.tieu_de}\n{'=' * 110}")
    for so, dong in mh.ma:
        p(f"   {so:3d} | {dong}")
    p("  Cấu trúc Kripke K = (S, S0, R, L):")
    for x in ("S", "S0", "R", "L"):
        dong = mh.dinh_nghia[x].split("\n")
        p(f"    {x:2s} : {dong[0]}")
        for d in dong[1:]:
            p(f"         {d}")


def in_vet(mh, kq, p):
    vet = kq["vet"]
    for x, v in vet["dau_vao"].items():
        p(f"      đầu vào Z3 chọn: {x} = {v}")
    if vet["phat_lai"]:
        p(f"      phát lại trên chương trình C thật:  build\\{vet['phat_lai'].split()[0]}.exe {' '.join(vet['phat_lai'].split()[1:])}")
    tt = vet["trang_thai"]
    n = len(tt)
    for j, st in enumerate(tt):
        if 3 <= j < n - 3 and n > 10:
            if j == 3:
                p(f"        ...  (bỏ qua {n - 6} bước giữa — xem đủ trong file HTML)")
            continue
        nhan = ",".join(x for x in st["nhan"] if x not in ("xong",)) or "-"
        if "vung" in st:
            o = " | ".join(f"{v['ten']}=" + " ".join(f"[{b}]" if d else b for b, d in zip(v["o"], v["doi"]))
                           + (f" {v['giai_ma']}" if v["giai_ma"] and v["ten"] != "ret" else "") for v in st["vung"])
            p(f"      s{j:<3d} pc={st['pc']:<8s} {o}")
            if st.get("canh"):
                p(f"           ↑ R: {st['canh']}")
            p(f"           L(s{j}) = {{{nhan}}}   {st['bien']}")
        else:
            b = st["bien"]
            p(f"      s{j:<3d} pcC={b['pcC']:<7s} pcT={b['pcT']:<7s} khóa={b['khóa']} status={b['status']:<9s} "
              f"valid_map[s]={b['valid_map[s]']} valid_map[card]={b['valid_map[card]']} card={b['card']:<9s} "
              f"L={{{nhan}}}" + (f"   ← {st['canh']}" if st.get("canh") else ""))


def main():
    chon = sys.argv[1:] or ["H1", "H3", "H6"]
    buf = io.StringIO()
    p = lambda *a: print(*a, file=buf)   # noqa: E731
    p("BMC BẰNG Z3 TRÊN MÔ HÌNH KRIPKE MỨC BỘ NHỚ — Nhóm 07")
    p("Trạng thái = (pc, biến, từng ô nhớ dạng bit-vector). Đầu vào là biến tự do: Z3 xét MỌI đầu vào cùng lúc.")
    p("Bad(s) là mệnh đề nguyên tử tính từ bộ nhớ. VI PHẠM = Z3 tìm được đường đi k bước tới trạng thái xấu.")
    lop = {"H1": (H1, 60, 60), "H3": (H3, 60, 45), "H6": (H6, 40, 40)}   # (lớp, kmax v0, kmax v1)
    du_lieu, log = [], []
    for ten in chon:
        cls, k0, k1 = lop[ten.upper()]
        for v1 in (False, True):
            mh = cls(v1)
            in_mo_hinh(mh, p)
            kq = bmc(mh, k1 if v1 else k0, buf)
            if getattr(mh, "v1", False) and hasattr(mh, "bat_bien") and any(r["ket_qua"] == "CHƯA KẾT LUẬN" for r in kq.values()):
                quy_nap(mh, kq, p)
            p("  Kết quả BMC (k = số lệnh CPU đã chạy):")
            for x in mh.thuoc_tinh:
                r = kq[x]
                if r["ket_qua"] == "VI PHẠM":
                    p(f"    AG(!{x:15s}) VI PHẠM ở k = {r['k']}   ({mh.nhan()[x][0]})")
                    trung = [y for y in mh.thuoc_tinh[:mh.thuoc_tinh.index(x)]
                             if kq[y]["ket_qua"] == "VI PHẠM" and kq[y]["vet"] == r["vet"]]
                    if trung:
                        p(f"      (cùng phản ví dụ với AG(!{trung[0]}) ở trên)")
                    else:
                        in_vet(mh, r, p)
                elif r["ket_qua"] == "AN TOÀN":
                    p(f"    AG(!{x:15s}) AN TOÀN — {r['ly_do']}")
                else:
                    p(f"    AG(!{x:15s}) CHƯA KẾT LUẬN trong k ≤ {r['k']}")
            if "quy_nap" in kq.get(mh.thuoc_tinh[0], {}):
                for d in kq[mh.thuoc_tinh[0]]["quy_nap"]:
                    p(f"      {d}")
            du_lieu.append({"ten": mh.ten, "tieu_de": mh.tieu_de, "ma": mh.ma, "dinh_nghia": mh.dinh_nghia,
                            "nhan": {x: d for x, (d, _) in mh.nhan().items()}, "thuoc_tinh": mh.thuoc_tinh,
                            "ket_qua": kq, "loai": "heap" if isinstance(mh, H6) else "bo_nho",
                            "do_thi": do_thi_h6(v1) if isinstance(mh, H6) else None})
            print(buf.getvalue(), end="", flush=True)        # in ngay từng mô hình
            log.append(buf.getvalue())
            buf.seek(0)
            buf.truncate()
    if {t.upper() for t in chon} != set(lop):
        # chạy một phần (vd lúc demo): giữ nguyên log và trang HTML đầy đủ của lần chạy toàn bộ trước đó
        print(f"\n(Chạy một phần nên không ghi đè log và trang HTML; chạy 'python bmc_z3.py' để cập nhật cả hai)")
        print(f"(Trang xem trạng thái: {HTML_OUT})")
        return
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "bmc_z3.txt"), "w", encoding="utf-8") as fh:
        fh.write("".join(log))
    ghi_html(du_lieu)
    print(f"\n(Đã ghi {os.path.join(LOGS, 'bmc_z3.txt')})")
    print(f"(Mở trang xem trạng thái: {HTML_OUT})")


def do_thi_h6(v1):
    """Đồ thị Kripke TƯỜNG MINH của H6 (liệt kê hết S và R bằng BFS) — dùng lại verify/mo_hinh_bo_nho.py
    của nhóm, cùng ngữ nghĩa với mô hình Z3 ở trên. Trang HTML vẽ đồ thị này và tô đường đi BMC tìm ra."""
    sys.path.insert(0, os.path.join(ROOT, "source", "verify"))
    import mo_hinh_bo_nho as tm
    ban = tm.H6_BAN[2 if v1 else 0]
    d, ds = tm.sinh_kripke(tm.H6_DAU, tm._buoc_h6(ban), tm._ten_h6, lambda st: tm._nhan_h6(st, ban))
    return {"states": d["states"], "initial": d["initial"], "transitions": d["transitions"],
            "labeling": d["labeling"], "mo_ta": {t: tm._anh_h6(st) for t, st in ds.items()}}


def ghi_html(du_lieu):
    with open(os.path.join(HERE, "xem_trang_thai.html"), encoding="utf-8") as fh:
        mau = fh.read()
    html = mau.replace("/*__DU_LIEU__*/null", json.dumps(du_lieu, ensure_ascii=False))
    with open(HTML_OUT, "w", encoding="utf-8") as fh:
        fh.write(html)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
