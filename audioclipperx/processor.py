"""
Audio processing logic. Runs inside subprocess workers — no Qt imports allowed here.
"""
import os
import tempfile

from audioclipperx.models import AudioTask, ProcessResult

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v", ".ts"
}


def process_file(task: AudioTask) -> ProcessResult:
    """Top-level function so ProcessPoolExecutor can pickle it."""
    logs: list[str] = []
    try:
        from pydub import AudioSegment

        logs.append(f"Processing: {os.path.basename(task.input_path)}")

        ext = os.path.splitext(task.input_path)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            logs.append("Video file detected, extracting audio...")
            tmp_path = _extract_audio_from_video(task.input_path, task.sample_rate)
            try:
                audio = AudioSegment.from_wav(tmp_path)
            finally:
                os.unlink(tmp_path)
            logs.append("Audio extraction complete")
        else:
            audio = AudioSegment.from_file(task.input_path)

        total_ms = len(audio)
        start = task.start_ms if task.start_ms is not None else 0
        end = task.end_ms if task.end_ms is not None else total_ms

        if start >= total_ms:
            raise ValueError(
                f"Start point ({start / 1000:.2f}s) exceeds audio duration ({total_ms / 1000:.2f}s)"
            )
        end = min(end, total_ms)

        if start > 0 or task.end_ms is not None:
            logs.append(
                f"Trimming: {start / 1000:.2f}s → {end / 1000:.2f}s "
                f"(duration {(end - start) / 1000:.2f}s)"
            )
            audio = audio[start:end]

        if audio.frame_rate != task.sample_rate:
            logs.append(f"Sample rate: {audio.frame_rate} Hz → {task.sample_rate} Hz")
            audio = audio.set_frame_rate(task.sample_rate)

        if audio.channels != task.channels:
            label = "mono" if task.channels == 1 else "stereo"
            logs.append(f"Channels: {audio.channels}ch → {task.channels}ch ({label})")
            audio = audio.set_channels(task.channels)

        target_width = task.bit_depth // 8
        if audio.sample_width != target_width:
            logs.append(f"Bit depth: {audio.sample_width * 8}bit → {task.bit_depth}bit")
            audio = audio.set_sample_width(target_width)

        if task.normalize:
            gain = task.normalize_dbfs - audio.max_dBFS
            logs.append(
                f"Normalize: peak {audio.max_dBFS:.1f} dBFS -> "
                f"{task.normalize_dbfs:.1f} dBFS (gain {gain:+.1f} dB)"
            )
            audio = audio.apply_gain(gain)

        os.makedirs(task.output_dir, exist_ok=True)
        export_kwargs: dict = {}
        if task.format == "mp3":
            export_kwargs["bitrate"] = "320k"

        audio.export(task.output_path, format=task.format, **export_kwargs)
        logs.append(f"Done ✓ → {os.path.basename(task.output_path)}")

        return ProcessResult(input_path=task.input_path, success=True, logs=logs)

    except Exception as exc:
        error_msg = str(exc)
        logs.append(f"Error: {error_msg}")
        return ProcessResult(
            input_path=task.input_path,
            success=False,
            logs=logs,
            error=error_msg,
        )


def _extract_audio_from_video(video_path: str, sample_rate: int) -> str:
    import ffmpeg

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    (
        ffmpeg.input(video_path)
        .output(tmp_path, acodec="pcm_s16le", ar=sample_rate, ac=2)
        .overwrite_output()
        .run(quiet=True)
    )
    return tmp_path
