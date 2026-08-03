# 独立分镜并行生图路由

## 路由优先级

| 模式 | 提供方 | 工具 | 使用条件 |
|---|---|---|---|
| **默认** | `codex_imagegen` | Codex App 内置 `image_gen` | 无额外按量密钥，默认使用 |
| 可选 | `grok_local` | `grok-local/grok_generate_image` | 用户明确切换或 Codex 不可用且已有会员 OAuth |
| 可选 | `apimart` | `scripts/generate_apimart_image.py` | 只有用户明确允许按量费用时使用 |

禁止静默切换提供方。可选提供方必须使用 `selection_mode: user_override` 或
`availability_fallback`，并写明 `override_reason`。任何密钥或 token 不写入项目、Skill
或日志。

## 默认生产策略

默认使用 `parallel_individual + parallel_all`。每个分镜直接生成一张最终独立图片，不生成
拼图、九宫格、联系表或分镜母版，也不做二次裁切。

1. 从已确认逐字稿、`script-lock-vNNN.json` 和脚本内预估时码划分连续心理阶段；不等待真实 `timing-vNNN.json`。
2. 一次性冻结全部正文分镜的 `script_segment_ids`、口播、预估配音区间、独立 prompt 和最终输出路径，并记录 `timing_basis: script_estimated`。
3. 为每个 `shot-NN.png` 创建一个独立生图请求；片头专用 `mask-source-vNNN.png` 也创建独立请求。
4. 把所有正文分镜请求和片头遮罩请求一次性提交。全部请求提交完成后才统一等待结果。
5. 禁止先生成 `visual-lock` 再生成其他图片，禁止在 `for` 循环里逐项 `await`，禁止等待一张完成后才提交下一张。
6. 支持并发调用时使用 `Promise.allSettled` 或等价机制；支持 batch API 时一次提交整个请求数组。
7. 每张图片返回时立即单张质检。正文图通过后马上触发对应原始图生视频，并记录完成、质检和视频启动时间；不得等待其他图片。
8. 全部主请求完成后，从首张通过质检的正文图路径登记 `visual_lock`。汇总所有失败图片，只允许再发起一个 `parallel_failed_only` 补图批次；不得重做已通过图片，也不得中止已经启动的图生视频。

只有提供方明确拒绝并发时才允许分成多个并发 wave；每个 wave 内仍要先全部提交再等待，
并在批次记录中写入限流证据。不得用“稳定”为理由主动退回串行。

## 独立图片规则

- 每个请求直接输出最终 `3:4` 分镜图片，首选 1536×2048，硬下限 1080×1440。
- 每张图都使用自己的完整 prompt，不允许在一张图片里安排多个分镜。
- 所有 prompt 共享相同的文字版 `style_lock`：人物年龄、禁长大衣的轻便服装范围、季节、清透成像、干净青绿与适度暖色、自然光、镜头语言和字幕安全区。
- `style_lock` 必须在发起并发批次前确定，并完整写入每个请求；不得通过“先生成第一张，再拿第一张做参考图”恢复串行依赖。
- 每张图只替换当前口播意群对应的空间、人物行为、侧脸神情、身体状态、视线方向、环境情绪功能、风景和单一运动线索；这些变量必须先从文案推导，不能随机选择。
- 片头专用图使用独立场景与构图，但和正文图片在同一个并发批次提交。

单张提示词骨架：

```text
3:4 竖幅，当代东方电影感，开阔自然空间，
空气清透、能见度高、细节锐利自然，方向明确但不过曝的自然光，
正常黑白层次、干净的中等对比，青绿清晰有层次、暖色适量，不灰、不脏、不泛白，
人物为中远景或远景的清晰侧脸，面向画面内侧，风景占画面主要面积，
[年轻女孩穿轻薄针织衫/衬衫/短外套/轻便上衣/简洁连衣裙之一，不穿长大衣、过膝风衣或厚重拖地外套]，
[从当前逐字稿意群推导的侧脸神情、身体状态、视线方向和行为]，
[从当前逐字稿意群推导的环境、空间距离、天气、光线，以及该环境承担的情绪功能]，
只保留一种可轻动态化的自然线索，[风/草/水面/窗光/衣角/远景剪影之一]，
顶部保留书名安全区，中下部保留字幕安全区，
不要多画面，不要拼图，不要分镜网格，不要文字、书名、Logo 或水印；
不要雾、霾、白纱感、奶油滤镜、灰白蒙层、低对比泛白、黑位抬高、过曝高光、大面积柔焦。
```

## 统一质检

每张并发请求返回后立即检查该独立图片；主批次结束后再做一次集合完整性检查：

- 人物存在且为清晰侧脸，不是背影、正脸近景或纯风景。
- 女孩没有穿长大衣、过膝风衣或厚重拖地外套。
- 中远景/远景风景占主要面积；女孩的神情、身体状态、视线和环境情绪功能都与对应口播意群一致。
- 空气通透、能见度高、对比干净且高光有细节；没有雾蒙、白蒙、灰白罩层、奶油滤镜或泛白过曝。
- 图片是单一完整画面，不含拼图、网格、相邻分镜或错误文字。
- 顶部书名区和中下字幕区可用。
- 实际输出至少 1080×1440。

每张通过质检的 `shot-NN.png` 立即作为视频模型的独立 `source_image`。先按预估时长生成 6/10 秒原始视频；真实配音完成后统一绑定实际时码和规格化最终片段。

## 并发批次记录

写入 `07-分镜/parallel-image-batch-vNNN.json`：

```json
{
  "id": "image-primary-v001",
  "strategy": "parallel_all",
  "wait_policy": "wait_after_all_submitted",
  "serial_wait_count": 0,
  "result_policy": "qc_and_trigger_video_per_image",
  "all_images_completed_at_utc": "2026-08-02T08:05:30Z",
  "requests": [
    {
      "id": "shot-01",
      "role": "body_shot",
      "provider": "codex_imagegen",
      "output": "08-正文画面/v001/shot-01.png",
      "status": "completed",
      "image_completed_at_utc": "2026-08-02T08:02:00Z",
      "qc_passed_at_utc": "2026-08-02T08:02:05Z",
      "video_started_at_utc": "2026-08-02T08:02:06Z"
    },
    {
      "id": "shot-02",
      "role": "body_shot",
      "provider": "codex_imagegen",
      "output": "08-正文画面/v001/shot-02.png",
      "status": "completed",
      "image_completed_at_utc": "2026-08-02T08:04:10Z",
      "qc_passed_at_utc": "2026-08-02T08:04:14Z",
      "video_started_at_utc": "2026-08-02T08:04:15Z"
    },
    {
      "id": "opening-mask",
      "role": "opening_mask",
      "provider": "codex_imagegen",
      "output": "08A-片头遮罩素材/v001/mask-source-v001.png",
      "status": "completed"
    }
  ],
  "retry_batch": {
    "id": "image-retry-v001",
    "mode": "parallel_failed_only",
    "wait_policy": "wait_after_all_submitted",
    "serial_wait_count": 0,
    "requests": []
  }
}
```

## 生图记录

写入 `07-分镜/image-generation-vNNN.json`：

```json
{
  "provider": "codex_imagegen",
  "selection_mode": "default",
  "override_reason": null,
  "generation_mode": "parallel_individual",
  "batch_strategy": "parallel_all",
  "batch_plan": "07-分镜/parallel-image-batch-v001.json",
  "timing_basis": "voice_actual_after_join",
  "pre_join_timing_basis": "script_estimated",
  "visual_lock": "08-正文画面/v001/shot-01.png",
  "style_lock": "统一人物设定、禁长大衣的轻便服装、清透成像、干净青绿与适度暖色、自然光、镜头语言和安全区",
  "outputs": [
    "08-正文画面/v001/shot-01.png",
    "08-正文画面/v001/shot-02.png"
  ],
  "shots": [
    {
      "id": "shot-01",
      "output": "08-正文画面/v001/shot-01.png",
      "source_type": "direct_generation",
      "batch_id": "image-primary-v001",
      "request_id": "shot-01",
      "script_segment_ids": ["viewer-expression-01"],
      "narration_text": "与这幅画面对应的完整口播意群。",
      "voice_start": 5.55,
      "voice_end": 15.6,
      "estimated_voice_start": 5.55,
      "estimated_voice_end": 15.6,
      "emotional_stage": "替观众表达",
      "character_emotion": "克制紧张，轻收下颌，视线避开远处人群",
      "environment_emotional_function": "开阔草地与远处人群形成距离，表现个人判断被群体压小",
      "emotion_environment_alignment_reason": "口播写在人群里逐渐失去自己的判断，所以女孩回避人群，环境用明显距离强化被裹挟感",
      "image_prompt": "完整独立分镜 prompt",
      "composition": {
        "human_required": true,
        "face_orientation": "side_profile",
        "shot_size": "medium_long",
        "character_gender": "young_woman",
        "wardrobe": "light_knit",
        "long_coat": false,
        "landscape_required": true,
        "landscape_elements": ["草地", "远山"],
        "clarity": "clear_transparent",
        "atmospheric_haze": "none",
        "white_veil": false,
        "contrast": "clean_mid_contrast",
        "highlights_controlled": true,
        "text_free": true,
        "subtitle_safe_area": true
      }
    }
  ]
}
```

`character_emotion`、`environment_emotional_function` 和 `emotion_environment_alignment_reason`
必须是针对当前 `narration_text` 的具体描述，不得填写“忧郁”“治愈”“电影感”等通用词。
补图成功的镜头改写为 `source_type: retry_generation`，并记录 `retry_batch_id`；输出路径和
下游引用保持不变。
