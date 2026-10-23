# -*- coding: utf-8 -*-
"""
doc_dac_ta.py — Đọc mô hình Kripke + danh sách công thức từ CHÍNH các file nộp cho phần mềm:
  - file Excel 10 sheet (.xlsx) — đọc bằng thư viện chuẩn (zipfile + xml), KHÔNG cần openpyxl;
  - file đặc tả JSON (state_machine) và file mô hình con JSON (flows).
Nhờ vậy BMC của nhóm chạy trên ĐÚNG mô hình mà phần mềm kiểm chứng (không chép tay lại).
"""
from __future__ import annotations

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict

from kripke import KripkeStructure

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def _xlsx_sheets(path):
    """Trả về {tên_sheet: [dict(cột -> giá trị), ...]} — dòng 1 là tiêu đề cột."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % _NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    out = OrderedDict()
    for sh in wb.find("m:sheets", _NS):
        target = rels[sh.get("{%s}id" % _NS["r"])].lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        rows = []
        for row in ET.fromstring(z.read(target)).find("m:sheetData", _NS).findall("m:row", _NS):
            cells = {}
            for c in row.findall("m:c", _NS):
                col = re.sub(r"\d", "", c.get("r"))
                v, t = c.find("m:v", _NS), c.get("t")
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter("{%s}t" % _NS["m"]))
                else:
                    val = v.text if v is not None else ""
                cells[col] = val
            rows.append(cells)
        if not rows:
            out[sh.get("name")] = []
            continue
        header = rows[0]
        data = []
        for r in rows[1:]:
            d = {header[c]: r.get(c, "") for c in header}
            if any(str(v).strip() for v in d.values()):
                data.append(d)
        out[sh.get("name")] = data
    return out


def _split(s):
    return [x.strip() for x in str(s or "").split(",") if x.strip()]


def doc_excel(path):
    """-> (ten_dac_ta, KripkeStructure, [công thức CTL], (atom1, atom2) | None)"""
    sh = _xlsx_sheets(path)
    info = {r["Truong"]: r["GiaTri"] for r in sh.get("ThongTin", [])}
    d = {"states": [], "initial": [], "labeling": {}, "transitions": []}
    for r in sh.get("MoHinhTrangThai", []):
        s = r["TrangThai"].strip()
        d["states"].append(s)
        if str(r.get("KhoiTao", "")).strip().lower() == "x":
            d["initial"].append(s)
        d["labeling"][s] = _split(r.get("Nhan"))
        d["transitions"] += [[s, t] for t in _split(r.get("ChuyenDenCacTrangThai"))]
    formulas = [r["CongThucCTL"].strip() for r in sh.get("ThuocTinhAnToan", []) if r.get("CongThucCTL")]
    mx = sh.get("LoaiTruLanNhau", [])
    mutex = (mx[0]["MenhDe1"], mx[0]["MenhDe2"]) if mx else None
    return info.get("name", path), KripkeStructure.from_dict(d), formulas, mutex


def doc_json_dac_ta(path):
    d = json.load(open(path, encoding="utf-8"))
    mx = d.get("mutual_exclusion")
    return (d["name"], KripkeStructure.from_dict(d["state_machine"]), d.get("safety_properties", []),
            (mx["atom1"], mx["atom2"]) if mx else None)


def doc_mo_hinh_con(path):
    """-> (tiêu đề, OrderedDict{tên luồng: KripkeStructure}, [công thức], (atom1, atom2) | None)"""
    d = json.load(open(path, encoding="utf-8"), object_pairs_hook=OrderedDict)
    flows = OrderedDict((n, KripkeStructure.from_dict(f)) for n, f in d["flows"].items())
    mx = d.get("suggested_mutex_atoms")
    return d.get("title", path), flows, d.get("suggested_ctl_formulas", []), tuple(mx) if mx else None
