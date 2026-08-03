# LTX-2.3 本地动态规格

## 使用边界

本地 LTX 是正文静图的可选轻动态通道，不是必需依赖，也不是默认通道。只有本机已经完成模型下载、运行探针和单镜头视觉验收时才可设置 `provider: ltx_local`。下载未完成、推理失败或画面变形时立即使用 `ffmpeg_fallback`，不得阻塞整条视频。

不处理真实书封、书封轮播、书名页、毛笔遮罩、字幕图和任何含文字素材。

## 固定组合

| 项目 | 值 |
|---|---|
| 主模型 | `prince-canuma/LTX-2.3-dev` |
| 文本编码器 | `mlx-community/gemma-3-12b-it-4bit` |
| 推理器 | `Blaizzy/mlx-video` |
| 管线 | `dev-two-stage-hq` |
| 环境变量 | `LTX_VIDEO_LOCAL_ROOT` |
| 默认原始规格 | 576×768、97 帧、24fps、约 4 秒 |

权重约 61GB，模型目录必须在 Skill 仓库外。不要提交权重、Hugging Face 缓存、Token、虚拟环境或下载日志。

## 启用探针

`LTX_VIDEO_LOCAL_ROOT` 下必须同时存在：

```text
run_i2v_hq.sh
models/LTX-2.3-dev/transformer/model.safetensors.index.json
models/gemma-3-12b-it-4bit/model.safetensors.index.json
```

继续解析两个索引，确认索引引用的全部分片真实存在。只看到索引文件不能判定下载完成。

然后使用一张不含文字的人物侧脸风景图生成 97 帧测试视频。只有同时满足以下条件才写入 `probe_status: approved`：

- 成功输出可解码 MP4。
- 脸、手、身体、人数和背景物体没有变化。
- 没有新增物体、闪烁、融化、构图漂移和首尾跳变。
- 运动克制且能在手机尺寸感知。

探针记录模型路径、版本、测试素材、输出、耗时和验收结果，但不得记录 Token。

## 镜头规则

- 每个镜头只指定一种动作：发梢、树叶、水面、云影、窗光、衣角或远景剪影之一。
- 默认锁定相机，保持原脸、姿势、构图、颜色、光线和字幕安全区。
- 禁止推拉、摇移、环绕、切镜、嘴型、表情变化、人物转身和新增物体。
- 每张图最多收紧提示词重试一次；仍失败就回退 FFmpeg。
- 原始短片生成后按真实 `voice_start`、`voice_end` 规格化到 1080×1440、30fps；不得循环人物动作。

推荐负面提示词：

```text
camera movement, zoom, pan, orbit, cut, text, new person, new object,
face change, anatomy change, flicker, morphing, dramatic motion
```

## 项目记录

在 `manifest.defaults.video_generation` 和每个 `shot-NN-qc.json` 中写入：

```json
{
  "provider": "ltx_local",
  "model": "prince-canuma/LTX-2.3-dev",
  "text_encoder": "mlx-community/gemma-3-12b-it-4bit",
  "pipeline": "dev-two-stage-hq",
  "probe_status": "approved",
  "source_image": "08-正文画面/v001/shot-01.png",
  "status": "approved",
  "fallback": null
}
```

当前渲染器仍从兼容目录 `09-Grok视频/vNNN/shot-NN-final.mp4` 读取最终动态素材。LTX 输出可以复制到该路径，但 QC 的 `provider` 必须如实写成 `ltx_local`。后续若迁移为通用动态目录，再统一升级 schema，不在单个项目中临时改目录。

## 当前状态

线程 `019fc1d8-9763-7c40-b98c-60a563547e37` 在 2026-08-03 已完成 LTX 主模型 31/31 文件和 8/8 Transformer 分片下载；Gemma 文本编码器当时仍在后台下载，因此不能据此声明端到端可用。每台电脑都必须重新执行探针，不能继承另一台电脑的 `approved` 状态。
