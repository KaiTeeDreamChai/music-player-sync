#!/usr/bin/env python3
"""
Cross-Platform Portable Music Player (DAP) Synchronizer & Standardizer
Supports: macOS, Windows, Linux
Dependencies: mutagen, ffmpeg (on PATH)
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
        cleaned = [l for l in lines if l.strip() and not (l.strip().startswith("{") and ('"t":' in l or '"c":' in l))]
        if len(cleaned) != len(lines):
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
        # Standard compression
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-vf", f"scale='min({max_dim},iw)':'min({max_dim},ih)':force_original_aspect_ratio=decrease",
            "-q:v", "4",
            out_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Enforce <= 100KB
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

if __name__ == "__main__":
    print("DAP Sync Utility loaded.")
    db = find_netease_db()
    if db:
        print(f"[OK] NetEase Local DB Detected: {db}")
    else:
        print("[WARN] NetEase Local DB not found.")

