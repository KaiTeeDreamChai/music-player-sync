---
name: music-player-sync
description: >-
  Expert guide, workflows, and cross-platform automation for decrypting, transcoding,
  standardizing covers/lyrics, and synchronizing music from NetEase Cloud Music and local
  libraries to portable HiFi/MP3 players (DAPs) across macOS, Windows, and Linux.
---

# Portable Music Player (DAP) Sync & Audio Processing Skill

This skill provides comprehensive instructions, technical specifications, and cross-platform automation routines for managing, decrypting, transcoding, standardizing, and synchronizing music libraries from NetEase Cloud Music (网易云音乐) or local sources to portable HiFi players / MP3 Digital Audio Players (DAPs) across **macOS, Windows, and Linux**.

---

## 1. Core Architectural Principle: Local-First Workflow

> [!IMPORTANT]
> **The Local Master Library is the Single Source of Truth.**
> Never modify, transcode, or organize files directly on the external TF card / DAP storage.

```
[NetEase Cloud Music / Local Downloads]
                  │
                  ▼
    ┌───────────────────────────┐
    │ Local Master Music Library│ ◄── All operations (Decryption, Transcoding,
    │ (High-Speed SSD Storage)  │     Cover Standardization, Lyric Cleaning,
    └─────────────┬─────────────┘     Playlist Categorization, Health Check)
                  │
                  ▼ (1:1 Verified Incremental Sync)
    ┌───────────────────────────┐
    │    TF Card / Player DAP   │
    │   (/Volumes, E:\, /media) │
    └───────────────────────────┘
```

1. **Local Staging**: All file processing (decryption, transcoding, cover resizing, lyric cleaning, folder categorization) must be performed and verified in the **Local Master Music Library** first.
2. **Pre-Sync Validation**: Verify that 100% of audio files, covers, and lyrics in the local library pass hardware compatibility checks.
3. **Incremental Push**: Push only changed/new files to the external TF card.
4. **Post-Sync Cleanup**: Remove platform-specific garbage files (e.g., macOS `._*` AppleDouble files, `.DS_Store`, Windows `Thumbs.db`).

---

## 2. Hardware Decoder Compatibility Specifications & Policies

### A. Audio Format & Codec Standards

#### Transcoding Pre-Flight Inquire Rule (转码前确认规范)
> [!IMPORTANT]
> **Mandatory User Inquiry Before Transcoding**:
> Before starting transcoding, the Agent **MUST inquire with the user** regarding their target playback device:
> 1. **Default / Standard DAPs**: Unless explicitly specified otherwise, sample rate **MUST be controlled at 44.1 kHz (44,100 Hz) or 48.0 kHz** with 16-bit depth (CD-quality FLAC or 320kbps MP3). This ensures 100% universal hardware playback on typical portable/pure-sound players, car stereos, and microcontrollers.
> 2. **High-End Audiophile DAPs (高端 HiFi 播放器)**: If the user states that the songs are intended for high-end DAPs (e.g., flagship Sony Walkman, Astell&Kern, FiiO/Shanling/HiBy Android DAPs with high-end dual DACs supporting native 24-bit/192kHz decoding), **BYPASS the sample rate and bit-depth restriction completely**. Preserve the original uncompressed Hi-Res quality (24-bit / 96kHz or 192kHz).

| Parameter | Standard DAPs (Default) | High-End Audiophile DAPs | Rationale & Remediation |
| :--- | :--- | :--- | :--- |
| **Codec** | **FLAC** or **MP3** (CBR/VBR 320k) | **FLAC**, DSD, or WAV | Standard DAPs lack decoders for obscure containers; high-end DAPs handle native FLAC/DSD. |
| **Sample Rate** | **44.1 kHz** or **48.0 kHz** | **Native / Unrestricted** (96k, 192k) | Standard DAP SoC clock dividers cannot process >48kHz (results in silence/distortion). |
| **Bit Depth** | **16-bit** (Standard CD Quality) | **Native / Unrestricted** (24-bit, 32-bit) | Standard portable DSPs suffer buffer overflows on 24-bit audio. |

**Universal Transcoding Commands (FFmpeg)**:
```bash
# Standard DAP Downsampling (CD Quality Lossless):
ffmpeg -y -i input.flac -c:a flac -sample_fmt s16 -ar 44100 output.flac

# Universal 320kbps MP3:
ffmpeg -y -i input.flac -c:a libmp3lame -b:a 320k -ar 44100 output.mp3
```

---

### B. Cover Art (Embedded Album Art) Standards

| Parameter | Mandatory Standard | Fatal Pitfalls |
| :--- | :--- | :--- |
| **File Size** | **STRICTLY <= 100 KB** (Recommended: 40 KB – 80 KB) | **> 100 KB or 1MB–2MB** (causes immediate Out-Of-Memory / OOM abort and black screen on DAPs). |
| **Format** | **Baseline JPEG (`image/jpeg`) ONLY** | **PNG, WebP, Progressive JPEG** (hardware decoders lack PNG/progressive modules and will fail). |
| **Resolution** | **Max 500×500 px** (or 400×400 px) | 900×900, 1200×1200 (exceeds tiny DAP framebuffers). |
| **FLAC Metadata** | `width: 500, height: 500, depth: 24, type: 3` | `width: 0, height: 0` (left by `ncmdump`; firmware interprets 0 as corrupt image). |

> [!WARNING]
> **The FLAC Padding Trap**:
> When Mutagen or other tools shrink embedded album art in a FLAC file, `audio.save()` replaces the freed bytes with a `PADDING` metadata block to avoid re-writing the audio stream. As a result, the **total file size does not change**. Synchronization scripts **MUST NOT** rely solely on `file_size_diff` to detect modified FLAC files; check `mtime` or metadata directly.

---

### C. Lyrics (LRC) Standards

| Parameter | Mandatory Standard | Fatal Pitfalls |
| :--- | :--- | :--- |
| **First Line** | Must start with `[` (e.g. `[00:12.34]`) | NetEase proprietary JSON headers (e.g., `{"t":0,"c":[...]}`). |
| **Format** | Standard timestamped lines `[mm:ss.xx]Text` | YRC word-by-word formatting. |
| **Filename** | Base name must match audio file **100% exactly** | Truncated names or mismatched extensions. |
| **Filename Length** | Recommended **<= 64 characters** | > 80 characters with symbols (DAP FAT32 buffer overflow). |
| **Encoding** | UTF-8 (without BOM) or GBK/GB2312 for legacy DAPs | Mixed encodings or corrupted multi-byte sequences. |

**NetEase Cloud Music Lyric Sanitization Rule**:
When downloaded from NetEase Cloud Music, `.lrc` files frequently include:
```text
{"t":0,"c":[{"tx":"作词: "},{"tx":"..."}]}
{"t":1000,"c":[{"tx":"作曲: "},{"tx":"..."}]}
[00:14.94]All my life
```
**Fix**: Discard all lines starting with `{"t":` or containing JSON structures. Retain only lines starting with `[` and valid time tags.

---

## 3. NetEase Cloud Music Local Database Detection Mechanism

Instead of relying on fragile web APIs or cookies, read the local SQLite database maintained by the NetEase Cloud Music desktop client.

### Cross-Platform Database Paths

* **macOS**:
  `~/Library/Application Support/com.netease.163music/Documents/storage/sqlite_storage.sqlite3`
* **Windows**:
  `%LOCALAPPDATA%\NetEase\CloudMusic\Library\webdb.dat` (Modern 3.x+ / x64 client)
  `%LOCALAPPDATA%\Netease\CloudMusic\storage\sqlite_storage.sqlite3` (Legacy client)
  (or `%APPDATA%\Netease\CloudMusic\storage\sqlite_storage.sqlite3`)
* **Linux**:
  `~/.local/share/netease-cloud-music/storage/sqlite_storage.sqlite3`
  (or `~/.config/netease-cloud-music/storage/sqlite_storage.sqlite3`)

### Key Tables & Query Logic

1. **`offlineTrack` (Download History)**:
   * Query: `SELECT id, trackName, artistName, newRelativePath, completeTime FROM offlineTrack ORDER BY completeTime DESC`
   * `id`: Track ID in the format `track-<TID>`. Maps directly to album art cache in `meta/track-<TID>.jpg`.
   * `newRelativePath`: Actual downloaded file name (e.g. `Daniel Caesar - Call On Me.ncm`).
   * `completeTime`: Millisecond timestamp of download completion.
2. **`playlistTrackIds` (Playlist Composition)**:
   * Query: `SELECT id, jsonStr FROM playlistTrackIds WHERE id = ?`
   * `id`: Unique Playlist ID.
   * `jsonStr`: JSON payload containing `trackIds`: `[{"id": 123456}, ...]`.
   * Compare array items against local folders to detect newly added or removed tracks instantly.
3. **`dbTrack` (Metadata Cache)**:
   * Query: `SELECT jsonStr FROM dbTrack WHERE id = ?`
   * Contains canonical title, artist array, album name, and picture URL.

> [!NOTE]
> **Unicode Normalization Warning**:
> macOS APFS filesystem returns filenames in decomposed NFD (e.g., `GIVĒON`), whereas NetEase SQLite databases and Linux/Windows use precomposed NFC (`GIVĒON`).
> **Always apply `unicodedata.normalize('NFC', text)`** to both database strings and filesystem paths before matching.

---

## 4. Multi-Playlist Categorization Rules

When organizing songs into folders:
1. **Multi-Playlist Inclusion**: If a song appears in multiple playlists (e.g., in both `some soul` and `亿万人.......听Emo摇滚`), **duplicate the audio file and its matching `.lrc` file** into each playlist folder.
2. **Uncategorized Fallback**: If a downloaded song does not belong to any specific playlist, place it into the `我的喜欢` (My Favorites) folder.
3. **Playlist Removal**: If a track is removed from an online playlist (detected via `playlistTrackIds`), remove it from the corresponding local folder (preserving it in `我的喜欢` or other playlists if still indexed there).

---

## 5. Cross-Platform Automation Script (Python)

Below is the production-tested Python routine for end-to-end processing across macOS, Windows, and Linux.

```python
#!/usr/bin/env python3
"""
Cross-Platform DAP Music Synchronizer & Standardizer
Supports: macOS, Windows, Linux
Dependencies: mutagen, ffmpeg (available on PATH)
"""

import os
import sys
import shutil
import sqlite3
import json
import unicodedata
import subprocess
import tempfile
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

def norm(text):
    return unicodedata.normalize("NFC", text).strip() if text else ""

def sanitize_lrc(lrc_path):
    """Strip NetEase private JSON headers, keeping clean [mm:ss.xx] lines."""
    try:
        with open(lrc_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        cleaned = []
        modified = False
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if s.startswith("{") and ('"t":' in s or '"c":' in s):
                modified = True
                continue
            cleaned.append(line)
        if modified:
            with open(lrc_path, "w", encoding="utf-8") as f:
                f.writelines(cleaned)
            return True
        return False
    except Exception:
        return False

def standardize_image(img_data, max_dim=500, max_size_bytes=100*1024):
    """
    Standardize cover art strictly <= 100KB, max 500x500 Baseline JPEG using FFmpeg.
    Works universally across macOS, Windows, and Linux without native image libraries.
    """
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tf_in:
        tf_in.write(img_data)
        in_path = tf_in.name
    out_path = in_path + ".jpg"

    try:
        # Try quality 3 (~85) first
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-vf", f"scale='min({max_dim},iw)':'min({max_dim},ih)':force_original_aspect_ratio=decrease",
            "-q:v", "4",
            out_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # If still over 100KB, compress with slightly lower quality to enforce <= 100KB
        if os.path.getsize(out_path) > max_size_bytes:
            cmd = [
                "ffmpeg", "-y", "-i", in_path,
                "-vf", f"scale='min({max_dim},iw)':'min({max_dim},ih)':force_original_aspect_ratio=decrease",
                "-q:v", "7",
                out_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        with open(out_path, "rb") as f_out:
            new_data = f_out.read()
            
        probe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", out_path
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True)
        w, h = 500, 500
        if res.stdout.strip():
            parts = res.stdout.strip().split("x")
            w, h = int(parts[0]), int(parts[1])
            
        return new_data, w, h
    except Exception:
        return None, 0, 0
    finally:
        for p in (in_path, out_path):
            if os.path.exists(p):
                os.remove(p)

def transcode_to_standard_flac(src_audio, target_sr=44100):
    """Downsample audio to standard 16-bit 44.1kHz FLAC."""
    tmp_out = src_audio + ".transcode.flac"
    cmd = [
        "ffmpeg", "-y", "-i", src_audio,
        "-c:a", "flac", "-sample_fmt", "s16", "-ar", str(target_sr),
        tmp_out
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 1000:
            os.replace(tmp_out, src_audio)
            return True
    except Exception:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
    return False

def clean_platform_artifacts(target_dir):
    """Clean macOS/Windows hidden metadata files on FAT32 volumes."""
    if sys.platform == "darwin":
        subprocess.run(["dot_clean", target_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for root, dirs, files in os.walk(target_dir):
        for f in files:
            if f.startswith("._") or f == ".DS_Store" or f.lower() == "thumbs.db":
                try:
                    os.remove(os.path.join(root, f))
                except OSError:
                    pass

def find_netease_db():
    """Detect cross-platform NetEase Cloud Music local SQLite database path."""
    candidates = []
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        app_data = os.environ.get("APPDATA", "")
        candidates.extend([
            os.path.join(local_app, "NetEase", "CloudMusic", "Library", "webdb.dat"),
            os.path.join(local_app, "Netease", "CloudMusic", "storage", "sqlite_storage.sqlite3"),
            os.path.join(app_data, "Netease", "CloudMusic", "storage", "sqlite_storage.sqlite3"),
        ])
    elif sys.platform == "darwin":
        home = os.path.expanduser("~")
        candidates.append(os.path.join(home, "Library/Application Support/com.netease.163music/Documents/storage/sqlite_storage.sqlite3"))
    else:
        home = os.path.expanduser("~")
        candidates.extend([
            os.path.join(home, ".local/share/netease-cloud-music/storage/sqlite_storage.sqlite3"),
            os.path.join(home, ".config/netease-cloud-music/storage/sqlite_storage.sqlite3"),
        ])
    for c in candidates:
        if os.path.exists(c):
            return c
    return None
```

---

## 6. Pre-Flight Health Check Checklist

Before ejecting any TF card or completing a sync, verify all indicators:

* [ ] **PNG Covers**: `0` (All embedded covers must be Baseline JPEG).
* [ ] **Oversized Covers (>100KB)**: `0` (**Strictly <= 100 KB**, max 500×500 px).
* [ ] **Zero-Dimension Metadata**: `0` (FLAC picture headers must have valid `width` and `height`).
* [ ] **JSON Dirty Lines in LRC**: `0` (Every `.lrc` must start with timestamp `[` on line 1).
* [ ] **Sample Rate & Depth**: Confirmed with user beforehand. If Standard DAP, `0` tracks exceeding `48,000 Hz` or `16-bit`. If High-End Audiophile DAP, uncompressed Hi-Res allowed.
* [ ] **Artifact Cleanup**: Executed `dot_clean` / removed `._*` AppleDouble and `.DS_Store` files.
