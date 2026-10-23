# Bảng truy vết và bảng ràng buộc đầu vào

Đáp ứng 2 ghi chú của giảng viên trong buổi báo cáo tiến độ:
1. *"Từ yêu cầu chức năng → trạng thái → sơ đồ trạng thái"* → **Bảng A3** (mục 1).
2. *"Yêu cầu về đầu vào cụ thể làm việc với memory/buffer → ràng buộc (kiểu dữ liệu, size, cách thức gọi dữ liệu)"*
   → **Bảng A4** (mục 2).

Nguồn dữ liệu: `source/spec/thanhtoan_donhang_v0.xlsx` / `v1.xlsx` (sheet YeuCauChucNang, MoHinhTrangThai,
ThuocTinhAnToan, RangBuoc, HamSinhMa, KiemTraSoHoc) và `source/spec/mo_hinh_con/*.json`.
Cách truy vết: mỗi yêu cầu ghi kèm **mã trường hợp** (C1.2, C2.2…); cùng mã đó xuất hiện ở cột `MaTruongHop`
của sheet MoHinhTrangThai và cột `GhiChu` của sheet ThuocTinhAnToan.
*Bảng được lập với sự hỗ trợ của AI (đọc file Excel bằng script để dò mã trường hợp); nhóm đã rà soát.*

---

## 1. Bảng A3 — Yêu cầu chức năng → Trạng thái → Sơ đồ

Trạng thái rủi ro ghi kèm nhãn lỗi trong ngoặc. Ảnh sơ đồ nằm trong `results/screenshots/`.

| Yêu cầu | Nội dung tóm tắt | Hành vi | Trạng thái bình thường | Trạng thái rủi ro (nhãn) – bản v0 | Bản v1 sửa bằng cách | Thuộc tính kiểm chứng | Sơ đồ |
|---|---|---|---|---|---|---|---|
| REQ-01 | Không ghi vượt bộ đệm mã đơn, kể cả khi mã dài đúng 16 ký tự | H1 | `h1_vao` → `h1_ok` | `h1_tran_1_byte` (off_by_one), `h1_tran_bo_dem` (buffer_overflow) | Bộ đệm 17 byte, mã > 16 ký tự → `ket_thuc_tu_choi` | `AG(!off_by_one)`, `AG(!buffer_overflow)` | `SLF_Ch1_M1_SoDo_v0` / `_v1b` |
| REQ-02 | Mã đơn hợp lệ không bị cắt cụt hay biến đổi | H1 | `m1_nhan_chuoi` → `m1_chep_dung` | `m1_cat_cut` (truncated) — **mô hình con M1, luồng v1a** | Luồng M1-v1b: chép nguyên vẹn hoặc từ chối | `AG(!truncated)` | `SLF_Ch1_M1_SoDo_v1a` / `_v1b` |
| REQ-03 | Kiểm tra NULL sau khi cấp phát mảng sản phẩm | H2 | `h2_vao` → `h2_ok` | `h2_null` (null_deref) | Kiểm tra NULL → `ket_thuc_tu_choi` | `AG(!null_deref)` | `SLF_Ch1_M2_SoDo_v0` / `_v1` |
| REQ-04 | Kích thước cấp phát (số dòng × 48 byte) không tràn số, không âm | H2 | `h2_vao` → `h2_ok` | `h2_sai_kich_thuoc` (alloc_size_overflow, heap_overflow) | Chỉ nhận 1 ≤ n ≤ 100 | `AG(!heap_overflow)` | `SLF_Ch1_M2_SoDo_v0` / `_v1` |
| REQ-05 | Không đọc dữ liệu đơn hàng trước khi khởi tạo | H2 | `h2_vao` → `h2_ok` | `h2_doc_rac` (uninit_read) | Dùng `calloc` (tự khởi tạo 0) | `AG(!uninit_read)` | `SLF_Ch1_M2_SoDo_v0` / `_v1` |
| REQ-06 | Tổng tiền không tràn int32, kể cả khi cộng dồn nhiều dòng | H3 | `h3_vao` → `h3_ok` | `h3_tran_so` (int_overflow) | Nhân bằng int64, hạn mức dòng 50 triệu, hạn mức đơn 2 tỷ | `AG(!int_overflow)` | `SLF_Ch1_M3_SoDo_v0` / `_v1` |
| REQ-07 | Số lượng, đơn giá, giảm giá, tổng tiền không âm | H3 | `h3_vao` → `h3_ok` | `h3_so_am` (negative_amount) | Kiểm tra miền đầu vào → `ket_thuc_tu_choi` | `AG(!negative_amount)` | `SLF_Ch1_M3_SoDo_v0` / `_v1` |
| REQ-08 | Trả góp không lỗi khi số kỳ = 0 | H3 | `h3_vao` → `h3_ok` | `h3_chia_0` (div_by_zero) | Chỉ nhận 1 ≤ months ≤ 24 | `AG(!div_by_zero)` | `SLF_Ch1_M3_SoDo_v0` / `_v1` |
| REQ-09 | Phân tích mã giao dịch từ callback không tràn bộ đệm | H4 | `h4_vao` → `h4_ok` | `h4_tran_txn` (buffer_overflow) | Mã > 20 ký tự → `h4_tu_choi_callback` | `AG(!buffer_overflow)` | `SLF_Ch1_M4_SoDo_v0` / `_v1` |
| REQ-10 | Mọi callback phải kiểm chữ ký, không có nhánh ẩn | H4 | `h4_vao` → `h4_ok` / `h4_tu_choi_callback` | `h4_nhanh_an` (hidden_bypass) | Xóa nhánh debug | `AG(!hidden_bypass)` | `SLF_Ch1_M4_SoDo_v0` / `_v1` |
| REQ-11 | Bản ghi log được giải phóng trên mọi nhánh, kể cả nhánh lỗi | H5 | `h5_vao` → `h5_ok` | `h5_ro_ri` (mem_leak) | `goto cleanup`: nhánh lỗi cũng `free` | `AG(!mem_leak)` | `SLF_Ch1_M5_SoDo_v0` / `_v1` |
| REQ-12 | Dữ liệu người dùng không làm chuỗi định dạng của printf | H5 | `h5_vao` → `h5_ok` | `h5_format_string` (format_string) | `printf("%s", msg)` | `AG(!format_string)` | `SLF_Ch1_M5_SoDo_v0` / `_v1` |
| REQ-13 | Hai worker không đồng thời giữ phiên | H6 | `h6_phien_ranh` → `h6_cb_giu` / `h6_to_giu` → `h6_giai_phong` | `h6_tranh_chap` (cb_locked + to_locked, race) | Mutex + trạng thái CLOSED | `AG(!race)` + kiểm tra loại trừ lẫn nhau `cb_locked`/`to_locked` | `SLF_Ch1_M6_SoDo_v0` / `_v1` |
| REQ-14 | Phiên chỉ được giải phóng đúng 1 lần | H6 | (như REQ-13) | `h6_double_free` (double_free) | Worker đến sau thấy CLOSED thì bỏ qua | `AG(!double_free)` | `SLF_Ch1_M6_SoDo_v0` / `_v1` |
| REQ-15 | Không truy cập phiên/bộ đệm thẻ sau khi giải phóng | H6 | (như REQ-13) | `h6_uaf` (use_after_free) | Như REQ-14, gán con trỏ về NULL | `AG(!use_after_free)` | `SLF_Ch1_M6_SoDo_v0` / `_v1` |
| REQ-16 | Xóa trắng số thẻ bằng lệnh không bị trình biên dịch bỏ | H6 | `h6_giai_phong` → `ket_thuc_ok` | `h6_con_so_the` (secret_residue) | `explicit_bzero` trước `free` | `AG(!secret_residue)` | `SLF_Ch1_M6_SoDo_v0` / `_v1` |
| REQ-17 | Mọi luồng xử lý cuối cùng phải kết thúc hợp lệ | Toàn luồng | `ket_thuc_ok`, `ket_thuc_tu_choi` (flow_end) | `dung_khong_an_toan` (unsafe_halt) — mọi trạng thái rủi ro dẫn vào đây | Không còn đường tới trạng thái rủi ro | `AF(flow_end)` | `02_SVL_Ch1_SoDo_1…4_v0` / `_v1` |
| REQ-18 | Luồng thành công đạt tới được; đầu vào xấu có nhánh từ chối | Toàn luồng | `ket_thuc_ok` (payment_done), `ket_thuc_tu_choi` (input_rejected) | v0 không có cạnh nào tới `ket_thuc_tu_choi` | Thêm các cạnh `hX_vao → ket_thuc_tu_choi` | `EF(payment_done)`, `EF(input_rejected)` | `02_SVL_Ch1_SoDo_1…4_v0` / `_v1` |

**Kết quả kiểm chứng tương ứng:** ở mô hình kết hợp v0, các thuộc tính của REQ-01, REQ-03…REQ-17, mutex và
`EF(input_rejected)` đều **VI PHẠM**, `EF(payment_done)` ĐÚNG; ở v1 tất cả **ĐÚNG**. Riêng REQ-02: `AG(!truncated)`
**VI PHẠM** ở luồng M1-v1a (bản "an toàn" phần mềm sinh) và ĐÚNG ở M1-v1b (bản sửa của nhóm). Chi tiết và minh
chứng: `docs/02`.

---

## 2. Bảng A4 — Đầu vào làm việc với bộ nhớ/bộ đệm → Ràng buộc

"Cách gọi/truy cập" mô tả hàm C dùng để đọc, ghi hoặc cấp phát dữ liệu đó — chính là chỗ rủi ro phát sinh.

| Đầu vào / vùng nhớ | Hành vi | Kiểu dữ liệu | Kích thước / miền giá trị | Cách gọi – bản v0 (rủi ro) | Cách gọi – bản v1 (đã ràng buộc) | Ràng buộc nguồn | Trạng thái liên quan |
|---|---|---|---|---|---|---|---|
| Mã đơn hàng `raw_order_id` | H1 | Chuỗi ký tự ASCII (`char *`) | Tối đa 16 ký tự → cần **17 byte** (thêm `'\0'`) | `strcpy` vào `char buffer[16]` — không kiểm tra độ dài | `char buffer[17]`; đo bằng `strnlen(src, 17)`, > 16 thì từ chối | CON-01; HamSinhMa `parse_order_id` (buffer 16 → 17) | `h1_tran_1_byte`, `h1_tran_bo_dem`, `m1_cat_cut` |
| Mã giao dịch `raw_txn_id` (từ callback) | H4 | Chuỗi ASCII (`char *`), **đến từ bên ngoài** | Tối đa 20 ký tự → cần 21 byte | `strcpy` vào `char buffer[20]` | `char buffer[21]`; `strnlen(src, 21) > 20` thì bỏ qua callback | CON-02; HamSinhMa `parse_gateway_txn_id` (20 → 21) | `h4_tran_txn` |
| Số dòng sản phẩm `n` | H2 | Số nguyên `int` | 1–100 dòng; mỗi dòng 48 byte → tối đa 4.800 byte | `malloc(n * 48)` — tích có thể tràn int32, n có thể âm; không kiểm tra NULL | Kiểm tra 1 ≤ n ≤ 100; `calloc(n, 48)`; kiểm tra NULL | CON-03; KiemTraSoHoc `alloc_bytes` | `h2_sai_kich_thuoc`, `h2_null` |
| Mảng sản phẩm `items` (vùng heap) | H2 | Mảng cấu trúc `Item` | n × 48 byte | Đọc `items[i].status` khi chưa gán (`malloc` không xóa rác) | `calloc` khởi tạo toàn bộ về 0 trước khi đọc | REQ-05 | `h2_doc_rac` |
| Đơn giá `price`, số lượng `qty` | H3 | Số nguyên có dấu 32-bit | `price` 0–50.000.000 VND; `qty` 1–1.000; giá trị 1 dòng ≤ 50.000.000 | `int line = price * qty` — tích tràn int32 | Nhân bằng `int64_t`; dòng > 50 triệu thì từ chối | CON-03; KiemTraSoHoc `line_amount_mul` | `h3_tran_so` |
| Tổng tiền `total` (cộng dồn) | H3 | Số nguyên có dấu 32-bit | Tối đa 2.147.483.647; hạn mức đơn 2.000.000.000 VND | `total += line` lặp nhiều dòng | Kiểm tra `total + line ≤ 2.000.000.000` **trước** khi cộng | CON-04; KiemTraSoHoc `accumulated_total`, `order_total_int32`; BMC vòng lặp | `h3_tran_so` |
| Giảm giá `discount` | H3 | Số nguyên 32-bit | 0 ≤ discount ≤ tạm tính | `total -= discount` — không kiểm tra dấu | Kiểm tra 0 ≤ discount ≤ subtotal | KiemTraSoHoc `negative_total` | `h3_so_am` |
| Phí giao hàng `shipping_fee` | H3 | Số nguyên 32-bit | 0–500.000 VND | Cộng thẳng vào tạm tính | Nằm trong hạn mức đơn 2 tỷ | KiemTraSoHoc `order_total_int32` | `h3_tran_so` |
| Số kỳ trả góp `months` | H3 | Số nguyên | 1–24 tháng | Dùng làm **mẫu số**: `total / months` | Kiểm tra 1 ≤ months ≤ 24 trước khi chia | CON-05; HamSinhMa `installment_amount` | `h3_chia_0` |
| `merchant_id`, `debug_pin` (từ callback) | H4 | Số nguyên | — | So sánh với hằng số ẩn → bỏ qua kiểm tra chữ ký | Xóa nhánh; mọi callback đều phải kiểm chữ ký | HamSinhMa `ipn_debug_bypass` | `h4_nhanh_an` |
| Bản ghi log `e` (vùng heap) | H5 | Con trỏ tới `LogEntry` | 1 bản ghi | `malloc`; nhánh lỗi `return` sớm, không `free` | `goto cleanup`: mọi nhánh đều `free(e)` | NFR-03; HamSinhMa `write_payment_log` | `h5_ro_ri` |
| Nội dung log `msg` (chứa dữ liệu người dùng) | H5 | Chuỗi ký tự | Theo kích thước bản ghi | `printf(msg)` — chuỗi người dùng thành chuỗi định dạng | `printf("%s", msg)` | REQ-12 | `h5_format_string` |
| Phiên thanh toán `s` (vùng heap, **dùng chung**) | H6 | Con trỏ tới `PaymentSession`, 2 luồng cùng truy cập | 1 phiên / giao dịch; tự hết hạn sau 15 phút | Hai worker cùng ghi `s->status` và cùng `free(s)`, không khóa | Khóa mutex; đặt `status = CLOSED`; worker đến sau thấy CLOSED thì bỏ qua; con trỏ về NULL | CON-06, NFR-04; HamSinhMa `close_payment_session` | `h6_tranh_chap`, `h6_double_free`, `h6_uaf` |
| Bộ đệm số thẻ `card` (PAN) | H6 | Mảng ký tự | **16 chữ số / 16 byte** | `memset(card, 0, 16)` rồi `free` — trình biên dịch có thể bỏ `memset` | `explicit_bzero(card, 16)` rồi `free` | CON-07, NFR-05; HamSinhMa `release_card_buffer` | `h6_con_so_the`, `h6_uaf` |

**Ghi chú:**
- Cột "Cách gọi – bản v1" mô tả mã **sau khi nhóm bổ sung kiểm tra**, đúng với mô hình v1 và các luồng con v1.
  Mã v1 do phần mềm tự sinh chỉ có phần kích thước bộ đệm (17, 21 byte); các bước kiểm tra như `strnlen`, kiểm tra NULL,
  hạn mức là phần nhóm bổ sung (xem `docs/03` mục 7).
- Các đầu vào **đến từ bên ngoài** (attack surface): mã đơn (từ trình duyệt/app), mã giao dịch, `merchant_id`,
  `debug_pin` và chữ ký (từ callback), ghi chú đơn hàng (đi vào nội dung log).
