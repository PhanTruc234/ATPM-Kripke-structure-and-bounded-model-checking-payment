# -*- coding: utf-8 -*-
"""
chay_kiem_chung.py — Kiểm chứng độc lập của nhóm 07 trên ĐÚNG các file nộp cho phần mềm.

Với mỗi mô hình (mô hình kết hợp v0/v1 trong file Excel + 6 mô hình con, mọi luồng):
  [1] Deadlock (trạng thái không có cạnh đi ra)
  [2] Các công thức CTL của đặc tả (cú pháp phần mềm hỗ trợ) — kiểm tra chéo kết quả phần mềm
  [3] Công thức CTL GHÉP/LỒNG NHAU (phần mềm KHÔNG hỗ trợ) — dạng "nếu ... thì cuối cùng ..."
  [4] BMC (bounded_checker theo giáo trình A.3.3): mỗi AG(!x) -> counterexample dài k bước,
      hoặc "an toàn" khi đã đạt completeness threshold; kèm bảng quét k cho AG(!violation)

Chạy (chỉ cần Python 3.8+ thư viện chuẩn):
    cd source/verify
    python chay_kiem_chung.py              -> in ra màn hình + ghi results/logs/kiem_chung_nhom.txt
"""
from __future__ import annotations

import glob
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from bounded_checker import bmc_check, find_completeness_threshold   # noqa: E402
from ctl_checker import CTLChecker, is_tool_syntax                   # noqa: E402
from doc_dac_ta import doc_excel, doc_mo_hinh_con                    # noqa: E402

SPEC = os.path.normpath(os.path.join(HERE, "..", "spec"))
LOGS = os.path.normpath(os.path.join(HERE, "..", "..", "results", "logs"))

# Công thức ghép bổ sung (LTL tương ứng ghi trong ngoặc) — theo từng mô hình
MO_RONG = {
    "thanhtoan": [("AG(!(cb_locked & to_locked))", "G ¬(cb ∧ to): mutex viết dạng CTL"),
                  ("AG(allocated -> AF(mem_clean))", "G(allocated → F mem_clean): cấp phát thì cuối cùng bộ nhớ sạch"),
                  ("AG(receiving -> AF(flow_end))", "G(receiving → F flow_end): nhận yêu cầu thì cuối cùng kết thúc"),
                  ("AG(callback_received -> AF(flow_end))", "G(callback → F flow_end)"),
                  ("EF(payment_done) & EF(input_rejected)", "có cả nhánh thành công lẫn nhánh từ chối")],
    "M1": [("AG(len_eq_cap -> AF(copied_ok))", "mã dài đúng 16 ký tự phải được chép NGUYÊN VẸN")],
    "M2": [("AG(ptr_null -> AX(input_rejected))", "malloc NULL thì bước kế tiếp phải từ chối"),
           ("AG(allocated -> AF(in_use))", "đã cấp phát thì cuối cùng được dùng hợp lệ")],
    "M3": [("AG(input_ok -> AF(amount_ok | input_rejected))", "đầu vào hợp lệ thì cuối cùng ra tổng hợp lệ hoặc bị từ chối")],
    "M4": [("AG(len_ok -> AF(accepted | callback_rejected))", "callback đúng độ dài thì cuối cùng được chấp nhận hoặc từ chối")],
    "M5": [("AG(allocated -> AF(freed))", "G(allocated → F freed): không rò rỉ")],
    "M6": [("AG(!(cb_locked & to_locked))", "mutex dạng CTL"),
           ("AG(releasing -> AF(session_freed))", "bắt đầu giải phóng thì cuối cùng phiên được giải phóng sạch")],
}


def _mo_rong_cho(ten):
    for key, v in MO_RONG.items():
        if ten.startswith(key) or os.path.basename(ten).startswith(key):
            return v
    return []


def kiem_chung(ten, model, formulas, mutex, extra, out):
    p = lambda *a: print(*a, file=out)
    ck = CTLChecker(model)
    n_tr = sum(len(v) for v in model.transitions.values())
    p(f"\n=== {ten}  |S|={len(model.states)}  |R|={n_tr}  S0={sorted(model.initial_states)}"
      f"  reachable={len(model.reachable_states())}")
    dl = model.deadlock_states()
    p(f"  [1] Deadlock: {sorted(dl) if dl else 'không có'}")

    p("  [2] CTL của đặc tả (cùng cú pháp phần mềm):")
    for f in formulas:
        ok, _ = ck.check(f)
        p(f"      {f:26s} -> {'ĐÚNG' if ok else 'VI PHẠM'}")
    if mutex:
        a, b = mutex
        bad = sorted(s for s in model.reachable_states() if {a, b} <= model.labels.get(s, set()))
        p(f"      Mutex({a}, {b})  -> {'ĐÚNG' if not bad else 'VI PHẠM tại ' + ', '.join(bad)}")

    if extra:
        p("  [3] CTL ghép/lồng nhau (phần mềm KHÔNG hỗ trợ cú pháp này — tự kiểm chứng):")
        for f, y_nghia in extra:
            ok, _ = ck.check(f)
            p(f"      {f:44s} -> {'ĐÚNG' if ok else 'VI PHẠM':7s}  ({y_nghia})")

    ct = find_completeness_threshold(model)
    p(f"  [4] BMC (bounded_checker) — completeness threshold CT = {ct}")
    for f in formulas:
        if not (is_tool_syntax(f) and f.replace(" ", "").startswith("AG(!")):
            continue
        atom = f.replace(" ", "")[4:-1]
        bad = {s for s in model.states if atom in model.labels.get(s, set())}
        res = None
        for k in range(0, (ct or 0) + 2):
            r = bmc_check(model, bad, k)
            if r.violated or r.reached_completeness_threshold:
                res = r
                break
        if res and res.violated:
            p(f"      {f:26s} VI PHẠM ở k={len(res.counterexample) - 1}: {' -> '.join(res.counterexample)}")
        elif res:
            p(f"      {f:26s} AN TOÀN — đã đạt CT ở k={res.k}, không còn trạng thái nào chưa duyệt")
        else:
            p(f"      {f:26s} chưa kết luận trong k <= {(ct or 0) + 1}")
    if any(f.replace(" ", "") == "AG(!violation)" for f in formulas):
        bad = {s for s in model.states if "violation" in model.labels.get(s, set())}
        cells = []
        for k in range(0, (ct or 0) + 2):
            r = bmc_check(model, bad, k)
            cells.append(f"k={k}:{'SAT' if r.violated else ('UNSAT+CT' if r.reached_completeness_threshold else 'UNSAT')}")
        p("      Quét k cho AG(!violation): " + "  ".join(cells))


def main():
    os.makedirs(LOGS, exist_ok=True)
    buf = io.StringIO()
    print("KIỂM CHỨNG ĐỘC LẬP CỦA NHÓM 07 — kripke.py + ctl_checker.py + bounded_checker.py (giáo trình A.1.1, A.3.3)", file=buf)
    print("Ghi chú BMC: SAT = tìm thấy đường đi tới trạng thái xấu trong <= k bước; UNSAT+CT = không có và đã duyệt hết.", file=buf)
    for ver in ("v0", "v1"):
        path = os.path.join(SPEC, f"thanhtoan_donhang_{ver}.xlsx")
        if not os.path.exists(path):
            continue
        ten, model, formulas, mutex = doc_excel(path)
        kiem_chung(f"{ten} (mô hình kết hợp, đọc từ {os.path.basename(path)})", model, formulas, mutex,
                   _mo_rong_cho("thanhtoan"), buf)
    for path in sorted(glob.glob(os.path.join(SPEC, "mo_hinh_con", "M*.json"))):
        title, flows, formulas, mutex = doc_mo_hinh_con(path)
        print(f"\n######## {title}", file=buf)
        for name, model in flows.items():
            kiem_chung(name, model, formulas, mutex, _mo_rong_cho(os.path.basename(path)), buf)
    text = buf.getvalue()
    with open(os.path.join(LOGS, "kiem_chung_nhom.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    print(f"(Đã ghi {os.path.join(LOGS, 'kiem_chung_nhom.txt')})")


if __name__ == "__main__":
    main()
