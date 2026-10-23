# Hướng dẫn chạy 2 phần mềm và thu bằng chứng

**Mục tiêu:** nạp đặc tả **v0** (cài lỗi) và **v1** (đã sửa) vào SpecVerificationLab và SecLabFramework, chạy kiểm
chứng, **chụp ảnh + lưu kết quả dạng chữ + xuất báo cáo của phần mềm**, rồi đối chiếu với kết quả kỳ vọng.

Thời gian dự kiến: khoảng **2 giờ** (A: 20 phút · B: 20 phút · C: 40 phút · D: 15 phút · E: 5 phút · đối chiếu: 20 phút).

---

## 0. Đọc trước khi làm

### 0.1. Ba loại bằng chứng cần thu

| Loại | Lưu ở đâu | Đặt tên | Vai trò |
|---|---|---|---|
| Ảnh chụp màn hình `.png` | `results/screenshots/` | `<STT>_<PhanMem>_<Tab>_<NoiDung>_<v0\|v1>.png` | Chứng minh nhóm **thực sự chạy giao diện** phần mềm của GV — **bắt buộc** |
| Văn bản `.txt` sao chép từ khung kết quả | `results/logs/` | `gui_<PhanMem>_<Tab>_<NoiDung>_<v0\|v1>.txt` | Đối chiếu chính xác từng dòng; trích dẫn vào báo cáo |
| Báo cáo PDF/DOCX do phần mềm xuất | `results/tool_reports/` | `SVL_v0.pdf`, `SLF_v0.pdf`, … | Bản kết quả đầy đủ nhất; đưa vào phụ lục |

Viết tắt: **SVL** = SpecVerificationLab, **SLF** = SecLabFramework. **Không thay ảnh bằng txt — nộp cả hai.**

**Khung chữ dài không hiển thị hết** (khung kết quả CTL, khung "Mã nguồn sinh ra từ đặc tả", kết quả pipeline):
chỉ cần **1 ảnh** chụp toàn cửa sổ ở thời điểm đó — miễn thấy được tiêu đề phần mềm, vài dòng kết quả đầu và
**tên đặc tả** (vd tiêu đề sơ đồ "Mô hình chính: thanhtoan_donhang_v0") — làm bằng chứng đã chạy giao diện;
**toàn bộ nội dung** thì sao chép vào file `gui_….txt` cùng tên. Không cần cố chụp nhiều ảnh cho đủ chữ.
Khi đưa ảnh vào báo cáo, mỗi ảnh cần chú thích: *ảnh này là bằng chứng cho trường hợp/thuộc tính nào*.

### 0.2. "Kết quả kỳ vọng" là gì, lấy từ đâu

Cột **"Kỳ vọng"** trong các bảng dưới đây lấy từ các file `results/logs/headless_*.txt`. Hai phần mềm của GV là
chương trình Python đóng gói thành `.exe`. Khi bấm nút trên giao diện, các module kiểm chứng bên trong
(`core.spec_pipeline`, `core.kripke`, `core.static_smt`…) được chạy. Các file `headless_*` được tạo (với hỗ trợ của
AI) bằng cách chạy **chính các module đó, không qua giao diện**, trên đúng file đặc tả của nhóm. Vì là cùng một mã
nên khi bấm nút, **kết luận phải trùng khớp**.

| File kỳ vọng | Đối chiếu cho phần |
|---|---|
| `headless_SpecVerificationLab_v0_xlsx.txt`, `…_v1_xlsx.txt` | A |
| `headless_SecLabFramework_v0_json.txt`, `…_v1_json.txt` (và `…_xlsx.txt`) | B |
| `headless_Ch1_mo_hinh_con.txt` | C |
| Các giá trị ghi sẵn trong bảng phần D | D |
| `kiem_chung_nhom.txt` (nhóm tự sinh lại được bằng `python chay_kiem_chung.py`) | E |

**Được phép lệch:** số lần crash của fuzzing (vd `11/300`), thứ tự các trạng thái trong danh sách "thoa tai",
định dạng chữ. **Không được lệch:** ĐÚNG/VI PHẠM của từng công thức, OK/VI PHẠM của mutex, deadlock, số phát hiện
Ch2, SAT/UNSAT của Z3, "bước 48" của BMC. Lệch ở nhóm sau → xem mục 7 (xử lý sự cố) hoặc gửi file `gui_*.txt` để kiểm tra.

### 0.3. Chuẩn bị máy

1. **Đóng file Excel** `thanhtoan_donhang_v0/v1.xlsx` nếu đang mở bằng Excel (tránh lỗi khi phần mềm đọc file).
   **Không sửa tay** các file trong `source/spec/` — chúng được sinh từ `sinh_dac_ta.py` và đã kiểm tra.
2. Mở `.exe` bằng cách nhấp đúp. Lần mở đầu có thể mất vài chục giây. Nếu Windows hiện cảnh báo
   "Windows protected your PC" → **More info → Run anyway** (phần mềm do GV cung cấp).
3. **Phóng to cửa sổ** phần mềm (ảnh rõ chữ hơn).
4. Chụp màn hình: **Win + Shift + S** → chọn vùng → mở thông báo vừa chụp → **Lưu** (File → Save as) dạng `.png`.
5. Sao chép kết quả dạng chữ: bấm vào khung kết quả/Console → bôi đen toàn bộ (**Ctrl+A**; nếu không được thì
   **Ctrl+/** hoặc kéo chuột) → **Ctrl+C** → dán vào Notepad → **File → Save as**, chọn **Encoding: UTF-8**.
6. Ở tab Ch1 của SLF, bấm **Xóa console** trước mỗi luồng mới để mỗi file `.txt` chỉ chứa kết quả của 1 luồng.

### 0.4. Phân công gợi ý (làm song song trên 2–3 máy)

| Người | Phần | Ghi chú |
|---|---|---|
| Nguyễn Văn Mạnh | A, B | 2 pipeline đầy đủ + xuất PDF |
| Phan Minh Trúc | C | 6 mô hình con — nhiều ảnh nhất |
| Nguyễn Kiêm Mạnh | D, E, đối chiếu | nhập tay BMC/SMT; chạy script nhóm; điền `docs/02` |

Dù chia việc, **cả 3 người đều phải đọc `docs/03`** để giải thích được kết quả khi GV hỏi.

---

## A. SpecVerificationLab — tab "Đặc tả → Kripke → Sinh mã → CWE/CVE"

File chạy: `Image_SpecVerificationLab/Ứng dụng hỗ trợ xử lý Spec - môn học Software_Security - updated/SpecVerificationLab.exe`
Đối chiếu với: `results/logs/headless_SpecVerificationLab_v0_xlsx.txt` (v0) và `…_v1_xlsx.txt` (v1).

| Bước | Thao tác | Kỳ vọng thấy | Lưu |
|---|---|---|---|
| A1 | Bấm **Nạp từ file Excel khác (.xlsx)…** → chọn `Nhom07_BTL/source/spec/thanhtoan_donhang_v0.xlsx` | Khung "Yêu cầu (requirements) trong đặc tả" hiện REQ-01…REQ-18, NFR-01…06, CON-01…07 | `01_SVL_NapExcel_v0.png` |
| A2 | Bấm **1) Sinh Kripke + kiểm chứng (Ch1)**. Ở dưới sơ đồ: tích "Tách sơ đồ lớn…", để **12** → **Áp dụng** | Deadlock: **không có**. **18 VI PHẠM**: 16 công thức `AG(!…)` + `AF(flow_end)` + `EF(input_rejected)`. **3 ĐÚNG**: `EF(payment_done)`, `EG(!violation)`, `EF(cb_locked)`. Mutual exclusion **VI PHẠM**. Trạng thái tô đỏ = có nhãn `violation` | `02_SVL_Ch1_SoDo_v0.png` (sơ đồ, có thể nhiều ảnh nếu tách sơ đồ con), `03_SVL_Ch1_KetQuaCTL_v0.png`; `gui_SVL_Ch1_KetQuaCTL_v0.txt`; bấm **Xuất TikZ** → `results/tool_reports/SVL_tikz_v0.tex` |
| A3 | Bấm **2) Sinh mã C/Python từ đặc tả** | Khung "Mã nguồn sinh ra": **7 hàm C** (2 hàm dùng `strcpy`; 3 hàm `malloc/free` có lỗi cố ý: leak, double-free, use-after-free) + **2 hàm Python** (`installment_amount`, `ipn_debug_bypass`) | `04_SVL_SinhMa_v0.png`; `gui_SVL_SinhMa_v0.txt` |
| A4 | Bấm **3) Chạy TOÀN BỘ Pipeline** | Ch2: **5 phát hiện** (2×`strcpy` dòng 8 và 15, memory-leak dòng 28, double-free dòng 38, use-after-free dòng 46). Ch3: 5 kiểm tra **sat** kèm giá trị. Ch4: `installment_amount` black-box có crash (≈11/300); `ipn_debug_bypass`: concolic tìm ra **(31337, 8080)** sau 3 lần thử (SVL chỉ in dòng concolic — phép so sánh với black-box 0/300 xem ở B2). Tổng **31** phân loại CWE | `05_SVL_Pipeline_Ch2Ch3_v0.png`, `06_SVL_Pipeline_CWE_v0.png`; `gui_SVL_Pipeline_v0.txt` (toàn bộ khung kết quả) |
| A5 | Bấm **Xuất báo cáo TÍCH HỢP (PDF/DOCX)** — *phải chạy A4 trước*, nếu không báo cáo chỉ là bản rút gọn | — | `results/tool_reports/SVL_v0.pdf` (+ `SVL_v0.docx`) |
| A6 | Lặp lại A1–A5 với `thanhtoan_donhang_v1.xlsx` (đổi hậu tố tên file thành `_v1`) | **21/21 công thức ĐÚNG**, mutex **OK**, Ch2 "Không phát hiện lỗi nào", Ch3 5 điều kiện **unsat**; còn **5** phân loại CWE-190 (từ cột BieuThucTran — giải thích ở `docs/03` mục 3) | các ảnh `…_v1.png`, `gui_SVL_…_v1.txt`, `SVL_v1.pdf` |

## B. SecLabFramework — tab "Ch6: Spec -> Kripke -> Code -> CWE/CVE"

File chạy: `Image_SecLabFramework/SecLabFramework.exe` → chọn tab **Ch6** ở hàng tab trên cùng.
Đối chiếu với: `headless_SecLabFramework_v0_json.txt` / `…_v1_json.txt` (và `…_xlsx.txt` cho B5).

| Bước | Thao tác | Kỳ vọng thấy | Lưu |
|---|---|---|---|
| B1 | Bấm **Nạp từ file JSON khác…** → `source/spec/thanhtoan_donhang_v0.json` (bản JSON có thêm BMC vòng lặp và 6 luồng con để hiển thị — Excel không chứa được 2 phần này) | Dòng trạng thái: "Đã nạp đặc tả 'thanhtoan_donhang_v0' — **9 hàm**, 6 kiểm tra số học, 14 test case"; yêu cầu hiện như A1. Sau B2, khu vực sơ đồ có thanh tab "Mô hình chính: thanhtoan_donhang_v0" + **6 tab luồng con** M1…M6 | `07_SLF_Ch6_NapJSON_v0.png` — chụp **sau B2** để thấy cả dòng trạng thái lẫn thanh tab sơ đồ (bằng chứng JSON đã nạp đủ 6 luồng con) |
| B2 | (1) **Bỏ tích** ô "Dùng Python wrap cho mã C trong Ch3/Ch4/toàn bộ pipeline" (khung "Python wrap cho mã C sinh từ đặc tả"); (2) ở dưới khung sơ đồ: **bỏ tích** "Tách sơ đồ lớn thành các sơ đồ trạng thái con" (hoặc đặt "Số trạng thái tối đa/sơ đồ con" = **40**) → **Áp dụng**; (3) bấm **5) Chạy TOÀN BỘ Pipeline (Ch1→Ch6, …)**. *Bước (2) tránh lỗi `name 'partition_states' is not defined` của SecLabFramework (mục 7); ảnh sơ đồ tách nhỏ đã có từ SVL ở bước A2.* *Lý do: tính năng wrap phải biên dịch mã C thành DLL bằng gcc 64-bit trên máy; máy không có hoặc có gcc 32-bit sẽ làm phần mềm dừng với lỗi `WinError 193` (mục 7). Tính năng này không ảnh hưởng các kết luận kiểm chứng.* | Như A2 + A4, thêm: dòng `ipn_debug_bypass: black-box: 0/300 lần crash \| concolic: … sau 3 lần thử` (bằng chứng black-box ↔ white-box); dòng `[Chương 3.0] BMC … bmc_cong_don_don_hang: VI PHẠM bất biến vòng lặp (đã unroll đến bước 48)`; CFG/Call Graph; mục Chương 5 (khuyến nghị LOW). Tổng **42** phân loại CWE | `08_SLF_Ch6_BMC_Fuzz_v0.png` (chụp dòng BMC và dòng black-box/concolic), `09_SLF_Ch6_CWE_v0.png`; `gui_SLF_Ch6_Pipeline_v0.txt` |
| B3 | Bấm **Xuất báo cáo TÍCH HỢP (PDF/DOCX)** | — | `results/tool_reports/SLF_v0.pdf` (+ `.docx`) |
| B4 | Lặp lại B1–B3 với `thanhtoan_donhang_v1.json` | CTL/mutex đều ĐÚNG; dòng BMC **không** vi phạm; còn **15** phân loại (5×CWE-190 + 10 khuyến nghị Ch5 mức LOW — `docs/03` mục 3, 4) | các ảnh `…_v1.png`, `gui_SLF_Ch6_Pipeline_v1.txt`, `SLF_v1.pdf` |
| B5 | (tùy chọn) Bấm **Nạp từ file Excel khác (.xlsx)…** → `thanhtoan_donhang_v0.xlsx` → **5)** | Giống B2 nhưng **không có dòng BMC** (Excel không có cột BMC) — **41** phân loại. Chứng minh Excel và JSON là cùng một đặc tả | `10_SLF_Ch6_Excel_v0.png` |

**Vì sao phần B không chụp từng sơ đồ:** mô hình kết hợp đã chụp ở A2 (SVL tách gọn thành 4 sơ đồ con); ở SLF phải tắt
tách sơ đồ (lỗi `partition_states`) nên chỉ còn 1 hình 35 trạng thái rất rối. 6 sơ đồ luồng con ở tab Ch6 **chỉ để hiển
thị, không được kiểm chứng** — chúng được chụp kèm kết quả kiểm chứng ở phần C. Bằng chứng riêng của phần B là dòng BMC
"bước 48", dòng black-box 0/300 ↔ concolic và bảng 42 phân loại CWE.

## C. SecLabFramework — tab "Ch1: Kripke & Verification" (6 mô hình con)

Đối chiếu với: `results/logs/headless_Ch1_mo_hinh_con.txt` (liệt kê kỳ vọng cho **mọi** luồng của 6 file).

Với **mỗi** file trong `source/spec/mo_hinh_con/` (M1 → M6), làm lần lượt:

1. Bấm **Nạp từ file khác…** → chọn file (vd `M1_tiep_nhan_yeu_cau.json`).
2. Ô **"Luồng đang dùng để kiểm chứng CTL/mutex/deadlock"** → chọn luồng `-v0` **trước**. Mỗi file có nhiều luồng
   (M1: `v0`, `v1a`, `v1b`; M2–M6: `v0`, `v1`) và **phải chạy hết từng luồng** — bước 8 quay lại đây chọn luồng tiếp theo.
3. Bấm **Xóa console**.
4. Khung **"Gợi ý kiểm chứng CTL"** liệt kê các công thức ghi sẵn trong file → chọn từng công thức → **Chạy**
   (hoặc gõ công thức vào ô "Kiểm chứng CTL" → **Kiểm tra công thức**).
5. Bấm **Tìm trạng thái Deadlock** (kỳ vọng: không có).
6. Riêng **M6**: nhập `cb_locked` và `to_locked` vào 2 ô của "Kiểm tra loại trừ lẫn nhau" → **Kiểm tra Mutual Exclusion**.
7. Chụp sơ đồ + console (trước khi chụp, bấm sang **tab sơ đồ của đúng luồng đang chạy** ở nửa dưới, để sơ đồ và
   console trong ảnh là cùng một luồng); sao chép console ra `gui_SLF_Ch1_M<số>_<luồng>.txt`; bấm **Xuất mã TikZ**
   (lưu vào `results/tool_reports/`).
8. Chọn luồng tiếp theo (`-v1`; riêng M1 có 3 luồng `v0`, `v1a`, `v1b`) và lặp lại từ bước 3.
9. **Xuất PDF: làm một lượt riêng** sau khi đã có txt của mọi luồng trong file. Lệnh xuất chép **nguyên nội dung
   console lúc bấm xuất** vào mục "2. Nhật ký kiểm chứng" của PDF (đã xác minh trong mã phần mềm). Nếu xuất ngay sau
   bước 8, mục 2 chỉ còn log của luồng cuối (vì bước 3 xóa console ở mỗi luồng), hoặc chỉ còn các dòng "Đã nạp…".
   1. Bấm **Xóa console** (chỉ **một lần**) → nạp lại file (dòng "Đã nạp: M…json" sẽ đứng đầu log trong PDF).
   2. Lần lượt từng luồng, `v0` trước: chọn luồng → chạy các công thức có dấu **★** (nút "▶ Chạy" mỗi lần chỉ chạy
      1 công thức) → **Tìm trạng thái Deadlock** → riêng M6 thêm **Kiểm tra Mutual Exclusion**.
      **Không** xóa console giữa các luồng.
   3. **Xuất báo cáo chi tiết (PDF/DOCX)** → ghi đè `results/tool_reports/SLF_Ch1_M<số>.pdf`.
   4. Mở PDF, xem mục 2: phải có dòng `-> Chuyển sang kiểm chứng trên luồng '…'` cho **mọi** luồng của file, mỗi
      luồng có đủ các công thức ★ và dòng deadlock.

   Số công thức ★: M1 5, M2 5, M3 5, M4 5, M5 4, M6 6 → cả 6 file khoảng 65 lần bấm "Chạy", mất 15–20 phút.

Tổng cộng **13 luồng** (M1: 3, M2–M6: mỗi file 2). Kỳ vọng tóm tắt:

| Mô hình | Luồng v0 | Luồng v1 |
|---|---|---|
| M1 Tiếp nhận yêu cầu | `AG(!buffer_overflow)`, `AG(!off_by_one)`, `AF(done)` VI PHẠM | **v1a**: `AG(!truncated)` **VI PHẠM**, `AF(done)` VI PHẠM · **v1b**: tất cả ĐÚNG |
| M2 Tạo đơn | `AG(!null_deref)`, `AG(!heap_overflow)`, `AG(!uninit_read)`, `AF(done)` VI PHẠM | tất cả ĐÚNG |
| M3 Tính tiền | `AG(!int_overflow)`, `AG(!negative_amount)`, `AG(!div_by_zero)`, `AF(done)` VI PHẠM | tất cả ĐÚNG |
| M4 Callback | `AG(!buffer_overflow)`, `AG(!hidden_bypass)`, `AF(done)` VI PHẠM | tất cả ĐÚNG |
| M5 Ghi log | `AG(!mem_leak)`, `AG(!format_string)`, `AF(freed)` VI PHẠM | tất cả ĐÚNG |
| M6 Đóng phiên | `AG(!race)`, `AG(!double_free)`, `AG(!use_after_free)`, `AG(!secret_residue)`, `AF(session_freed)`, **Mutex** VI PHẠM | tất cả ĐÚNG, Mutex ĐÚNG |

Các công thức `EF(...)` trong file (vd `EF(len_eq_cap)`, `EF(ptr_null)`) đều **ĐÚNG** ở mọi luồng — chúng cho thấy
mô hình có xét tới trường hợp đó. Ba ảnh **quan trọng nhất** (bắt buộc có):

| Ảnh | Luồng | Vì sao quan trọng |
|---|---|---|
| `11_SLF_Ch1_M1_v1a.png` | M1-v1a (bản "an toàn" phần mềm sinh) | `AG(!truncated)` **VI PHẠM** — phần mềm báo mã sạch nhưng mô hình chỉ ra mã đơn bị cắt cụt (lỗi tầng 2) |
| `12_SLF_Ch1_M2_v0.png` | M2-v0 | 3 lỗi NULL / tính sai kích thước / đọc chưa khởi tạo — static checker của phần mềm KHÔNG phát hiện (tầng 2) |
| `13_SLF_Ch1_M6_v0_mutex.png` | M6-v0 | Mutex `cb_locked`/`to_locked` VI PHẠM + `AG(!secret_residue)` VI PHẠM |

Các luồng còn lại đặt tên tiếp `14_…`, `15_…` theo thứ tự chạy.

## D. SecLabFramework — tab "Ch3: AST/CFG/SMT/BMC" (nhập tay — chứng minh nhóm biết dùng công cụ)

Các ô nằm ở cột trái của tab Ch3 (cuộn xuống nếu cần). Kết quả hiện ở khung bên phải.

| Bước | Ô nhập | Kỳ vọng | Lưu |
|---|---|---|---|
| D1 — BMC v0 | Khung "BMC: unroll vong lap": **init (JSON)** `{"i":0,"total":0}` · **step** `i = i + 1; total = total + 45000000` · **cond_continue** `i < 100` · **assertion** `total <= 2147483647` → **Chạy BMC** | Vi phạm tại bước **48**, `total = 2160000000` (48 dòng × 45 triệu vượt 2.147.483.647) | `30_SLF_Ch3_BMC_v0.png`; `gui_SLF_Ch3_BMC_v0.txt` |
| D2 — BMC v1 | Như D1, đổi **cond_continue** thành `i < 100 and total + 45000000 <= 2000000000` (kiểm tra hạn mức trước khi cộng) | **Không** vi phạm; vòng lặp dừng ở `i = 44`, `total = 1980000000` | `31_SLF_Ch3_BMC_v1.png`; `gui_SLF_Ch3_BMC_v1.txt` |
| D3 — SMT v0 | Khung "Kiểm tra thỏa mãn SMT": điều kiện `price >= 0 and price <= 50000000 and qty >= 1 and qty <= 1000 and price * qty > 2147483647` · biến `price,qty` → **Kiểm tra SAT** | **sat**, ví dụ `price = 44564485, qty = 512` (Z3 có thể chọn giá trị khác, miễn là sat) | `32_SLF_Ch3_SMT_v0.png` |
| D4 — SMT v1 | Điều kiện `price >= 0 and price <= 50000000 and qty >= 1 and qty <= 1000 and price * qty <= 50000000 and price * qty > 2147483647` · biến `price,qty` | **unsat** — với kiểm tra hạn mức dòng, không tồn tại giá trị nào gây tràn | `33_SLF_Ch3_SMT_v1.png` |
| D5 — Overflow | Khung "Biểu thức SỐ HỌC kiểm tra Overflow int32": `price * qty` → **Kiểm tra Overflow int32** | **sat** — luôn sat vì phần mềm xét toàn miền int32 (`docs/03` mục 3) | `34_SLF_Ch3_Overflow.png` |

Gõ đúng từng ký tự; **không dùng số âm dạng `-2000000000`** (bộ phân tích biểu thức của phần mềm không nhận — xem mục 7).

## E. Bộ kiểm chứng của nhóm (BMC + completeness threshold)

Mở Terminal/PowerShell:
```
cd C:\Users\Eco-mart\Desktop\AnToanPhanMem\Nhom07_BTL\source\verify
python chay_kiem_chung.py
```
Script đọc **trực tiếp** 2 file Excel và 6 file mô hình con, in kết quả và ghi đè `results/logs/kiem_chung_nhom.txt`.

Chụp phần `[4] BMC` của mô hình kết hợp v0 và v1 (`40_Nhom_BMC_v0.png`, `41_Nhom_BMC_v1.png`). Kỳ vọng:
- v0: mỗi `AG(!x)` có counterexample. Ví dụ `AG(!off_by_one)` vi phạm ở **k = 2**: `start -> h1_vao -> h1_tran_1_byte`;
  `AG(!double_free)` ở **k = 12**. Completeness threshold **CT = 12**.
- v1: mọi `AG(!x)` **AN TOÀN — đã đạt CT ở k=13**; bảng quét k: UNSAT ở mọi k, `k=13: UNSAT+CT`.
- Phần `[2]` phải trùng 100% với kết quả CTL của phần mềm ở A2/A6 (kiểm tra chéo hai công cụ độc lập).

---

## 6. Đối chiếu sau khi chạy

1. Mở song song file `gui_…txt` của nhóm và file `headless_…txt` tương ứng (bảng ở mục 0.2).
2. Dùng **Ctrl+F** tìm từng công thức (vd `AG(!off_by_one)`) và so sánh kết luận ĐÚNG/VI PHẠM.
3. So số phát hiện Ch2, SAT/UNSAT ở Ch3, dòng BMC, tổng số phân loại CWE.
4. Ghi tên ảnh vào cột **"Ảnh minh chứng"** của `docs/02_bang_before_after.md`.
5. Có thể gửi lại các file `gui_*.txt`, PDF và ảnh để được kiểm tra chéo.

## 7. Xử lý sự cố

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Kết quả CTL khác hẳn kỳ vọng | Nạp nhầm v0/v1 hoặc nạp file cũ | Xem tên đặc tả ở đầu kết quả: phải là `thanhtoan_donhang_v0` hoặc `_v1`; nạp lại từ `Nhom07_BTL/source/spec/` |
| Không thấy dòng BMC ở tab Ch6 | Đang nạp file **Excel** | BMC vòng lặp chỉ có trong file **JSON** → nạp `thanhtoan_donhang_v0.json` |
| `ipn_debug_bypass` black-box crash rất nhiều lần (vd 300/300) | Đang dùng bản đặc tả cũ có tham số tên `merchant_code` (bị đoán là chuỗi) | Nạp lại file mới — tham số phải là `merchant_id, debug_pin` (xem sheet HamSinhMa) |
| Lỗi `Cú pháp không hỗ trợ: UnaryOp…` | Có số âm dạng `-2000000000` trong điều kiện (do sửa tay) | Không sửa tay Excel; viết `x + 2000000000 >= 0` thay cho `x >= -2000000000` |
| Kết quả công thức tự gõ khác với `ctl_checker.py` | Gõ công thức ghép (`&`, `\|`, `->`, lồng nhau) vào phần mềm | Phần mềm chỉ hiểu đúng dạng `OP(p)` / `OP(!p)`; công thức ghép **cho kết quả sai mà không báo lỗi** (`docs/03` mục 6) |
| Số lần crash fuzzing khác (vd 9/300 thay vì 11/300) | Thiết lập seed/số vòng của giao diện | Bình thường — kết luận "có crash / không crash" mới quan trọng |
| Thông báo sanitizer (ASan/UBSan) không khả dụng | gcc trên Windows không hỗ trợ ASan | Bình thường, không ảnh hưởng kết luận của pipeline |
| Sơ đồ Kripke quá rối, chữ chồng lên nhau | Mô hình kết hợp có 35 trạng thái | Tích "Tách sơ đồ lớn…", 12 trạng thái/sơ đồ → **Áp dụng**; hoặc **Xem toàn màn hình** rồi chụp |
| Không bôi đen được nội dung khung kết quả | Phím tắt khác nhau theo khung | Kéo chuột từ đầu đến cuối; hoặc dùng báo cáo PDF/DOCX xuất ra làm bản chữ |
| Hộp thoại "Lỗi pipeline — name 'partition_states' is not defined" ở tab Ch6 SecLabFramework (báo cáo chữ vẫn hiện, nhưng khung sơ đồ còn hiện mô hình cũ, vd `file_upload_auth`) | **Lỗi của SecLabFramework**: khi tích "Tách sơ đồ lớn…" và mô hình có nhiều hơn số trạng thái tối đa, hàm vẽ `expand_flows_for_display` gọi hàm `partition_states` không tồn tại. Mô hình kết hợp của nhóm có 35 trạng thái > 12 nên gặp lỗi; các đặc tả mẫu của GV chỉ 4–7 trạng thái nên không gặp. (SpecVerificationLab không có lỗi này — bước A2 tách sơ đồ bình thường) | Bấm **OK** → bỏ tích "Tách sơ đồ lớn…" (hoặc đặt số trạng thái tối đa = 40) → **Áp dụng** → chạy lại **5)** → kiểm tra phần chữ đầy đủ tới mục `[Chương 6] Phân loại CWE/CVE`. Làm tương tự **trước khi** bấm **Xuất báo cáo TÍCH HỢP** |
| Nút xuất báo cáo cho bản quá ngắn | Chưa chạy pipeline đầy đủ | Chạy **3)** (SVL) hoặc **5)** (SLF) **trước** khi xuất |
| Hộp thoại "Unhandled exception in script … Failed to load dynlib/dll '…\Temp\sl_cwrap_…' … OSError: [WinError 193] %1 is not a valid Win32 application" khi bấm **5)** ở tab Ch6 | Đang tích "Dùng Python wrap cho mã C…": phần mềm (Python 64-bit) biên dịch mã C sinh ra thành DLL bằng gcc của máy rồi nạp DLL đó. WinError 193 = DLL không đúng kiến trúc — thường do gcc trên máy là bản **32-bit** (MinGW cũ, gcc đi kèm Dev-C++/Code::Blocks) | Đóng hộp thoại (mở lại phần mềm nếu bị tắt) → nạp lại file JSON → **bỏ tích** ô "Dùng Python wrap cho mã C…" → bấm **5)**. Kết luận CTL, Ch2, Z3, BMC, fuzzing hàm Python, bảng CWE **không đổi** (log kỳ vọng cũng được tạo khi phần wrap không chạy được). Muốn dùng wrap: mở Command Prompt gõ `gcc -dumpmachine`; nếu không ra `x86_64-…` thì cài gcc 64-bit (MSYS2 UCRT64) và đặt lên đầu PATH |

## 8. Về các file `headless_*` khi nộp bài

- Bằng chứng chính thức trong báo cáo là kết quả **nhóm tự chạy giao diện** (ảnh, `gui_*.txt`, PDF của phần mềm).
- Các file `headless_*` chỉ dùng để đối chiếu. Nếu giữ chúng trong gói nộp, báo cáo phải ghi rõ: *được tạo với hỗ
  trợ của AI bằng cách chạy mã kiểm chứng của phần mềm ngoài giao diện, nhằm đối chiếu*. Cách an toàn hơn: chuyển
  chúng ra khỏi thư mục nộp, giữ làm tài liệu nội bộ của nhóm.
- `kiem_chung_nhom.txt` là kết quả của công cụ do nhóm nộp (`source/verify/`) — giữ trong gói nộp.

## 9. Checklist cuối

- [ ] **A**: ảnh 01–06 (v0 và v1), `gui_SVL_*_v0/v1.txt`, `SVL_v0.pdf`, `SVL_v1.pdf`
- [ ] **B**: ảnh 07–10, có ảnh dòng BMC "bước 48", `gui_SLF_Ch6_Pipeline_v0/v1.txt`, `SLF_v0.pdf`, `SLF_v1.pdf`
- [ ] **C**: đủ 13 luồng của 6 mô hình con; 3 ảnh quan trọng 11–13; `gui_SLF_Ch1_*.txt`; `SLF_Ch1_M1…M6.pdf` (mục 2 của mỗi PDF có log của **mọi** luồng — xem bước 9)
- [ ] **D**: D1–D5 nhập tay thành công, ảnh 30–34
- [ ] **E**: `kiem_chung_nhom.txt` vừa chạy lại, ảnh 40–41
- [ ] Mục 6: đã đối chiếu, mọi kết luận trùng kỳ vọng (ghi lại chỗ nào lệch và lý do)
- [ ] Đã điền cột "Ảnh minh chứng" trong `docs/02_bang_before_after.md`
- [ ] Cả 3 thành viên đã đọc `docs/03`
