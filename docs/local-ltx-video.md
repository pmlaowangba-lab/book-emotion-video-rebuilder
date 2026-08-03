# LTX-2.3 本地图生视频

本文记录 Codex 线程 `019fc1d8-9763-7c40-b98c-60a563547e37` 中部署的本地模型，供迁移到其他 Apple Silicon 电脑时复现。它是可选增强能力，不是生成读书视频的必需依赖。

## 它负责什么

LTX-2.3 只负责把已经确认的正文分镜静图转换成短视频，不负责生图、书封、字幕、配音、BGM、片头遮罩或最终合成。

适合的动态包括头发轻摆、树叶微动、水面缓慢流动、云层或光影变化。每个镜头只给一种低幅动作，默认输出 97 帧、24fps，约 4 秒。

以下画面不要交给模型：

- 真实书封、书名轮播、标题页和字幕画面；模型可能破坏文字。
- 需要完全保持几何形状的 UI、图表或排版。
- 已经出现变脸、肢体变化、新增物体、闪烁或构图漂移的镜头。

遇到上述情况直接回退到 FFmpeg 连续缩放、平移或呼吸动效。

## 部署组合

| 项目 | 本次部署值 | 作用 |
|---|---|---|
| 主模型 | `prince-canuma/LTX-2.3-dev` | LTX-2.3 Dev/HQ 图生视频 |
| 文本编码器 | `mlx-community/gemma-3-12b-it-4bit` | 理解动作提示词 |
| 推理器 | `Blaizzy/mlx-video` | Apple Silicon 的 MLX 推理实现 |
| 管线 | `dev-two-stage-hq` | 两阶段 HQ 生成与放大 |
| MLX | `0.31.1` | 本次机器实际安装版本 |
| MLX-Video | `0.0.1`，源码提交 `87db56a` | 本次机器实际安装状态 |
| 本次机器 | M3 Max、40 核 GPU、48GB 统一内存 | 已完成下载的硬件基线 |

本机落盘体积：LTX 主模型约 53GB，Gemma 文本编码器约 8.1GB，Python 环境和缓存另计。建议至少保留 80GB 可用空间。

## 2026-08-03 的实际状态

- LTX-2.3 主模型已完成 31/31 文件下载，8/8 Transformer 分片齐全。
- Gemma 3 12B 4-bit 文本编码器仍在后台断点下载。
- 因文本编码器尚未完整，端到端图生视频没有完成最终运行验收。
- “模型文件已落盘”不等于“本地动态视频已经可用于生产”；必须通过下方验收后才能启用。

完成下载后，应更新本节状态并保留一条实际生成成功的短视频验收记录。

## 新电脑安装

要求：macOS、Apple Silicon、Python 3.10+、Git、FFmpeg，建议使用 `uv` 管理独立环境。

```bash
mkdir -p ltx-video-local/models
cd ltx-video-local

git clone https://github.com/Blaizzy/mlx-video.git source
python3 -m venv source/.venv
source source/.venv/bin/activate
pip install --upgrade pip
pip install git+https://github.com/Blaizzy/mlx-video.git
pip install huggingface_hub

hf download prince-canuma/LTX-2.3-dev \
  --local-dir models/LTX-2.3-dev

hf download mlx-community/gemma-3-12b-it-4bit \
  --local-dir models/gemma-3-12b-it-4bit
```

Hugging Face 下载支持断点续传；下载中断后重复执行相同命令即可。不要把 Hugging Face Token 写进仓库、脚本或日志。

模型来源：

- [LTX-2.3 Dev 权重](https://huggingface.co/prince-canuma/LTX-2.3-dev)
- [Gemma 3 12B 4-bit 文本编码器](https://huggingface.co/mlx-community/gemma-3-12b-it-4bit)
- [MLX-Video 推理器](https://github.com/Blaizzy/mlx-video)

## 推荐目录

模型目录应放在仓库外部，避免误提交几十 GB 的权重：

```text
ltx-video-local/
├── models/
│   ├── LTX-2.3-dev/
│   └── gemma-3-12b-it-4bit/
├── source/
└── output/
```

在终端中声明路径，供后续脚本或 Skill 查找：

```bash
export LTX_VIDEO_LOCAL_ROOT="/absolute/path/to/ltx-video-local"
```

不要把个人电脑的绝对路径写死在仓库中。

## 参考调用

```bash
python -m mlx_video.models.ltx_2.generate \
  --pipeline dev-two-stage-hq \
  --model-repo "$LTX_VIDEO_LOCAL_ROOT/models/LTX-2.3-dev" \
  --text-encoder-repo "$LTX_VIDEO_LOCAL_ROOT/models/gemma-3-12b-it-4bit" \
  --image /absolute/path/shot-01.png \
  --image-strength 1.0 \
  --prompt "Locked camera. Only a few hair tips move gently in a light breeze. Preserve the exact face, pose, composition, colors and lighting." \
  --negative-prompt "camera movement, zoom, pan, orbit, cut, text, new person, new object, face change, anatomy change, flicker, morphing, dramatic motion" \
  --width 576 \
  --height 768 \
  --num-frames 97 \
  --fps 24 \
  --cfg-scale 3.0 \
  --cfg-rescale 0.7 \
  --apg \
  --stg-blocks 28 \
  --tiling auto \
  --seed 42 \
  --output-path /absolute/path/shot-01-ltx.mp4
```

生成成功后再统一规格化到项目的 1080×1440、30fps 成片规格。

## 启用前验收

1. 两个模型目录都有 `model.safetensors.index.json`，所有索引中的分片实际存在。
2. 用一张不含文字的人物侧脸或风景分镜生成 97 帧测试视频。
3. 检查脸、手、身体、背景物体和构图没有漂移。
4. 检查首尾帧没有跳变、闪烁或突然缩放。
5. 失败镜头必须自动或人工回退 FFmpeg，不能阻断整条视频。

## 不进入 Git 的内容

- `models/` 下的所有权重。
- `*.safetensors`、`*.gguf`、`*.ckpt`、`*.pth`、`*.pt`。
- Hugging Face 缓存、虚拟环境、下载日志和临时生成视频。
- Hugging Face Token、火山引擎密钥及任何其他凭证。
