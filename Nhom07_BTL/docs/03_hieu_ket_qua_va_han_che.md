# Hiểu kết quả của phần mềm và các hạn chế (tư liệu cho mục 5–6 của báo cáo)

Các điểm dưới đây được nhóm **xác minh trực tiếp** bằng cách chạy mã kiểm chứng của SpecVerificationLab /
SecLabFramework trên đặc tả của nhóm và trên các mô hình thử nhỏ. Đây chính là phần "hiểu kết quả" mà giảng
viên yêu cầu — nêu được trong báo cáo sẽ cho thấy nhóm không chỉ chạy công cụ rồi dán kết quả.

## 1. Đọc bảng kết quả CTL

Dòng `AG(!off_by_one) -> VI PHAM (thoa tai: [...])`:
- `thoa tai` là tập **Sat(φ)** — các trạng thái mà công thức đúng tại đó.
- Công thức **ĐÚNG** khi **mọi trạng thái khởi tạo** thuộc Sat(φ). Ở v0, `start` không thuộc Sat(AG(!off_by_one))
  vì từ `start` có đường đi tới `h1_tran_1_byte` (mang nhãn `off_by_one`).
- Phần mềm chỉ cho kết luận ĐÚNG/SAI, **không cho đường đi phản ví dụ** — counterexample cụ thể lấy từ BMC của
  nhóm (`kiem_chung_nhom.txt`), ví dụ `start -> h1_vao -> h1_tran_1_byte` (k = 2).
- Với công thức dạng `EF(...)` thì "ĐÚNG" nghĩa là *có thể xảy ra*. Ví dụ `EF(input_rejected)` VI PHẠM ở v0 nghĩa là
  bản v0 **không có** nhánh từ chối đầu vào xấu — đây cũng là một lỗi thiết kế (CWE-693, Protection Mechanism Failure).

## 2. Dòng "Mutual exclusion"

- v0: `VI PHAM (trang thai nguy hiem: [h1_ok, h1_vao, …, h6_tranh_chap, start])` — danh sách này là **tập trạng thái
  đã duyệt**, không phải các trạng thái vi phạm. Trạng thái vi phạm thật là trạng thái mang **cả hai** nhãn:
  `h6_tranh_chap`.
- v1: `OK (trang thai nguy hiem: ['h6_tranh_chap'])` — `h6_tranh_chap` vẫn tồn tại trong mô hình (không gian trạng
  thái không đổi) nhưng **không còn đường đi tới** → OK. → Chỉ đọc kết luận VI PHAM/OK, không đọc danh sách.
- Cùng lý do đó, **sơ đồ v1 vẫn có các nút tô đỏ** (ảnh `03_SVL_Ch1_KetQuaCTL_v1.png`, `08_SLF_Ch6_BMC_Fuzz_v1.png`):
  phần mềm tô màu theo **nhãn** `violation`, không theo khả năng đạt tới. Ở v1 không còn đường đi nào từ `start` tới các
  nút đỏ (|R| giảm từ 53 xuống 41, số trạng thái đạt tới được giảm từ 34 xuống 18) → mọi `AG(!…)` đều ĐÚNG.

## 3. Vì sao v1 vẫn còn 5 phân loại CWE-190

Mỗi dòng sheet `KiemTraSoHoc` có 2 kiểm tra:
- **DieuKien** (`check_satisfiability`): nhóm viết miền giá trị **sau khi đã kiểm tra đầu vào** → v0 SAT, v1 UNSAT.
  Đây là bằng chứng an toàn thật của v1.
- **BieuThucTran** (`check_int32_overflow`): phần mềm luôn cho mỗi biến chạy trên **toàn miền int32**, không biết tới
  các kiểm tra đầu vào → tổng/tích 2 biến int32 *luôn* có thể tràn → luôn SAT ở cả v0 lẫn v1 (đúng như mục 3.9
  của "Hướng dẫn tạo Spec file dạng excel": "BieuThucTran cũng cho sat"). 5 dòng CWE-190 ở v1 là hệ quả của
  thiết kế công cụ, không phải lỗi còn sót. Ví dụ ở ảnh `06_SVL_Pipeline_CWE_v1.png`:
  `negative_total (int32 overflow?): sat model={'subtotal': -2, 'discount': 2147483647}` — `subtotal = -2` là giá
  trị mà kiểm tra đầu vào của v1 đã loại bỏ. (Log `gui_SVL_Pipeline_v1.txt` của lần chạy trước ghi
  `{'subtotal': 0, 'discount': -2147483648}`: Z3 chọn phản ví dụ khác nhau giữa các lần chạy, nhưng cả hai đều nằm
  ngoài miền v1 cho phép — `subtotal >= 0`, `discount >= 0`.)

**UNSAT ở v1 chứng minh điều gì** (cột DieuKien và bước D4 ở tab Ch3): mỗi dòng có dạng
*điều kiện chặn ∧ điều kiện xấu*. UNSAT nghĩa là **điều kiện chặn đủ để loại trừ trạng thái xấu**
(điều kiện chặn ⇒ an toàn). Có dòng gần như hiển nhiên: `line_amount_mul` v1 / D4 chứa cả `price * qty <= 50000000`
lẫn `price * qty > 2147483647`. Phần đáng giá nằm ở thiết kế: phép nhân phải được tính trên **int64 trước** khi so
với hạn mức. Nếu nhân trên int32 rồi mới kiểm tra, phép kiểm tra chạy trên giá trị đã tràn. Z3 ở đây làm việc trên số
nguyên toán học nên **không mô hình hóa** chi tiết kiểu dữ liệu đó — đây là một giả thiết của mô hình, phải nêu
trong báo cáo. Dòng `accumulated_total` v1 có ý nghĩa hơn: nó là **bước quy nạp** của vòng lặp cộng dồn
(`total_before <= 2000000000 - line_total` ⇒ tổng mới không vượt trần), khớp với BMC vòng lặp v1 dừng ở `i = 44`.

## 4. Các khuyến nghị "Chương 5" mức LOW (10 dòng ở SecLabFramework)

- `raw-new-delete -> CWE-772`: phần mềm khuyên thay malloc/free bằng `std::vector`/smart pointer — áp dụng cho C++,
  trong khi mã sinh ra là **C**. `missing-hardening-flags`, `missing-dynamic-verification`: nhắc biên dịch với
  `-Wall -fsanitize=…` và chạy valgrind/ASan. Đây là khuyến nghị quy trình, không ứng với trạng thái rủi ro nào.

## 5. Ánh xạ CWE của BMC vòng lặp

Phần mềm gán vi phạm bất biến vòng lặp vào **CWE-835 (Infinite Loop)**. Với đặc tả của nhóm, bất biến là
`total <= 2147483647`, nên CWE đúng là **CWE-190 (Integer Overflow)**. Ánh xạ CWE tự động mang tính chung — người
phân tích phải đối chiếu lại với ngữ nghĩa của thuộc tính.

Cột **"Ví dụ CVE minh họa"** cũng được gán tự động theo CWE và có chỗ không khớp. Ở v1 (ảnh
`09_SLF_Ch6_CWE_v1.png`, `06_SVL_Pipeline_CWE_v1.png`), cả 5 dòng CWE-190 đều kèm **CVE-2016-5195 ("Dirty COW")**.
Chính dòng mô tả của phần mềm ghi đó là "điều kiện tranh chấp" — tức một lỗi race condition (CWE-362), không phải
tràn số nguyên. Ngược lại, CWE-120 → **CVE-2003-0352** (tràn bộ đệm RPC/DCOM, bị sâu MSBlast khai thác) là ví dụ đúng.
→ Báo cáo chỉ trích CVE minh họa sau khi đã tự kiểm tra lại.

## 6. Tám ràng buộc/bẫy của phần mềm (đã xử lý trong đặc tả)

| # | Ràng buộc | Hệ quả nếu không biết | Cách nhóm xử lý |
|---|---|---|---|
| 1 | CTL chỉ nhận **1 toán tử + 1 nhãn** (có thể `!`) | Công thức ghép như `AG(!(a & b))`, `EF(a \| b)`, `AG(a -> AF(b))` **không báo lỗi mà cho kết quả sai** — xem `headless_bay_cong_thuc_ghep.txt`: `AG(!(cb_locked & to_locked))` ra ĐÚNG ở v0 dù có tranh chấp | Điều kiện ghép được gắn thành **1 nhãn riêng** (vd `use_after_free`); công thức ghép kiểm bằng `ctl_checker.py` của nhóm |
| 2 | Công thức đánh giá tại **tất cả** trạng thái khởi tạo | Nhiều mô hình rời nhau, mỗi mô hình 1 trạng thái khởi tạo → mọi `EF(...)` sai | Mô hình kết hợp có **1** trạng thái khởi tạo `start` |
| 3 | `additional_flows` chỉ để **hiển thị** | Tưởng đã kiểm chứng các luồng con | 6 mô hình con kiểm chứng ở tab Ch1 (file `flows`) |
| 4 | `LoaiTruLanNhau` chỉ kiểm **dòng đầu** | Cặp quan trọng ở dòng sau không được kiểm | Dòng đầu là `cb_locked / to_locked` |
| 5 | Excel **không có cột BMC** | Không chạy được BMC vòng lặp từ Excel | Thêm bản JSON với các trường `bmc_*` |
| 6 | Bộ phân tích biểu thức **không nhận số âm** dạng `-2000000000` | Pipeline dừng với lỗi `Cú pháp không hỗ trợ: UnaryOp` | Viết tương đương `discount + 2000000000 >= 0` |
| 7 | Fuzzer đoán kiểu tham số **theo tên**: tên chứa `code, key, name, data, msg, token, …` bị coi là chuỗi | Black-box "crash 300/300" do TypeError giả, che mất ý nghĩa so sánh black-box ↔ concolic | Đặt tên `merchant_id, debug_pin` → black-box 0/300, concolic tìm ra sau 3 lần thử |
| 8 | Static checker dựa trên **regex trong phạm vi 1 hàm** | Không thấy thiếu kiểm tra NULL, đọc chưa khởi tạo, lỗi xuyên hàm | Các lỗi này nằm ở **tầng 2** — phát hiện bằng mô hình Kripke |

## 7. Hai "lỗi trong bản sửa" mà phần mềm không báo

1. **Quy ước KichThuocBuffer = độ dài tối đa** (hướng dẫn Excel mục 3.8): mã đơn tối đa 16 ký tự cần **17 byte**.
   Với `strcpy`, mã dài đúng 16 ký tự (hợp lệ) ghi 17 byte → lệch 1 byte (C1.2).
2. **Khuôn mẫu "an toàn"** của `buffer_copy` là `strncpy(buffer, src, sizeof(buffer) - 1); buffer[sizeof(buffer)-1] = '\0';`
   → không tràn nhưng **cắt âm thầm** mã đơn 16 ký tự còn 15 (C1.4) → có thể trùng mã đơn khác. Bản sửa của
   nhóm: bộ đệm 17 byte và **từ chối** đầu vào dài hơn 16 thay vì cắt (`M1-v1b`).

Ngoài ra, khuôn mẫu Python `divide` / `magic_value` không có biến thể "đã sửa", nên bản v1 loại 2 hàm này; bằng
chứng an toàn của v1 cho C3.5 và C4.3 lấy từ mô hình M3-v1, M4-v1 và các kiểm tra Z3.

**Khoảng cách giữa mô hình v1 và mã v1 do phần mềm sinh** (phải nêu trong báo cáo): mã v1 sinh tự động (ảnh
`04_SVL_SinhMa_v1.png`) chỉ là **khung theo khuôn mẫu**. Ví dụ:
- `parse_order_id` có `buffer[17]` + `strncpy(…, sizeof(buffer) - 1)` → mã 16 ký tự được chép nguyên vẹn (hết C1.2,
  C1.4), nhưng đầu vào **dài hơn 16 ký tự vẫn bị cắt im lặng**, không bị từ chối.
- `create_order_items` vẫn là `malloc` không kiểm tra NULL.

Mô hình kết hợp v1 (cạnh `h1_vao → ket_thuc_tu_choi`, `h2_vao → ket_thuc_tu_choi`, …) và các luồng con v1
(M1-v1b, M2-v1, …) mô tả **mã sau khi nhóm bổ sung các kiểm tra** mà khuôn mẫu không biểu diễn được (strnlen + từ chối,
kiểm tra n và NULL + calloc, int64 + hạn mức, mutex + explicit_bzero). Static checker báo "0 phát hiện" trên mã v1
sinh ra **không** chứng minh các kiểm tra này tồn tại — đó cũng chính là lý do các lỗi tầng 2 chỉ được chứng minh
trên mô hình.

## 8. Giới hạn của chính phương pháp (trung thực — mục "Thảo luận & Hạn chế")

- **Trừu tượng hóa:** mô hình Kripke là trừu tượng hóa của mã — mỗi trạng thái đại diện cho một lớp trường hợp
  (vd "độ dài = 16"). Kết luận đúng **trên mô hình**; mức độ khớp với mã thật dựa trên bảng ánh xạ trạng thái ↔
  câu lệnh (cột GhiChu của sheet MoHinhTrangThai và trường `description` của từng luồng con).
- **BMC tường minh:** `bounded_checker` duyệt BFS theo trạng thái tường minh, không mã hóa SAT; phù hợp mô hình
  nhỏ (35 trạng thái), không mở rộng được cho mã thật (bùng nổ trạng thái — giáo trình mục 3.5.1).
- **Completeness threshold:** CT = 12 là độ sâu BFS chạm hết trạng thái đạt tới được; `bmc_check` chỉ *xác nhận*
  đã đạt CT ở k = CT + 1 = 13 (frontier ở độ sâu 12 phải được mở thêm 1 bước mới biết rỗng).
  CT chỉ đảm bảo đầy đủ cho thuộc tính **safety** (`AG(!x)`); thuộc tính **liveness** (`AF`) được kiểm bằng điểm bất động
  CTL, không phải bằng BMC tìm trạng thái xấu.
- **Vì sao v1 dùng `explicit_bzero`** (C6.5, CWE-14 "Compiler Removal of Code to Clear Buffers"): trình biên dịch
  tối ưu có thể xóa lệnh `memset` đặt ngay trước `free` vì coi đó là lệnh ghi vô ích (dead store), nên số thẻ vẫn
  còn trong bộ nhớ. Gói nộp **không** có thí nghiệm biên dịch riêng; điểm này dẫn theo mô tả của CWE-14, không phải
  kết quả đo của nhóm.

## 9. Lỗi của phần mềm gặp khi chạy giao diện (ghi nhận ngày 13/10/2026)

| Lỗi | Nơi gặp | Nguyên nhân (đã xác minh trong mã phần mềm) | Ảnh hưởng tới kết luận |
|---|---|---|---|
| `name 'partition_states' is not defined` | SecLabFramework, tab Ch6, khi bật "Tách sơ đồ lớn thành các sơ đồ trạng thái con" với mô hình > số trạng thái tối đa | Hàm vẽ `gui.visualizer.expand_flows_for_display` gọi `partition_states` nhưng hàm này không được định nghĩa trong bản SecLabFramework (SpecVerificationLab thì có) | Không — chỉ hỏng phần vẽ sơ đồ; phần chữ của pipeline vẫn chạy. Tắt tách sơ đồ để chạy lại |
| `WinError 193 … not a valid Win32 application` khi nạp `sl_cwrap_…` | SecLabFramework, tab Ch6, khi bật "Dùng Python wrap cho mã C…" | Phần mềm 64-bit nạp DLL do gcc của máy biên dịch; gcc 32-bit tạo DLL sai kiến trúc | Không — wrap là tính năng phụ (chạy test trên mã C qua DLL); tắt ô này để chạy |

Ý nghĩa cho báo cáo: đặc tả của nhóm (35 trạng thái) lớn hơn nhiều so với đặc tả mẫu (4–7 trạng thái), nên làm lộ
những nhánh mã của công cụ chưa từng được chạy với dữ liệu mẫu — một ví dụ thực tế cho nhận định "công cụ kiểm
chứng cũng là phần mềm và cũng cần được kiểm chứng".
