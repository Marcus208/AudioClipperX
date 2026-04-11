# AudioClipperX

A Python desktop tool for trimming audio clips, converting formats, and batch-processing audio and video files — all from a clean GUI.

![AudioClipperX main window](img/UI.png)

---

## Features

- **Waveform timeline** — visual waveform with draggable clip handles and a seekable red playback cursor
- **Flexible trimming** — drag handles, click Mark Start / Mark End while playing, or type times directly into the Start / End fields
- **Format conversion** — output to WAV, MP3, FLAC, OGG, AAC, M4A
- **Sample rate & bit depth** — configurable per file (e.g. 48 kHz / 24-bit for car audio systems)
- **Channel control** — Mono or Stereo
- **Volume normalization** — peak-normalize all outputs to a target dBFS level
- **Video input** — automatically extracts the audio track from MP4, MKV, AVI, MOV, and other video formats
- **Batch processing** — queue any number of files; each file can override the global defaults
- **Per-file parameter overrides** — right-click any file to set its own format, sample rate, bit depth, channels, normalize level, and output directory
- **Parallel processing** — uses all CPU cores via `ProcessPoolExecutor`; the UI stays responsive throughout
- **Real-time log** — per-file progress and gain details printed as processing runs
- **Waveform cache** — waveform data is computed once per file and cached in memory; switching back to a file is instant
- **Flexible file loading** — Add Files dialog, Add Folder scan, drag-and-drop onto the list, or Paste Paths manually (useful on WSL2 where directory listing can fail)

---

## Requirements

- [Anaconda](https://www.anaconda.com/) or Miniconda
- FFmpeg (installed via conda — see below)
- Python 3.11+

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Marcus208/AudioClipperX.git
cd AudioClipperX
```

### 2. Create the conda environment

```bash
conda env create -f environment.yml
conda activate audioclipperx
```

`environment.yml` installs Python 3.11, FFmpeg, and all Python dependencies automatically.

### 3. Install the package in editable mode

```bash
pip install -e .
```

---

## Running

```bash
conda activate audioclipperx
python -m audioclipperx.main
```

---

## Interface overview

The window is divided into four areas:

### 1 — Global Default Parameters (top bar)

| Control | Description |
|---------|-------------|
| **Format** | Output container: `wav`, `mp3`, `flac`, `ogg`, `aac`, `m4a` |
| **Sample Rate** | e.g. `44100`, `48000` Hz |
| **Bit Depth** | `16`, `24`, or `32` bit (WAV only) |
| **Channels** | `Mono` or `Stereo` |
| **Normalize** | Tick to enable peak normalization; set the target level in dBFS (default `-1.0`) |
| **Output Dir** | Folder where all output files are written; click **Browse** to pick one |

These settings apply to every file unless a file has its own overrides (see §4).

### 2 — File list (left panel)

| Column | Meaning |
|--------|---------|
| ☑ | Include / exclude this file from the next processing run |
| **Filename** | Short name; hover to see the full path |
| **Start / End** | Clip start and end times set for this file |
| **Duration** | Length of the trimmed clip |
| **Params** | `Global` or `Custom` (shown in blue when overrides are active) |
| **Status** | `Pending` → `Processing` → `Done ✓` / `Failed ✗` |

**Adding files:**

| Button | Behaviour |
|--------|-----------|
| **+ Add Files** | Open a file picker for individual audio/video files |
| **+ Add Folder** | Scan a folder and add all supported files found in it |
| **+ Paste Paths** | Type or paste absolute file paths, one per line |
| **Drag & drop** | Drop files directly onto the list |

Supported input formats: `.mp3` `.wav` `.flac` `.ogg` `.aac` `.m4a` `.wma` `.opus` `.mp4` `.mkv` `.avi` `.mov` `.flv` `.wmv` `.webm` `.m4v` `.ts`

**Right-click menu:**

| Item | Action |
|------|--------|
| Remove from List | Removes the entry — the original file on disk is **never** deleted |
| Edit Parameters… | Override format, sample rate, bit depth, channels, normalize, and output directory for this file |
| Reset to Global Defaults | Discard any per-file overrides |
| Select All / Deselect All | Toggle the checkbox for every file |

### 3 — Player (right panel)

Click any row in the file list to load it in the player.

**Waveform timeline:**

The large waveform area shows the audio amplitude across the full file duration.

- **Blue handles** (left and right ends of the blue bar) — drag to set the clip start and end points
- **Red line with triangle** — current playback position; drag it to scrub through the audio. Dragging pauses playback automatically.
- The blue highlighted region between the handles is the portion that will be exported.

**Playback controls:**

- **▶ / ⏸** — play or pause; playback stops automatically at the clip end and rewinds to the clip start
- **Time display** — shows current position / total duration (e.g. `0:05.3 / 3:42.0`)

**Clip range controls:**

| Control | Action |
|---------|--------|
| **Start** field | Type a time and press Enter to set the clip start |
| **Mark Start** | Capture the current playback position as the clip start |
| **Mark End** | Capture the current playback position as the clip end |
| **End** field | Type a time and press Enter to set the clip end |
| **Reset** | Restore the range to the full file duration |

Accepted time formats in the Start / End fields:

| Input | Meaning |
|-------|---------|
| `90` | 90 seconds |
| `90.5` | 90.5 seconds |
| `1:30` | 1 min 30 s |
| `1:30.5` | 1 min 30.5 s |
| `0:01:30` | 1 min 30 s (H:MM:SS) |

### 4 — Log panel (bottom)

Displays real-time progress messages and per-file results as processing runs. The progress bar tracks how many files have completed out of the total queued.

---

## Workflow

1. Set the global output parameters in the top bar (format, sample rate, bit depth, output directory, etc.)
2. Add files via **+ Add Files**, **+ Add Folder**, **+ Paste Paths**, or drag-and-drop
3. Click each file in the list to load it in the player; drag the blue handles or use Mark Start / Mark End to set the clip range
4. (Optional) right-click any file to override its parameters individually
5. Make sure at least one file is checked (☑) and an output directory is set
6. Click **Start Processing**

The UI locks during processing. Each file runs in a separate worker process. A summary dialog appears when all files finish, showing how many succeeded or failed (with error details for any failures).

---

## Example: car lock sound (BYD Encore)

The custom lock sound for this vehicle requires:

| Requirement | Value |
|-------------|-------|
| Format | WAV |
| Sample rate | 48000 Hz |
| Bit depth | 24 bit |
| Max duration | 5 seconds |

Set Format to `wav`, Sample Rate to `48000`, Bit Depth to `24` in the Global Default Parameters. Load your audio files, trim each clip to under 5 seconds using the player, enable **Normalize** if desired, then click **Start Processing**.

---

## Notes on WSL2

Running under WSL2 with files on a Windows drive (`/mnt/c/`, `/mnt/e/`, …) can cause intermittent directory I/O errors. If **+ Add Folder** fails, use **+ Paste Paths** and paste the full paths manually — this bypasses the system directory listing entirely.

Chinese (CJK) filenames are supported. The app loads the Microsoft YaHei font (`msyh.ttc`) from the Windows font directory automatically when running under WSL2.

---

## Project structure

```
AudioClipperX/
├── audioclipperx/
│   ├── main.py              # Entry point; CJK font setup
│   ├── models.py            # Data classes (FileEntry, FileParams, AudioTask, …)
│   ├── processor.py         # Core audio processing (runs in subprocess workers)
│   ├── worker.py            # QThread wrapper around ProcessPoolExecutor
│   └── ui/
│       ├── main_window.py   # Top-level window
│       ├── file_list.py     # File table with checkbox, drag-drop, right-click menu
│       ├── player_widget.py # Audio player with waveform loader and clip controls
│       ├── range_slider.py  # Custom waveform timeline widget
│       ├── settings_panel.py
│       ├── params_dialog.py
│       └── log_panel.py
├── img/
│   └── UI.png
├── data/
│   ├── input/               # Source files (git-ignored)
│   └── output/              # Processed files (git-ignored)
├── environment.yml
└── setup.py
```

---

## License

[Apache-2.0](./LICENSE)
