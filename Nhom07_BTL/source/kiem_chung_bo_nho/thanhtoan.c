/*
 * thanhtoan.c — Mã C THẬT của 3 hành vi rủi ro bộ nhớ trong quy trình thanh toán (Nhóm 07).
 *
 * Chương trình KHÔNG chỉ in "đúng/sai": mỗi ca in ra NỘI DUNG BỘ NHỚ THẬT (địa chỉ, từng byte, giá trị
 * giải mã) trước và sau lệnh nguy hiểm. Mỗi lần in là một trạng thái s = (pc, biến, bộ nhớ) — đúng định
 * nghĩa trạng thái của mô hình Kripke mức bộ nhớ trong bmc_z3.py. Đầu vào của các ca chính là phản ví dụ
 * mà BMC/Z3 tìm ra, nên chạy ca này = phát lại phản ví dụ trên chương trình thật.
 *
 *   Ca 1  H1  strcpy mã đơn vào OrderRecord.order_id[16]   -> byte thừa đè lên ô total (tiền đơn hàng)
 *   Ca 2  H1  strcpy vào char buffer[16] trên stack (mã SpecVerificationLab sinh) -> mục tiêu cho ASan
 *   Ca 3  H3  cộng dồn tổng tiền trên ô nhớ int32           -> ô 4 byte không chứa nổi, giá trị quay vòng
 *   Ca 4  H6  2 worker (callback, timeout) đóng chung 1 phiên theo LỊCH CHẠY do BMC tìm ra -> UAF/double free
 *
 * Biên dịch (Windows gcc/MinGW hoặc Linux):
 *   gcc -O0 -g -o tt_v0 thanhtoan.c                 bản lỗi v0
 *   gcc -O0 -g -DV1 -o tt_v1 thanhtoan.c            bản sửa v1
 * Với ASan + UBSan (chỉ Linux/WSL/Docker):
 *   gcc -O0 -g -fsanitize=address,undefined -o tt_v0_asan thanhtoan.c
 *
 * Chạy:
 *   tt_v0 1 DH20261015000123             (mã đơn đúng 16 ký tự, hợp lệ theo nghiệp vụ)
 *   tt_v0 1 DH20261015000123-QUA-DAI     (mã đơn 24 ký tự)
 *   tt_v0 2 DH20261015000123
 *   tt_v0 3 45000000 48                  (48 dòng, mỗi dòng 45.000.000 VND)  hoặc  tt_v0 3 g1,g2,g3,...
 *   tt_v0 4 CCCCT                        (C = worker callback chạy 1 lệnh, T = worker timeout chạy 1 lệnh)
 */
#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#  include <windows.h>
#endif

#ifdef V1
#  define PHIEN_BAN    "v1 (ĐÃ SỬA)"
#  define ORDER_ID_BUF 17          /* 16 ký tự + '\0' */
#else
#  define PHIEN_BAN    "v0 (CÓ LỖI)"
#  define ORDER_ID_BUF 16
#endif

#if defined(__SANITIZE_ADDRESS__)
#  define CO_ASAN 1
#elif defined(__has_feature)
#  if __has_feature(address_sanitizer)
#    define CO_ASAN 1
#  endif
#endif
#ifndef CO_ASAN
#  define CO_ASAN 0
#endif

#define TONG_DON   489000           /* đơn mẫu: 3 món, 489.000 VND */
#define HAN_MUC    2000000000LL     /* CON-04: hạn mức 1 đơn */
#define MAX_DONG   100              /* CON-03 */
#define MAX_GIA    50000000         /* CON-03: giá trị 1 dòng tối đa */

/* ======================================================================= in bộ nhớ */
typedef struct {
    const char *ten;
    size_t off, len;
} Vung;

static void in_byte(const unsigned char *p, const unsigned char *truoc, size_t off, size_t len)
{
    for (size_t k = off; k < off + len; k++) {
        if (truoc && truoc[k] != p[k])
            printf("[%02X]", p[k]);           /* byte vừa bị thay đổi */
        else
            printf(" %02X ", p[k]);
    }
}

/* In từng vùng nhớ: địa chỉ thật | tên vùng | các byte (byte đổi so với 'truoc' đặt trong [..]) */
static void in_vung(const void *base, const unsigned char *truoc, const Vung *v, int nv)
{
    const unsigned char *p = base;
    for (int j = 0; j < nv; j++) {
        printf("    %p  +%-2u %-12s", (void *)(p + v[j].off), (unsigned)v[j].off, v[j].ten);
        in_byte(p, truoc, v[j].off, v[j].len);
        printf("\n");
    }
}

/* ======================================================================= CA 1 — H1, OrderRecord */
typedef struct {
    char    order_id[ORDER_ID_BUF];   /* mã đơn */
    int32_t total;                    /* tổng tiền VND — nằm NGAY SAU order_id trong bộ nhớ */
    int32_t status;                   /* 0 = CHO_THANH_TOAN */
} OrderRecord;

typedef struct {                      /* khung quan sát (giáo trình Hình 2.1): bản ghi + ô địa chỉ trả về */
    OrderRecord rec;
    uint64_t    ret;                  /* bản sao địa chỉ trả về thật của hàm, đặt ngay sau bản ghi */
} Khung;

#ifndef V1
static int h1_nhan_ma_don(OrderRecord *r, const char *raw)
{
    strcpy(r->order_id, raw);                          /* LỆNH NGUY HIỂM: không biết order_id dài bao nhiêu */
    return 0;
}
#else
static int h1_nhan_ma_don(OrderRecord *r, const char *raw)
{
    size_t len = strnlen(raw, sizeof r->order_id);     /* chỉ đọc, tối đa 17 byte */
    if (len > sizeof r->order_id - 1)
        return -1;                                     /* từ chối mã dài hơn 16 ký tự */
    memcpy(r->order_id, raw, len + 1);
    return 0;
}
#endif

static void in_khung(const Khung *k, const unsigned char *truoc)
{
    Vung v[] = {
        {"order_id", offsetof(Khung, rec.order_id), sizeof k->rec.order_id},
        {"total", offsetof(Khung, rec.total), sizeof k->rec.total},
        {"status", offsetof(Khung, rec.status), sizeof k->rec.status},
        {"ret", offsetof(Khung, ret), sizeof k->ret},
    };
    in_vung(k, truoc, v, 4);
    printf("    => total  = %" PRId32 " VND%s\n", k->rec.total,
           k->rec.total == TONG_DON ? "" : "   <-- KHÁC 489000: TIỀN ĐƠN HÀNG ĐÃ BỊ ĐỔI (mất độ chính xác)");
    printf("    => status = %" PRId32 "%s\n", k->rec.status, k->rec.status == 0 ? "" : "   <-- trạng thái đơn bị ghi đè");
}

static int ca_h1(const char *raw)
{
    Khung k;
    unsigned char truoc[sizeof k];

    memset(k.rec.order_id, 0xCC, sizeof k.rec.order_id);   /* 0xCC = byte rác chưa khởi tạo */
    k.rec.total = TONG_DON;
    k.rec.status = 0;
    k.ret = (uint64_t)(uintptr_t)__builtin_return_address(0);

    printf("H1 — %s — strcpy mã đơn vào OrderRecord\n", PHIEN_BAN);
    printf("  sizeof(order_id)=%u  offset total=%u  offset ret=%u   đầu vào: \"%s\" (dài %u ký tự = %u byte kể cả '\\0')\n",
           (unsigned)sizeof k.rec.order_id, (unsigned)offsetof(Khung, rec.total), (unsigned)offsetof(Khung, ret),
           raw, (unsigned)strlen(raw), (unsigned)strlen(raw) + 1);
    printf("\n  TRẠNG THÁI TRƯỚC lệnh copy (pc = dòng copy):\n");
    in_khung(&k, NULL);
    memcpy(truoc, &k, sizeof k);

    int rc = h1_nhan_ma_don(&k.rec, raw);

    printf("\n  TRẠNG THÁI SAU lệnh copy (byte đổi nằm trong [..]):\n");
    in_khung(&k, truoc);
    if (rc != 0)
        printf("\n  KẾT QUẢ: mã đơn bị TỪ CHỐI (dài hơn 16 ký tự) — bộ nhớ không bị ghi\n");
    else
        printf("\n  KẾT QUẢ: order_id = \"%s\"\n", k.rec.order_id);
    if (memcmp(truoc + offsetof(Khung, ret), (unsigned char *)&k + offsetof(Khung, ret), sizeof k.ret) != 0)
        printf("  !! ô địa chỉ trả về đã bị đổi: lệnh return sẽ nhảy tới 0x%016" PRIx64 "\n", k.ret);
    return 0;
}

/* ======================================================================= CA 2 — H1 trên stack (cho ASan) */
/* Nguyên văn mã SpecVerificationLab sinh từ đặc tả v0 (results/logs/gui_SVL_SinhMa_v0.txt, dòng 7-11) */
static void parse_order_id(const char *raw_order_id)
{
#ifndef V1
    char buffer[16];
    strcpy(buffer, raw_order_id);
#else
    char buffer[17];
    size_t len = strnlen(raw_order_id, sizeof buffer);
    if (len > 16) {
        printf("  TỪ CHỐI: mã dài hơn 16 ký tự\n");
        return;
    }
    memcpy(buffer, raw_order_id, len + 1);
#endif
    printf("  buffer = \"%s\"\n", buffer);
}

static int ca_h1_stack(const char *raw)
{
    printf("H1 — %s — parse_order_id (char buffer[%d] cục bộ trên stack), đầu vào %u byte kể cả '\\0'\n",
           PHIEN_BAN, ORDER_ID_BUF, (unsigned)strlen(raw) + 1);
    printf("  ASan: %s\n", CO_ASAN ? "BẬT (vùng đỏ quanh buffer sẽ bắt byte ghi lố)"
                                   : "TẮT — ghi lố vẫn xảy ra nhưng không ai báo (lỗi ẩn)");
    parse_order_id(raw);
    printf("  chạy xong\n");
    return 0;
}

/* ======================================================================= CA 3 — H3, ô nhớ int32 */
static void in_o_total(int i, const void *o, size_t n, int64_t dung)
{
    const unsigned char *b = o;
    int64_t trong_o = (n == 4) ? (int64_t)*(const int32_t *)o : *(const int64_t *)o;
    printf("    i=%-3d ô total (%u byte, little-endian):", i, (unsigned)n);
    for (size_t k = 0; k < n; k++)
        printf(" %02X", b[k]);
    printf("  -> %14" PRId64 "   giá trị đúng = %13" PRId64 "%s\n", trong_o, dung,
           trong_o == dung ? "" : "   <-- MẤT ĐỘ CHÍNH XÁC");
}

static int ca_h3(const int32_t *dong, int n)
{
    int64_t dung = 0;                          /* "biến ma": tổng toán học, chỉ để so sánh */
    int in_het = n <= 12;

    printf("H3 — %s — cộng dồn tổng tiền %d dòng\n", PHIEN_BAN, n);
#ifndef V1
    int32_t total = 0;                         /* ô nhớ 4 byte */
    printf("  int32_t total = 0;  for (i...) total += dong[i];     (miền int32: -2147483648 .. 2147483647)\n");
    for (int i = 0; i < n; i++) {
        int32_t cu = total;
        total += dong[i];                      /* LỆNH NGUY HIỂM: cộng trên ô 32 bit, tràn thì quay vòng */
        dung += dong[i];
        if (in_het || i < 2 || i >= n - 2 || (int64_t)cu + dong[i] != (int64_t)total)
            in_o_total(i, &total, sizeof total, dung);
        else if (i == 2)
            printf("    ...\n");
    }
    printf("\n  KẾT QUẢ: total = %" PRId32 " VND, đúng ra phải là %" PRId64 " VND%s\n", total, dung,
           total == dung ? "" : "  => SỐ TIỀN SAI");
#else
    int64_t total = 0;                         /* ô nhớ 8 byte + kiểm tra hạn mức trước mỗi lần cộng */
    printf("  int64_t total = 0;  if (total + dong[i] > HAN_MUC) từ chối;  total += dong[i];\n");
    for (int i = 0; i < n; i++) {
        if (dong[i] < 0 || dong[i] > MAX_GIA || total + dong[i] > HAN_MUC) {
            printf("    i=%-3d total + dong[i] = %" PRId64 " > hạn mức %lld  => TỪ CHỐI đơn, không cộng\n",
                   i, total + dong[i], HAN_MUC);
            printf("\n  KẾT QUẢ: đơn bị từ chối an toàn; total giữ nguyên %" PRId64 " (= giá trị đúng)\n", total);
            return 0;
        }
        total += dong[i];
        dung += dong[i];
        if (in_het || i < 2 || i >= n - 2)
            in_o_total(i, &total, sizeof total, dung);
        else if (i == 2)
            printf("    ...\n");
    }
    printf("\n  KẾT QUẢ: total = %" PRId64 " VND\n", total);
#endif
    return 0;
}

/* ======================================================================= CA 4 — H6, heap + 2 worker */
enum { MO = 0, PAID = 1, CANCELLED = 2, CLOSED = 3 };
static const char *TEN_TT[] = {"OPEN", "PAID", "CANCELLED", "CLOSED"};

typedef struct {
    int32_t status;
    char   *card;                     /* 16 byte số thẻ (PAN) */
    int     khoa;                     /* mutex: 0 = trống, 'C' / 'T' = worker đang giữ */
} PaymentSession;

/* valid_map (giáo trình mục 3.6): theo dõi vùng heap nào còn hợp lệ — thứ ASan làm bằng shadow memory */
static struct { void *p; const char *ten; size_t n; int hop_le; } g_heap[4];
static int g_nheap;

static void *cap_phat(size_t n, const char *ten)
{
    void *p = calloc(1, n);
    g_heap[g_nheap].p = p;
    g_heap[g_nheap].ten = ten;
    g_heap[g_nheap].n = n;
    g_heap[g_nheap].hop_le = 1;
    g_nheap++;
    return p;
}

static int hop_le(const void *p)
{
    for (int j = 0; j < g_nheap; j++)
        if (g_heap[j].p == p)
            return g_heap[j].hop_le;
    return 0;
}

static void danh_dau_free(const void *p)
{
    for (int j = 0; j < g_nheap; j++)
        if (g_heap[j].p == p)
            g_heap[j].hop_le = 0;
}

static void in_heap(const PaymentSession *s, const char *card)
{
    printf("        heap:");
    for (int j = 0; j < g_nheap; j++)
        printf("  %s@%p(%uB)=%s", g_heap[j].ten, g_heap[j].p, (unsigned)g_heap[j].n,
               g_heap[j].hop_le ? "HỢP LỆ" : "ĐÃ FREE");
    if (hop_le(s))
        printf("  | status=%s khóa=%c", TEN_TT[s->status], s->khoa ? s->khoa : '-');
    if (hop_le(card)) {
        int con_so_the = 0;
        for (int k = 0; k < 16; k++)
            con_so_the |= card[k] != 0;
        printf("  | card: %s", con_so_the ? "CÒN số thẻ" : "đã xóa");
    }
    printf("\n");
}

typedef struct { char ten; int pc; int32_t v; } Worker;

#ifndef V1
/* Kiểm tra 1 truy cập theo valid_map. Không có ASan: dừng ở vi phạm đầu tiên để không chạy hành vi không
   xác định. Có ASan: vẫn chạy thật để ASan tự bắt và in báo cáo. */
static int duoc_phep(const void *p, int la_free, const Worker *w, const char *lenh)
{
    if (hop_le(p))
        return 1;
    printf("     %c dòng %d: %-26s => %s trên vùng ĐÃ FREE\n", w->ten, w->pc, lenh,
           la_free ? "FREE LẦN 2 (double free)" : "TRUY CẬP (use-after-free)");
    if (CO_ASAN) {
        printf("        (ASan bật: chạy thật lệnh này để ASan báo cáo)\n");
        fflush(stdout);
        return 1;
    }
    printf("        (dừng tại vi phạm đầu tiên — biên dịch với -fsanitize=address để ASan báo cáo)\n");
    return 0;
}
#endif

/* Chạy đúng 1 lệnh của worker w. Trả về 1 nếu đã chạy, 2 nếu phải chờ khóa, 0 nếu worker đã xong,
   -1 nếu vi phạm. */
static int buoc(Worker *w, PaymentSession *s, char *card)
{
#ifndef V1
    static const char *MA[] = {"", "s->status = V;", "memset(s->card, 0, 16);", "free(s->card);", "free(s);", "return;"};
    if (w->pc == 5)
        return 0;
    const char *lenh = MA[w->pc];
    switch (w->pc) {
    case 1: if (!duoc_phep(s, 0, w, lenh)) return -1; s->status = w->v; break;
    case 2: if (!duoc_phep(s, 0, w, lenh) || !duoc_phep(card, 0, w, lenh)) return -1; memset(s->card, 0, 16); break;
    case 3: if (!duoc_phep(s, 0, w, lenh) || !duoc_phep(card, 1, w, lenh)) return -1; danh_dau_free(card); free(s->card); break;
    case 4: if (!duoc_phep(s, 1, w, lenh)) return -1; danh_dau_free(s); free(s); break;
    }
#else
    static const char *MA[] = {"", "lock(&s->mtx);", "if (s->status == CLOSED) goto 7;", "s->status = V;",
                               "explicit_bzero(s->card, 16);", "free(s->card);", "s->status = CLOSED;",
                               "unlock(&s->mtx);", "return;"};
    if (w->pc == 8)
        return 0;
    const char *lenh = MA[w->pc];
    switch (w->pc) {
    case 1:
        if (s->khoa) { printf("     %c dòng 1: %-26s => chờ (worker %c đang giữ khóa)\n", w->ten, lenh, s->khoa); return 2; }
        s->khoa = w->ten; break;
    case 2: if (s->status == CLOSED) { printf("     %c dòng 2: %-26s => phiên đã CLOSED, bỏ qua\n", w->ten, lenh); w->pc = 7; in_heap(s, card); return 1; } break;
    case 3: s->status = w->v; break;
    case 4: { volatile char *c = s->card; for (int k = 0; k < 16; k++) c[k] = 0; } break;   /* không bị bỏ như memset */
    case 5: danh_dau_free(card); free(s->card); s->card = NULL; break;
    case 6: s->status = CLOSED; break;
    case 7: s->khoa = 0; break;
    }
#endif
    printf("     %c dòng %d: %-26s\n", w->ten, w->pc, lenh);
    w->pc++;
    in_heap(s, card);
    return 1;
}

static int ca_h6(const char *lich)
{
    PaymentSession *s = cap_phat(sizeof *s, "s");
    char *card = cap_phat(16, "card");
    s->card = card;
    memcpy(card, "4111111111111111", 16);            /* số thẻ thử nghiệm */
    s->status = MO;
    Worker cb = {'C', 1, PAID}, to = {'T', 1, CANCELLED};

    printf("H6 — %s — worker Callback (V=PAID) và worker Timeout (V=CANCELLED) cùng đóng 1 phiên\n", PHIEN_BAN);
    printf("  lịch chạy: %s   (C/T = worker đó chạy 1 lệnh; hết lịch thì chạy nốt C rồi T)\n", lich);
    printf("  ASan: %s\n\n  trạng thái đầu:\n", CO_ASAN ? "BẬT" : "TẮT (dùng valid_map của chương trình)");
    in_heap(s, card);
    for (const char *c = lich; *c; c++) {
        Worker *w = (*c == 'C' || *c == 'c') ? &cb : &to;
        if (buoc(w, s, card) < 0)
            return 1;
    }
    for (;;) {                                       /* chạy nốt: ưu tiên C, C xong hoặc phải chờ khóa thì chạy T */
        int r = buoc(&cb, s, card);
        if (r < 0)
            return 1;
        if (r == 1)
            continue;
        int r2 = buoc(&to, s, card);
        if (r2 < 0)
            return 1;
        if (r == 0 && r2 == 0)
            break;
    }
    printf("\n  KẾT QUẢ: 2 worker xong, không vi phạm bộ nhớ\n");
#ifdef V1
    free(s);                                         /* bộ quản lý phiên giải phóng s sau khi 2 worker xong */
#endif
    return 0;
}

/* ======================================================================= main */
int main(int argc, char **argv)
{
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
    setvbuf(stdout, NULL, _IONBF, 0);                /* in ngay, không mất dòng khi ASan dừng chương trình */
    int ca = argc > 1 ? atoi(argv[1]) : 0;
    const char *a2 = argc > 2 ? argv[2] : NULL;

    switch (ca) {
    case 1: return ca_h1(a2 ? a2 : "DH20261015000123");
    case 2: return ca_h1_stack(a2 ? a2 : "DH20261015000123");
    case 3: {
        static int32_t dong[MAX_DONG * 10];
        int n = 0;
        if (a2 && strchr(a2, ',')) {                 /* danh sách g1,g2,... (phản ví dụ Z3) */
            for (char *p = (char *)a2; *p && n < MAX_DONG * 10; n++) {
                dong[n] = (int32_t)strtol(p, &p, 10);
                if (*p == ',')
                    p++;
            }
        } else {                                     /* <giá mỗi dòng> <số dòng> */
            int32_t gia = a2 ? (int32_t)strtol(a2, NULL, 10) : 45000000;
            n = argc > 3 ? atoi(argv[3]) : 48;
            if (n > MAX_DONG * 10)
                n = MAX_DONG * 10;
            for (int i = 0; i < n; i++)
                dong[i] = gia;
        }
        return ca_h3(dong, n);
    }
    case 4: return ca_h6(a2 ? a2 : "");
    default:
        printf("dùng: %s <ca> [đầu vào]\n"
               "  1 <mã đơn>          H1: strcpy vào OrderRecord, in bộ nhớ trước/sau\n"
               "  2 <mã đơn>          H1: buffer cục bộ trên stack (chạy với ASan)\n"
               "  3 <giá> <số dòng>   H3: cộng dồn int32   (hoặc 3 g1,g2,...)\n"
               "  4 <lịch C/T>        H6: 2 worker đóng phiên theo lịch chạy\n", argv[0]);
        return 2;
    }
}
