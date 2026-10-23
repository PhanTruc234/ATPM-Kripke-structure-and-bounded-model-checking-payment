# Kiểm chứng mức bộ nhớ: Kripke + BMC (Z3) + ASan

Thư mục này trả lời góp ý của giảng viên: trạng thái Kripke phải là **trạng thái của máy** (dòng lệnh CPU sắp chạy,
biến, từng ô nhớ, vùng heap còn hợp lệ hay đã free), không phải "đầu vào loại X thì báo Y".

| File | Vai trò |
|---|---|
| `thanhtoan.c` | Mã C thật của H1 (chép mã đơn), H3 (cộng tổng tiền int32), H6 (2 worker đóng phiên). Mỗi ca in **địa chỉ và từng byte** trước/sau lệnh nguy hiểm. `-DV1` = bản sửa. |
| `bmc_z3.py` | Mô hình Kripke mức bộ nhớ của đúng 3 hàm trên + BMC: Z3 giải `I(s0) ∧ T(s0,s1) ∧ … ∧ Bad(sk)`. Phản ví dụ gồm đầu vào do Z3 chọn và nội dung bộ nhớ ở mọi bước. |
| `xem_trang_thai.html` | Mẫu trang xem trạng thái; `bmc_z3.py` đổ kết quả vào và ghi `results/xem_trang_thai_bo_nho.html`. |
| `chay_asan.sh` | Biên dịch `thanhtoan.c` với `-fsanitize=address,undefined` và chạy với các đầu vào Z3 tìm ra. Trên Windows dùng clang của llvm-mingw ở `E:\AnToanPhanMem\tools\`; trên Linux/WSL dùng gcc. |
| `bien_dich.bat` | Biên dịch v0, v1 bằng gcc trên Windows. |

## Chạy

```
pip install z3-solver
cd source/kiem_chung_bo_nho
bien_dich.bat                      (hoặc: gcc -O0 -g -o build/tt_v0.exe thanhtoan.c ; gcc -O0 -g -DV1 -o build/tt_v1.exe thanhtoan.c)
build\tt_v0.exe 1 DH20261015000123
python bmc_z3.py                   (khoảng 25 giây; hoặc python bmc_z3.py H1 / H3 / H6)
```

Mở `results/xem_trang_thai_bo_nho.html` bằng trình duyệt (không cần mạng). Dùng phím ← → để đi từng trạng thái.

ASan: `bash chay_asan.sh` (Git Bash trên Windows, hoặc Linux/WSL) → `results/logs/asan_thanhtoan_v0.txt`,
`asan_thanhtoan_v1.txt`. Trên Windows cần thư mục `E:\AnToanPhanMem\tools\llvm-mingw-20261006-ucrt-x86_64`
(clang có ASan, tải từ github.com/mstorsjo/llvm-mingw); gcc MinGW không có ASan.

Kịch bản trình bày đầy đủ: `docs/09_demo_kripke_muc_bo_nho.md`.
