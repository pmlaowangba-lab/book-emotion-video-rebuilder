# Book Emotion Video Rebuilder

从真实书籍出发，生成 1080×1440 情绪读书视频的 Codex Skill。项目包含内容规格、两字毛笔遮罩、固定海面近景飞鸟片头、书封轮播规则、火山引擎 TTS、动态分镜、水波锁书、FFmpeg 合成和剪映草稿脚本。

## 快速开始

```bash
git clone https://github.com/pmlaowangba-lab/book-emotion-video-rebuilder.git
cd book-emotion-video-rebuilder

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/check_environment.py
```

macOS 如果缺少 FFmpeg：

```bash
brew install ffmpeg
```

创建项目：

```bash
python scripts/init_project.py \
  --output-root output \
  --title "自控力" \
  --author "Kelly McGonigal"
```

## 作为 Codex Skill 安装

将仓库链接到 Codex Skill 目录：

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)" ~/.codex/skills/book-emotion-video-rebuilder
```

重新启动 Codex 后，使用：

```text
$book-emotion-video-rebuilder 讲一本书《自控力》
```

## 新电脑需要什么

### 必需项

| 能力 | 依赖 | 是否需要本地模型 |
|---|---|---|
| 项目、时间轴、校验 | Python 3.9+ | 否 |
| 视频编码、音频混音 | FFmpeg + ffprobe | 否 |
| 图像、水波、遮罩处理 | NumPy、OpenCV、Pillow | 否 |
| 片头飞鸟背景 | 仓库已内置 `seagulls-over-sea-close-v001.mp4` | 否 |
| 中文字体 | 仓库已内置杨任东竹石体 Heavy | 否 |

### 云端能力

| 能力 | 默认方案 | 配置 |
|---|---|---|
| 正文生图 | Codex App `image_gen` | 在 Codex App 内运行，不需要仓库密钥 |
| 中文配音 | 火山引擎 TTS | 复制 `assets/volcengine.env.example` 为 `assets/volcengine.env` 并填入 API Key |
| 动态镜头 | Grok CLI，可选 | 安装 Grok CLI 并使用会员 OAuth；缺失时用 FFmpeg 动态图片回退 |

### 本地模型说明

核心流程 **没有必须下载的本地 AI 模型**：没有本地视频模型时，正文画面会使用 FFmpeg 连续微动完成，仍可正常合成成片。

线程 `019fc1d8-9763-7c40-b98c-60a563547e37` 另外部署了一套可选的本地图生视频能力：

- 模型：`prince-canuma/LTX-2.3-dev`
- 文本编码器：`mlx-community/gemma-3-12b-it-4bit`
- 推理器：[Blaizzy/mlx-video](https://github.com/Blaizzy/mlx-video)，Apple Silicon 使用 MLX
- 管线：`dev-two-stage-hq`
- 用途：把不含文字的正文静图转为约 4 秒的克制轻动态镜头
- 回退：模型缺失、生成失败或人物变形时，继续使用 FFmpeg 动态图片

模型权重合计约 61GB，不会提交到 Git。建议新电脑至少预留 80GB 可用空间。完整的安装、调用约束和当前验证状态见 [本地 LTX-2.3 图生视频说明](docs/local-ltx-video.md)。

- 配音已从 VoxCPM2 本地模型切换为火山引擎 TTS，默认音色 `S_Bkoh3uBT1`。
- 生图默认通过 Codex App 云端能力完成。
- Grok 只是可选图生视频通道，不是必需本地模型。
- 如需恢复 VoxCPM2，需另外安装 PyTorch、VoxCPM2 代码和模型权重；当前脚本未接入该分支。

## 私密素材与外部文件

以下内容故意不提交到 GitHub：

1. `assets/volcengine.env`：真实火山引擎凭证。
2. `assets/bgm-library/*.mp3|wav|flac|m4a`：用户本地提供的音乐。
3. `output/`：每本书的生成图、音频、中间视频和成片。

把 BGM 文件放到 `assets/bgm-library/`，然后在 `library.json` 中确认文件名、SHA-256 和 `status: available`。BGM 缺失时不会自动下载替代音乐。

## 剪映草稿（可选）

剪映草稿依赖另一个 `videocut` 项目：

```bash
cd ..
git clone https://github.com/pmlaowangba-lab/videocut.git
cd book-emotion-video-rebuilder
export VIDEOCUT_ROOT="$(cd ../videocut && pwd)"
```

`create_jianying_draft.py` 默认会寻找同级 `../videocut`，也可通过 `--videocut-root` 或 `VIDEOCUT_ROOT` 覆盖。

## 当前需要补齐的素材能力

下列内容在原 Skill 中已被规格引用，但源文件尚未进入项目：

- `scripts/build_book_carousel_cards.py`
- `assets/book-card-library/manifest.json` 及真实书封库
- `assets/sfx-library/jianying-carousel-clockwork-v001.mp3`
- `assets/sfx-library/jianying-book-lock-waterdrop-v001.mp3`

因此，内容、配音、遮罩、水波、动态正文和 FFmpeg 合成脚本可迁移；要完整自动生成“9 张真实书封轮播 + 两个剪映原声音效”，仍需补齐上述四项。

## 检查

```bash
python scripts/check_environment.py
python -m py_compile scripts/*.py
```

`scripts/check_environment.py` 的 `MISSING` 会阻断核心脚本；`OPTIONAL` 表示只影响 TTS、BGM、Grok 或剪映草稿等对应分支。

## 素材来源

默认飞鸟片头使用 Pexels 视频 `10052474`，来源和哈希记录在 `assets/opening-mask-video-library/manifest.json`。原视频作者为 Alexander Savchuk，使用遵循 Pexels License。
