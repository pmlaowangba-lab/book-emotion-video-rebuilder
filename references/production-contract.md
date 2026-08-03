# 项目与交付契约

## 目录

- 项目目录
- 清单状态
- 文案 JSON
- 时间轴 JSON
- 最终视频 → 可编辑剪映草稿
- 图片提示词
- 验收顺序

## 项目目录

```text
<书名>_YYYYMMDD_情绪读书视频/
├─ manifest.json
├─ 01-书籍资料/
├─ 02-情绪提炼/
├─ 03-逐字稿/
├─ 04-声音设计/
├─ 05-配音/
├─ 06-配乐音效/
├─ 07-分镜/
├─ 08-正文画面/
├─ 08A-片头遮罩素材/
├─ 09-Grok视频/
├─ 10-片头字幕/
├─ 11-时间轴/
├─ 12-预览/
└─ 13-剪映草稿/
```

版本使用 `v001`、`v002`。已锁定的文件不覆盖。

当前 `manifest.json` 使用 `schema_version: 8`。版本 8 保留 6 个内部状态节点，但默认只停在 3 个用户审核点：内容包、声音与视觉联合包、高清成片与剪映草稿双交付包。时间轴、高清成片和剪映草稿连续生成，中间不请求确认。

```json
{
  "defaults": {
    "voice": {
      "provider": "volcengine",
      "speaker": "S_Bkoh3uBT1",
      "selection_mode": "default",
      "speed_mode": "reference_locked",
      "reference_video_id": "7668678283642779072",
      "provider_speech_rate": 10,
      "target_chars_per_second": 4.56,
      "tolerance_chars_per_second": 0.02
    },
    "image_generation": {
      "provider": "codex_imagegen",
      "selection_mode": "default",
      "override_reason": null,
      "fallback_provider": "grok_local",
      "allowed_providers": ["codex_imagegen", "grok_local", "apimart"],
      "generation_mode": "parallel_individual",
      "batch_strategy": "parallel_all",
      "wait_policy": "wait_after_all_submitted",
      "preferred_image_size": [1536, 2048],
      "minimum_image_size": [1080, 1440],
      "retry_mode": "parallel_failed_only",
      "max_retry_batches": 1,
      "serial_waits_allowed": 0
    },
    "video_generation": {
      "provider": "grok_cli",
      "bridge": "grok-local",
      "model": "grok-imagine-video-via-cli",
      "mode": "reference_to_video",
      "auth_mode": "membership_oauth_only",
      "motion_profile": "restrained_micro_motion",
      "selection_mode": "default"
    },
    "typography": {
      "chinese_font_id": "yrdzst-heavy",
      "chinese_font_asset": "assets/fonts/杨任东竹石体-Heavy.ttf",
      "english_font_family": "Georgia"
    },
    "content": {
      "contract_version": 3,
      "entry_mode": "direct_theme",
      "max_script_seconds": 60,
      "preferred_han_count": [245, 268],
      "target_han_count": 256,
      "max_han_count": 270,
      "segment_han_targets": {
        "hook": 14,
        "book_lead": 12,
        "viewer_expression": 46,
        "pressure_escalation": 54,
        "cognitive_reversal": 62,
        "action_permission": 36,
        "identity_close": 32
      },
      "duration_override": null,
      "mask_keyword_han_count": 2,
      "mask_preview_required": true,
      "mask_approval_stage": "content_package",
      "book_lead_template": "今天分享的是，《{title}》。",
      "book_title_delivery": {
        "lead_text": "今天分享的是",
        "pre_title_pause_seconds": [0.45, 0.65],
        "pre_title_target_seconds": 0.55,
        "post_title_pause_seconds": [0.45, 0.70],
        "post_title_target_seconds": 0.60,
        "title_emphasis": "firm_low_falling",
        "timing_evidence_required": true,
        "fallback": "pause_only_postprocess"
      },
      "forbidden_confirmation_openings": [
        "你是不是也这样",
        "你有没有发现",
        "你是否也",
        "有没有过这种时候",
        "你是不是经常"
      ]
    },
    "music": {
      "selection_mode": "user_provided_library_only",
      "library_manifest": "assets/bgm-library/library.json",
      "required_source_scope": "user_provided_local_file"
    },
    "parallel_pipeline": {
      "mode": "event_driven_dag_after_content_lock",
      "content_lock_required": true,
      "scheduler": "dependency_ready_queue",
      "resource_groups": ["voice", "body_visual", "opening", "subtitle_music"],
      "dispatch_policy": "dispatch_when_dependencies_completed",
      "progression_policy": "advance_each_asset_immediately",
      "image_to_video_trigger": "per_image_qc_pass",
      "pre_join_timing_basis": "script_estimated",
      "final_timing_basis": "voice_actual",
      "join_policy": "final_assembly_waits_only_for_declared_dependencies",
      "failure_scope": "descendants_only",
      "max_ready_queue_delay_seconds": 30,
      "progress_reporting": {
        "mode": "event_driven_realtime",
        "refresh_on_every_transition": true,
        "heartbeat_seconds": 60,
        "json_output": "07-分镜/progress-state-v001.json",
        "markdown_output": "07-分镜/progress-v001.md"
      },
      "paired_review_steps": ["sound_package", "visual_package"]
    },
    "delivery": {
      "profile": "1080p_3x4_editable",
      "video_master": {
        "width": 1080,
        "height": 1440,
        "fps": 30,
        "video_codec": "h264",
        "pixel_format": "yuv420p",
        "audio_codec": "aac",
        "audio_sample_rate": 48000,
        "audio_channels": 2
      },
      "jianying_draft": {
        "required": true,
        "same_timeline_required": true,
        "editable_tracks_required": true,
        "flattened_mp4_only": false
      }
    }
  },
  "steps": {
    "content_package": {"status": "pending", "version": null, "artifacts": []},
    "sound_package": {"status": "pending", "version": null, "artifacts": []},
    "visual_package": {"status": "pending", "version": null, "artifacts": []},
    "timeline_package": {"status": "pending", "version": null, "artifacts": []},
    "final_video": {"status": "pending", "version": null, "artifacts": []},
    "jianying_draft": {"status": "pending", "version": null, "artifacts": []}
  }
}
```

关卡与素材目录的映射：

- `content_package`：01–03，书籍核验、情绪、逐字稿、两字毛笔遮罩候选和静态确认图。
- `sound_package`：04–06，试听、全文配音、BGM、音效和混音。
- `visual_package`：07–10 中的片头素材，分镜、选定提供方生成的图片、Grok/回退片段和片头。
- `timeline_package`：10–12 中的字幕、时间轴和最终视频 MP4；校验通过后直接进入剪映草稿生成，不单独停下。
- `final_video`：12 中的 1080×1440 H.264/AAC 高清主成片。
- `jianying_draft`：13 中的真实可编辑剪映草稿；基于同一份已校验时间轴连续执行，与高清主成片合并交付。

内容包确认后进入一个连续的事件驱动生产阶段。必须先生成 `03-逐字稿/script-lock-vNNN.json`，再按 [事件驱动并行生产规格](parallel-pipeline-spec.md) 维护依赖图与就绪队列；任何素材满足依赖后立即推动对应镜头。两包都完成后一起进入 `awaiting_confirmation`，只做一次联合审核。

并行生产还必须落盘：

- `07-分镜/parallel-pipeline-vNNN.json`：任务依赖、逐任务起止时间、状态和最终装配点。
- `07-分镜/timing-bind-vNNN.json`：真实配音时码与每个分镜的最终绑定。
- `07-分镜/progress-state-vNNN.json`：供页面和自动化实时读取的原子快照。
- `07-分镜/progress-vNNN.md`：供用户直接查看的实时进度面板。

时长结构保持：

```json
{
  "duration": {
    "mode": "adaptive",
    "requested": null,
    "observed_reference_range_seconds": [42, 66],
    "estimated": null,
    "locked": null
  }
}
```

`observed_reference_range_seconds` 只记录本地样本的观察结果，不参与生成限制。新写或重写稿的完整口播推荐 245–268 个汉字，默认目标 256 字，硬上限 270 字；按固定 4.56 字/秒和 0.2–0.5 秒尾音计算，成片必须小于 60 秒。内容包把完整文案的估算时长写入 `estimated`，声音包把连续配音实测时长写入 `locked`。用户要求更短的固定时长时使用 `mode: fixed` 和 `requested`；不接受超过 60 秒的新建项目。

`content_package` 只有在 01/02/03 三个目录的必需文件、两字毛笔 alpha mask、遮罩确认图和遮罩记录全部生成并验收后才能标记 `awaiting_confirmation`。第一阶段交付必须在回复中直接展示遮罩确认图并写明“遮罩文字：XX（2 字）”。用户确认内容包时把遮罩记录改为 `confirmed`；内容包确认后并行执行声音和视觉，后续只能复用已确认字形。任一分支先完成都不得停下等待确认。两者产物齐全、完成真实时码汇合并通过自检后，同时标记 `awaiting_confirmation`。时间轴与剪映草稿仍按上游确认关系执行。

旧的 schema 7 项目进入本 Skill 时，按以下映射合并状态，不删除旧素材：

- `content_package` → `content_package`
- `sound_design` + `voice` + `music_sfx` → `sound_package`
- `storyboard` + `grok_video` + `opening` → `visual_package`
- `subtitles` + `timeline` + 旧 `final_video` → `timeline_package`
- `jianying_draft` → `jianying_draft`

使用脚本迁移：

```bash
python3 <skill_root>/scripts/migrate_manifest_v8.py --project <project_dir>
```

旧步骤全部为 `locked` 的合并关卡转为 `confirmed`；全部为 `pending` 时保持 `pending`；已做一部分的关卡转为 `working`。

迁移会为项目设置 Codex App 默认生图路由、四分支并行生产策略、逐图触发视频、Grok 图生轻动态视频和杨任东竹石体配置。旧项目迁移后默认回到 `codex_imagegen`；需要其他渠道时再显式覆盖。

## 清单状态

`manifest.json` 里每个关卡只能使用：

- `pending`：未执行。
- `working`：正在执行。
- `awaiting_confirmation`：产物已生成并通过自检，正在等用户确认。
- `confirmed`：用户已确认，下游可使用。
- `blocked`：缺少来源、工具、授权或上游文件。
- `stale`：上游已产生新版本，本步需重做。

## 文案 JSON

`03-逐字稿/script-vNNN.json` 最少包含：

```json
{
  "title": "书名",
  "script_structure": "moyan_emotional_v1",
  "entry_mode": "direct_theme",
  "reference_thread_id": "019fb90e-e259-7fa0-b0b5-1ce0c8179a03",
  "quote_mode": "interpretation",
  "duration_mode": "adaptive",
  "target_chars_per_second": 4.56,
  "duration_estimate": 56.14,
  "ending_tail_seconds": 0.3,
  "video_duration_estimate": 56.44,
  "hook": "情绪钩子",
  "book_lead": "今天分享的是，《书名》。",
  "book_lead_delivery": {
    "lead_text": "今天分享的是",
    "title_text": "书名",
    "tts_text": "今天分享的是，\n书名。\n",
    "pre_title_pause_seconds": [0.45, 0.65],
    "pre_title_target_seconds": 0.55,
    "post_title_pause_seconds": [0.45, 0.70],
    "post_title_target_seconds": 0.60,
    "title_emphasis": "firm_low_falling",
    "fallback": "pause_only_postprocess"
  },
  "segments": [
    {
      "id": "s01",
      "role": "viewer_expression",
      "text": "正文意群",
      "start": 5.55,
      "end": 12.4
    }
  ],
  "timing_plan": [
    {"role": "hook", "han_count": 14, "duration_estimate": 3.07, "start_estimate": 0.0, "end_estimate": 3.07},
    {"role": "book_lead", "han_count": 12, "duration_estimate": 2.63, "start_estimate": 3.07, "end_estimate": 5.70},
    {"role": "viewer_expression", "han_count": 46, "duration_estimate": 10.09, "start_estimate": 5.70, "end_estimate": 15.79},
    {"role": "pressure_escalation", "han_count": 54, "duration_estimate": 11.84, "start_estimate": 15.79, "end_estimate": 27.63},
    {"role": "cognitive_reversal", "han_count": 62, "duration_estimate": 13.60, "start_estimate": 27.63, "end_estimate": 41.23},
    {"role": "action_permission", "han_count": 36, "duration_estimate": 7.89, "start_estimate": 41.23, "end_estimate": 49.12},
    {"role": "identity_close", "han_count": 32, "duration_estimate": 7.02, "start_estimate": 49.12, "end_estimate": 56.14}
  ],
  "source_refs": ["01-书籍资料/sources-v001.md"]
}
```

`quote_mode` 只能是：

- `verified_quote`：有可核验原文和位置。
- `interpretation`：基于书中观点的原创解读。

`adaptive` 模式使用 `duration_estimate`，不写 `duration_target`；`fixed` 模式才使用用户要求的更短 `duration_target`。新写或重写稿必须使用 `entry_mode: direct_theme`，书名锚点必须精确写成“今天分享的是，《核验书名》。”，并提供上述 `book_lead_delivery`。书名后的第一句直接陈述主题，禁止确认式提问。`segments.role` 至少覆盖 `viewer_expression`、`pressure_escalation`、`cognitive_reversal`、`action_permission` 和 `identity_close`。`timing_plan` 必须按口播顺序包含七个角色，每段的字数、时长和累计起止点都由 4.56 字/秒计算。作者信息只保留在 `01-书籍资料/book-vNNN.json`，不写入口播字段。

## 第一阶段遮罩记录

`02-情绪提炼/mask-keyword-vNNN.json` 最少包含：

```json
{
  "schema_version": 1,
  "version": "v001",
  "approval_stage": "content_package",
  "keyword": "清醒",
  "han_count": 2,
  "hook": "愿你看完这段，重新找回自己的判断。",
  "alpha_mask": "02-情绪提炼/keyword-brush-mask-v001.png",
  "preview": "02-情绪提炼/mask-preview-v001.png",
  "preview_type": "actual_alpha_mask_confirmation",
  "review_status": "awaiting_confirmation",
  "downstream_policy": "reuse_exact_approved_mask"
}
```

`keyword` 必须匹配 `[\u3400-\u9fff]{2}`，`han_count` 固定为 2。`alpha_mask` 和 `preview` 必须是 1080×1440 PNG 并位于 `02-情绪提炼/`；确认图必须真实使用该 alpha mask 展示片头字形，不能只显示候选文字列表。用户确认内容包时把 `review_status` 改为 `confirmed`。后期 `opening.keyword` 必须与它一致，`10-片头字幕/keyword-mask-vNNN.png` 必须与 `alpha_mask` 逐像素一致。

## 声音方案 JSON

`04-声音设计/sound-blueprint-vNNN.json` 最少包含：

```json
{
  "emotion_preset": "清醒型",
  "primary_reference": "moyan-01-jiexian",
  "opening_reference": "shier-05-pingbili",
  "opening_template": "masked_book_carousel",
  "voice": {
    "provider": "volcengine",
    "speaker": "S_Bkoh3uBT1",
    "selection_mode": "default",
    "override_reason": null,
    "speed_mode": "reference_locked",
    "reference_video_id": "7668678283642779072",
    "provider_speech_rate": 10,
    "target_chars_per_second": 4.56,
    "tolerance_chars_per_second": 0.02,
    "normalization": "ffmpeg_atempo_pitch_preserving",
    "generation_mode": "continuous",
    "book_title_delivery": {
      "lead_text": "今天分享的是",
      "pre_title_pause_seconds": [0.45, 0.65],
      "pre_title_target_seconds": 0.55,
      "post_title_pause_seconds": [0.45, 0.70],
      "post_title_target_seconds": 0.60,
      "title_emphasis": "firm_low_falling",
      "fallback": "pause_only_postprocess"
    }
  },
  "music": {
    "library_track_id": "user-track-id",
    "source_scope": "user_provided_local_file",
    "selection_mode": "ai_selected_from_user_library",
    "family": "felt-piano-low-drone",
    "lyrics": false,
    "strong_beat": false
  },
  "stages": [
    {"id": "hook", "start": 0.0, "end": 1.35, "voice_intent": "低声情绪认证", "music_action": "底床立即进入"},
    {"id": "mask_expand", "start": 1.35, "end": 2.9, "voice_intent": "完成钩子并开始今天分享的是", "music_action": "增加轻空气纹理"},
    {"id": "carousel", "start": 2.9, "end": 4.1, "voice_intent": "说完今天分享的是并保留书名前停顿", "music_action": "连续轻脉冲，无逐卡音效"},
    {"id": "book_lock", "start": 4.1, "end": 5.55, "voice_intent": "低位结实下收地单独念书名，念完保留正文前停顿", "music_action": "短暂收窄后恢复"}
  ]
}
```

`04-声音设计/voice-selection-vNNN.json` 最少包含：

```json
{
  "emotion_preset": "清醒型",
  "selection_mode": "default",
  "selected_speaker": "S_Bkoh3uBT1",
  "override_reason": null,
  "selected_speech_rate": 10,
  "target_chars_per_second": 4.56,
  "selection_reason": "使用默认读书音色和固定语速，从同速生成中选出最稳定的表演",
  "candidates": [
    {
      "speaker": "S_Bkoh3uBT1",
      "speech_rate": 10,
      "variant": "stable-take-a",
      "scores": {"emotion": 35, "credibility": 23, "clarity": 18, "fatigue": 9, "music_fit": 9},
      "total": 94
    },
    {
      "speaker": "S_Bkoh3uBT1",
      "speech_rate": 10,
      "variant": "stable-take-b",
      "scores": {"emotion": 29, "credibility": 22, "clarity": 19, "fatigue": 8, "music_fit": 8},
      "total": 86
    }
  ]
}
```

`selected_speaker` 必须来自候选列表，且与 `sound-blueprint-vNNN.json` 中最终使用的 `voice.speaker` 一致。`selection_mode=default` 时必须使用 `S_Bkoh3uBT1`。只有 `user_override` 或 `availability_fallback` 可以改用其他 speaker，且 `override_reason` 不得为空。所有候选的 `speech_rate` 必须都是 10，最终口播的 `target_chars_per_second` 必须是 4.56，不得用语速作为候选变量。

`05-配音/timing-vNNN.json` 还必须写入 `speed_mode: reference_locked`、`reference_video_id: 7668678283642779072`、`provider_speech_rate: 10`、`target_chars_per_second: 4.56`、`chars_per_second`、`first_word_start_seconds`、`last_word_end_seconds` 和 `ending_tail_seconds`。`chars_per_second` 只允许 4.54–4.58 的技术取整容差。

新项目还必须写入可复核的书名节奏证据：

```json
{
  "book_title_delivery": {
    "lead_text": "今天分享的是",
    "title_text": "书名",
    "lead_end_seconds": 3.55,
    "title_start_seconds": 4.07,
    "pre_title_pause_seconds": 0.52,
    "title_end_seconds": 4.93,
    "body_start_seconds": 5.51,
    "post_title_pause_seconds": 0.58,
    "title_emphasis": "firm_low_falling",
    "evidence_source": "word_timestamps_and_waveform",
    "pause_postprocess_applied": false
  }
}
```

`pre_title_pause_seconds` 必须等于 `title_start_seconds - lead_end_seconds`，并处于 0.45–0.65 秒；`post_title_pause_seconds` 必须等于 `body_start_seconds - title_end_seconds`，并处于 0.45–0.70 秒。`body_start_seconds` 必须与真实第一正文段起点一致。模型停顿不足时只允许补足静音并平移后续时码，记录 `pause_postprocess_applied: true`；不得拆开重录书名或改变全篇语速。

## 生图记录 JSON

`07-分镜/image-generation-vNNN.json` 最少包含：

```json
{
  "provider": "codex_imagegen",
  "selection_mode": "default",
  "override_reason": null,
  "generation_mode": "parallel_individual",
  "batch_strategy": "parallel_all",
  "batch_plan": "07-分镜/parallel-image-batch-v001.json",
  "pre_join_timing_basis": "script_estimated",
  "timing_basis": "voice_actual_after_join",
  "visual_lock": "08-正文画面/v001/shot-01.png",
  "style_lock": "统一人物设定、禁长大衣的轻便服装、清透成像、干净青绿与适度暖色、自然光、镜头语言和安全区",
  "outputs": [
    "08-正文画面/v001/shot-01.png"
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
      "voice_end": 13.40,
      "estimated_voice_start": 5.55,
      "estimated_voice_end": 13.40,
      "emotional_stage": "替观众表达",
      "character_emotion": "克制紧张，轻收下颌，视线避开远处人群",
      "environment_emotional_function": "开阔草地与远处人群形成距离，表现个人判断被群体压小",
      "emotion_environment_alignment_reason": "人物神情和空间距离均来自当前口播冲突",
      "image_prompt": "3:4 竖幅，空气清透，人物清晰侧脸与明亮风景，女孩不穿长大衣……",
      "composition": {"human_required": true, "face_orientation": "side_profile", "shot_size": "medium_long", "character_gender": "young_woman", "wardrobe": "light_knit", "long_coat": false, "landscape_required": true, "landscape_elements": ["草地", "远山"], "clarity": "clear_transparent", "atmospheric_haze": "none", "white_veil": false, "contrast": "clean_mid_contrast", "highlights_controlled": true, "text_free": true, "subtitle_safe_area": true}
    }
  ]
}
```

`provider` 必须与 `manifest.defaults.image_generation.provider` 一致；默认是 `codex_imagegen`，只有显式覆盖才允许 `grok_local` 或 `apimart`。`generation_mode` 固定为 `parallel_individual`，`batch_strategy` 固定为 `parallel_all`，并引用真实存在的 `parallel-image-batch-vNNN.json`。主批次必须包含全部独立正文图片和独立片头遮罩图，`serial_wait_count` 必须为 0。`visual_lock` 直接引用首张通过质检的 `shot-NN.png`，不能是前置生成依赖。`outputs` 中的文件必须落在项目内且真实存在，`shots[].output` 与之逐项对应；主批次图片记录 `source_type: direct_generation`、`batch_id` 和 `request_id`，补图记录 `source_type: retry_generation` 和 `retry_batch_id`。每项都必须绑定连续逐字稿、实测配音区间、完整独立 prompt、具体人物情绪、环境情绪功能、文案对齐理由，以及“人物侧脸 + 轻便服装且无长大衣 + 中远景/远景风景 + 清透无雾无白蒙”构图验收字段。

生图记录本身必须登记到 `manifest.steps.visual_package.artifacts`，保证更换提供方后能追溯每张图的实际来源。

## 时间轴 JSON

`11-时间轴/timeline-vNNN.json` 最少包含：

```json
{
  "canvas": {"width": 1080, "height": 1440, "fps": 30},
  "deliveryProfile": "1080p_3x4_editable",
  "typography": {
    "chinese_font_id": "yrdzst-heavy",
    "chinese_font_asset": "assets/fonts/杨任东竹石体-Heavy.ttf",
    "title_px": 88,
    "author_px": 44,
    "zh_caption_px": 60,
    "english_font_family": "Georgia",
    "en_caption_px": 32
  },
  "delivery": "jianying_draft",
  "preview_renderer": "ffmpeg",
  "duration": 53.7,
  "duration_source": "manifest.duration.locked",
  "voice_timing_source": "05-配音/timing-v001.json",
  "opening": {
    "template": "masked_book_carousel",
    "target_flash_start": 0.0,
    "target_flash_end": 0.1,
    "hook_start": 0.1,
    "keyword": "清醒",
    "keyword_hold_end": 1.35,
    "mask_mode": "horizontal_band_expand",
    "same_source_video": true,
    "mask_source_role": "opening_mask_only",
    "body_asset_reuse": false,
    "content_independence_reviewed": true,
    "mask_source_image_asset": "08A-片头遮罩素材/v001/mask-source-v001.png",
    "mask_source_video_asset": "08A-片头遮罩素材/v001/mask-source-v001.mp4",
    "mask_source_plan_asset": "08A-片头遮罩素材/v001/opening-mask-plan-v001.json",
    "keyword_mask_style": "custom_reviewed",
    "keyword_mask_asset": "10-片头字幕/keyword-mask-v001.png",
    "masked_keyword_video_asset": "10-片头字幕/masked-keyword-expand-v001.mp4",
    "expand_start": 1.35,
    "expand_end": 2.9,
    "carousel_start": 2.9,
    "carousel_end": 4.1,
    "card_durations": [0.10, 0.13, 0.13, 0.13, 0.13, 0.13, 0.13, 0.13, 0.13],
    "carousel_motion": {"type": "snap_settle", "scale_start": 1.035, "scale_end": 1.0, "soft_focus_px": 1.5, "transition": "hard_cut"},
    "carousel_cards": [
      {"title": "老人与海", "role": "carousel", "asset": "10-片头字幕/carousel-v001/card-01-老人与海-v001.png"}
    ],
    "target_cover_hold_start": 4.1,
    "target_cover_hold_end": 4.85,
    "target_cover_base_asset": "10-片头字幕/v001/target-cover-base-v001.png",
    "target_cover_title_page_asset": "10-片头字幕/v001/target-cover-title-page-v001.png",
    "target_cover_title_binding": {"mode": "same_page_as_cover", "title_start": 4.1, "title_settle_end": 4.43, "title_above_cover": true, "cover_visible_during_title_motion": true, "visible_through_waterwave": true, "persist_to_body": true, "title_safe_area": {"top": 60, "bottom": 220}, "cover_safe_area": {"top": 240, "bottom": 1320}},
    "target_lock_start": 4.85,
    "target_lock_end": 5.55,
    "target_lock_mode": "cover_waterwave_then_title_drop",
    "target_hero_asset": "10-片头字幕/target-hero-v001.mp4",
    "title_motion": {"type": "cover_page_title_settle", "settle_frames": 10, "easing": "ease_out_cubic", "start_anchor": "cover_page_upper_center", "end_anchor": "cover_page_top"},
    "waterdrop_lock_response": {"type": "cover_waterwave_then_title_drop", "effect_on": "entire_page", "effect_style": "full_frame_displacement_map", "effect_scope": "entire_page", "effect_asset": "10-片头字幕/v001/waterwave-page-refraction-v001.mp4", "source_page_asset": "10-片头字幕/v001/target-cover-title-page-v001.png", "includes_title_layer": true, "visual_start": 4.45, "wave_trigger_at": 4.45, "sfx_at": 4.45, "visual_end": 4.85, "hero_cut_at": 4.85, "literal_water_graphic": false, "overlay_graphic": false, "visible_ring": false, "page_deformation": true, "refraction": true, "perceptible_motion": true, "title_keyframes": [{"frame": 0, "scale": 1.50, "opacity": 0.35, "blur_px": 2.5, "y_px": 150, "transform_y": -0.60}, {"frame": 1, "scale": 1.42, "opacity": 0.55, "blur_px": 2.2, "y_px": 139, "transform_y": -0.63}, {"frame": 2, "scale": 1.34, "opacity": 1.0, "blur_px": 1.8, "y_px": 127, "transform_y": -0.66}, {"frame": 5, "scale": 1.18, "opacity": 1.0, "blur_px": 0.0, "y_px": 99, "transform_y": -0.72}, {"frame": 8, "scale": 1.05, "opacity": 1.0, "blur_px": 0.0, "y_px": 78, "transform_y": -0.77}, {"frame": 10, "scale": 1.0, "opacity": 1.0, "blur_px": 0.0, "y_px": 70, "transform_y": -0.79}]},
    "book_title_delivery": {"lead_text": "今天分享的是", "title_text": "书名", "pre_title_pause_seconds": 0.52, "post_title_pause_seconds": 0.58, "title_emphasis": "firm_low_falling", "timing_source": "05-配音/timing-v001.json"},
    "body_voice_start": 5.55
  },
  "openingTrack": [
    {"id": "target-flash", "start": 0.0, "end": 0.1, "asset": "10-片头字幕/target-hero-v001.mp4", "transition_out": "hard_cut", "motion": {"type": "static", "scale_start": 1.0, "scale_end": 1.0, "pan_x": 0, "pan_y": 0}},
    {"id": "masked-keyword", "start": 0.1, "end": 2.9, "asset": "10-片头字幕/masked-keyword-expand-v001.mp4", "transition_out": "hard_cut", "motion": {"type": "static", "scale_start": 1.0, "scale_end": 1.0, "pan_x": 0, "pan_y": 0}},
    {"id": "carousel-01", "start": 2.9, "end": 3.13, "asset": "10-片头字幕/carousel-v001/card-01-老人与海-v001.png", "transition_out": "hard_cut", "motion": {"type": "snap_settle", "scale_start": 1.035, "scale_end": 1.0, "soft_focus_px": 1.5, "pan_x": 0, "pan_y": 0}},
    {"id": "target-cover-hold", "start": 4.1, "end": 4.85, "asset": "10-片头字幕/v001/target-cover-base-v001.png", "transition_in": "hard_cut", "transition_out": "hard_cut", "motion": {"type": "snap_settle", "scale_start": 1.02, "scale_end": 1.0}},
    {"id": "target-cover-waterwave-page", "start": 4.45, "end": 4.85, "wave_trigger_at": 4.45, "asset": "10-片头字幕/v001/waterwave-page-refraction-v001.mp4", "source_page_asset": "10-片头字幕/v001/target-cover-title-page-v001.png", "includes_title_layer": true, "layer": "page_effect", "effect_on": "entire_page", "motion": {"type": "full_frame_displacement_map", "page_deformation": true, "overlay_graphic": false, "visible_ring": false}},
    {"id": "target-lock", "start": 4.85, "end": 5.55, "asset": "10-片头字幕/target-hero-v001.mp4", "transition_in": "hard_cut", "transition_out": "crossfade", "motion": {"type": "grok_video", "scale_start": 1.0, "scale_end": 1.0, "pan_x": 0, "pan_y": 0}, "title_motion": {"type": "cover_page_title_settle", "settle_frames": 10, "easing": "ease_out_cubic", "start_anchor": "cover_page_upper_center", "end_anchor": "cover_page_top"}}
  ],
  "sceneTrack": [
    {"id": "scene-01", "start": 5.55, "end": 14.2, "voice_start": 5.55, "voice_end": 13.90, "script_segment_ids": ["viewer-expression-01"], "narration_text": "与第一张图对应的完整口播意群。", "asset": "09-Grok视频/v001/shot-01-final.mp4", "source_still": "08-正文画面/v001/shot-01.png", "emotional_stage": "具体处境", "visual_change_reason": "initial_state", "motion": {"type": "grok_video", "scale_start": 1.0, "scale_end": 1.0, "pan_x": 0, "pan_y": 0}},
    {"id": "scene-02", "start": 13.8, "end": 22.6, "voice_start": 13.90, "voice_end": 22.60, "script_segment_ids": ["pressure-escalation-01"], "narration_text": "与第二张图对应的完整口播意群。", "asset": "08-正文画面/v001/shot-02.png", "source_still": "08-正文画面/v001/shot-02.png", "emotional_stage": "外部压力", "visual_change_reason": "subject_relation_change", "motion": {"type": "zoom_out", "scale_start": 1.12, "scale_end": 1.0, "pan_x_ratio": 0.0, "pan_y_ratio": 0.0, "interpolation": "cubic_ease_in_out", "sample_per_frame": true, "container": {"coverage": "full_canvas", "overflow": "hidden", "fit": "cover", "transform_target": "inner_image"}}}
  ],
  "captionTrack": [
    {"id": "cap-01", "start": 5.55, "reveal_end": 5.55, "display_mode": "segment", "end": 7.8, "zh": "中文字幕", "en": "English subtitle"}
  ],
  "audioTrack": [
    {"id": "voice-01", "type": "voice", "start": 0.0, "end": 53.7, "asset": "05-配音/voice-v001.wav", "volume": 1.0},
    {"id": "bgm-01", "type": "bgm", "start": 0.0, "end": 53.7, "asset": "06-配乐音效/bgm-v001.wav", "volume": 0.22, "fade_in": 0.2, "fade_out": 0.4}
  ],
  "bookMeta": {"start": 4.1, "end": 53.7, "title": "《书名》", "author": "作者"},
  "accentTrack": [],
  "transitionTrack": [
    {"from": "scene-01", "to": "scene-02", "start": 13.8, "end": 14.0, "duration": 0.2, "type": "short_fade", "reason": "emotional_continuity"}
  ]
}
```

最终 MP4 和过程预览必须实际使用 `assets/fonts/杨任东竹石体-Heavy.ttf` 渲染中文。生成剪映草稿时，把同一字体复制到 `Resources/local_fonts/`，并在草稿报告记录 `font_binding: requires_jianying_local_font_activation`；当前草稿库不支持任意 TTF 自动绑定，不得伪报已完成剪映字体激活。

`opening.template` 只能使用 `masked_book_carousel`。`opening.keyword` 必须与内容包已确认的两字关键词完全一致；审核过的毛笔蒙版要从 `02-情绪提炼/` 复用，后期不得重新选词或重画。遮罩专用源图和源视频必须位于 `08A-片头遮罩素材/`，同源展开片段作为独立素材落盘。遮罩图片与视频不得复用正文路径，也不得与正文文件 SHA-256 相同。`carousel_cards` 必须完整写入 9 项，本示例只展示第一项。`openingTrack` 保留可编辑片头素材，`sceneTrack` 保留动态片段和回退静态图，`captionTrack` 拆成中英文轨，`audioTrack` 拆成配音、BGM 和音效轨。每个 `sceneTrack` 项必须包含 `emotional_stage`、`visual_change_reason`、逐字稿段 ID、口播和实测配音区间，并与同一 `source_still` 的生图记录一致；第一组使用 `initial_state`，后续使用规格中定义的真实换图理由。`duration`、配音轨终点、末场景口播终点和最终视频必须共同等于 `manifest.duration.locked`，误差不超过 0.05 秒。

`target_cover_title_binding.mode` 必须为 `same_page_as_cover`。书名起势、收稳和水波阶段都必须保留同页真实封面；水波源页必须是已含落位书名的 `target_cover_title_page_asset`。

直接上轴的静态正文图必须使用 `zoom_in`、`zoom_out`、`pan_left`、`pan_right` 或 `emotional_hold`，并记录全画布隐藏溢出容器。相邻静态镜头不得重复同一种运动，横移不得超过画宽 4%。强转折和记忆碎片使用具名硬切，情绪连续才使用 0.12–0.30 秒 `short_fade`；三个及以上正文转场不得全部使用同一类型。Grok 真动态片段使用 `grok_video`，不得再叠加确定性缩放。

## 时间轴与最终视频 → 可编辑剪映草稿

关卡 4 从同一份时间轴连续生成 `12-预览/final-video-vNNN.mp4`。主成片固定为 `1080p_3x4_editable`：1080×1440、3:4、30fps、H.264、`yuv420p`、AAC 48kHz 双声道，并通过时长、音轨、响度与真峰值校验。校验通过后不等待用户确认，立即进入关卡 5 创建剪映草稿。项目内 `13-剪映草稿/draft-vNNN.json` 记录真实草稿路径，实体草稿至少包含 `draft_content.json`、`draft_meta_info.json`、新版剪映入口文件、`book_emotion_draft_report.json` 和 `Resources/local_media/`。

最终视频与草稿必须来自同一份已校验时间轴。草稿必须保留片头遮罩源图、遮罩源视频、遮罩成片段、正文画面、中文字幕、英文字幕、书名、作者、配音、BGM 和音效独立轨道或本地媒体引用；不覆盖旧草稿，也不允许把最终 MP4 当成唯一素材导入草稿。草稿报告与项目指针都必须写入 `delivery_profile: 1080p_3x4_editable`、高清成片绝对路径、`same_timeline_as_video_master: true` 和 `flattened_final_mp4: false`。`final_video.artifacts` 记录最终 MP4，`jianying_draft.artifacts` 只记录草稿清单与真实路径。两者完成后一次性进入 `awaiting_confirmation`，只做一次最终双交付审核。

## 图片提示词

母提示词固定清透成像与服装边界；每张图只替换从口播推导出的女孩神情、身体状态、视线、空间和环境情绪功能：

```text
3:4 竖幅，当代东方电影感，开阔自然空间，
空气清透、能见度高、细节清晰，正常黑白层次与干净中等对比，
方向明确但不过曝的自然光，青绿清晰有层次、暖色适量，不灰、不脏、不泛白，
人物为中远景或远景的清晰侧脸，面向画面内侧，安静行走或停留，
女孩穿轻薄针织衫、衬衫、短外套、轻便上衣或简洁连衣裙，不穿长大衣或过膝风衣，
人物神情、身体状态、视线和环境必须从对应逐字稿意群推导，
风景占画面主要面积，场景必须从对应逐字稿意群推导，
有风、草、水面、动物或车辆中的一种自然运动线索，
主体与字幕区不重叠，顶部留出书名作者安全区，中下部留出字幕安全区，
不要文字，不要书名，不要 Logo，不要水印，不要恐怖、阴森、无脸密集人群、巨大嘴部或裂脸，
不要雾、霾、白纱感、奶油滤镜、灰白蒙层、低对比泛白、黑位抬高、过曝高光或大面积柔焦。
```

分镜变量示例：

```text
年轻女孩穿浅色针织衫，侧脸克制紧张，轻收下颌并避开远处人群，独自站在清透开阔的草地，
人群在另一侧缓慢移动，空间距离表达她在人群中逐渐失去判断；天空与草地层次清晰，风只轻动衣角，中下部保留干净字幕区。
```

## 验收顺序

1. 先看关卡 1 的遮罩确认图，确认关键词恰好两个汉字；再逐像素检查最终蒙版没有换词或换字形。随后逐帧看 0–6 秒片头，检查 3 帧预闪、毛笔字同源视频填充、横带展开、9 张真实书封卡 `snap_settle`、齿轮结束后的目标书封展示，以及 `cover_waterwave_then_title_drop`：书名必须在目标封面所在的同一页上方用 10–14 帧由大到小收稳，封面全程可见；水滴声与整页形变触发对齐，书名、封面文字、边缘和背景同时低幅位移，峰值后连续恢复，再切主画面并保持书名位置；不得出现可见水珠、下落轨迹、飞溅、椭圆/同心圆轮廓或高光环。
2. 关闭声音看一遍，检查字幕是否可独立读懂。
3. 闭眼听一遍，检查配音是否连续、“今天分享的是”与书名有没有 0.45–0.65 秒间隔、书名和正文有没有 0.45–0.70 秒间隔、书名是否低位结实下收、各声音环节是否按声音方案执行、音乐是否压人声。
4. 在手机尺寸下看一遍，检查顶部书名、中文和英文字幕。
5. 使用 `validate_package.py` 检查 JSON、情绪弧完整性、估算与锁定时长、画布、镜头和成片媒体参数。
