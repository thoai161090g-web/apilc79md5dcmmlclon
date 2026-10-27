# AUZA LC79 MD5 prediction API (Render)

Backend Flask lấy lịch sử từ TELE68 `lite-sessions`, chuẩn hóa `list[].id`, `resultTruyenThong`, `dices`, `point`, chạy thuật toán Tài/Xỉu từ file người dùng cung cấp và trả JSON theo cấu trúc dashboard.

## Deploy lên Render
1. Đưa các file trong thư mục này lên một GitHub repository.
2. Render → New → Web Service → chọn repository.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Trong Environment, đặt `TELE68_AT` thành giá trị `at` hợp lệ do bạn cung cấp/được phép sử dụng. Có thể đặt `TELE68_API_URL` nếu endpoint thay đổi.
6. Deploy xong, kiểm tra `/health` và `/api/predict`.

## Endpoints
- `/` — thông tin service
- `/health` — health check
- `/api/predict` — JSON kết quả phân tích
- `/api/raw` — phản hồi nguồn để gỡ lỗi; nên khóa hoặc tắt khi public.

## Cấu hình
- `TELE68_AT`: token truy cập API, bắt buộc; không ghi token vào code hoặc repository.
- `TELE68_API_URL`: mặc định `https://wtxmd52.tele68.com/v1/txmd5/lite-sessions`
- `APP_TIMEZONE`: mặc định `Asia/Ho_Chi_Minh`

Dữ liệu được chuẩn hóa từ `list` với `id`, `resultTruyenThong` (`TAI`/`XIU`), `dices` (mảng 3 xúc xắc) và `point`. `phien_truoc` là phiên hoàn tất mới nhất, `phien_nay` là số phiên kế tiếp. Kết quả dự đoán không đảm bảo thắng. Thuật toán gốc trả trạng thái không áp dụng trong khoảng 00:00–04:59 theo giờ Việt Nam.
