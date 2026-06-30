echo "# Movie Auto Editor" > README.md
# Movie Auto Editor

Ứng dụng Python này tự dựng video review từ 3 file người dùng cung cấp:

1. **Kịch bản chữ** (`.txt`)
2. **Voice-over** đã tạo sẵn (`.mp3`, `.wav`, `.m4a`, ...)
3. **Video phim nguồn** (`.mp4`, `.mov`, `.mkv`, ...)

> Lưu ý quan trọng: công cụ này **không thể bảo đảm tránh bản quyền YouTube hoặc Content ID**. Nó chỉ hỗ trợ dựng video theo hướng review/bình luận: dùng đoạn ngắn, thêm voice-over, phụ đề, crop/zoom và chỉnh màu nhẹ. Bạn vẫn cần bảo đảm quyền sử dụng nội dung hoặc tự đánh giá yếu tố fair use/fair dealing tại nơi bạn sống.

## Yêu cầu đã cài

Bạn đã có đúng các phần chính:

- Python
- Visual Studio Code
- Extension Python, Pylance, Black Formatter, Error Lens
- FFmpeg và FFprobe trong `PATH`

Kiểm tra nhanh trong Terminal của VS Code:

```bash
python --version
ffmpeg -version
ffprobe -version
```

## Cách dùng nhanh

Đặt file vào một thư mục, ví dụ:

```text
project-files/
├── script.txt
├── voice.mp3
└── movie.mp4
```

Chạy lệnh:

```bash
python auto_review_editor.py \
  --script project-files/script.txt \
  --voice project-files/voice.mp3 \
  --movie project-files/movie.mp4 \
  --output outputs/review_video.mp4
```

Mặc định video xuất ra dạng dọc `1080:1920`, phù hợp Shorts/TikTok/Reels. Nếu muốn video ngang YouTube, chạy thêm:

```bash
python auto_review_editor.py \
  --script project-files/script.txt \
  --voice project-files/voice.mp3 \
  --movie project-files/movie.mp4 \
  --output outputs/review_video_ngang.mp4 \
  --resolution 1920:1080
```

## Cách chuẩn bị kịch bản

Nên chia kịch bản thành nhiều đoạn, cách nhau bằng một dòng trống. Mỗi đoạn sẽ được dùng để tạo một clip và phụ đề tương ứng.

Ví dụ `script.txt`:

```text
Hôm nay mình review nhanh bộ phim này và lý do cảnh mở đầu rất quan trọng.

Ở phần giữa phim, nhân vật chính bắt đầu thay đổi sau biến cố lớn.

Đoạn kết tạo cảm giác bất ngờ vì chi tiết này đã được cài từ đầu.
```

Nếu file không có dòng trống, ứng dụng sẽ tự chia kịch bản thành các đoạn ngắn.

## Ứng dụng đang tự làm gì?

- Đọc thời lượng voice-over bằng FFprobe.
- Chia kịch bản thành các phân đoạn theo độ dài chữ.
- Lấy các đoạn video ngắn rải đều từ phim nguồn.
- Crop/scale về đúng tỉ lệ xuất.
- Thêm phụ đề từ kịch bản.
- Ghép tất cả clip lại.
- Gắn voice-over làm âm thanh chính.

## Gợi ý để video review an toàn hơn

Không có mẹo kỹ thuật nào bảo đảm tránh khiếu nại bản quyền. Thay vào đó, hãy tập trung vào nội dung review thật sự:

- Dùng đoạn phim ngắn, chỉ đủ minh họa ý đang bình luận.
- Thêm phân tích, nhận xét, phê bình hoặc giáo dục rõ ràng bằng voice-over.
- Không đăng lại các cảnh dài liên tục.
- Không dùng âm thanh gốc của phim nếu không cần thiết.
- Nếu có thể, dùng trailer/press kit/chất liệu được cấp phép.
- Luôn đọc chính sách YouTube và cân nhắc tư vấn pháp lý nếu kênh có doanh thu lớn.

## Cấu trúc file

- `auto_review_editor.py`: CLI chính để dựng video.
- `requirements.txt`: ghi chú rằng không cần package Python ngoài.
- `outputs/`: thư mục xuất video, được tạo tự động khi chạy.