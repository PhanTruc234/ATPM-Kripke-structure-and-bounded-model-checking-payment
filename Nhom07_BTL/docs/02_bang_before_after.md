# Bảng tổng hợp before/after (v0 ↔ v1)

Nguồn số liệu: chạy giao diện 2 phần mềm theo `docs/01` (ngày 13–14/10/2026) và bộ kiểm chứng của nhóm.
**Tầng 1** = phần mềm của GV tự phát hiện; **Tầng 2** = chỉ mô hình Kripke của nhóm phát hiện
(công cụ quét/sinh mã của phần mềm không thấy).

Cột **Minh chứng** ghi tên file, không kèm phần mở rộng:
- tên bắt đầu bằng số (`03_…`, `40_…`) hoặc `SLF_Ch1_…` là **ảnh** `.png` trong `results/screenshots/`;
- tên bắt đầu bằng `gui_…`, `kiem_chung_…` là **log** `.txt` trong `results/logs/` (nội dung đầy đủ của khung kết quả);
- tên kết thúc bằng `.pdf` là **báo cáo do phần mềm xuất** trong `results/tool_reports/`.

## 1. Tổng quan

| Chỉ số | v0 (cài lỗi) | v1 (đã sửa) | Minh chứng |
|---|---|---|---|
| Công thức CTL VI PHẠM (21 công thức, mô hình kết hợp 35 trạng thái) | 18 | 0 | `03_SVL_Ch1_KetQuaCTL_v0/v1`, `gui_SVL_Ch1_KetQuaCTL_v0/v1` |
| Mutual exclusion `cb_locked` / `to_locked` | VI PHẠM | ĐÚNG | `05_SVL_Pipeline_Ch2Ch3_v0/v1` (dòng đầu khung) |
| Deadlock | không có | không có | `03_SVL_Ch1_KetQuaCTL_v0/v1` (dòng thứ 2) |
| Static checker Ch2 (mã sinh từ HamSinhMa) | 5 phát hiện | 0 | `05_SVL_Pipeline_Ch2Ch3_v0/v1` |
| Z3 — cột DieuKien (5 kiểm tra số học) | 5 SAT (có phản ví dụ) | 5 UNSAT (chứng minh an toàn) | `gui_SVL_Pipeline_v0/v1` (mục Chương 3); nhập tay: `32_…`, `33_SLF_Ch3_SMT_v1` |
| BMC vòng lặp cộng dồn tiền (SecLabFramework, JSON) | vi phạm tại bước 48 | không vi phạm (unroll 45 bước) | `08_SLF_Ch6_BMC_Fuzz_v0/v1`; nhập tay: `30_…`, `31_SLF_Ch3_BMC_v1` |
| Fuzzing hàm Python | 2 hàm crash | hàm đã loại bỏ/thay bằng kiểm tra | `08_SLF_Ch6_BMC_Fuzz_v0`; `04_SVL_SinhMa_v1` ("0 hàm Python") |
| BMC của nhóm (`bounded_checker`), CT = 12 | 16/16 `AG(!x)` có counterexample | 16/16 an toàn, đã đạt CT | `40_Nhom_BMC_v0`, `41_Nhom_BMC_v1`, `kiem_chung_nhom` |
| 6 mô hình con (tab Ch1) | mọi luồng v0 vi phạm | mọi luồng v1 đúng | `SLF_Ch1_M1.pdf` … `SLF_Ch1_M6.pdf`, `gui_SLF_Ch1_M*_*` |
| Tổng phân loại CWE — SpecVerificationLab | 31 | 5 (CWE-190 từ BieuThucTran) | `06_SVL_Pipeline_CWE_v0/v1`, `SVL_v0.pdf`, `SVL_v1.pdf` |
| Tổng phân loại CWE — SecLabFramework (JSON) | 42 | 15 (5 CWE-190 + 10 khuyến nghị Ch5 mức LOW) | `09_SLF_Ch6_CWE_v0/v1`, `SLF_v0.pdf`, `SLF_v1.pdf` |

5 + 10 phân loại còn lại ở v1 **không phải lỗi của thiết kế v1** — giải thích ở `docs/03` mục 3 và 4.

## 2. Chi tiết từng trường hợp rủi ro

| Mã | Hành vi | CWE | Thuộc tính / trạng thái | v0 — bằng chứng | v1 — bằng chứng | Tầng | Minh chứng |
|---|---|---|---|---|---|---|---|
| C1.2 | H1 | 193, 787 | `AG(!off_by_one)` · `h1_tran_1_byte` | VI PHẠM; BMC k=2: `start→h1_vao→h1_tran_1_byte`; Ch2 `strcpy` dòng 8 | ĐÚNG; BMC an toàn (CT); Ch2 0; M1-v1b ĐÚNG | 1 | v0: `03_SVL_Ch1_KetQuaCTL_v0`, `40_Nhom_BMC_v0`, `05_SVL_Pipeline_Ch2Ch3_v0` · v1: `41_Nhom_BMC_v1`, `05_SVL_Pipeline_Ch2Ch3_v1`, `SLF_Ch1_M1.pdf` |
| C1.3 | H1 | 120, 121 | `AG(!buffer_overflow)` · `h1_tran_bo_dem` | VI PHẠM; Ch2 `strcpy` dòng 8 (CWE-120) | ĐÚNG; mô hình từ chối khi > 16 ký tự (mã sinh tự động chỉ cắt — `docs/03` mục 7) | 1 | v0: `03_SVL_Ch1_KetQuaCTL_v0`, `04_SVL_SinhMa_v0` (`char buffer[16]; strcpy`) · v1: `03_SVL_Ch1_KetQuaCTL_v1`, `04_SVL_SinhMa_v1` (`buffer[17]`) |
| C1.4 | H1 | 222 | M1: `AG(!truncated)` · `m1_cat_cut` | M1-v1a (bản "an toàn" phần mềm sinh): VI PHẠM, k=2 `m1_nhan_chuoi→m1_len_bang_16→m1_cat_cut` | M1-v1b (buf[17] + strnlen): ĐÚNG | **2** | v0: `SLF_Ch1_M1_v1a_KetQua`, `SLF_Ch1_M1_SoDo_v1a` · v1: `SLF_Ch1_M1_SoDo_v1b`, `SLF_Ch1_M1.pdf` |
| C2.2 | H2 | 476, 690 | `AG(!null_deref)` · `h2_null` | VI PHẠM, k=4; Ch2 **không** phát hiện (create_order_items sạch) | ĐÚNG; M2-v1 ĐÚNG | **2** | v0: `SLF_Ch1_M2_v0_KetQua`, `40_Nhom_BMC_v0`, `05_SVL_Pipeline_Ch2Ch3_v0` (không có dòng nào cho `create_order_items`) · v1: `SLF_Ch1_M2.pdf`, `41_Nhom_BMC_v1` |
| C2.3 | H2 | 190→680 | `AG(!heap_overflow)` · Z3 `alloc_bytes` | VI PHẠM, k=4; Z3 SAT `n_items = 67.107.688` (× 48 byte > INT_MAX) | ĐÚNG; Z3 UNSAT (n ≤ 100) | 1 | v0: `SLF_Ch1_M2_v0_KetQua`, `40_Nhom_BMC_v0`, `gui_SVL_Pipeline_v0` · v1: `SLF_Ch1_M2.pdf`, `gui_SVL_Pipeline_v1` |
| C2.4 | H2 | 457, 908 | `AG(!uninit_read)` · `h2_doc_rac` | VI PHẠM, k=4; Ch2 không phát hiện | ĐÚNG (calloc) | **2** | v0: `SLF_Ch1_M2_v0_KetQua`, `40_Nhom_BMC_v0` · v1: `SLF_Ch1_M2.pdf`, `41_Nhom_BMC_v1` |
| C3.2 | H3 | 190 | `AG(!int_overflow)` · Z3 `order_total_int32`, `line_amount_mul` | VI PHẠM, k=6; SAT `(2147483647, 1)`, `price = 33.765.495 × qty = 509` | ĐÚNG; 2 kiểm tra UNSAT | 1 | v0: `40_Nhom_BMC_v0`, `gui_SVL_Pipeline_v0`, `32_SLF_Ch3_SMT_v0`, `34_SLF_Ch3_Overflow` · v1: `33_SLF_Ch3_SMT_v1`, `gui_SVL_Pipeline_v1` |
| C3.3 | H3 | 190 | Z3 `accumulated_total` · BMC vòng lặp | SAT; BMC vi phạm bước 48, `total = 2.160.000.000` | UNSAT; BMC dừng ở `i = 44`, `total = 1.980.000.000` | 1 | v0: `08_SLF_Ch6_BMC_Fuzz_v0`, `30_SLF_Ch3_BMC_v0`, `gui_SLF_Ch3_BMC_v0` · v1: `08_SLF_Ch6_BMC_Fuzz_v1`, `31_SLF_Ch3_BMC_v1`, `gui_SLF_Ch3_BMC_v1` |
| C3.4 | H3 | 191, 839 | `AG(!negative_amount)` · Z3 `negative_total` | VI PHẠM, k=6; SAT `(subtotal 0, discount 1)` | ĐÚNG; UNSAT | 1 | v0: `40_Nhom_BMC_v0`, `gui_SVL_Pipeline_v0` · v1: `41_Nhom_BMC_v1`, `gui_SVL_Pipeline_v1` (dòng `negative_total: unsat model=None`) |
| C3.5 | H3 | 369 (phần mềm ghi 248) | `AG(!div_by_zero)` · fuzz `installment_amount` | VI PHẠM, k=6; black-box 11/300 lần ZeroDivisionError | ĐÚNG; M3-v1 ĐÚNG (1 ≤ months ≤ 24) | 1 | v0: `08_SLF_Ch6_BMC_Fuzz_v0`, `40_Nhom_BMC_v0` · v1: `SLF_Ch1_M3.pdf`, `41_Nhom_BMC_v1` |
| C4.2 | H4 | 120 | `AG(!buffer_overflow)` · `h4_tran_txn` | VI PHẠM; Ch2 `strcpy` dòng 15 | ĐÚNG; Ch2 0 | 1 | v0: `05_SVL_Pipeline_Ch2Ch3_v0`, `04_SVL_SinhMa_v0` · v1: `05_SVL_Pipeline_Ch2Ch3_v1`, `04_SVL_SinhMa_v1` (`buffer[21]`) |
| C4.3 | H4 | 912, 798 | `AG(!hidden_bypass)` · fuzz `ipn_debug_bypass` | VI PHẠM, k=8; black-box **0/300**; concolic tìm (31337, 8080) sau 3 lần thử | ĐÚNG; hàm cửa sau đã xóa; M4-v1 ĐÚNG | 1 | v0: `08_SLF_Ch6_BMC_Fuzz_v0`, `40_Nhom_BMC_v0` · v1: `04_SVL_SinhMa_v1` ("0 hàm Python"), `SLF_Ch1_M4.pdf` |
| C5.2 | H5 | 401 | `AG(!mem_leak)` · `h5_ro_ri` | VI PHẠM, k=10; Ch2 memory-leak dòng 28 | ĐÚNG; Ch2 0 | 1 | v0: `05_SVL_Pipeline_Ch2Ch3_v0`, `40_Nhom_BMC_v0` · v1: `05_SVL_Pipeline_Ch2Ch3_v1`, `41_Nhom_BMC_v1` |
| C5.3 | H5 | 134 | M5: `AG(!format_string)` | VI PHẠM, k=10; M5-v0 VI PHẠM | ĐÚNG; M5-v1 ĐÚNG | **2** | v0: `SLF_Ch1_M5_SoDo_v0`, `SLF_Ch1_M5.pdf`, `40_Nhom_BMC_v0` · v1: `SLF_Ch1_M5_SoDo_v1`, `SLF_Ch1_M5.pdf`, `41_Nhom_BMC_v1` |
| C6.2 | H6 | 362, 667 | Mutex + `AG(!race)` · `h6_tranh_chap` | VI PHẠM, k=11 | ĐÚNG | 1 | v0: `SLF_Ch1_M6_v0_KetQua` (`GIỮ ĐƯỢC? False`), `05_SVL_Pipeline_Ch2Ch3_v0`, `40_Nhom_BMC_v0` · v1: `SLF_Ch1_M6_v1_KetQua` (`True`), `05_SVL_Pipeline_Ch2Ch3_v1` |
| C6.3 | H6 | 415 | `AG(!double_free)` · `h6_double_free` | VI PHẠM, k=12; Ch2 double-free dòng 38 | ĐÚNG; Ch2 0 | 1 | v0: `05_SVL_Pipeline_Ch2Ch3_v0`, `SLF_Ch1_M6_v0_KetQua` · v1: `05_SVL_Pipeline_Ch2Ch3_v1`, `SLF_Ch1_M6_v1_KetQua` |
| C6.4 | H6 | 416 | `AG(!use_after_free)` · `h6_uaf` | VI PHẠM, k=12; Ch2 use-after-free dòng 46 | ĐÚNG; Ch2 0 | 1 | v0: `05_SVL_Pipeline_Ch2Ch3_v0`, `SLF_Ch1_M6_v0_KetQua` · v1: `05_SVL_Pipeline_Ch2Ch3_v1`, `SLF_Ch1_M6_v1_KetQua` |
| C6.5 | H6 | 226, 244, 14 | `AG(!secret_residue)` · `h6_con_so_the` | VI PHẠM, k=12; M6-v0 VI PHẠM | ĐÚNG (explicit_bzero); M6-v1 ĐÚNG | **2** | v0: `SLF_Ch1_M6_v0_KetQua`, `40_Nhom_BMC_v0` · v1: `SLF_Ch1_M6_v1_KetQua`, `41_Nhom_BMC_v1` |
| Toàn luồng | — | 693 | `AF(flow_end)`, `EF(input_rejected)` | cả 2 VI PHẠM (đường đi rơi vào `dung_khong_an_toan`; không có nhánh từ chối) | cả 2 ĐÚNG | 1 | v0: `40_Nhom_BMC_v0` (mục [2]), `gui_SVL_Ch1_KetQuaCTL_v0` · v1: `05_SVL_Pipeline_Ch2Ch3_v1` (dòng đầu khung), `41_Nhom_BMC_v1` |

Ghi chú:
- **k** là số bước của counterexample ngắn nhất (BMC của nhóm). Completeness threshold của mô hình kết hợp
  là **CT = 12**: mọi trạng thái đạt tới được đều nằm trong ≤ 12 bước, nên "an toàn" của v1 là kết luận đầy đủ.
- **Giá trị phản ví dụ của Z3** (vd `n_items`, `price × qty`) lấy từ log giao diện `gui_SVL_Pipeline_v0`. Z3 có thể
  trả về giá trị khác ở lần chạy khác (bước nhập tay D3 ra `price = 33.379.327, qty = 938`); kết luận SAT/UNSAT
  không đổi. Khi trích vào báo cáo, dùng đúng giá trị có trong ảnh/log được trích.
- Tầng 2 gồm **5 trường hợp** (C1.4, C2.2, C2.4, C5.3, C6.5). So với danh mục ban đầu, C3.4 chuyển lên tầng 1
  vì đặc tả đã có dòng `negative_total` trong sheet KiemTraSoHoc, còn C5.3 xuống tầng 2 vì khuôn mẫu sinh mã
  của phần mềm không tạo được lỗi chuỗi định dạng.
