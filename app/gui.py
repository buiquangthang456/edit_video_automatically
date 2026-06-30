"""Tkinter desktop interface for Movie Auto Editor."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core.video_processor import VideoProcessor
from engines.ffmpeg_engine import FFmpegEngine
from models.config import RenderConfig


class MovieAutoEditorApp(tk.Tk):
    """Simple desktop GUI for selecting inputs and rendering a review video."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Movie Auto Editor")
        self.geometry("820x620")
        self.minsize(760, 560)

        self.script_path = tk.StringVar()
        self.voice_path = tk.StringVar()
        self.movie_path = tk.StringVar()
        self.output_path = tk.StringVar(value=str(Path("outputs") / "review_video.mp4"))
        self.resolution = tk.StringVar(value="1080:1920")
        self.status = tk.StringVar(value="Sẵn sàng")
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._worker: threading.Thread | None = None

        self._build_layout()
        self.after(100, self._drain_log_queue)

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=18)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(7, weight=1)

        title = ttk.Label(container, text="Movie Auto Editor", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        note = ttk.Label(
            container,
            text=(
                "Chọn kịch bản, voice-over và video phim. Ứng dụng sẽ dựng video review bằng FFmpeg. "
                "Không có công cụ nào bảo đảm tránh bản quyền/Content ID."
            ),
            wraplength=760,
        )
        note.grid(row=1, column=0, columnspan=3, sticky="we", pady=(0, 16))

        self._file_row(container, 2, "Kịch bản (.txt)", self.script_path, self._browse_script)
        self._file_row(container, 3, "Voice-over", self.voice_path, self._browse_voice)
        self._file_row(container, 4, "Video phim", self.movie_path, self._browse_movie)
        self._file_row(container, 5, "File xuất", self.output_path, self._browse_output)

        options = ttk.Frame(container)
        options.grid(row=6, column=0, columnspan=3, sticky="we", pady=(8, 12))
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="Tỉ lệ xuất").grid(row=0, column=0, sticky="w", padx=(0, 12))
        resolution_box = ttk.Combobox(
            options,
            textvariable=self.resolution,
            values=("1080:1920", "1920:1080", "720:1280", "1280:720"),
            width=18,
        )
        resolution_box.grid(row=0, column=1, sticky="w")

        self.render_button = ttk.Button(options, text="Bắt đầu dựng video", command=self._start_render)
        self.render_button.grid(row=0, column=2, sticky="e")

        log_frame = ttk.LabelFrame(container, text="Log xử lý")
        log_frame.grid(row=7, column=0, columnspan=3, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=14, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        status_bar = ttk.Label(container, textvariable=self.status, anchor="w")
        status_bar.grid(row=8, column=0, columnspan=3, sticky="we", pady=(8, 0))

    def _file_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        command: Callable[[], None],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 12))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="we", pady=4)
        ttk.Button(parent, text="Chọn...", command=command).grid(row=row, column=2, sticky="e", pady=4, padx=(12, 0))

    def _browse_script(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn file kịch bản",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
        )
        if path:
            self.script_path.set(path)

    def _browse_voice(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn file voice-over",
            filetypes=(
                ("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
                ("All files", "*.*"),
            ),
        )
        if path:
            self.voice_path.set(path)

    def _browse_movie(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn video phim",
            filetypes=(
                ("Video files", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"),
                ("All files", "*.*"),
            ),
        )
        if path:
            self.movie_path.set(path)

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Chọn nơi lưu video",
            defaultextension=".mp4",
            initialfile="review_video.mp4",
            filetypes=(("MP4 video", "*.mp4"), ("All files", "*.*")),
        )
        if path:
            self.output_path.set(path)

    def _start_render(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Đang xử lý", "Video vẫn đang được dựng, vui lòng chờ.")
            return

        try:
            config = self._build_config()
        except ValueError as exc:
            messagebox.showerror("Thiếu thông tin", str(exc))
            return

        self._clear_log()
        self._append_log("Bắt đầu dựng video...\n")
        self.status.set("Đang xử lý...")
        self.render_button.configure(state="disabled")
        self._worker = threading.Thread(target=self._render_in_background, args=(config,), daemon=True)
        self._worker.start()

    def _build_config(self) -> RenderConfig:
        values = {
            "script": self.script_path.get().strip(),
            "voice": self.voice_path.get().strip(),
            "movie": self.movie_path.get().strip(),
            "output": self.output_path.get().strip(),
            "resolution": self.resolution.get().strip(),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError("Vui lòng chọn đầy đủ script, voice, movie, output và tỉ lệ xuất.")
        if ":" not in values["resolution"]:
            raise ValueError("Tỉ lệ xuất phải có dạng rộng:cao, ví dụ 1080:1920.")
        return RenderConfig(
            script=Path(values["script"]),
            voice=Path(values["voice"]),
            movie=Path(values["movie"]),
            output=Path(values["output"]),
            resolution=values["resolution"],
        )

    def _render_in_background(self, config: RenderConfig) -> None:
        try:
            engine = FFmpegEngine(logger=self._thread_log)
            VideoProcessor(engine=engine, logger=self._thread_log).render(config)
        except Exception as exc:  # noqa: BLE001 - surface all background errors to the user.
            self._thread_log(f"\nLỗi: {exc}\n")
            self._log_queue.put("__FAILED__")
        else:
            self._log_queue.put("__DONE__")

    def _thread_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _drain_log_queue(self) -> None:
        while True:
            try:
                message = self._log_queue.get_nowait()
            except queue.Empty:
                break
            if message == "__DONE__":
                self.status.set("Hoàn tất")
                self.render_button.configure(state="normal")
                messagebox.showinfo("Hoàn tất", "Video đã dựng xong.")
            elif message == "__FAILED__":
                self.status.set("Có lỗi")
                self.render_button.configure(state="normal")
                messagebox.showerror("Có lỗi", "Dựng video thất bại. Xem log để biết chi tiết.")
            else:
                self._append_log(message)
        self.after(100, self._drain_log_queue)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")


def main() -> None:
    """Run the desktop GUI."""
    app = MovieAutoEditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()