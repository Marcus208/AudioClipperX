from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Optional

STATUS_PENDING = "Pending"
STATUS_PROCESSING = "Processing"
STATUS_DONE = "Done"
STATUS_FAILED = "Failed"

FORMATS = ["wav", "mp3", "flac", "ogg", "aac", "m4a"]
SAMPLE_RATES = [8000, 16000, 22050, 44100, 48000, 96000]
BIT_DEPTHS = [16, 24, 32]


@dataclass
class FileParams:
    format: str = "wav"
    sample_rate: int = 48000
    bit_depth: int = 24
    channels: int = 2
    output_dir: str = ""
    normalize: bool = False
    normalize_dbfs: float = -1.0  # target peak level in dBFS

    def copy(self) -> FileParams:
        return FileParams(
            format=self.format,
            sample_rate=self.sample_rate,
            bit_depth=self.bit_depth,
            channels=self.channels,
            output_dir=self.output_dir,
        )


@dataclass
class FileEntry:
    input_path: str
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    custom_params: Optional[FileParams] = None
    enabled: bool = True
    status: str = STATUS_PENDING
    error: str = ""

    @property
    def filename(self) -> str:
        return os.path.basename(self.input_path)

    def get_params(self, global_params: FileParams) -> FileParams:
        return self.custom_params if self.custom_params is not None else global_params

    def has_custom_params(self) -> bool:
        return self.custom_params is not None


@dataclass
class AudioTask:
    input_path: str
    output_dir: str
    start_ms: Optional[int]
    end_ms: Optional[int]
    format: str
    sample_rate: int
    bit_depth: int
    channels: int
    normalize: bool = False
    normalize_dbfs: float = -1.0

    @property
    def output_filename(self) -> str:
        name = os.path.splitext(os.path.basename(self.input_path))[0]
        return f"{name}.{self.format}"

    @property
    def output_path(self) -> str:
        return os.path.join(self.output_dir, self.output_filename)


@dataclass
class ProcessResult:
    input_path: str
    success: bool
    logs: list = field(default_factory=list)
    error: Optional[str] = None
