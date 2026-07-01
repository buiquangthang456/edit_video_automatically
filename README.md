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


## Chạy giao diện desktop

Nếu bạn không muốn dùng lệnh CLI, chạy giao diện chọn file bằng Tkinter:

```bash
python auto_review_gui.py
```

Trong giao diện, chọn lần lượt:

1. File kịch bản `.txt`
2. File voice-over `.mp3`, `.wav`, `.m4a`, ...
3. File video phim `.mp4`, `.mkv`, `.mov`, ...
4. Nơi lưu video xuất ra
5. Tỉ lệ xuất, ví dụ `1080:1920` cho video dọc hoặc `1920:1080` cho video ngang

Sau đó bấm **Bắt đầu dựng video** và theo dõi log trong app.

## Cách chuẩn bị kịch bản

Nên chia kịch bản thành nhiều đoạn, cách nhau bằng một dòng trống. Mỗi đoạn nên mô tả một phần liên tục của câu chuyện để nội dung dễ kiểm soát. Ứng dụng sẽ tự tách từng câu thành phụ đề ngắn, sau đó căn từng câu với cảnh nguồn.

Ví dụ `script.txt`:

```text
Hôm nay mình review nhanh bộ phim này và lý do cảnh mở đầu rất quan trọng.

Ở phần giữa phim, nhân vật chính bắt đầu thay đổi sau biến cố lớn.

Đoạn kết tạo cảm giác bất ngờ vì chi tiết này đã được cài từ đầu.
```

Nếu file không có dòng trống, ứng dụng vẫn tự tách theo câu và độ dài phụ đề. Tuy nhiên, ngắt đoạn đúng theo từng phần của câu chuyện sẽ giúp chọn cảnh chính xác hơn.

## Ứng dụng đang tự làm gì?

- Đọc thời lượng voice-over bằng FFprobe và dò các khoảng nghỉ tự nhiên trong giọng đọc.
- Tách kịch bản theo đoạn, câu và giới hạn độ dài phụ đề; căn thời điểm đổi phụ đề vào khoảng nghỉ gần nhất của voice.
- Nếu video có phụ đề chữ nhúng, dùng tên nhân vật, địa danh, số và từ khóa chung để căn kịch bản với timeline câu thoại của phim theo đúng thứ tự câu chuyện.
- Bám keyframe gần nhất khi phù hợp để hạn chế bắt đầu clip giữa cảnh. Nếu video không có phụ đề chữ, ứng dụng tự quay về cách lấy cảnh theo thứ tự thời gian.
- Crop/scale về đúng tỉ lệ xuất.
- Thêm phụ đề từ kịch bản.
- Ghép tất cả clip lại.
- Xóa toàn bộ âm thanh gốc, thay bằng voice-over, chuẩn hóa âm lượng và chốt thời lượng output đúng bằng voice.

## Nếu video xuất ra không có tiếng

Phiên bản hiện tại sẽ xóa âm thanh gốc của video phim, thay bằng file voice-over bạn chọn, kiểm tra file voice-over có audio stream trước khi render và kiểm tra lại video output sau khi gắn voice. Nếu app báo lỗi không có tiếng, hãy thử:

1. Mở file voice-over bằng trình nghe nhạc để chắc chắn file có tiếng.
2. Đổi voice-over sang `.wav` hoặc `.mp3` rồi render lại.
3. Kiểm tra log trong app để xem FFmpeg có báo lỗi audio không.
4. Đảm bảo bạn chọn đúng file voice ở ô **Voice-over**, không chọn nhầm file text/video.

## Gợi ý để video review an toàn hơn

Không có mẹo kỹ thuật nào bảo đảm tránh khiếu nại bản quyền. Thay vào đó, hãy tập trung vào nội dung review thật sự:

- Dùng đoạn phim ngắn, chỉ đủ minh họa ý đang bình luận.
- Thêm phân tích, nhận xét, phê bình hoặc giáo dục rõ ràng bằng voice-over.
- Không đăng lại các cảnh dài liên tục.
- Không dùng âm thanh gốc của phim nếu không cần thiết.
- Nếu có thể, dùng trailer/press kit/chất liệu được cấp phép.
- Luôn đọc chính sách YouTube và cân nhắc tư vấn pháp lý nếu kênh có doanh thu lớn.

## Kiến trúc project

Code đã được tách module để dễ mở rộng thay vì gom toàn bộ logic vào một file:

```text
app/                  # CLI, entry point và orchestration cấp ứng dụng
core/                 # Logic chính: segmentation và workflow dựng video
engines/              # FFmpeg/FFprobe media engine
models/               # Dataclass và config models
utils/                # Helper đọc text, escape subtitle, validate input
tests/                # Unit test cho logic cơ bản
auto_review_editor.py # Wrapper tương thích ngược để chạy CLI
auto_review_gui.py    # Launcher giao diện desktop Tkinter
```

Các module quan trọng:

- `app/cli.py`: parse tham số CLI và tạo `RenderConfig`.
- `app/gui.py`: giao diện desktop để chọn file, chọn tỉ lệ xuất và xem log render.
- `core/video_processor.py`: điều phối toàn bộ workflow dựng video.
- `core/segmentation.py`: chia kịch bản và timeline theo thời lượng voice-over.
- `core/alignment.py`: căn các câu trong kịch bản với timeline phụ đề của video nguồn.
- `engines/ffmpeg_engine.py`: tập trung toàn bộ lệnh FFmpeg/FFprobe.
- `models/config.py`, `models/segment.py` và `models/subtitle.py`: cấu trúc dữ liệu chính.
- `utils/text.py` và `utils/validation.py`: helper xử lý text và kiểm tra input.
- `requirements.txt`: ghi chú rằng không cần package Python ngoài.
- `outputs/`: thư mục xuất video, được tạo tự động khi chạy.

## Chạy test

```bash
python -m unittest discover tests
python -m compileall app core engines models utils tests auto_review_editor.py auto_review_gui.py
```
