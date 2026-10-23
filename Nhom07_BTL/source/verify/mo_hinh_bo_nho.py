# -*- coding: utf-8 -*-
"""
mo_hinh_bo_nho.py — Mô hình Kripke MỨC CÂU LỆNH + BỘ NHỚ cho H1 (stack) và H6 (heap, 2 worker).

Theo giáo trình CSE703093, mục 3.6 (Memory Model, valid_map) và Phụ lục C.5 Phần II Câu 1:
"BMC mô hình chương trình như một Kripke Structure mở rộng, trong đó mỗi trạng thái bao gồm cả giá trị
biến chương trình và nội dung bộ nhớ ... quan hệ chuyển R tương ứng với ngữ nghĩa thực thi từng câu lệnh".

Khác mô hình kết hợp 35 trạng thái (mức TÌNH HUỐNG, trạng thái lỗi do nhóm đặt), ở đây:
  - trạng thái = (dòng lệnh CPU sắp chạy, giá trị biến, nội dung bộ nhớ stack/heap, valid_map);
  - mỗi cạnh của R = CPU thực thi xong MỘT câu lệnh; vòng lặp ghi bộ nhớ (strcpy, strncpy, memcpy) được
    trải ra thành từng lần ghi 1 byte; lệnh chỉ đọc đầu vào (strnlen) được gộp thành 1 bước;
  - trạng thái lỗi KHÔNG vẽ tay: nhãn được TÍNH từ nội dung bộ nhớ (vd byte ngoài buffer đã bị đổi)
    hoặc từ việc một lệnh free/ghi vào vùng có valid_map = False.
Kripke được SINH TỰ ĐỘNG bằng BFS từ trạng thái khởi tạo, rồi kiểm chứng bằng chính kripke.py,
ctl_checker.py và bounded_checker.py của nhóm.

  H1 — stack: parse_order_id chép mã đơn vào buffer trên stack (mã do SpecVerificationLab sinh,
       results/logs/gui_SVL_SinhMa_v0.txt và _v1.txt, cùng số dòng) + bản sửa của nhóm (M1-v1b).
  H6 — heap: worker callback và worker timeout cùng đóng 1 phiên (mã của M6). Mọi thứ tự xen kẽ của
       2 worker do BFS sinh ra, trạng thái tranh chấp không vẽ tay.

Chạy (Python 3.8+, chỉ thư viện chuẩn):
    cd source/verify
    python mo_hinh_bo_nho.py
  -> in ra màn hình + ghi results/logs/kiem_chung_bo_nho.txt
  -> xuất source/spec/mo_hinh_bo_nho/H1_stack.json, H6_heap.json (cùng định dạng file mô hình con)
"""
from __future__ import annotations

import io
import json
import os
import sys
from collections import OrderedDict, deque, namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from bounded_checker import bmc_check, find_completeness_threshold   # noqa: E402
from ctl_checker import CTLChecker                                    # noqa: E402
from kripke import KripkeStructure                                    # noqa: E402

SPEC_OUT = os.path.normpath(os.path.join(HERE, "..", "spec", "mo_hinh_bo_nho"))
LOGS = os.path.normpath(os.path.join(HERE, "..", "..", "results", "logs"))

# Thuộc tính in phản ví dụ từng bước (các thuộc tính khác chỉ in độ dài k)
CHI_TIET = {"buffer_overflow", "control_hijack", "truncated",
            "race", "double_free", "use_after_free", "secret_residue"}


# ============================================================================ dựng Kripke tự động
def sinh_kripke(s0, buoc, ten_cua, nhan_cua):
    """BFS mọi bước thực thi từ s0 -> (dict Kripke dạng JSON, {tên: trạng thái}).
    buoc(st) trả về các trạng thái sau khi CPU chạy 1 câu lệnh; [] nghĩa là bị kẹt (deadlock)."""
    ten, ds = {}, OrderedDict()

    def dat_ten(st):
        if st not in ten:
            t = ten_cua(st)
            if t in ds:
                raise ValueError(f"Hai trạng thái khác nhau trùng tên: {t}")
            ten[st], ds[t] = t, st
        return ten[st]

    d = {"states": [], "initial": [dat_ten(s0)], "labeling": {}, "transitions": []}
    canh, hang, da_xet = OrderedDict(), deque([s0]), {s0}
    while hang:
        st = hang.popleft()
        for nx in buoc(st):
            canh[(dat_ten(st), dat_ten(nx))] = None
            if nx not in da_xet:
                da_xet.add(nx)
                hang.append(nx)
    for t, st in ds.items():
        d["states"].append(t)
        d["labeling"][t] = nhan_cua(st)
    d["transitions"] = [list(e) for e in canh]
    return d, ds


# ============================================================================ H1 — STACK
MAU = "DH20261015000123-QUA-DAI"   # chuỗi đại diện 24 ký tự; chỉ độ dài L quyết định tràn hay không
CAP = 16                           # mã đơn hợp lệ dài tối đa 16 ký tự (sheet RangBuoc)
KE, RET = 4, 8                     # stack frame rút gọn (giáo trình Hình 2.1): buffer | 4 byte biến kề | 8 byte địa chỉ trả về
RAC, NUL = "·", "\0"               # "·" = byte rác chưa khởi tạo

# pc: dòng lệnh CPU sắp chạy (số dòng trong mã C) hoặc khoi_tao / xong / tu_choi / nhay_la
# i: chỉ số vòng lặp chép; n: biến len (chỉ bản v1 của nhóm); mem: nội dung stack frame từng byte
H1 = namedtuple("H1", "pc L i n mem")


def _mem0(N):
    return (RAC,) * N + ("K",) * KE + ("R",) * RET


def _ghi(mem, k, c):
    m = list(mem)
    m[k] = c
    return tuple(m)


def _src(L):
    """Chuỗi đầu vào độ dài L, kèm '\\0' kết thúc."""
    return MAU[:L] + NUL


def _chuoi(mem):
    """Những gì printf("%s") đọc được: từ ô 0 tới '\\0' đầu tiên."""
    out = []
    for c in mem:
        if c == NUL:
            break
        out.append(c)
    return "".join(out)


def _tra_ve(st, N):
    """Lệnh return: CPU nạp địa chỉ trả về từ stack. Bị ghi đè thì nhảy tới địa chỉ lạ."""
    return st._replace(pc="nhay_la" if st.mem[N + KE:] != _mem0(N)[N + KE:] else "xong")


def _buoc_h1_v0(st, N):
    if st.pc == 9:                       # strcpy: mỗi vòng lặp chép 1 byte, dừng sau khi chép '\0'
        c = _src(st.L)[st.i]
        mem = _ghi(st.mem, st.i, c)
        return [st._replace(pc=10, mem=mem) if c == NUL else st._replace(i=st.i + 1, mem=mem)]
    if st.pc == 10:                      # printf("%s") đọc buffer tới '\0'
        return [st._replace(pc=11)]
    if st.pc == 11:
        return [_tra_ve(st, N)]
    raise ValueError(st.pc)


def _buoc_h1_v1_svl(st, N):
    if st.pc == 9:                       # strncpy(buffer, src, 16): đúng 16 lần ghi, hết chuỗi thì đệm '\0'
        c = MAU[st.i] if st.i < st.L else NUL
        mem = _ghi(st.mem, st.i, c)
        return [st._replace(pc=10, mem=mem) if st.i == N - 2 else st._replace(i=st.i + 1, mem=mem)]
    if st.pc == 10:                      # buffer[16] = '\0'
        return [st._replace(pc=11, mem=_ghi(st.mem, N - 1, NUL))]
    if st.pc == 11:
        return [st._replace(pc=12)]
    if st.pc == 12:
        return [_tra_ve(st, N)]
    raise ValueError(st.pc)


def _buoc_h1_v1_nhom(st, N):
    if st.pc == 9:                       # len = strnlen(src, 17): chỉ đọc src, tối đa 17 byte
        return [st._replace(pc=10, n=min(st.L, CAP + 1))]
    if st.pc == 10:                      # if (len > 16) từ chối
        return [st._replace(pc="tu_choi") if st.n > CAP else st._replace(pc=11)]
    if st.pc == 11:                      # memcpy(buffer, src, len + 1): mỗi lần ghi 1 byte
        mem = _ghi(st.mem, st.i, _src(st.L)[st.i])
        return [st._replace(pc=12, mem=mem) if st.i == st.n else st._replace(i=st.i + 1, mem=mem)]
    if st.pc == 12:
        return [st._replace(pc=13)]
    if st.pc == 13:
        return [_tra_ve(st, N)]
    raise ValueError(st.pc)


H1_BAN = [
    {"ngan": "v0", "N": 16, "buoc": _buoc_h1_v0, "sau_in": {11, "xong", "nhay_la"},
     "ten": "H1-v0: mã SpecVerificationLab sinh từ đặc tả v0 — char buffer[16] + strcpy (CÓ LỖI)",
     "ma": OrderedDict([(7, "void parse_order_id(const char *raw_order_id) {"),
                        (8, "    char buffer[16];"),
                        (9, "    strcpy(buffer, raw_order_id);"),
                        (10, '    printf("%s\\n", buffer);'),
                        (11, "}")])},
    {"ngan": "v1-SVL", "N": 17, "buoc": _buoc_h1_v1_svl, "sau_in": {12, "xong", "nhay_la"},
     "ten": "H1-v1-SVL: mã SpecVerificationLab sinh từ đặc tả v1 — char buffer[17] + strncpy",
     "ma": OrderedDict([(7, "void parse_order_id(const char *raw_order_id) {"),
                        (8, "    char buffer[17];"),
                        (9, "    strncpy(buffer, raw_order_id, sizeof(buffer) - 1);"),
                        (10, "    buffer[sizeof(buffer) - 1] = '\\0';"),
                        (11, '    printf("%s\\n", buffer);'),
                        (12, "}")])},
    {"ngan": "v1-nhóm", "N": 17, "buoc": _buoc_h1_v1_nhom, "sau_in": {13, "xong", "nhay_la"},
     "ten": "H1-v1-nhóm: bản sửa của nhóm (M1-v1b) — buffer[17] + strnlen + từ chối",
     "ma": OrderedDict([(7, "void parse_order_id(const char *raw_order_id) {"),
                        (8, "    char buffer[17];"),
                        (9, "    size_t len = strnlen(raw_order_id, 17);"),
                        (10, "    if (len > 16) return;   /* từ chối mã dài hơn 16 ký tự */"),
                        (11, "    memcpy(buffer, raw_order_id, len + 1);"),
                        (12, '    printf("%s\\n", buffer);'),
                        (13, "}")])},
]

H1_CTL = ["AG(!buffer_overflow)", "AG(!off_by_one)", "AG(!ret_overwritten)", "AG(!control_hijack)",
          "AG(!oob_read)", "AG(!truncated)", "AG(!violation)", "AF(flow_end)", "EF(copied_ok)",
          "EF(input_rejected)"]
H1_GHEP = [("AG(len_eq_cap -> AF(copied_ok))", "mã dài đúng 16 ký tự thì được chép nguyên vẹn, không hỏng bộ nhớ"),
           ("AG(len_gt_cap -> AF(input_rejected))", "mã dài hơn 16 ký tự thì cuối cùng bị từ chối")]


def _buoc_h1(ban):
    def buoc(st):
        if st.pc == "khoi_tao":          # môi trường gửi chuỗi: mọi độ dài 0..24 đều có thể
            return [H1(pc=9, L=L, i=0, n=None, mem=st.mem) for L in range(len(MAU) + 1)]
        if st.pc in ("xong", "tu_choi", "nhay_la"):
            return [st]                  # trạng thái cuối tự lặp (R toàn phần)
        return ban["buoc"](st, ban["N"])
    return buoc


def _ten_h1(st):
    if st.pc == "khoi_tao":
        return "khoi_tao"
    if isinstance(st.pc, int):
        return f"L{st.L:02d}_d{st.pc}_i{st.i:02d}"
    return f"L{st.L:02d}_{st.pc}"


def _nhan_h1(st, ban):
    """Nhãn được TÍNH từ dòng lệnh và nội dung bộ nhớ, không gán tay."""
    if st.pc == "khoi_tao":
        return ["receiving", "start"]
    N, goc = ban["N"], _mem0(ban["N"])
    lab = {f"dong_{st.pc}"} if isinstance(st.pc, int) else set()
    lab.add("len_lt_cap" if st.L < CAP else "len_eq_cap" if st.L == CAP else "len_gt_cap")
    hong = st.mem[N:] != goc[N:]                         # có byte ngoài buffer đã bị đổi
    if hong:
        lab |= {"buffer_overflow", "violation"}
    if st.mem[N] == NUL and st.mem[N + 1:] == goc[N + 1:]:
        lab.add("off_by_one")                            # đúng 1 byte '\0' ghi lố sau buffer
    if st.mem[N + KE:] != goc[N + KE:]:
        lab.add("ret_overwritten")                       # địa chỉ trả về bị ghi đè
    if st.pc == "nhay_la":
        lab |= {"control_hijack", "violation"}           # CPU nhảy tới địa chỉ do dữ liệu đầu vào quyết định
    in_ra = _chuoi(st.mem)
    if st.pc in ban["sau_in"] and len(in_ra) >= N:
        lab |= {"oob_read", "violation"}                 # printf đọc qua cuối buffer
    if st.pc == "tu_choi":
        lab |= {"input_rejected", "flow_end", "done"}
    if st.pc == "xong":
        lab |= {"flow_end", "done"}
        if in_ra != MAU[:st.L]:
            lab |= {"truncated", "violation"}            # in ra khác mã đơn nhận được
        elif not hong:
            lab.add("copied_ok")
    return sorted(lab)


def _anh_h1(ban):
    N = ban["N"]
    h = lambda cs: "".join("∅" if c == NUL else c for c in cs)   # noqa: E731
    return lambda st: f"buffer[{N}]={h(st.mem[:N])} | kề={h(st.mem[N:N + KE])} | ret={h(st.mem[N + KE:])}"


def _mo_ta_h1(ban):
    ma = ban["ma"]

    def f(a, b):
        if a == b:
            return "(tự lặp)"
        if a.pc == "khoi_tao":
            return f'nhận chuỗi L={b.L}: "{MAU[:b.L]}"'
        if b.pc == "nhay_la":
            return "return: địa chỉ trả về đã bị ghi đè → CPU nhảy tới địa chỉ lạ"
        if b.pc == "xong" and a.pc != "xong":
            return "return bình thường"
        if b.pc == "tu_choi":
            return f"dòng {a.pc} {ma[a.pc].strip()}  → len={a.n} > 16: TỪ CHỐI"
        doi = [k for k in range(len(a.mem)) if a.mem[k] != b.mem[k]]
        if doi:
            k, c = doi[0], b.mem[doi[0]]
            vung = "" if k < ban["N"] else ("  ← NGOÀI buffer (biến kề)" if k < ban["N"] + KE
                                             else "  ← NGOÀI buffer (địa chỉ trả về)")
            return f"dòng {a.pc} {ma[a.pc].strip()}  ghi ô [{k}] = {'∅' if c == NUL else repr(c)}{vung}"
        if b.n is not None and a.n is None:
            return f"dòng {a.pc} {ma[a.pc].strip()}  → len = {b.n}"
        return f"dòng {a.pc} {ma[a.pc].strip()}"
    return f


# ============================================================================ H6 — HEAP, 2 WORKER
# cb, to: dòng lệnh sắp chạy của worker callback / worker timeout (0 = đã return)
# khoa: worker đang giữ mutex; status: s->status; s, card: valid_map[s], valid_map[s->card]
# the: vùng card còn chứa số thẻ; loi: hành vi không xác định ĐẦU TIÊN (sau đó mô hình dừng, như ASan/CBMC)
H6 = namedtuple("H6", "cb to khoa status s card the loi")
H6_DAU = H6(cb=1, to=1, khoa=None, status="OPEN", s=True, card=True, the=True, loi=None)

# Mỗi lệnh: (thao tác, tham số, mã C). {V} = PAID ở worker callback, CANCELLED ở worker timeout.
# "vung": các dòng mà worker đang thao tác/giữ phiên (nhãn cb_locked, to_locked)
H6_BAN = [
    {"ngan": "v0", "ten": "H6-v0: không khóa, memset rồi free (CÓ LỖI) — mã của M6-v0", "vung": {2, 3, 4},
     "ma": [("status", None, "s->status = {V};"),
            ("memset", None, "memset(s->card, 0, 16);"),
            ("free_card", None, "free(s->card);"),
            ("free_s", None, "free(s);"),
            ("return", None, "return;")]},
    {"ngan": "v1a", "ten": "H6-v1a: CHỈ thêm mutex (phiên s do bộ quản lý phiên giải phóng sau khi 2 worker xong)",
     "vung": {2, 3, 4, 5},
     "ma": [("lock", None, "lock(&s->mtx);"),
            ("status", None, "s->status = {V};"),
            ("memset", None, "memset(s->card, 0, 16);"),
            ("free_card", None, "free(s->card);"),
            ("unlock", None, "unlock(&s->mtx);"),
            ("return", None, "return;")]},
    {"ngan": "v1b", "ten": "H6-v1b: bản sửa của nhóm — mutex + kiểm tra CLOSED + explicit_bzero — mã của M6-v1",
     "vung": {2, 3, 4, 5, 6, 7},
     "ma": [("lock", None, "lock(&s->mtx);"),
            ("if_closed", 7, "if (s->status == CLOSED) goto dòng 7;"),
            ("status", None, "s->status = {V};"),
            ("bzero", None, "explicit_bzero(s->card, 16);"),
            ("free_card", None, "free(s->card);"),
            ("status", "CLOSED", "s->status = CLOSED;"),
            ("unlock", None, "unlock(&s->mtx);"),
            ("return", None, "return;")]},
]

H6_CTL = ["AG(!race)", "AG(!double_free)", "AG(!use_after_free)", "AG(!secret_residue)", "AG(!violation)",
          "AF(session_freed)", "EF(cb_locked)", "EF(to_locked)"]
H6_GHEP = [("AG(!(cb_locked & to_locked))", "mutex viết dạng CTL"),
           ("AG(paid -> AG(!cancelled))", "đơn đã ghi PAID thì không bao giờ bị ghi đè thành CANCELLED")]
H6_MUTEX = ("cb_locked", "to_locked")


def _buoc_h6(ban):
    ma = ban["ma"]

    def chay(st, w):
        """Worker w chạy 1 lệnh. Trả về [] nếu đã xong hoặc đang chờ khóa."""
        pc = getattr(st, w)
        if pc == 0:
            return []
        op, arg, _ = ma[pc - 1]
        tiep = st._replace(**{w: pc + 1})
        loi = lambda kieu: [st._replace(loi=f"{kieu}@{w}:{pc}")]   # noqa: E731
        if op == "return":
            return [st._replace(**{w: 0})]
        if not st.s:                                     # mọi lệnh còn lại đều đọc/ghi vào *s
            return loi("double_free" if op == "free_s" else "use_after_free")
        if op == "lock":
            return [] if st.khoa else [tiep._replace(khoa=w)]
        if op == "unlock":
            return [tiep._replace(khoa=None)]
        if op == "status":
            return [tiep._replace(status=arg or ("PAID" if w == "cb" else "CANCELLED"))]
        if op == "if_closed":
            return [st._replace(**{w: arg}) if st.status == "CLOSED" else tiep]
        if op == "free_s":
            return [tiep._replace(s=False)]
        if not st.card:                                  # các lệnh còn lại đọc/ghi/free vùng card
            return loi("double_free" if op == "free_card" else "use_after_free")
        if op == "free_card":
            return [tiep._replace(card=False)]
        if op == "bzero":
            return [tiep._replace(the=False)]
        if op == "memset":
            # memset ngay trước free là "dead store": trình biên dịch được phép BỎ (CWE-14),
            # nên có 2 khả năng: xóa thật, hoặc vùng card vẫn còn số thẻ
            return [tiep._replace(the=False), tiep]
        raise ValueError(op)

    def buoc(st):
        if st.loi or (st.cb == 0 and st.to == 0):
            return [st]                                  # lỗi hoặc cả 2 đã xong: tự lặp
        return chay(st, "cb") + chay(st, "to")           # mọi thứ tự xen kẽ: worker nào chạy trước cũng được
    return buoc


_TT = {"OPEN": "mo", "PAID": "tt", "CANCELLED": "huy", "CLOSED": "dong"}


def _ten_h6(st):
    t = (f"cb{st.cb or 'x'}_to{st.to or 'x'}_k{st.khoa or '0'}_{_TT[st.status]}"
         f"_s{int(st.s)}c{int(st.card)}t{int(st.the)}")
    if st.loi:
        kieu, vt = st.loi.split("@")
        t += ("_df_" if kieu == "double_free" else "_uaf_") + vt.replace(":", "")
    return t


def _nhan_h6(st, ban):
    lab = {"paid" if st.status == "PAID" else "cancelled" if st.status == "CANCELLED"
           else "closed" if st.status == "CLOSED" else "sess_open"}
    if st == H6_DAU:
        lab.add("start")
    if st.cb in ban["vung"]:
        lab.add("cb_locked")
    if st.to in ban["vung"]:
        lab.add("to_locked")
    if {"cb_locked", "to_locked"} <= lab:
        lab |= {"race", "violation"}
    if st.loi:
        lab |= {st.loi.split("@")[0], "violation"}
    if not st.card and st.the:
        lab |= {"secret_residue", "violation"}       # vùng card đã free nhưng số thẻ còn trong heap
    if st.cb == 0 and st.to == 0 and not st.loi:
        lab |= {"done", "flow_end"}
        if not st.card:
            lab.add("session_freed")
            if not st.the:
                lab.add("mem_clean")
    return sorted(lab)


def _anh_h6(st):
    khoa = {None: "–", "cb": "CB", "to": "TO"}[st.khoa]
    return (f"[CB:{st.cb or 'xong'} TO:{st.to or 'xong'} | khóa={khoa} | status={st.status} "
            f"| valid_map: s={int(st.s)} card={int(st.card)} | card {'CÒN số thẻ' if st.the else 'đã xóa'}]")


def _mo_ta_h6(ban):
    ma = ban["ma"]
    TEN = {"cb": "CALLBACK", "to": "TIMEOUT "}
    ma_c = lambda w, pc: ma[pc - 1][2].replace("{V}", "PAID" if w == "cb" else "CANCELLED")   # noqa: E731

    def f(a, b):
        if a == b:
            return "(tự lặp)"
        if b.loi and not a.loi:
            kieu, vt = b.loi.split("@")
            w, pc = vt.split(":")
            hau_qua = "FREE LẦN 2 (double free)" if kieu == "double_free" else "DÙNG VÙNG ĐÃ FREE (use-after-free)"
            return f"{TEN[w]} dòng {pc}: {ma_c(w, int(pc))}  ⇒ {hau_qua}"
        for w in ("cb", "to"):
            pa, pb = getattr(a, w), getattr(b, w)
            if pa != pb:
                s = f"{TEN[w]} dòng {pa}: {ma_c(w, pa)}"
                if ma[pa - 1][0] == "memset" and b.the:
                    s += "  ← trình biên dịch đã BỎ lệnh này"
                if ma[pa - 1][0] == "if_closed" and pb == ma[pa - 1][1]:
                    s += "  → phiên đã đóng, bỏ qua"
                return s
        return "?"
    return f


# ============================================================================ kiểm chứng + in kết quả
def _in_vet(p, path, ds, mo_ta, anh):
    """In phản ví dụ: mỗi bước là 1 lệnh CPU chạy; vòng lặp dài được rút gọn."""
    sts = [ds[t] for t in path]
    p(f"          bước  0  {'(trạng thái khởi tạo)':76s} {anh(sts[0])}")
    buoc = [(k, sts[k - 1], sts[k]) for k in range(1, len(sts))]
    j = 0
    while j < len(buoc):
        k, a, b = buoc[j]
        pc = getattr(a, "pc", None)
        run = j
        while (isinstance(pc, int) and run + 1 < len(buoc)
               and getattr(buoc[run][1], "pc", None) == pc == getattr(buoc[run][2], "pc", None)):
            run += 1
        if run - j >= 4:                                 # vòng lặp: in 2 bước đầu, rút gọn phần giữa
            for kk, aa, bb in buoc[j:j + 2]:
                p(f"          bước {kk:2d}  {mo_ta(aa, bb):76s} {anh(bb)}")
            p(f"          ...      (lặp tiếp {run - j - 2} lần, mỗi lần chép 1 byte)")
            j = run
            continue
        p(f"          bước {k:2d}  {mo_ta(a, b):76s} {anh(b)}")
        j += 1


def kiem_chung(ban, d, ds, cong_thuc, ghep, mutex, mo_ta, anh, out, ket_qua):
    p = lambda *a: print(*a, file=out)   # noqa: E731
    m = KripkeStructure.from_dict(d)
    ck = CTLChecker(m)
    kq = ket_qua.setdefault(ban["ten"], {})
    p(f"\n=== {ban['ten']}")
    ma = ban["ma"]
    if isinstance(ma, dict):
        for so, dong in ma.items():
            p(f"      {so:2d} | {dong}")
    else:
        p("      (V = PAID ở worker callback, CANCELLED ở worker timeout; 2 worker chạy song song)")
        for so, (_, _, dong) in enumerate(ma, 1):
            p(f"      {so:2d} | {dong.replace('{V}', 'V')}")
    n_r = sum(len(v) for v in m.transitions.values())
    p(f"  |S|={len(m.states)}  |R|={n_r}  S0={sorted(m.initial_states)}  đạt tới được={len(m.reachable_states())}")
    dl = m.deadlock_states()
    p(f"  [1] Deadlock: {', '.join(sorted(dl)) if dl else 'không có'}")

    p("  [2] CTL:")
    for f in cong_thuc:
        ok, _ = ck.check(f)
        kq[f] = [ok, None]
        p(f"      {f:28s} -> {'ĐÚNG' if ok else 'VI PHẠM'}")
    if mutex:
        a, b = mutex
        xau = sorted(s for s in m.reachable_states() if {a, b} <= m.labels.get(s, set()))
        kq[f"Mutex({a}, {b})"] = [not xau, None]
        p(f"      Mutex({a}, {b})  -> {'ĐÚNG' if not xau else f'VI PHẠM tại {len(xau)} trạng thái, vd {xau[0]}'}")
    for f, y_nghia in ghep:
        ok, _ = ck.check(f)
        kq[f] = [ok, None]
        p(f"      {f:40s} -> {'ĐÚNG' if ok else 'VI PHẠM':7s}  ({y_nghia})")

    ct = find_completeness_threshold(m)
    p(f"  [3] BMC (bounded_checker) — completeness threshold CT = {ct}; k = số lệnh CPU đã chạy")
    for f in cong_thuc:
        if not f.startswith("AG(!"):
            continue
        atom = f[4:-1]
        bad = {s for s in m.states if atom in m.labels.get(s, set())}
        res = None
        for k in range(0, (ct or 0) + 2):
            r = bmc_check(m, bad, k)
            if r.violated or r.reached_completeness_threshold:
                res = r
                break
        if res and res.violated:
            k = len(res.counterexample) - 1
            kq[f][1] = k
            p(f"      {f:28s} VI PHẠM ở k={k}" + (":" if atom in CHI_TIET else ""))
            if atom in CHI_TIET:
                _in_vet(p, res.counterexample, ds, mo_ta, anh)
        elif res:
            p(f"      {f:28s} AN TOÀN — đã đạt CT ở k={res.k}, không còn trạng thái nào chưa duyệt")
        else:
            p(f"      {f:28s} chưa kết luận trong k <= {(ct or 0) + 1}")
    return d


def _bang_tom_tat(p, tieu_de, bans, cong_thuc, ket_qua):
    p(f"\n  {tieu_de}")
    p("  " + f"{'Thuộc tính':42s}" + "".join(f"{b['ngan']:>14s}" for b in bans))
    for f in cong_thuc:
        o = []
        for b in bans:
            ok, k = ket_qua[b["ten"]][f]
            o.append("ĐÚNG" if ok else (f"VI PHẠM k={k}" if k is not None else "VI PHẠM"))
        p("  " + f"{f:42s}" + "".join(f"{x:>14s}" for x in o))


def _xuat_json(ten_file, title, desc, flows, ctl, mutex=None):
    os.makedirs(SPEC_OUT, exist_ok=True)
    d = OrderedDict([("title", title), ("description", desc), ("flows", flows), ("suggested_ctl_formulas", ctl)])
    if mutex:
        d["suggested_mutex_atoms"] = list(mutex)
    with open(os.path.join(SPEC_OUT, ten_file), "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)


def main():
    buf = io.StringIO()
    p = lambda *a: print(*a, file=buf)   # noqa: E731
    p("MÔ HÌNH KRIPKE MỨC CÂU LỆNH + BỘ NHỚ — Nhóm 07 (giáo trình mục 3.6; Phụ lục C.5, Phần II, Câu 1)")
    p("Trạng thái = (dòng lệnh CPU sắp chạy, biến, nội dung bộ nhớ, valid_map); mỗi cạnh của R = CPU chạy 1 lệnh.")
    p("Kripke SINH TỰ ĐỘNG bằng BFS; nhãn TÍNH từ bộ nhớ; kiểm chứng bằng ctl_checker + bounded_checker của nhóm.")
    ket_qua = {}

    # ---------------- H1
    p("\n" + "#" * 100)
    p("# H1 — STACK: parse_order_id chép mã đơn vào buffer trên stack")
    p(f"# Stack frame (giáo trình Hình 2.1, rút gọn): buffer[N] | {KE} byte biến kề (K) | {RET} byte địa chỉ trả về (R)")
    p(f'# Đầu vào: mọi độ dài L = 0..{len(MAU)} (môi trường chọn); nội dung = tiền tố của "{MAU}"')
    p("# (chỉ độ dài quyết định tràn; mọi L > 17 hành xử như nhau ở 2 bản v1 vì strncpy/strnlen đọc tối đa 16/17 byte)")
    p("#" * 100)
    flows1 = OrderedDict()
    for ban in H1_BAN:
        d, ds = sinh_kripke(H1(pc="khoi_tao", L=None, i=0, n=None, mem=_mem0(ban["N"])), _buoc_h1(ban),
                            _ten_h1, lambda st, b=ban: _nhan_h1(st, b))
        kiem_chung(ban, d, ds, H1_CTL, H1_GHEP, None, _mo_ta_h1(ban), _anh_h1(ban), buf, ket_qua)
        flows1[ban["ten"]] = OrderedDict([("description", " ".join(x.strip() for x in ban["ma"].values()))] +
                                         list(d.items()))

    # ---------------- H6
    p("\n" + "#" * 100)
    p("# H6 — HEAP: worker callback và worker timeout cùng đóng 1 phiên PaymentSession *s")
    p("# Bộ nhớ heap theo dõi bằng valid_map (giáo trình mục 3.6): valid_map[p] = 1 khi p đã cấp phát và chưa free.")
    p("# Mọi thứ tự xen kẽ 2 worker do BFS sinh ra; dừng ở hành vi không xác định đầu tiên (như ASan/CBMC).")
    p("#" * 100)
    flows6 = OrderedDict()
    for ban in H6_BAN:
        d, ds = sinh_kripke(H6_DAU, _buoc_h6(ban), _ten_h6, lambda st, b=ban: _nhan_h6(st, b))
        kiem_chung(ban, d, ds, H6_CTL, H6_GHEP, H6_MUTEX, _mo_ta_h6(ban), _anh_h6, buf, ket_qua)
        flows6[ban["ten"]] = OrderedDict([("description", " ".join(x[2] for x in ban["ma"]))] + list(d.items()))

    # ---------------- tóm tắt
    p("\n" + "#" * 100)
    p("# TÓM TẮT (k = độ dài phản ví dụ ngắn nhất, tính bằng số lệnh CPU)")
    p("#" * 100)
    _bang_tom_tat(p, "H1 — stack", H1_BAN, H1_CTL + [f for f, _ in H1_GHEP], ket_qua)
    _bang_tom_tat(p, "H6 — heap", H6_BAN, H6_CTL + ["Mutex(cb_locked, to_locked)"] + [f for f, _ in H6_GHEP], ket_qua)

    v1a = ket_qua.get(H6_BAN[1]["ten"], {})
    if v1a and v1a["AG(!race)"][0] and not v1a["AG(!use_after_free)"][0]:
        p("\n  NHẬN XÉT H6: chỉ thêm mutex (v1a) thì hết tranh chấp, nhưng worker đến sau vẫn memset vùng card đã")
        p("  free (use-after-free). Mô hình kết hợp chỉ có đường tới h6_double_free/h6_uaf qua h6_tranh_chap nên")
        p("  không thấy điều này; mô hình mức bộ nhớ cho thấy vì sao bản sửa cần thêm kiểm tra status == CLOSED.")

    _xuat_json("H1_stack.json", "H1 mức câu lệnh + stack: parse_order_id",
               "Sinh tự động bởi source/verify/mo_hinh_bo_nho.py. Trạng thái L<độ dài>_d<dòng>_i<chỉ số>.",
               flows1, H1_CTL)
    _xuat_json("H6_heap.json", "H6 mức câu lệnh + heap: 2 worker đóng phiên",
               "Sinh tự động bởi source/verify/mo_hinh_bo_nho.py. Trạng thái cb<dòng>_to<dòng>_k<khóa>_<status>"
               "_s<valid s>c<valid card>t<còn số thẻ>.", flows6, H6_CTL, H6_MUTEX)

    text = buf.getvalue()
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "kiem_chung_bo_nho.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    print(f"(Đã ghi {os.path.join(LOGS, 'kiem_chung_bo_nho.txt')})")
    print(f"(Đã xuất {os.path.join(SPEC_OUT, 'H1_stack.json')} và H6_heap.json)")


if __name__ == "__main__":
    main()
