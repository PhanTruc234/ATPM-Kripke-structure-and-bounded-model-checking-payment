"""Vẽ sơ đồ trạng thái dùng trong báo cáo, đọc trực tiếp từ đặc tả JSON đã nạp vào hai phần mềm.

Chạy:  python ve_so_do.py      (cần PyMuPDF: pip install pymupdf; font Arial/Consolas của Windows)
Kết quả ghi vào results/hinh_bao_cao/:
- h33_tong_quan.png  : mô hình kết hợp 35 trạng thái (thanhtoan_donhang_v0/v1.json), vẽ chồng v0 và v1
- h34..h39_mX.png    : sáu mô hình con M1–M6 (mo_hinh_con/*.json), mỗi luồng một khung
Vị trí các nút do nhóm đặt tay (bảng POS); trạng thái, nhãn và cạnh lấy hoàn toàn từ file đặc tả.
Kích thước canvas bằng kích thước in (450 pt = độ rộng vùng chữ của báo cáo).
"""
import json, math, os
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = HERE + os.sep
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "results", "hinh_bao_cao"))
os.makedirs(OUT, exist_ok=True)

FONTS = {"R": r"C:/Windows/Fonts/arial.ttf", "B": r"C:/Windows/Fonts/arialbd.ttf",
         "I": r"C:/Windows/Fonts/ariali.ttf", "M": r"C:/Windows/Fonts/consola.ttf",
         "MB": r"C:/Windows/Fonts/consolab.ttf"}
FOBJ = {k: pymupdf.Font(fontfile=v) for k, v in FONTS.items()}

BLK = (0.1, 0.1, 0.1)
GRY = (0.35, 0.35, 0.35)
LGRY = (0.6, 0.6, 0.6)
KIND = {  # viền, nền
    "init": ((0.15, 0.35, 0.6), (0.85, 0.91, 0.98)),
    "risk": ((0.72, 0.15, 0.15), (0.99, 0.88, 0.88)),
    "end": ((0.15, 0.5, 0.25), (0.88, 0.96, 0.89)),
    "halt": ((0.55, 0.08, 0.08), (0.93, 0.72, 0.72)),
    "norm": ((0.4, 0.4, 0.4), (1, 1, 1)),
}
E_BOTH = dict(color=(0.22, 0.22, 0.22), width=0.8, dashes=None)
E_V0 = dict(color=(0.75, 0.12, 0.12), width=0.9, dashes="[3 2] 0")
E_V1 = dict(color=(0.1, 0.55, 0.2), width=1.3, dashes=None)
E_SUB = dict(color=(0.22, 0.22, 0.22), width=0.8, dashes=None)

ID_FS, LB_FS = 6.3, 5.4


def tl(s, f, fs):
    return FOBJ[f].text_length(s, fontsize=fs)


def new_page(w, h):
    doc = pymupdf.open()
    pg = doc.new_page(width=w, height=h)
    for k, v in FONTS.items():
        pg.insert_font(fontname=k, fontfile=v)
    return doc, pg


def text(pg, x, y, s, f="R", fs=7, col=BLK, align="l", rotate=0):
    w = tl(s, f, fs)
    if align == "c":
        x -= w / 2
    elif align == "r":
        x -= w
    pg.insert_text((x, y), s, fontname=f, fontsize=fs, color=col, rotate=rotate)
    return w


def wrap(tokens, f, fs, maxw, sep=", "):
    lines, cur = [], ""
    for i, t in enumerate(tokens):
        piece = t + ("," if sep == ", " and i < len(tokens) - 1 else "")
        trial = (cur + " " + piece).strip() if cur else piece
        if cur and tl(trial, f, fs) > maxw:
            lines.append(cur)
            cur = piece
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def kind_of(labels, initial):
    if initial:
        return "init"
    if "unsafe_halt" in labels:
        return "halt"
    if "violation" in labels:
        return "risk"
    if "done" in labels or "flow_end" in labels:
        return "end"
    return "norm"


class Node:
    def __init__(self, sid, show, labels, kind, cx, cy, w):
        self.sid, self.show, self.labels, self.kind = sid, show, labels, kind
        self.cx, self.cy, self.w = cx, cy, w
        lab = ["{" + labels[0]] + labels[1:] if labels else ["{}"]
        lab[-1] = lab[-1] + "}"
        self.lines = wrap(lab, "R", LB_FS, w - 6) if labels else []
        self.h = 4 + ID_FS * 1.15 + len(self.lines) * LB_FS * 1.2 + 3
        if tl(show, "MB", ID_FS) > w - 4:
            print("  !! ten qua dai:", show)

    @property
    def rect(self):
        return pymupdf.Rect(self.cx - self.w / 2, self.cy - self.h / 2, self.cx + self.w / 2, self.cy + self.h / 2)

    def port(self, p, off=0.0):
        r = self.rect
        return {"l": (r.x0, self.cy + off), "r": (r.x1, self.cy + off),
                "t": (self.cx + off, r.y0), "b": (self.cx + off, r.y1)}[p]

    def draw(self, pg):
        st, fill = KIND[self.kind]
        pg.draw_rect(self.rect, color=st, fill=fill, width=1.0 if self.kind != "norm" else 0.8, radius=0.18)
        y = self.rect.y0 + 3.2 + ID_FS * 0.9
        text(pg, self.cx, y, self.show, "MB", ID_FS, BLK, "c")
        y += ID_FS * 0.3
        for ln in self.lines:
            y += LB_FS * 1.2
            text(pg, self.cx, y - 0.6, ln, "R", LB_FS, GRY, "c")


def clip(node, toward):
    """Điểm trên biên của nút theo hướng tới điểm 'toward'."""
    r = node.rect
    dx, dy = toward[0] - node.cx, toward[1] - node.cy
    if dx == 0 and dy == 0:
        return (node.cx, node.cy)
    tx = (r.width / 2) / abs(dx) if dx else 1e9
    ty = (r.height / 2) / abs(dy) if dy else 1e9
    t = min(tx, ty)
    return (node.cx + dx * t, node.cy + dy * t)


def arrowhead(pg, p, q, col, L=4.6, a=0.42):
    ang = math.atan2(q[1] - p[1], q[0] - p[0])
    p1 = (q[0] - L * math.cos(ang - a), q[1] - L * math.sin(ang - a))
    p2 = (q[0] - L * math.cos(ang + a), q[1] - L * math.sin(ang + a))
    pg.draw_polyline([p1, q, p2, p1], color=col, fill=col, width=0.4, closePath=True)


def polyline(pg, pts, st):
    for a, b in zip(pts, pts[1:]):
        pg.draw_line(a, b, color=st["color"], width=st["width"], dashes=st["dashes"])
    arrowhead(pg, pts[-2], pts[-1], st["color"])


def edge(pg, A, B, st, src=None, dst=None, via=()):
    """src/dst: None = tự cắt theo biên; hoặc (cổng, độ lệch) hoặc toạ độ."""
    def resolve(n, spec, other):
        if spec is None:
            return clip(n, other)
        if isinstance(spec, tuple) and isinstance(spec[0], str):
            return n.port(*spec)
        return spec
    first_target = via[0] if via else (B.cx, B.cy)
    last_source = via[-1] if via else (A.cx, A.cy)
    p = resolve(A, src, first_target)
    q = resolve(B, dst, last_source)
    polyline(pg, [p, *via, q], st)


def self_loop(pg, n, st, side=0.22):
    r = n.rect
    x1, x2 = n.cx + n.w * side, n.cx + n.w * (side + 0.18)
    y = r.y0
    c1, c2 = (x1 - 1, y - 9), (x2 + 1, y - 9)
    pg.draw_bezier((x1, y), c1, c2, (x2, y), color=st["color"], width=st["width"])
    arrowhead(pg, c2, (x2, y), st["color"], L=3.8)


def self_loop_right(pg, n, st):
    r = n.rect
    x, y1, y2 = r.x1, n.cy - 5, n.cy + 5
    c1, c2 = (x + 11, y1 - 3), (x + 11, y2 + 3)
    pg.draw_bezier((x, y1), c1, c2, (x, y2), color=st["color"], width=st["width"])
    arrowhead(pg, c2, (x, y2), st["color"], L=3.8)


def legend(pg, x, y, items, fs=6.2):
    """items: ('node', kind, text) | ('edge', style, text) | ('text', s)."""
    for it in items:
        if it[0] == "node":
            st, fill = KIND[it[1]]
            pg.draw_rect((x, y - 5.5, x + 11, y + 1.5), color=st, fill=fill, width=0.8, radius=0.2)
            x += 14
        elif it[0] == "edge":
            s = it[1]
            pg.draw_line((x, y - 2), (x + 15, y - 2), color=s["color"], width=s["width"], dashes=s["dashes"])
            arrowhead(pg, (x, y - 2), (x + 17, y - 2), s["color"], L=3.8)
            x += 20
        x += text(pg, x, y, it[-1], "R", fs, BLK) + 9


def save(doc, name, zoom=4):
    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    pix.save(os.path.join(OUT, name))
    print("da luu", name, pix.width, "x", pix.height, "| in:", round(doc[0].rect.width), "x", round(doc[0].rect.height), "pt")


def check_overlap(nodes, tag):
    ns = list(nodes)
    for i in range(len(ns)):
        for j in range(i + 1, len(ns)):
            a, b = ns[i].rect, ns[j].rect
            if a.intersects(b):
                print("  !! chong nut", tag, ns[i].sid, ns[j].sid)


# =====================================================================================
# 1. MÔ HÌNH KẾT HỢP — chồng v0 và v1
# =====================================================================================
def tong_quan():
    d0 = json.load(open(SPEC + "thanhtoan_donhang_v0.json", encoding="utf-8"))["state_machine"]
    d1 = json.load(open(SPEC + "thanhtoan_donhang_v1.json", encoding="utf-8"))["state_machine"]
    assert d0["states"] == d1["states"] and d0["labeling"] == d1["labeling"]
    lab = d0["labeling"]
    e0, e1 = set(map(tuple, d0["transitions"])), set(map(tuple, d1["transitions"]))
    W, NW, PITCH = 450, 78, 31.5
    X = {"L": 46, "A": 130, "B": 250, "C": 345}
    BAR_R = (402, 436)
    BAR_L = (8, 32)

    # (bands) mỗi băng: tiêu đề, danh sách (state, cột, hàng trong băng)
    bands = [
        ("H1 · Tiếp nhận yêu cầu", [("h1_vao", "A", 0), ("h1_ok", "A", 1), ("h1_tran_1_byte", "B", 0), ("h1_tran_bo_dem", "B", 1)]),
        ("H2 · Tạo đơn", [("h2_vao", "A", 0), ("h2_ok", "A", 1), ("h2_null", "B", 0), ("h2_sai_kich_thuoc", "B", 1), ("h2_doc_rac", "B", 2)]),
        ("H3 · Tính tổng tiền", [("h3_vao", "A", 0), ("h3_ok", "A", 1), ("h3_tran_so", "B", 0), ("h3_so_am", "B", 1), ("h3_chia_0", "B", 2)]),
        ("H4 · Nhận callback", [("h4_vao", "A", 0), ("h4_ok", "A", 1), ("h4_tran_txn", "B", 0), ("h4_nhanh_an", "B", 1), ("h4_tu_choi_callback", "L", 1)]),
        ("H5 · Ghi log", [("h5_vao", "A", 0), ("h5_ok", "A", 1), ("h5_ro_ri", "B", 0), ("h5_format_string", "B", 1)]),
        ("H6 · Đóng phiên", [("h6_phien_ranh", "A", 0), ("h6_cb_giu", "A", 1), ("h6_to_giu", "B", 1), ("h6_giai_phong", "A", 2),
                             ("h6_tranh_chap", "B", 2), ("h6_double_free", "C", 1.5), ("h6_uaf", "C", 2.5),
                             ("ket_thuc_ok", "L", 3), ("h6_con_so_the", "B", 3.4)]),
    ]
    nodes = {}
    y = 22
    nodes["start"] = Node("start", "start", lab["start"], "init", X["A"], y, NW)
    y += 22
    band_rects = []
    for title, items in bands:
        top = y
        y0 = top + 23
        maxr = 0
        for sid, col, r in items:
            labels = [l for l in lab[sid] if not (len(l) == 2 and l[0] == "h" and l[1].isdigit())]
            nodes[sid] = Node(sid, sid, labels, kind_of(labels, False), X[col], y0 + r * PITCH, NW)
            maxr = max(maxr, r)
        bottom = y0 + maxr * PITCH + 17
        band_rects.append((title, top, bottom))
        y = bottom + 5
    H = y + 26
    doc, pg = new_page(W, H)

    # băng nền
    for i, (title, top, bottom) in enumerate(band_rects):
        x0 = 38 if i < 3 else 4
        pg.draw_rect((x0, top, BAR_R[0] - 6, bottom), color=None, fill=(0.95, 0.96, 0.98) if i % 2 == 0 else (0.98, 0.98, 0.99), radius=0.04)
        text(pg, 54, top + 9, title, "B", 7, (0.15, 0.25, 0.45))

    # hai trạng thái "thanh" ở hai bên
    top_all, bot_all = band_rects[0][1], band_rects[-1][2]
    rr = pymupdf.Rect(BAR_R[0], top_all + 10, BAR_R[1], bot_all - 2)
    st, fill = KIND["halt"]
    pg.draw_rect(rr, color=st, fill=fill, width=1.1, radius=0.12)
    s1, s2 = "dung_khong_an_toan", "{unsafe_halt}"
    L1, L2 = tl(s1, "MB", 8), tl(s2, "R", 7)
    cx, cy = (rr.x0 + rr.x1) / 2, (rr.y0 + rr.y1) / 2
    text(pg, cx - 1.5, cy + L1 / 2, s1, "MB", 8, BLK, rotate=90)
    text(pg, cx + 7.5, cy + L2 / 2, s2, "R", 7, GRY, rotate=90)
    halt = Node("dung_khong_an_toan", "", [], "halt", cx, cy, rr.width)
    halt.h = rr.height

    lr = pymupdf.Rect(BAR_L[0], band_rects[0][1] + 10, BAR_L[1], band_rects[2][2] - 2)
    st, fill = KIND["end"]
    pg.draw_rect(lr, color=st, fill=fill, width=1.1, radius=0.12)
    s1, s2 = "ket_thuc_tu_choi", "{flow_end, input_rejected, mem_clean}"
    L1, L2 = tl(s1, "MB", 7.4), tl(s2, "R", 6)
    cx, cy = (lr.x0 + lr.x1) / 2, (lr.y0 + lr.y1) / 2
    text(pg, cx - 0.5, cy + L1 / 2, s1, "MB", 7.4, BLK, rotate=90)
    text(pg, cx + 7, cy + L2 / 2, s2, "R", 6, GRY, rotate=90)
    rej = Node("ket_thuc_tu_choi", "", [], "end", cx, cy, lr.width)
    rej.h = lr.height
    nodes["dung_khong_an_toan"], nodes["ket_thuc_tu_choi"] = halt, rej
    assert set(nodes) == set(d0["states"]), set(d0["states"]) ^ set(nodes)

    def sty(e):
        return E_BOTH if (e in e0 and e in e1) else (E_V0 if e in e0 else E_V1)

    done = set()
    def E(a, b, **kw):
        e = (a, b)
        assert e in e0 or e in e1, e
        edge(pg, nodes[a], nodes[b], sty(e), **kw)
        done.add(e)

    N = nodes
    E("start", "h1_vao")
    for h in "12345":
        E(f"h{h}_vao", f"h{h}_ok")
    for a, b in [("h1_ok", "h2_vao"), ("h2_ok", "h3_vao"), ("h3_ok", "h4_vao"), ("h4_ok", "h5_vao"), ("h5_ok", "h6_phien_ranh")]:
        E(a, b)
    risk_of = {"h1_vao": ["h1_tran_1_byte", "h1_tran_bo_dem"], "h2_vao": ["h2_null", "h2_sai_kich_thuoc", "h2_doc_rac"],
               "h3_vao": ["h3_tran_so", "h3_so_am", "h3_chia_0"], "h4_vao": ["h4_tran_txn", "h4_nhanh_an"],
               "h5_vao": ["h5_ro_ri", "h5_format_string"]}
    for v, rs in risk_of.items():
        for r in rs:
            E(v, r, src=("r", 0), dst=("l", 0))
    # risk -> dừng không an toàn
    for sid in d0["states"]:
        if sid != "dung_khong_an_toan" and (sid, "dung_khong_an_toan") in e0 | e1:
            n = N[sid]
            E(sid, "dung_khong_an_toan", src=("r", 0), dst=(BAR_R[0], n.cy))
    # v1: từ chối đầu vào
    for v in ["h1_vao", "h2_vao", "h3_vao"]:
        E(v, "ket_thuc_tu_choi", src=("l", 0), dst=(BAR_L[1], N[v].cy))
    # H4 callback bị từ chối -> phiên rảnh (đi dọc cột trái)
    tc = N["h4_tu_choi_callback"]
    E("h4_vao", "h4_tu_choi_callback", src=("l", 0), dst=("t", 0), via=((tc.cx, N["h4_vao"].cy),))
    E("h4_tu_choi_callback", "h6_phien_ranh", src=("b", 0), dst=("l", 0), via=((tc.cx, N["h6_phien_ranh"].cy),))
    # H6
    E("h6_phien_ranh", "h6_cb_giu")
    E("h6_phien_ranh", "h6_to_giu", src=("r", 0), dst=("t", 0), via=((N["h6_to_giu"].cx, N["h6_phien_ranh"].cy),))
    E("h6_cb_giu", "h6_giai_phong")
    E("h6_to_giu", "h6_tranh_chap")
    E("h6_cb_giu", "h6_tranh_chap", src=("r", 0), dst=("l", -4))
    E("h6_to_giu", "h6_giai_phong", src=("l", 0), dst=("r", -4))
    E("h6_tranh_chap", "h6_double_free", src=("r", 0), dst=("l", 0))
    E("h6_tranh_chap", "h6_uaf", src=("r", 0), dst=("l", 0))
    E("h6_giai_phong", "ket_thuc_ok", src=("l", 0), dst=("t", 0), via=((N["ket_thuc_ok"].cx, N["h6_giai_phong"].cy),))
    E("h6_giai_phong", "h6_con_so_the", src=("b", 20), dst=("l", 0))
    # tự lặp
    for sid in ["ket_thuc_ok"]:
        self_loop(pg, N[sid], sty((sid, sid)), side=0.12)
        done.add((sid, sid))
    for n, key in [(halt, "dung_khong_an_toan"), (rej, "ket_thuc_tu_choi")]:
        r = n.rect
        x1, x2 = r.x0 + 4, r.x1 - 4
        pg.draw_bezier((x1, r.y0), (x1 - 2, r.y0 - 10), (x2 + 2, r.y0 - 10), (x2, r.y0), color=E_BOTH["color"], width=0.8)
        arrowhead(pg, (x2 + 2, r.y0 - 10), (x2, r.y0), E_BOTH["color"], L=3.8)
        done.add((key, key))
    missing = (e0 | e1) - done
    assert not missing, missing

    for sid, n in nodes.items():
        if sid not in ("dung_khong_an_toan", "ket_thuc_tu_choi"):
            n.draw(pg)
    check_overlap([n for k, n in nodes.items() if k not in ("dung_khong_an_toan", "ket_thuc_tu_choi")], "tong_quan")

    ly = H - 15
    legend(pg, 6, ly, [("node", "init", "khởi tạo"), ("node", "norm", "bình thường"), ("node", "risk", "lỗi (có nhãn violation)"),
                       ("node", "end", "kết thúc"), ("node", "halt", "dừng không an toàn")])
    legend(pg, 6, ly + 10, [("edge", E_BOTH, "có ở cả v0 và v1"), ("edge", E_V0, "chỉ có ở v0 (bản sửa cắt bỏ)"),
                            ("edge", E_V1, "chỉ có ở v1 (nhánh từ chối mới)")])
    print("canh: chung", len(e0 & e1), "| chi v0", len(e0 - e1), "| chi v1", len(e1 - e0), "| |R| v0 =", len(e0), "v1 =", len(e1))
    save(doc, "h33_tong_quan.png")


# =====================================================================================
# 2. SÁU MÔ HÌNH CON
# =====================================================================================
POS = {
    "M1": {
        "_common": {"nhan_chuoi": (0, 1), "len_nho": (1, 0), "len_bang_16": (1, 1), "len_lon": (1, 2), "chep_dung": (2, 0)},
        "v0": {"tran_1_byte": (2, 1), "tran_nhieu_byte": (2, 2)},
        "v1a": {"cat_cut": (2, 1.5)},
        "v1b": {"tu_choi": (2, 2)},
    },
    "M2": {
        "_common": {"nhan_n": (0, 2), "n_hop_le": (1, 1), "malloc_null": (2, 2), "da_khoi_tao": (3, 0), "su_dung": (4, 0)},
        "v0": {"n_bat_thuong": (1, 3), "cap_phat_chua_kt": (2, 0), "tran_heap": (2, 3), "doc_rac": (3, 1), "null_deref": (3, 2)},
        "v1": {"tu_choi": (2, 3)},
    },
    "M3": {
        "_common": {"nhan_du_lieu": (0, 1), "dau_vao_hop_le": (1, 0), "nhan_dong": (2, 0), "cong_don": (3, 0), "tong_hop_le": (4, 0)},
        "v0": {"dau_vao_am": (1, 1), "ky_han_0": (1, 2), "tong_am": (2, 1), "chia_0": (2, 2), "tran_nhan": (3, 1), "tran_cong_don": (4, 1)},
        "v1": {"tu_choi": (3, 1.5)},
    },
    "M4": {
        "_common": {"nhan_callback": (0, 1), "txn_hop_le": (1, 0.4), "kiem_chu_ky": (2, 0), "chu_ky_dung": (3, 0), "chap_nhan": (4, 0)},
        "v0": {"txn_qua_dai": (1, 2), "nhanh_an": (2, 1), "tran_txn": (2, 2), "tu_choi": (3, 1)},
        "v1": {"tu_choi": (3, 1.5)},
    },
    "M5": {
        "_common": {"bat_dau": (0, 1), "cap_phat": (1, 1), "ghi_noi_dung": (2, 1), "in_an_toan": (3, 0), "loi_ghi_dia": (3, 2)},
        "v0": {"format_string": (3, 1), "giai_phong": (4, 0), "ro_ri": (4, 2)},
        "v1": {"giai_phong": (4, 1)},
    },
    "M6": {
        "_common": {"phien_mo": (0, 1.5), "cb_giu": (1, 0.5), "to_giu": (1, 2.5)},
        "v0": {"giai_phong": (2, 0.5), "tranh_chap": (2, 2.5), "con_so_the": (3, 1.3), "double_free": (3, 3.3),
               "da_dong": (4, 0), "uaf": (4, 2)},
        "v1": {"giai_phong": (2, 1.5), "xoa_trang": (3, 1.5), "da_dong": (4, 1.5), "den_sau_bo_qua": (5, 1.5)},
    },
}
# Kết quả kiểm chứng của từng luồng (results/logs/kiem_chung_nhom.txt, khớp tab Ch1 của SecLabFramework)
KQ = {
    "M1-v0": ("AG(!buffer_overflow), AG(!off_by_one), AF(done)", 2),
    "M1-v1a": ("AG(!truncated), AF(done)", 2),
    "M1-v1b": (None, 3),
    "M2-v0": ("AG(!null_deref), AG(!heap_overflow), AG(!uninit_read), AF(done)", 2),
    "M2-v1": (None, 4),
    "M3-v0": ("AG(!int_overflow), AG(!negative_amount), AG(!div_by_zero), AF(done)", 2),
    "M3-v1": (None, 5),
    "M4-v0": ("AG(!buffer_overflow), AG(!hidden_bypass), AF(done)", 2),
    "M4-v1": (None, 5),
    "M5-v0": ("AG(!mem_leak), AG(!format_string), AF(freed)", 3),
    "M5-v1": (None, 5),
    "M6-v0": ("AG(!race), AG(!double_free), AG(!use_after_free), AG(!secret_residue), AF(session_freed), loại trừ lẫn nhau", 2),
    "M6-v1": (None, 6),
}
FILES = {"M1": "M1_tiep_nhan_yeu_cau.json", "M2": "M2_tao_don_cap_phat.json", "M3": "M3_tinh_tong_tien.json",
         "M4": "M4_nhan_callback.json", "M5": "M5_ghi_log.json", "M6": "M6_dong_phien.json"}


def mo_hinh_con(key, out):
    spec = json.load(open(SPEC + "mo_hinh_con/" + FILES[key], encoding="utf-8"))
    flows = list(spec["flows"].items())
    pos = POS[key]
    allcols = [c for k, v in pos.items() for (c, r) in v.values()]
    maxc = max(allcols)
    W, NW, M = 450, 64, 8
    pitch = min(118, (W - 2 * M - NW - 12) / maxc)
    span = NW + pitch * maxc
    x0 = (W - 12 - span) / 2 + NW / 2
    RP = 33
    pre = "m" + key[1] + "_"

    # dựng trước để biết chiều cao
    panels = []
    for name, fl in flows:
        tag, rest = name.split(":", 1)
        ver = tag.split("-")[1]
        p = dict(pos["_common"]); p.update(pos[ver])
        lab = fl["labeling"]
        nodes = {}
        minr = min(p[x[len(pre):]][1] for x in fl["states"])
        for sid in fl["states"]:
            short = sid[len(pre):]
            assert short in p, (key, ver, short)
            c, r = p[short]
            nodes[sid] = Node(sid, short, lab.get(sid, []), kind_of(lab.get(sid, []), sid in fl["initial"]), x0 + c * pitch, (r - minr) * RP, NW)
        extra = set(k for k in p if pre + k not in fl["states"])
        if extra:
            print("  (vi tri khong dung o", tag, ":", extra, ")")
        code_lines = wrap(fl["description"].split(" "), "M", 5.3, W - 2 * M - 8, sep=" ")
        rows = max(r for (c, r) in [p[s[len(pre):]] for s in fl["states"]]) - minr
        gh = rows * RP + max(n.h for n in nodes.values())
        panels.append((tag, rest.strip(), fl, nodes, code_lines, gh))

    head_h = lambda cl: 13 + len(cl) * 6.6 + 14
    H = sum(head_h(cl) + gh + 22 for (_, _, _, _, cl, gh) in panels) + (len(panels) - 1) * 6 + 22
    doc, pg = new_page(W, H)
    y = 4
    for tag, rest, fl, nodes, cl, gh in panels:
        top = y
        bottom = top + head_h(cl) + gh + 22
        pg.draw_rect((3, top, W - 3, bottom), color=(0.75, 0.78, 0.84), fill=(0.985, 0.988, 0.995), width=0.7, radius=0.03)
        ver = tag.split("-")[1]
        ttl = {"v0": "Bản lỗi v0", "v1": "Bản sửa v1", "v1a": "Bản “an toàn” do phần mềm sinh (v1a)", "v1b": "Bản sửa của nhóm (v1b)"}[ver]
        w = text(pg, 10, top + 10.5, ttl, "B", 7.6, (0.15, 0.25, 0.45))
        text(pg, 10 + w + 6, top + 10.5, "— luồng " + tag + " trong đặc tả", "R", 6.4, GRY)
        cy = top + 13
        for ln in cl:
            cy += 6.6
            text(pg, 12, cy, ln, "M", 5.3, (0.25, 0.25, 0.4))
        gy = top + head_h(cl) + max(n.h for n in nodes.values()) / 2 - 4
        for n in nodes.values():
            n.cy += gy
        # cạnh
        for a, b in map(tuple, fl["transitions"]):
            if a == b:
                self_loop_right(pg, nodes[a], E_SUB)
            else:
                edge(pg, nodes[a], nodes[b], E_SUB)
        for n in nodes.values():
            n.draw(pg)
        check_overlap(nodes.values(), tag)
        bad, ct = KQ[tag]
        fy = bottom - 6
        if bad:
            w = text(pg, 10, fy, "Vi phạm: ", "B", 6.3, (0.7, 0.12, 0.12))
            w2 = text(pg, 10 + w, fy, bad, "R", 6.3, (0.7, 0.12, 0.12))
            text(pg, W - 10, fy, f"phản ví dụ ngắn nhất: k = {ct}", "I", 6.1, GRY, "r")
        else:
            text(pg, 10, fy, "Mọi thuộc tính đều đúng, loại trừ lẫn nhau đạt" if key == "M6" else "Mọi thuộc tính đều đúng", "B", 6.3, (0.1, 0.45, 0.18))
            text(pg, W - 10, fy, f"BMC đạt completeness threshold ở k = {ct}", "I", 6.1, GRY, "r")
        y = bottom + 6
    legend(pg, 6, H - 8, [("node", "init", "khởi tạo"), ("node", "norm", "bình thường"), ("node", "risk", "lỗi (nhãn violation)"),
                          ("node", "end", "kết thúc (nhãn done)"), ("text", "cung bên phải nút: tự lặp")])
    save(doc, out)


if __name__ == "__main__":
    tong_quan()
    for i, k in enumerate(["M1", "M2", "M3", "M4", "M5", "M6"]):
        mo_hinh_con(k, f"h3{4 + i}_{k.lower()}.png")
