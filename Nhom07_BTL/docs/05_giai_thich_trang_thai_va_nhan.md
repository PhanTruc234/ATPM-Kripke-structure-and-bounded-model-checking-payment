# Giải thích hành vi, trạng thái và nhãn — bằng tình huống cụ thể

Tài liệu này giải thích **từng trạng thái** của mô hình Kripke (35 trạng thái của mô hình kết hợp và các trạng thái
của 6 mô hình con), **từng nhãn**, và **khi nào** mỗi tình huống xảy ra ngoài đời. Dữ liệu lấy đúng từ
`source/spec/sinh_dac_ta.py` và `source/spec/mo_hinh_con/*.json`. Dùng cho mục 3 của báo cáo và để trả lời câu hỏi.

---

## 1. Câu chuyện xuyên suốt: một lượt thanh toán

Chị An đặt mua 3 món trên một trang bán hàng: áo 250.000 đ, giày 120.000 đ, ví 89.000 đ, phí giao hàng 30.000 đ.
Hệ thống cấp mã đơn **`DH20261015000123`** (đúng 16 ký tự — mức tối đa cho phép). Phía máy chủ xử lý như sau:

| Hành vi | Máy chủ làm gì | Hàm/biến trong đặc tả |
|---|---|---|
| **H1** Tiếp nhận yêu cầu | Nhận mã đơn từ trình duyệt, chép vào bộ đệm `order_id[16]` | `parse_order_id` |
| **H2** Tạo đơn | Xin cấp bộ nhớ cho 3 dòng sản phẩm, mỗi dòng 48 byte: `malloc(3 × 48)` | `create_order_items` |
| **H3** Tính tổng tiền | 250.000 + 120.000 + 89.000 + 30.000 = **489.000 đ**, kiểu số nguyên 32-bit | `add_shipping_fee`, `installment_amount` |
| **H4** Nhận callback | Chị An trả tiền ở cổng thanh toán; cổng gọi ngược về máy chủ (IPN): "đơn này đã trả, mã giao dịch X, chữ ký Y" | `parse_gateway_txn_id`, `ipn_debug_bypass` |
| **H5** Ghi log | Ghi một bản ghi "DH… đã thanh toán 489.000 đ lúc …" | `write_payment_log` |
| **H6** Đóng phiên | Giải phóng "phiên thanh toán" (có chứa số thẻ). **Hai luồng** có thể đóng phiên: *worker callback* (khi IPN tới) và *worker timeout* (khi quá 15 phút không thấy IPN) | `close_payment_session`, `release_card_buffer` |

Mỗi hành vi có **một điểm rẽ nhánh** (trạng thái `hX_vao`): từ đó hoặc đi tiếp an toàn (`hX_ok`), hoặc rơi vào một
trạng thái rủi ro. Đường đi "đẹp" của chị An trong mô hình:

```
start → h1_vao → h1_ok → h2_vao → h2_ok → h3_vao → h3_ok → h4_vao → h4_ok → h5_vao → h5_ok
      → h6_phien_ranh → h6_cb_giu → h6_giai_phong → ket_thuc_ok
```

Bản lỗi **v0** có thêm các cạnh rẽ vào trạng thái rủi ro. Bản sửa **v1** giữ nguyên 35 trạng thái nhưng **bỏ các cạnh**
đó và thêm cạnh sang `ket_thuc_tu_choi` (từ chối đầu vào xấu). Vì vậy, trên sơ đồ v1 các nút đỏ vẫn còn nhưng
không còn đường nào đi tới.

---

## 2. Cách đọc tên trạng thái và nhãn

- **Tên trạng thái** viết tiếng Việt không dấu: `h1_tran_1_byte` = "H1 – tràn 1 byte", `h6_cb_giu` = "H6 – worker
  callback đang giữ phiên".
- **Nhãn** là các mệnh đề nguyên tử **đúng tại trạng thái đó**. Công thức CTL chỉ "nhìn" thấy nhãn, không thấy tên
  trạng thái. Có 4 loại nhãn:

| Loại nhãn | Ví dụ | Dùng để |
|---|---|---|
| Vị trí | `h1` … `h6`, `start` | Biết trạng thái thuộc hành vi nào |
| Tiến trình (bình thường) | `receiving`, `allocating`, `computing`, `callback_received`, `logging`, `releasing` | Mô tả việc đang làm |
| Rủi ro | `buffer_overflow`, `null_deref`, `double_free` … **và luôn kèm `violation`** | Viết thuộc tính an toàn `AG(!x)` |
| Kết thúc | `flow_end`, `payment_done`, `input_rejected`, `mem_clean`, `unsafe_halt` | Viết thuộc tính liveness/khả đạt |

- **`violation`** là nhãn tổng: mọi trạng thái rủi ro đều mang nó, nên `AG(!violation)` bắt được tất cả cùng lúc;
  các nhãn riêng (`off_by_one`, `race`…) cho biết **lỗi cụ thể** nào. Trên sơ đồ, nút **đỏ** = có `violation`.

---

## 3. Từng hành vi và trạng thái (mô hình kết hợp, 35 trạng thái)

### H1 — Tiếp nhận yêu cầu: chép mã đơn vào `order_id[16]`

Quy định: mã đơn tối đa 16 ký tự. Chuỗi trong C cần thêm 1 byte `'\0'` ở cuối, nên mã 16 ký tự cần **17 byte**.

| Trạng thái | Nhãn | Mã | Khi nào xảy ra (tình huống cụ thể) | Hậu quả |
|---|---|---|---|---|
| `h1_vao` | `h1`, `receiving` | H1 | Máy chủ vừa nhận chuỗi mã đơn từ trình duyệt/app, chưa chép | — |
| `h1_ok` | `h1`, `input_ok` | C1.1 | Mã ngắn hơn 16 ký tự, vd `DH123456` (8 ký tự + `'\0'` = 9 byte ≤ 16) | Chép đủ, an toàn |
| `h1_tran_1_byte` | `h1`, `buffer_overflow`, `off_by_one`, `violation` | C1.2 | Mã dài **đúng** 16 ký tự như `DH20261015000123` — hoàn toàn hợp lệ theo quy định. `strcpy` ghi 16 ký tự + `'\0'` = 17 byte vào mảng 16 byte | Byte `'\0'` đè lên biến nằm kề (vd một byte của trường số tiền). **Không crash, không báo lỗi** → lỗi ẩn; kiểm thử với mã ngắn không bao giờ thấy |
| `h1_tran_bo_dem` | `h1`, `buffer_overflow`, `violation` | C1.3 | Mã dài hơn 16 ký tự: kẻ tấn công gửi 200 ký tự `A` | Ghi đè vùng stack, có thể đè địa chỉ trả về → sập chương trình hoặc bị chiếm quyền điều khiển |

- **v0:** `h1_vao` → `h1_ok` / `h1_tran_1_byte` / `h1_tran_bo_dem`.
- **v1:** `h1_vao` → `h1_ok` / `ket_thuc_tu_choi` (bộ đệm 17 byte; dùng `strnlen` đo độ dài, > 16 thì **từ chối**).
- Thuộc tính bắt: `AG(!off_by_one)` (CWE-193), `AG(!buffer_overflow)` (CWE-120/121/787).
- Trường hợp **cắt cụt C1.4** chỉ có ở mô hình con M1 (mục 5).

### H2 — Tạo đơn: `items = malloc(n × 48)`

| Trạng thái | Nhãn | Mã | Khi nào xảy ra | Hậu quả |
|---|---|---|---|---|
| `h2_vao` | `h2`, `allocating` | H2 | Đơn có n dòng sản phẩm (chị An: n = 3 → xin 144 byte) | — |
| `h2_ok` | `h2`, `allocated`, `initialized` | C2.1 | Cấp phát thành công và mọi trường đã gán giá trị | An toàn |
| `h2_null` | `h2`, `null_deref`, `violation` | C2.2 | Máy chủ **cạn bộ nhớ** (đợt flash sale, hàng nghìn đơn cùng lúc) → `malloc` trả `NULL`; mã không kiểm tra, ghi luôn `items[0].qty = …` | Truy cập con trỏ NULL → tiến trình sập. Lỗi ẩn: máy lập trình viên đủ RAM nên **không bao giờ** thấy |
| `h2_sai_kich_thuoc` | `h2`, `alloc_size_overflow`, `heap_overflow`, `violation` | C2.3 | n bất thường do request bị sửa. Vd n = 89.478.486 → n × 48 = 4.294.967.328 vượt int32, phép nhân **quay vòng còn 32** → chỉ được cấp 32 byte nhưng chương trình vẫn ghi đủ n dòng. (Z3 tìm được n = 67.107.688 làm n × 48 > 2.147.483.647) | Ghi tràn vùng heap, phá dữ liệu của đối tượng khác |
| `h2_doc_rac` | `h2`, `uninit_read`, `violation` | C2.4 | `malloc` không xóa vùng nhớ. Mã đọc `items[i].status` **trước khi gán** → đọc phải "rác" còn sót của lần dùng trước | Nếu rác tình cờ bằng mã PAID, **đơn chưa trả tiền bị coi là đã trả**. Lúc có lúc không → rất khó tái hiện |

- **v1:** kiểm tra 1 ≤ n ≤ 100, dùng `calloc` (tự xóa về 0), kiểm tra NULL → `h2_vao` → `h2_ok` / `ket_thuc_tu_choi`.
- Thuộc tính: `AG(!null_deref)` (CWE-476/690), `AG(!heap_overflow)` (CWE-190→680), `AG(!uninit_read)` (CWE-457/908).

### H3 — Tính tổng tiền (số nguyên 32-bit, đơn vị VND)

Trần int32 = **2.147.483.647** (khoảng 2,1 tỷ đồng) — đơn doanh nghiệp vượt mức này là chuyện bình thường.

| Trạng thái | Nhãn | Mã | Khi nào xảy ra | Hậu quả |
|---|---|---|---|---|
| `h3_vao` | `h3`, `computing` | H3 | Đang tính Σ đơn giá × số lượng + phí ship − giảm giá | — |
| `h3_ok` | `h3`, `amount_ok` | C3.1 | Đơn của chị An: 489.000 đ | An toàn |
| `h3_tran_so` | `h3`, `int_overflow`, `violation` | C3.2, C3.3 | **(C3.2) nhân 1 dòng:** đơn sỉ đơn giá 33.765.495 × 509 cái ≈ 17,2 tỷ → tràn ngay khi nhân. **(C3.3) cộng dồn:** đơn công ty 48 laptop × 45.000.000 = 2.160.000.000 → mỗi dòng hợp lệ nhưng tổng vượt trần | Tổng quay vòng thành số âm (≈ −2.134.967.296) → hệ thống tính sai tiền, có thể coi như phải trả lại tiền cho khách |
| `h3_so_am` | `h3`, `negative_amount`, `violation` | C3.4 | Số lượng −1 (request bị sửa), hoặc mã giảm giá 500.000 đ áp vào đơn 489.000 đ → tổng **−11.000 đ** | Hệ thống "nợ" khách tiền; có thể bị lạm dụng để rút tiền |
| `h3_chia_0` | `h3`, `div_by_zero`, `violation` | C3.5 | Chọn trả góp nhưng form gửi số kỳ `months = 0` → `total / months` | Lỗi chia cho 0, chương trình dừng (fuzz black-box gặp 11/300 lần) |

- **v1:** kiểm tra miền đầu vào (số lượng 1..1000, đơn giá ≤ 50 triệu, giảm giá ≥ 0, 1 ≤ months ≤ 24), nhân bằng int64,
  hạn mức tổng 2 tỷ → `h3_vao` → `h3_ok` / `ket_thuc_tu_choi`.
- Thuộc tính: `AG(!int_overflow)` (CWE-190), `AG(!negative_amount)` (CWE-191/839), `AG(!div_by_zero)` (CWE-369).

### H4 — Nhận callback (IPN) từ cổng thanh toán

Đây là dữ liệu **đến từ bên ngoài** (attack surface): kẻ xấu có thể tự gửi callback giả tới máy chủ.

| Trạng thái | Nhãn | Mã | Khi nào xảy ra | Hậu quả |
|---|---|---|---|---|
| `h4_vao` | `h4`, `callback_received` | H4 | Có một yêu cầu callback gọi tới máy chủ | — |
| `h4_ok` | `h4`, `callback_verified` | C4.1 | Mã giao dịch ≤ 20 ký tự, chữ ký HMAC đúng | Chấp nhận: đơn chuyển sang "đã thanh toán" |
| `h4_tu_choi_callback` | `h4`, `callback_rejected` | C4.1 | Callback giả hoặc sai chữ ký → bỏ qua | An toàn. Đơn vẫn chưa thanh toán, nên phiên sẽ do worker timeout đóng sau 15 phút — vì vậy có cạnh `h4_tu_choi_callback → h6_phien_ranh` (bỏ qua H5) |
| `h4_tran_txn` | `h4`, `buffer_overflow`, `violation` | C4.2 | Callback gửi mã giao dịch dài 64 ký tự (cổng đổi định dạng, hoặc kẻ tấn công) → `strcpy` vào `txn[20]` | Tràn bộ đệm như C1.3 |
| `h4_nhanh_an` | `h4`, `hidden_bypass`, `violation` | C4.3 | Lập trình viên **bỏ quên nhánh debug**: nếu `merchant_id = 31337` và `debug_pin = 8080` thì chấp nhận luôn, **không kiểm chữ ký** | Ai biết cặp số này có thể giả callback "đã trả tiền" để lấy hàng mà không trả. Lỗi ẩn: thử ngẫu nhiên 300 lần không chạm (0/300); concolic giải ràng buộc tìm ra sau 3 lần |

- **v1:** kiểm tra độ dài (`strnlen(…, 21) > 20` → bỏ qua), xóa nhánh debug → `h4_vao` → `h4_ok` / `h4_tu_choi_callback`.
- Thuộc tính: `AG(!buffer_overflow)` (CWE-120), `AG(!hidden_bypass)` (CWE-912/798).

### H5 — Ghi log giao dịch: `e = malloc(LogEntry)`

| Trạng thái | Nhãn | Mã | Khi nào xảy ra | Hậu quả |
|---|---|---|---|---|
| `h5_vao` | `h5`, `logging` | H5 | Cấp phát bản ghi log và ghi nội dung | — |
| `h5_ok` | `h5`, `log_freed` | C5.1 | Ghi xong và `free(e)` | An toàn |
| `h5_ro_ri` | `h5`, `mem_leak`, `violation` | C5.2 | Ghi đĩa thất bại (đĩa đầy) → hàm `return -1` sớm, **quên `free(e)`** | Mỗi lần lỗi mất một ít bộ nhớ. Ngày sale có hàng chục nghìn giao dịch lỗi → bộ nhớ cạn dần → máy chủ chậm rồi sập (và kéo theo C2.2). Lỗi ẩn: tích lũy chậm, kiểm thử ngắn không thấy |
| `h5_format_string` | `h5`, `format_string`, `violation` | C5.3 | Log chứa dữ liệu khách nhập, vd ghi chú đơn `"Giao giờ hành chính %x %x %n"`, rồi gọi `printf(msg)` | `printf` hiểu `%x` là lệnh **đọc** stack, `%n` là lệnh **ghi** bộ nhớ → lộ dữ liệu hoặc bị ghi đè bộ nhớ |

- **v1:** `printf("%s", msg)` và `goto cleanup` (luôn `free` kể cả nhánh lỗi) → chỉ còn `h5_vao → h5_ok`.
- Thuộc tính: `AG(!mem_leak)` (CWE-401), `AG(!format_string)` (CWE-134).

### H6 — Đóng phiên: hai worker dùng chung một phiên

Mỗi lượt thanh toán có một **phiên** (`PaymentSession`) trên heap, giữ trạng thái đơn và bộ đệm số thẻ. Tình huống
nguy hiểm: **IPN tới đúng lúc hết 15 phút** — cả worker callback lẫn worker timeout cùng lao vào đóng phiên.

| Trạng thái | Nhãn | Mã | Khi nào xảy ra | Hậu quả |
|---|---|---|---|---|
| `h6_phien_ranh` | `h6`, `sess_free` | H6 | Phiên đang mở, **chưa worker nào giữ**. Lưu ý: `sess_free` nghĩa là "phiên rảnh", **không phải** "bộ nhớ đã free" | — |
| `h6_cb_giu` | `h6`, `cb_locked` | C6.1 | Worker callback đang giữ phiên (đánh dấu PAID) | Bình thường |
| `h6_to_giu` | `h6`, `to_locked` | C6.1 | Worker timeout đang giữ phiên (đánh dấu CANCELLED) | Bình thường |
| `h6_tranh_chap` | `h6`, `cb_locked`, `to_locked`, `race`, `violation` | C6.2 | v0 không có khóa: IPN tới đúng phút thứ 15 → **cả hai cùng giữ** | Trạng thái đơn bị ghi đè qua lại PAID ↔ CANCELLED: khách **đã trả tiền mà đơn bị hủy**, hoặc ngược lại. Vi phạm loại trừ lẫn nhau |
| `h6_double_free` | `h6`, `double_free`, `violation` | C6.3 | Sau tranh chấp, cả hai cùng gọi `free(session)` | Giải phóng 2 lần → hỏng cấu trúc quản lý heap, có thể bị khai thác |
| `h6_uaf` | `h6`, `use_after_free`, `violation` | C6.4 | Worker A đã `free` phiên; worker B đến sau vẫn ghi `s->status = …` | Ghi vào vùng đã trả lại hệ thống — vùng đó có thể đã được cấp cho **phiên của khách khác** → phá dữ liệu người khác |
| `h6_giai_phong` | `h6`, `releasing` | C6.1 | Một worker đang xóa bộ đệm thẻ và giải phóng phiên | Bình thường |
| `h6_con_so_the` | `h6`, `secret_residue`, `violation` | C6.5 | Mã gọi `memset(card, 0, 16)` rồi `free`. Trình biên dịch tối ưu có thể **xóa luôn lệnh memset** vì vùng nhớ sắp bị free không còn ai đọc (CWE-14) | 16 chữ số thẻ vẫn nằm trong heap; vùng nhớ cấp lại cho yêu cầu khác hoặc lộ qua bản dump bộ nhớ → **lộ số thẻ** |

- **v0:** `h6_phien_ranh` → `h6_cb_giu` / `h6_to_giu`; mỗi bên → `h6_giai_phong` hoặc `h6_tranh_chap`;
  `h6_tranh_chap` → `h6_double_free` / `h6_uaf`; `h6_giai_phong` → `ket_thuc_ok` / `h6_con_so_the`.
- **v1:** mutex + đánh dấu `status = CLOSED` (worker đến sau thấy CLOSED thì bỏ qua) + `explicit_bzero` (lệnh xóa mà
  trình biên dịch không được bỏ) → `h6_cb_giu` → `h6_giai_phong`, `h6_to_giu` → `h6_giai_phong`,
  `h6_giai_phong` → `ket_thuc_ok`.
- Thuộc tính: loại trừ lẫn nhau `cb_locked`/`to_locked` và `AG(!race)` (CWE-362/667), `AG(!double_free)` (CWE-415),
  `AG(!use_after_free)` (CWE-416), `AG(!secret_residue)` (CWE-226/244/14).
- `h6_tranh_chap` là trạng thái duy nhất mang **cả hai** nhãn `cb_locked` và `to_locked` — đó chính là định nghĩa của
  "vi phạm loại trừ lẫn nhau".

### Trạng thái đầu và cuối

| Trạng thái | Nhãn | Ý nghĩa | Ghi chú |
|---|---|---|---|
| `start` | `start`, `safe` | Bắt đầu xử lý một yêu cầu thanh toán | Trạng thái khởi tạo **duy nhất** (S0) |
| `ket_thuc_ok` | `flow_end`, `payment_done`, `mem_clean` | Thanh toán xong, đơn PAID, mọi vùng nhớ đã giải phóng sạch, số thẻ đã xóa | Tự lặp (đường đi vô hạn cho CTL) |
| `ket_thuc_tu_choi` | `flow_end`, `input_rejected`, `mem_clean` | Yêu cầu xấu bị từ chối gọn gàng: báo lỗi cho khách, không để lại bộ nhớ dở dang | **Chỉ đạt tới được ở v1** → ở v0 `EF(input_rejected)` VI PHẠM (không có cơ chế từ chối) |
| `dung_khong_an_toan` | `unsafe_halt` | "Hố" sau vi phạm: hệ thống ở trạng thái không còn tin cậy (đã sập, bộ nhớ đã hỏng) | Mọi trạng thái rủi ro (trừ `h6_tranh_chap`) đều dẫn vào đây. Tự lặp mãi, **không có `flow_end`** → `AF(flow_end)` VI PHẠM ở v0. Giống "error location" trong BMC |

---

## 4. Bảng tra nhãn (mô hình kết hợp)

| Nhãn | Nghĩa | Trạng thái mang nhãn | Dùng trong |
|---|---|---|---|
| `start`, `safe` | điểm bắt đầu, an toàn | `start` | — |
| `h1` … `h6` | thuộc hành vi H1 … H6 | các trạng thái `h1_*` … `h6_*` | — |
| `receiving` | đang nhận dữ liệu | `h1_vao` | — |
| `input_ok` | mã đơn chép đủ | `h1_ok` | — |
| `allocating` / `allocated` / `initialized` | đang cấp phát / đã cấp phát / đã khởi tạo | `h2_vao` / `h2_ok` / `h2_ok` | — |
| `computing` / `amount_ok` | đang tính / tổng tiền hợp lệ | `h3_vao` / `h3_ok` | — |
| `callback_received` / `callback_verified` / `callback_rejected` | nhận / xác thực được / từ chối callback | `h4_vao` / `h4_ok` / `h4_tu_choi_callback` | — |
| `logging` / `log_freed` | đang ghi log / đã giải phóng bản ghi | `h5_vao` / `h5_ok` | — |
| `sess_free` | phiên rảnh (chưa ai giữ) | `h6_phien_ranh` | — |
| `cb_locked` | worker callback giữ phiên | `h6_cb_giu`, `h6_tranh_chap` | mutex, `EF(cb_locked)` |
| `to_locked` | worker timeout giữ phiên | `h6_to_giu`, `h6_tranh_chap` | mutex |
| `releasing` | đang giải phóng | `h6_giai_phong` | — |
| `buffer_overflow` | ghi vượt biên bộ đệm | `h1_tran_1_byte`, `h1_tran_bo_dem`, `h4_tran_txn` | `AG(!buffer_overflow)` |
| `off_by_one` | lệch đúng 1 byte | `h1_tran_1_byte` | `AG(!off_by_one)` |
| `null_deref` | dùng con trỏ NULL | `h2_null` | `AG(!null_deref)` |
| `alloc_size_overflow`, `heap_overflow` | tính sai kích thước cấp phát, ghi tràn heap | `h2_sai_kich_thuoc` | `AG(!heap_overflow)` |
| `uninit_read` | đọc vùng nhớ chưa khởi tạo | `h2_doc_rac` | `AG(!uninit_read)` |
| `int_overflow` | tràn số nguyên | `h3_tran_so` | `AG(!int_overflow)` |
| `negative_amount` | số tiền âm | `h3_so_am` | `AG(!negative_amount)` |
| `div_by_zero` | chia cho 0 | `h3_chia_0` | `AG(!div_by_zero)` |
| `hidden_bypass` | nhánh ẩn bỏ qua xác thực | `h4_nhanh_an` | `AG(!hidden_bypass)` |
| `mem_leak` | rò rỉ bộ nhớ | `h5_ro_ri` | `AG(!mem_leak)` |
| `format_string` | dữ liệu người dùng làm chuỗi định dạng | `h5_format_string` | `AG(!format_string)` |
| `race` | hai luồng tranh chấp | `h6_tranh_chap` | `AG(!race)` |
| `double_free` | giải phóng 2 lần | `h6_double_free` | `AG(!double_free)` |
| `use_after_free` | dùng sau khi giải phóng | `h6_uaf` | `AG(!use_after_free)` |
| `secret_residue` | dữ liệu bí mật còn sót | `h6_con_so_the` | `AG(!secret_residue)` |
| `violation` | nhãn tổng của mọi trạng thái rủi ro | 16 trạng thái đỏ | `AG(!violation)`, `EG(!violation)` |
| `flow_end` | luồng đã kết thúc hợp lệ | `ket_thuc_ok`, `ket_thuc_tu_choi` | `AF(flow_end)` |
| `payment_done` | thanh toán thành công | `ket_thuc_ok` | `EF(payment_done)` |
| `input_rejected` | đầu vào xấu bị từ chối | `ket_thuc_tu_choi` | `EF(input_rejected)` |
| `mem_clean` | bộ nhớ đã sạch | `ket_thuc_ok`, `ket_thuc_tu_choi` | (cặp loại trừ phụ) |
| `unsafe_halt` | dừng trong trạng thái không an toàn | `dung_khong_an_toan` | (cặp loại trừ phụ) |

---

## 5. Sáu mô hình con — soi kỹ từng hành vi

Mô hình kết hợp gộp mỗi hành vi thành vài trạng thái. Mô hình con **tách nhỏ** để thấy *vì sao* một đầu vào dẫn tới
lỗi, và so sánh các phiên bản sửa. Nhãn `done` trong mô hình con = "hành vi kết thúc" (dùng cho `AF(done)`).

### M1 — Tiếp nhận yêu cầu (3 luồng: v0, v1a, v1b)

Ý tưởng: chia **mọi** độ dài L của mã đơn thành 3 lớp so với dung lượng N = 16 — L < 16, L = 16, L > 16. Ba lớp
này phủ kín mọi khả năng, nên kết luận trên mô hình là đầy đủ.

| Trạng thái | Nhãn | Tình huống |
|---|---|---|
| `m1_nhan_chuoi` | `receiving` | Vừa nhận chuỗi mã đơn |
| `m1_len_nho` | `len_lt_cap` | L < 16, vd `DH123456` |
| `m1_len_bang_16` | `len_eq_cap` | L = 16, vd `DH20261015000123` |
| `m1_len_lon` | `len_gt_cap` | L > 16, vd 200 ký tự `A` |
| `m1_chep_dung` | `copied_ok`, `done` | Mã được chép nguyên vẹn |
| `m1_tran_1_byte` | `buffer_overflow`, `off_by_one`, `violation` | (v0) L = 16, `strcpy` ghi 17 byte |
| `m1_tran_nhieu_byte` | `buffer_overflow`, `violation` | (v0) L > 16, tràn nhiều byte |
| `m1_cat_cut` | `truncated`, `violation` | (v1a) Bản "an toàn" do phần mềm sinh: `strncpy(buf, src, 15)` → `DH20261015000123` bị cắt thành `DH2026101500012`. Đơn `…0123` và đơn `…0124` **cùng bị cắt thành một mã** → tiền của đơn này có thể ghi vào đơn kia (CWE-222). Không crash, không cảnh báo |
| `m1_tu_choi` | `input_rejected`, `done` | (v1b) Bản sửa của nhóm: L > 16 thì **từ chối** |

Cạnh khác nhau giữa 3 luồng: L = 16 → **v0** tràn 1 byte · **v1a** cắt cụt · **v1b** chép đúng;
L > 16 → **v0** tràn nhiều byte · **v1a** cắt cụt · **v1b** từ chối.

### M2 — Tạo đơn, cấp phát (2 luồng)

| Trạng thái | Nhãn | Tình huống |
|---|---|---|
| `m2_nhan_n` | `receiving` | Nhận số dòng sản phẩm n |
| `m2_n_hop_le` / `m2_n_bat_thuong` | `size_ok` / `size_wrong` | n trong 1..100 / n âm hoặc quá lớn |
| `m2_malloc_null` | `ptr_null` | `malloc` trả NULL (cạn bộ nhớ) |
| `m2_cap_phat_chua_kt` | `allocated`, `uninitialized` | Đã có vùng nhớ nhưng còn rác |
| `m2_da_khoi_tao` | `allocated`, `initialized` | Đã gán giá trị cho mọi trường |
| `m2_null_deref` / `m2_tran_heap` / `m2_doc_rac` | `null_deref` / `heap_overflow` / `uninit_read` + `violation` | Ba lỗi như C2.2 / C2.3 / C2.4 |
| `m2_su_dung` | `in_use`, `done` | Đơn được dùng bình thường |
| `m2_tu_choi` | `input_rejected`, `done` | (v1) n sai hoặc NULL → từ chối |

v1 dùng `calloc` nên đi thẳng `m2_n_hop_le → m2_da_khoi_tao`, không còn trạng thái "chưa khởi tạo".

### M3 — Tính tổng tiền (2 luồng)

| Trạng thái | Nhãn | Tình huống |
|---|---|---|
| `m3_nhan_du_lieu` | `receiving` | Nhận đơn giá, số lượng, giảm giá, số kỳ |
| `m3_dau_vao_hop_le` / `m3_dau_vao_am` / `m3_ky_han_0` | `input_ok` / `negative_input` / `zero_divisor` | Đầu vào bình thường / có số âm / số kỳ = 0 |
| `m3_nhan_dong` → `m3_cong_don` | `multiplying` → `accumulating` | Đang nhân từng dòng → đang cộng dồn |
| `m3_tong_hop_le` | `amount_ok`, `done` | Tổng tiền đúng |
| `m3_tran_nhan` / `m3_tran_cong_don` | `int_overflow`, `violation` | Tràn khi nhân 1 dòng (C3.2) / khi cộng dồn (C3.3) |
| `m3_tong_am` / `m3_chia_0` | `negative_amount` / `div_by_zero` + `violation` | C3.4 / C3.5 |
| `m3_tu_choi` | `input_rejected`, `done` | (v1) Từ chối ở 3 chốt: đầu vào sai miền; một dòng > 50 triệu; tổng sắp vượt 2 tỷ |

### M4 — Nhận callback (2 luồng)

| Trạng thái | Nhãn | Tình huống |
|---|---|---|
| `m4_nhan_callback` | `receiving` | Callback gọi tới |
| `m4_txn_hop_le` / `m4_txn_qua_dai` | `len_ok` / `len_gt_cap` | Mã giao dịch ≤ 20 / > 20 ký tự |
| `m4_tran_txn` | `buffer_overflow`, `violation` | (v0) `strcpy` mã quá dài |
| `m4_nhanh_an` | `hidden_bypass`, `violation` | (v0) Nhánh debug (31337, 8080) — nằm **trước** bước kiểm chữ ký nên bỏ qua được nó |
| `m4_kiem_chu_ky` → `m4_chu_ky_dung` | `verifying` → `verified` | Đang kiểm chữ ký → chữ ký đúng |
| `m4_chap_nhan` / `m4_tu_choi` | `accepted` / `callback_rejected` + `done` | Chấp nhận / bỏ qua callback |

### M5 — Ghi log (2 luồng)

| Trạng thái | Nhãn | Tình huống |
|---|---|---|
| `m5_bat_dau` → `m5_cap_phat` → `m5_ghi_noi_dung` | `receiving` → `allocated` → `allocated`, `in_use` | Cấp phát và điền nội dung log |
| `m5_in_an_toan` | `allocated`, `printed` | In bằng `printf("%s", msg)` |
| `m5_format_string` | `format_string`, `violation` | (v0) `printf(msg)` với msg chứa `%x %n` |
| `m5_loi_ghi_dia` | `allocated`, `error_path` | Ghi đĩa thất bại |
| `m5_ro_ri` | `mem_leak`, `violation` | (v0) `return` sớm, quên `free` |
| `m5_giai_phong` | `freed`, `done` | Đã `free(e)` |

v1: `m5_loi_ghi_dia → m5_giai_phong` nhờ `goto cleanup` — nhánh lỗi cũng đi qua chỗ giải phóng.

### M6 — Đóng phiên (2 luồng)

| Trạng thái | Nhãn | Tình huống |
|---|---|---|
| `m6_phien_mo` | `sess_free` | Phiên mở, chưa ai giữ |
| `m6_cb_giu` / `m6_to_giu` | `cb_locked` / `to_locked` | Một trong hai worker giữ phiên |
| `m6_tranh_chap` | `cb_locked`, `to_locked`, `race`, `violation` | (v0) Cả hai cùng giữ |
| `m6_double_free` / `m6_uaf` | `double_free` / `use_after_free` + `violation` | (v0) Hậu quả của tranh chấp; ngoài ra `m6_da_dong → m6_uaf`: worker đến muộn ghi vào phiên **đã đóng** |
| `m6_giai_phong` | `releasing` | Đang giải phóng |
| `m6_con_so_the` | `secret_residue`, `violation` | (v0) memset bị bỏ, số thẻ còn sót |
| `m6_xoa_trang` | `wiped` | (v1) Đã xóa số thẻ bằng `explicit_bzero` |
| `m6_da_dong` | `session_freed`, `done` | Phiên đã giải phóng |
| `m6_den_sau_bo_qua` | `late_ignored`, `session_freed`, `done` | (v1) Worker đến muộn thấy `status = CLOSED` nên **bỏ qua**, không đụng vào phiên |

---

## 6. Đọc một phản ví dụ thành câu chuyện

BMC của nhóm báo `AG(!race)` vi phạm ở **k = 11**:

```
start → h1_vao → h1_ok → h2_vao → h2_ok → h3_vao → h3_ok → h4_vao → h4_tu_choi_callback
      → h6_phien_ranh → h6_cb_giu → h6_tranh_chap
```

Kể lại: đơn của chị An qua H1–H3 bình thường. Callback đầu tiên tới bị từ chối (vd sai chữ ký do lỗi mạng), nên đơn
chưa thanh toán và phiên chờ đóng. Cổng thanh toán **gửi lại** IPN; worker callback giữ phiên để đánh dấu PAID — đúng
lúc worker timeout hết 15 phút cũng giữ phiên để hủy đơn. Bản v0 không có khóa nên hai worker cùng giữ →
`h6_tranh_chap`. Đây là lỗi chỉ xảy ra khi **hai sự kiện trùng thời điểm** — kiểm thử thông thường gần như không bao
giờ tái hiện được, nhưng mô hình xét mọi thứ tự xen kẽ nên tìm ra ngay.

---

## 7. Vì sao mô hình được thiết kế như vậy

| Câu hỏi | Lý do |
|---|---|
| Vì sao v1 vẫn giữ các trạng thái rủi ro? | Để hai phiên bản có **cùng không gian trạng thái**, chỉ khác tập cạnh R → so sánh công bằng: v1 an toàn vì **không còn đường đi tới** (đạt tới được giảm từ 34 xuống 18 trạng thái), không phải vì xóa bớt trạng thái |
| Vì sao trạng thái rủi ro dẫn vào `dung_khong_an_toan`? | Sau khi bộ nhớ hỏng, hệ thống không còn tin cậy; gom về một "hố" để biểu diễn điều đó và để `AF(flow_end)` phát hiện được đường đi không bao giờ kết thúc hợp lệ |
| Vì sao `h6_tranh_chap` không vào `dung_khong_an_toan`? | Tranh chấp chưa phải điểm cuối — nó **gây ra** lỗi tiếp theo (`h6_double_free`, `h6_uaf`), nên mô hình đi tiếp tới các hậu quả đó |
| Vì sao các trạng thái cuối tự lặp? | CTL xét đường đi vô hạn, R phải toàn phần; trạng thái không có cạnh ra là deadlock |
| Vì sao chỉ có một trạng thái khởi tạo? | Phần mềm đánh giá công thức tại **mọi** trạng thái khởi tạo; một `start` duy nhất giúp `EF(…)` có nghĩa (xem `docs/03` mục 6) |
| Vì sao gắn nhãn tổng `violation` và nhãn ghép như `race`? | CTL của phần mềm chỉ nhận 1 toán tử + 1 nhãn; điều kiện ghép (vd "cùng giữ khóa") phải được gắn sẵn thành **một nhãn** |
