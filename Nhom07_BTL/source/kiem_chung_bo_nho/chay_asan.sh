#!/usr/bin/env bash
# chay_asan.sh — Chạy ASan + UBSan trên mã C THẬT của đề tài (thanhtoan.c), với ĐÚNG các đầu vào mà BMC/Z3
# tìm ra (xem results/logs/bmc_z3.txt, dòng "phát lại trên chương trình C thật").
#
# Windows (Git Bash): dùng clang của llvm-mingw đặt ở E:\AnToanPhanMem\tools\llvm-mingw-20261006-ucrt-x86_64
#   (gcc MinGW không có thư viện ASan). Linux/WSL: dùng gcc của máy (sudo apt install gcc).
# Chạy:   cd source/kiem_chung_bo_nho && bash chay_asan.sh
# Kết quả: results/logs/asan_thanhtoan_v0.txt và asan_thanhtoan_v1.txt
set -u
cd "$(dirname "$0")"
mkdir -p build ../../results/logs

LLVM_MINGW=../../../tools/llvm-mingw-20261006-ucrt-x86_64/bin
if [ -d "$LLVM_MINGW" ]; then
  PATH="$(cd "$LLVM_MINGW" && pwd):$PATH"      # cũng để Windows tìm thấy libclang_rt.asan_dynamic-x86_64.dll
  CC=x86_64-w64-mingw32-clang
  export ASAN_OPTIONS=                          # LeakSanitizer không có trên Windows
else
  CC=gcc
  export ASAN_OPTIONS=detect_leaks=1
fi

CA=(
  "1 DH20261015000123"            # H1: mã đơn HỢP LỆ 16 ký tự, ghi lố 1 byte vào ô total (cùng struct)
  "1 DH20261015000123-QUA-DAI"    # H1: 24 ký tự, đè total, status, ret (vẫn trong cùng khung)
  "2 DH20261015000123"            # H1: cùng đầu vào nhưng buffer là biến cục bộ riêng trên stack
  "3 50000000 43"                 # H3: 43 dòng x 50.000.000, ô int32 tràn
  "4 CCCCT"                       # H6: C chạy hết rồi T -> dùng vùng đã free
  "4 CCTTTC"                      # H6: lịch xen kẽ Z3 tìm ra -> free card 2 lần
)

echo "Biên dịch bằng: $("$CC" --version | head -1)"
for v in v0 v1; do
  if [ "$v" = v1 ]; then DEF=-DV1; else DEF=; fi
  "$CC" -O0 -g -fsanitize=address,undefined -fno-omit-frame-pointer $DEF -o "build/tt_${v}_asan" thanhtoan.c || exit 1
  log="../../results/logs/asan_thanhtoan_$v.txt"
  echo "### ASan + UBSan trên thanhtoan.c — $v — $("$CC" --version | head -1) — $(date '+%d/%m/%Y %H:%M')" > "$log"
  echo
  echo "== $v: ASan/UBSan báo gì cho từng ca (đầy đủ trong $log)"
  for ca in "${CA[@]}"; do
    # shellcheck disable=SC2086
    out=$("./build/tt_${v}_asan" $ca 2>&1)
    rc=$?
    { echo; echo "===== ./tt_${v}_asan $ca"; echo "$out"; echo "----- mã thoát: $rc"; } >> "$log"
    # dòng báo lỗi đầu tiên do ASan/UBSan in ra (không phải do chương trình in)
    bao=$(echo "$out" | grep -m1 -E "ERROR: AddressSanitizer|runtime error" | sed -E 's/^==[0-9]+==//; s/ on address.*| on 0x.*//')
    printf "   %-30s -> %s\n" "$ca" "${bao:-không có báo cáo nào}"
  done
done
