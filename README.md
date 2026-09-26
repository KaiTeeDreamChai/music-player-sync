# music-player-sync 🎵

> 🎧 **Portable Music Player (DAP) Sync & Audio Processing Skill for Antigravity & AI Agents**  
> 专为便携播放器 (MP3 / HiFi DAP) 打造的音乐库解密、智能转码、封面标准化、歌词清洗与跨平台同步技能。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-brightgreen)](https://github.com/KaiTeeDreamChai/music-player-sync)
[![AI Agents](https://img.shields.io/badge/AI%20Agent-Antigravity%20Compatible-orange)](https://github.com/KaiTeeDreamChai/music-player-sync)

---

## 🌟 核心特色 (Key Features)

- **本地优先工作流 (Local-First Architecture)**：在本地 SSD 维护完整的 1:1 主音乐库，所有解密、转码、封面对齐、歌词清洗在本地完成并 100% 通过健康度复验后，再以增量模式秒级推送到外置 TF 卡。
- **转码前设备确认机制 (Sample Rate Policy)**：
  - **默认/普通便携设备**：严格控制采样率为 **44.1kHz 或 48kHz（16-bit 无损 FLAC / 320k MP3）**，保证普通纯音播放器（如炬力 ATJ2127、瑞芯微 Rockchip Nano、车载音响）100% 硬件流畅硬解。
  - **高端 HiFi 播放器**：若用户指定为旗舰 DAP（如索尼黑砖、艾利和、海贝/山灵旗舰），**无视采样率限制，完整保留 24-bit / 96k / 192k 原生超清母带音质**。
- **封面严格控制在 100KB 以内**：将封面统一压制为 **500×500 Baseline JPEG，严格限制在 100KB 以内**（PNG 自动转码为 JPEG，修复 FLAC 图片头 `w:500, h:500, depth:24`），彻底告别低运存播放器显存溢出（OOM）黑屏。
- **网易云歌词 (LRC) 深度清洗**：自动剔除网易云私有的 `{"t":...}` JSON 逐字/作者脏行，确保第一行直接以标准 `[mm:ss.xx]` 开始，播放器秒解析。
- **网易云数据库无感捕获**：直接读取本地客户端的 SQLite 数据库（`offlineTrack`, `playlistTrackIds`, `dbTrack`），秒级感知新下载歌曲与歌单增删变动，无需任何网络 API 或账号 Cookie。
- **多歌单副本逻辑**：一首歌若同时存在于多个歌单中，在各个歌单文件夹下各保存一份独立完整的音频与歌词文件；未归类歌曲进入 `我的喜欢`。
- **真正跨平台支持**：完整兼容 **macOS、Windows、Linux**，自动处理 APFS NFD 与 Windows/Linux NFC 的 Unicode 编码差异，并自动清除 FAT32 TF 卡上的 `._*` 隐藏碎片。

---

## 📂 仓库结构 (Repository Structure)

```text
music-player-sync/
├── SKILL.md             # Antigravity 标准 Skill 规范定义文件
├── README.md            # 本说明文档
├── LICENSE              # MIT 开源协议
└── scripts/
    └── dap_sync.py      # 跨平台 (macOS/Windows/Linux) 音频与封面处理核心工具脚本
```

---

## 🚀 如何安装使用 (Installation & Usage)

### 方式 1：作为 Antigravity / AI Agent Skill 安装

将本仓库克隆或复制到 Agent 的全局配置或工程配置目录即可：

```bash
# 全局安装 (对本机所有 Agent 生效)
git clone https://github.com/KaiTeeDreamChai/music-player-sync.git ~/.gemini/config/skills/music-player-sync

# 或项目工程安装 (对特定工作区生效)
git clone https://github.com/KaiTeeDreamChai/music-player-sync.git .agents/skills/music-player-sync
```

安装后，Agent 在检测到音频分类、TF 卡同步、网易云音乐整理或播放器解码问题时，会自动激活该技能。

### 方式 2：作为独立 Python 工具运行

依赖项：
```bash
pip install mutagen
# 系统需安装 ffmpeg 并加入 PATH
```

运行核心脚本：
```bash
python scripts/dap_sync.py
```

---

## 📋 便携播放器健康度自检清单 (Pre-Flight Checklist)

在每次同步或拔出 TF 卡前，确保以下指标全部为 0：

- [ ] **PNG 格式封面**: `0`（全部转为 Baseline JPEG）
- [ ] **超标封面 (>100KB)**: `0`（严格 <= 100KB，最大 500×500 px）
- [ ] **异常零尺寸封面**: `0`（FLAC 图片头必须有正确的宽高位深）
- [ ] **JSON 脏行歌词**: `0`（第一行必须以 `[` 时间戳开始）
- [ ] **采样率超标**: 转码前已与用户确认。普通便携播放器不超过 48,000 Hz / 16-bit
- [ ] **系统临时文件**: 已执行 `dot_clean` 清除 `._*` AppleDouble 隐藏碎片

---

## 📄 License

[MIT License](LICENSE) © 2026 KaiTeeDreamChai
