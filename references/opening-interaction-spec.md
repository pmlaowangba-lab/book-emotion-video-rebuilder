# 片头交互规格

## 目录

- 唯一片头模板
- 逐帧状态
- 毛笔字视频遮罩
- 动态数量真实书封卡
- 目标书锁定
- 声画同步
- 时间轴字段
- 验收

## 唯一片头模板

所有新项目只使用 `masked_book_carousel`：

```text
3 帧目标书主画面预闪
→ 黑底情绪句 + 毛笔关键词视频填充
→ 横线向上下展开出同源视频
→ 按书名时码计算数量的标准化真实书封卡快速硬切
→ 目标书封与书名同页展示 + 书名在封面上方由大到小收稳 + 水滴声触发书名与封面整页水面形变 + 硬切目标主画面并保持书名位置
→ 正文
```

缺少遮罩或缺少书封轮播都是失败。不再提供 `portrait_carousel` 或 `keyword_expand` 二选一的入口。

## 逐帧状态

30fps 固定时间基准：

| 时间 | 状态 | 画面行为 | 文字行为 |
|---|---|---|---|
| 0.00–0.10s | `target_flash` | 显示目标书主画面 3 帧 | 顶部书名作者可见 |
| 0.10–1.35s | `hook_keyword` | 黑底；毛笔关键词内部播放同源桥段视频 | 底部按实测口播时码整段显示当前钩子字幕；中央蒙版仍只有两字 |
| 1.35–1.45s | `horizontal_cut` | 从关键词垂直中心出现横线并延长至全宽 | 情绪句和关键词保持 |
| 1.45–2.90s | `mask_expand` | 同一桥段视频从横带向上、向下展开至全屏 | 文字被展开画面逐步覆盖 |
| 2.90s–书名首字 | `book_carousel` | 按最终配音时码动态计算非目标真实书封数量；每张 3–4 帧内由 103%–104% 快速收稳至 100%，卡间硬切 | 卡片不叠加新文字 |
| 书名首字起 | `target_cover_hold` | 齿轮声结束并展示目标真实书封；封面始终可见；书名落位后触发书名、封面和背景一起做整帧水波位移 | 书名从封面页第 1 帧起位于同页安全区，10–14 帧内由大到小收稳 |
| 水波恢复后–正文首字 | `target_lock` | 继续保持目标真实书封，直到正文首字开始才切下一帧 | 书名保持与封面页落位时相同的顶部位置，不重新入场 |
| 正文首字起 | `body_enter` | 切入或短叠化到第一正文镜头 | 第一张正文字幕进入 |

允许因 TTS 稍微平移，但必须同时满足：

- `target_flash` 固定 0.10 秒。
- `horizontal_cut` 开始于 1.30–1.45 秒。
- `mask_expand` 在 2.80–3.00 秒之间完成。
- `carousel_start` 固定在 2.80–3.00 秒；`carousel_end` 不再固定为 4.10 秒，必须与书名首字实测时码同帧。
- 每张卡严格为 3 或 4 帧，数量由轮播总帧数反推；目标书封展示、水波和书名后停顿都服从真实配音时码。
- 正文只在 `book_title_delivery.body_start_seconds` 开始，不再用固定 5.55 秒强行约束。

## 毛笔字视频遮罩

关键词从这本书要给观众的核心情绪中提取，例如“清醒”“自救”“屏蔽”“遇见”“出走”。关键词必须且只能由两个汉字组成，不要把完整书名硬塞进大字，也不得使用 1 字、3–4 字、标点、数字、英文或空格。

关键词和实际毛笔 alpha mask 必须在关卡 1 内容包中生成并确认。内容包固定落盘 `02-情绪提炼/keyword-brush-mask-vNNN.png`、`mask-preview-vNNN.png` 和 `mask-keyword-vNNN.json`；用户必须能直接看到确认图。确认后把记录的 `review_status` 改为 `confirmed`，后续片头只能复用这张已确认蒙版，不能重新选词、换字体或重画字形。

必须分层实现，且片头遮罩素材与正文素材完全隔离：

1. `mask_source_video`：固定取自 `assets/opening-mask-video-library/manifest.json` 的 `seagulls-over-sea-close-v001`。画面必须同时看见海面和天空，且白色飞鸟贴近镜头向上飞。复制到 `08A-片头遮罩素材/vNNN/`后使用，项目内不引用 Skill 外路径。
2. `keyword_alpha_mask`：内容包已确认的两字毛笔 alpha 遮罩，字内填入 `mask_source_video`。
3. `horizontal_band_mask`：与关键词使用同一条 `mask_source_video` 和同一时间位置，从 2–4px 横线展开到全屏。
4. `hook_caption_track`：白色杨任东竹石体 Heavy 口播字幕，放在底部安全区，按实测钩子时码整段切换。它是独立字幕层，不并入中央两字 alpha mask。

新项目禁止创建 `mask_source_image`，也禁止用 Codex、APIMart、Grok CLI 或其他生图/图生视频工具替换这条固定素材。

生产顺序固定为：

```text
02-情绪提炼/keyword-brush-mask-vNNN.png（内容包确认）
→ 校验 assets/opening-mask-video-library/manifest.json 与默认视频 SHA-256
→ 复制为 08A-片头遮罩素材/vNNN/mask-source-vNNN.mp4
→ 08A-片头遮罩素材/vNNN/opening-mask-plan-vNNN.json
→ build_masked_keyword_opening.py
→ 10-片头字幕/masked-keyword-expand-vNNN.mp4
```

使用本地生成器把上述分层固定为独立素材：

```bash
python3 <skill_root>/scripts/build_masked_keyword_opening.py \
  --bridge-video <project_dir>/08A-片头遮罩素材/v001/mask-source-v001.mp4 \
  --keyword "<两个汉字>" \
  --hook "<第一行>\\n<第二行>" \
  --keyword-mask <project_dir>/02-情绪提炼/keyword-brush-mask-v001.png \
  --content-mask-record <project_dir>/02-情绪提炼/mask-keyword-v001.json \
  --output <project_dir>/10-片头字幕/masked-keyword-expand-v001.mp4 \
  --version v001
```

脚本同时产出 `keyword-mask-vNNN.png` 和 `masked-keyword-expand-vNNN.json`，便于后续复用、重做和质检。

`--keyword-mask` 使用内容包已确认的 1080×1440 黑底白字 PNG，白色区域是视频填充区。输出的 `keyword-mask-vNNN.png` 必须与内容包候选逐像素一致。新项目不得省略该参数；系统楷体只允许旧项目结构诊断，不得进入新项目预览或成片。元数据中的 `keyword_mask_style` 会标记当前来源。

禁止：

- 用静态纹理冒充字内视频。
- 为片头遮罩生成静态背景图，或将静图再做图生视频。
- 用透明度淡入冒充横向遮罩。
- 在展开中替换视频，造成字内纹理与全屏画面跳变。
- 直接把参考原片的飞鸟素材用于新成片。
- 把 `08-正文画面/` 中的任何图片当成 `mask_source_image`。
- 把 `09-Grok视频/` 中的任何片段当成 `mask_source_video`。
- 对正文图做复制、改名、裁切、镜像、补边或调色后冒充片头专用图。

## 动态数量真实书封卡

使用可追溯来源的真实书封清单。先按文案估算数量，再按真实配音时码完成最终重算：

```bash
python3 <skill_root>/scripts/plan_book_carousel.py \
  --script <project_dir>/03-逐字稿/script-v001.json \
  --cover-manifest <book_cover_manifest> \
  --target-title "<目标书名>" \
  --output <project_dir>/10-片头字幕/carousel-plan-estimated-v001.json \
  --version v001

python3 <skill_root>/scripts/plan_book_carousel.py \
  --timing <project_dir>/05-配音/timing-v001.json \
  --cover-manifest <book_cover_manifest> \
  --target-title "<目标书名>" \
  --output <project_dir>/10-片头字幕/carousel-plan-v001.json \
  --version v001

python3 <skill_root>/scripts/build_book_carousel_cards.py \
  --manifest <book_cover_manifest> \
  --plan <project_dir>/10-片头字幕/carousel-plan-v001.json \
  --project <project_dir> \
  --output-dir <project_dir>/10-片头字幕/carousel-v001 \
  --target-title "<目标书名>" \
  --version v001
```

计算规则：

- 配音前：`title_start_estimate = (hook_han + lead_text_han) / 4.56 + 0.55`。该结果只负责估算需要准备多少封面。
- 配音后：直接读取 `book_title_delivery.title_start_seconds`；`carousel_end = title_start_seconds`。
- `total_frames = carousel_end_frame - carousel_start_frame`；在每张 3–4 帧的约束下优先保持参考片接近 4 帧/张的节奏，再把不足 4 帧的余量均匀分配为 3 帧卡。
- 最终 `carousel-plan-vNNN.json` 必须写 `timing_source_type: voice_actual` 和 `needs_actual_timing_replan: false`。
- 真实非目标书封少于计算张数时直接阻断并扩充书库；禁止缩短轮播、提前上目标封面或把单卡拉到 5 帧以上。
- 生成对应数量的 1080×1440 PNG 和 `carousel-cards-vNNN.json`，记录书名、作者、源书封、卡片文件、逐卡帧数与时长。

卡片视觉语法：

- 背景使用同一书封铺满裁切、高斯模糊和轻度压暗。
- 中央放置清晰真实书封，保持原比例，增加白色柔光边和轻阴影。
- 不加电商价格、评分、销量、购买按钮、额外书名或作者层。
- 卡片内部固定使用 `snap_settle`：首帧 103%–104% 并带 1–2px 柔焦，随后在剩余 2–3 帧快速收稳到 100%。这不是长推拉，而是短促“显现—定帧”。
- 卡片之间全屏硬切，不滑动、不叠化、不弹跳，不为每张卡加 whoosh。禁止把动态数量的静态 PNG 无动效直拼。
- 目标书严格从快速卡序列中排除。

## 目标书锁定

目标锁定固定使用 `cover_waterwave_then_title_drop`，但书名动画必须发生在目标封面所在的同一页。必须同时看见真实封面、封面上方的书名收稳和整页水面形变，不能看见额外画上去的圆环。

先生成两张几何位置完全一致的锁书页：无书名基底页用于书名起势，已落位书名同页定帧用于整页水波。

```bash
python3 <skill_root>/scripts/build_target_cover_title_page.py \
  --cover <project_dir>/01-书籍资料/cover-v001.jpg \
  --title "<目标书名>" \
  --output-dir <project_dir>/10-片头字幕/v001 \
  --version v001
```

脚本输出 `target-cover-base-vNNN.png`、`target-cover-title-page-vNNN.png` 和对应 JSON。水波的输入必须是 `target-cover-title-page-vNNN.png`，不得回退使用无书名基底页。

- 齿轮声结束后，目标真实书封必须展示 0.65–0.85 秒，不能只闪 3 帧。书名必须与封面同时存在于这一页：书名占用顶部 60–220px 安全区，封面主体从约 240px 开始，两者不重叠。
- 书名从封面页第 1 帧起就在上方安全区出现，以 135%–155%、35%–55% 不透明度和 2–3px 柔焦起势；随后在 10–14 帧内用 ease-out 缩小到 100%并落在顶部安全区。这个过程中封面不得消失、被换成正文图或只留模糊背景。
- 书名落位后，水滴声主瞬态触发“书名＋封面＋背景”整页波浪位移，0.30–0.50 秒内连续起伏并恢复。水波结束后仍保持该书封页，直到书名末字和书名后停顿全部结束；只能在正文首字开始时切入目标动态主画面。
- 作者不与中央大书名同时抢画面；书名接近顶部后作者再淡入。书名与作者落位后保持到结尾，不随正文切镜重新入场。
- 锁定开始同步一次柔和水滴/水波尾韵音；目标书名朗读重音落在锁定开始后 0–0.20 秒。
- 目标书名念完后留 0.45–0.70 秒呼吸，正文严格在实测 `body_start_seconds` 进入；正文进入时书封展示页切换或短叠化到第一正文镜头，顶部书名作者保留。

### 水滴式书名锁定

2026-08-01 对 `modal_id=7668678283642779072` 的 30fps 原片重新逐帧测量：目标书封先独立出现。2026-08-02 用户针对《自控力》明确书名必须与封面同页；2026-08-03 又明确念到《活着》等目标书名时仍需展示真实封面，不能提前切下一帧。生产规则以最新明确反馈为准：水波恢复后保持书名封面页到 `body_voice_start`。

- 实现名保持为 `cover_waterwave_then_title_drop`，但必须声明 `target_cover_title_binding.mode: same_page_as_cover`。先生成无书名封面基底页和已落位书名封面同页定帧，再以后者生成整帧不透明 MP4 页面形变素材。
- 水滴音主瞬态与 `wave_trigger_at` 使用同一时间点，最大误差 1 帧；`visual_end` 必须晚于触发点 0.30–0.50 秒并与水波素材结束对齐。`cover_release_at` 必须等于 `body_voice_start`，且不得早于书名末字和书名后停顿的终点。
- `title_keyframes` 必须逐帧列出 opacity、scale、blur、`y_px` 和 `transform_y`；至少包含 0、1、2 帧与第 10–14 帧之间的最终落位帧。书名起势和落位都必须在封面上方安全区，禁止切到无封面主画面再做标题动画。
- 水滴效果只允许表现为“整帧页面像水面一样低幅形变→峰值→连续恢复”。禁止出现可见水珠、下落轨迹、落点飞溅、椭圆/同心圆轮廓、高光环、硬白描边、满屏雨或 Logo 光圈。如果关闭叠加层后页面像素不动，说明实现错了。

## 声画同步

- 情绪钩子从 0.00–0.12 秒开始，不等黑底画面完成。
- “今天分享的是”横跨遮罩展开末段和轮播段完成，具体起止服从真实字级时码。
- 引导句末到目标书名首字必须留 0.45–0.65 秒实测停顿。目标书名使用低位、结实、下收的重音，并与目标封面同页书名的出现同步。
- 书名末字到正文首字必须再留 0.45–0.70 秒实测停顿。正文第一句严格从真实 `body_start_seconds` 进入，不按固定秒数提前 J-cut。
- 轮播结构音固定使用剪映原声 `assets/sfx-library/jianying-carousel-clockwork-v001.mp3`（“闹钟上发条旋钮转动齿轮”）。从轮播开始只触发一次；跳过文件开头约 83ms 静音，原声短于轮播时自然结束并保留后段静音，原声长于轮播时才在动态 `carousel_end` 裁切并做 20–40ms 淡出。不变速、不循环、不复制第二遍、不拆成逐卡点击，也不为每张卡重复触发完整音效。
- 目标书锁定固定使用剪映原声 `assets/sfx-library/jianying-book-lock-waterdrop-v001.mp3`（“一滴水滴声”）。从封面水波的 `wave_trigger_at` 播放一次，保留自然尾韵。禁止使用旧的参考视频分离音、合成正弦水滴、金属叮声或普通低促音替换。
- 画面固定使用 `waterdrop_lock_response.type=cover_waterwave_then_title_drop`。`sfx_at` 与 `wave_trigger_at`、`visual_end` 与整页水波结束的误差分别不得超过 1 帧。`target_lock_hold_asset` 必须与目标书封同页，`target_lock_end` 必须等于 `body_voice_start`；书名朗读期间不得出现下一镜头。时间轴或水波元数据含 `hero_cut_at` 时，它必须大于等于 `body_voice_start`；任何提前值都是硬失败。

## 时间轴字段

`opening` 至少包含：

```json
{
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
  "mask_narration_captions_present": true,
  "mask_caption_track": [
    {"id": "mask-cap-01", "text": "片头配音字幕一", "start": 0.10, "end": 1.35},
    {"id": "mask-cap-02", "text": "片头配音字幕二", "start": 1.35, "end": 2.90}
  ],
  "expand_start": 1.35,
  "expand_end": 2.9,
  "carousel_start": 2.9,
  "carousel_end": 5.366667,
  "carousel_count": 19,
  "carousel_plan_asset": "10-片头字幕/carousel-plan-v001.json",
  "card_durations": [0.1, 0.133333, 0.133333, 0.133333, 0.133333, 0.133333, 0.133333, 0.133333, 0.133333, 0.1, 0.133333, 0.133333, 0.133333, 0.133333, 0.133333, 0.133333, 0.133333, 0.133333, 0.133333],
  "carousel_motion": {"type": "snap_settle", "scale_start": 1.035, "scale_end": 1.0, "soft_focus_px": 1.5, "transition": "hard_cut"},
  "carousel_cards": [
    {"title": "非目标书名", "role": "carousel", "asset": "10-片头字幕/carousel-v001/card-01.png"}
  ],
  "target_cover_hold_start": 5.366667,
  "target_cover_hold_end": 6.116667,
  "target_cover_base_asset": "10-片头字幕/v001/target-cover-base-v001.png",
  "target_cover_title_page_asset": "10-片头字幕/v001/target-cover-title-page-v001.png",
  "target_cover_title_binding": {
    "mode": "same_page_as_cover",
    "title_start": 5.366667,
    "title_settle_end": 5.733333,
    "title_above_cover": true,
    "cover_visible_during_title_motion": true,
    "visible_through_waterwave": true,
    "cover_visible_while_title_spoken": true,
    "persist_to_body": true,
    "title_safe_area": {"top": 60, "bottom": 220},
    "cover_safe_area": {"top": 240, "bottom": 1320}
  },
  "target_lock_start": 6.116667,
  "target_lock_end": 6.65,
  "target_lock_mode": "cover_waterwave_then_title_drop",
  "target_lock_asset": "10-片头字幕/v001/target-cover-title-page-v001.png",
  "target_lock_hold_asset": "10-片头字幕/v001/target-cover-title-page-v001.png",
  "cover_persists_until_body": true,
  "book_title_voice_start": 5.366667,
  "book_title_voice_end": 5.85,
  "cover_visible_while_title_spoken": true,
  "carousel_sfx_asset": "assets/sfx-library/jianying-carousel-clockwork-v001.mp3",
  "carousel_sfx_source_start": 0.083,
  "target_lock_sfx_asset": "assets/sfx-library/jianying-book-lock-waterdrop-v001.mp3",
  "target_hero_asset": "10-片头字幕/target-hero-v001.mp4",
  "title_motion": {"type": "cover_page_title_settle", "settle_frames": 10, "easing": "ease_out_cubic", "start_anchor": "cover_page_upper_center", "end_anchor": "cover_page_top"},
  "waterdrop_lock_response": {
    "type": "cover_waterwave_then_title_drop",
    "effect_on": "entire_page",
    "effect_style": "full_frame_displacement_map",
    "effect_scope": "entire_page",
    "effect_asset": "10-片头字幕/v001/waterwave-page-refraction-v001.mp4",
    "source_page_asset": "10-片头字幕/v001/target-cover-title-page-v001.png",
    "includes_title_layer": true,
    "visual_start": 5.716667,
    "wave_trigger_at": 5.716667,
    "sfx_at": 5.716667,
    "visual_end": 6.116667,
    "cover_release_at": 6.65,
    "literal_water_graphic": false,
    "overlay_graphic": false,
    "visible_ring": false,
    "page_deformation": true,
    "refraction": true,
    "perceptible_motion": true,
    "title_keyframes": [
      {"frame": 0, "scale": 1.50, "opacity": 0.35, "blur_px": 2.5, "y_px": 150, "transform_y": -0.60},
      {"frame": 1, "scale": 1.42, "opacity": 0.55, "blur_px": 2.2, "y_px": 139, "transform_y": -0.63},
      {"frame": 2, "scale": 1.34, "opacity": 1.0, "blur_px": 1.8, "y_px": 127, "transform_y": -0.66},
      {"frame": 5, "scale": 1.18, "opacity": 1.0, "blur_px": 0.0, "y_px": 99, "transform_y": -0.72},
      {"frame": 8, "scale": 1.05, "opacity": 1.0, "blur_px": 0.0, "y_px": 78, "transform_y": -0.77},
      {"frame": 10, "scale": 1.0, "opacity": 1.0, "blur_px": 0.0, "y_px": 70, "transform_y": -0.79}
    ]
  },
  "book_title_delivery": {"lead_text": "今天分享的是", "title_text": "书名", "title_start_seconds": 5.366667, "title_end_seconds": 5.85, "body_start_seconds": 6.65, "pre_title_pause_seconds": 0.52, "post_title_pause_seconds": 0.60, "title_emphasis": "firm_low_falling", "timing_source": "05-配音/timing-v001.json"},
  "body_voice_start": 6.65
}
```

`mask_source_image_asset` 和 `mask_source_video_asset` 必须位于 `08A-片头遮罩素材/`，必须真实存在，且不能与 `08-正文画面/` 或 `09-Grok视频/` 中的任何文件路径或 SHA-256 相同。查看联系表并确认叙事、主体和构图也不同后，才写入 `content_independence_reviewed: true`。`body_asset_reuse` 必须为 `false`，`mask_source_role` 必须为 `opening_mask_only`。

`opening-mask-plan-vNNN.json` 最少包含：

```json
{
  "role": "opening_mask_only",
  "content_independence_reviewed": true,
  "image_generation": {
    "provider": "codex_imagegen",
    "batch_id": "image-primary-v001",
    "prompt": "片头遮罩专用 prompt",
    "output": "08A-片头遮罩素材/v001/mask-source-v001.png"
  },
  "video_generation": {
    "provider": "grok_cli",
    "mode": "reference_to_video",
    "source_image": "08A-片头遮罩素材/v001/mask-source-v001.png",
    "output": "08A-片头遮罩素材/v001/mask-source-v001.mp4",
    "camera_locked": true,
    "motion_action": "只让远处草叶轻微随风摆动",
    "status": "approved"
  }
}
```

`prompt` 必须与正文 prompt 分开记录。`batch_id` 必须指向 `parallel-image-batch-vNNN.json` 的主并发批次；片头专用图与全部正文独立图片同时提交，但使用独立请求、独立构图和独立文件。`motion_action` 只写一种环境动作；不得用“画面动起来”等无约束提示词。

`carousel_cards` 数量必须等于 `carousel_count` 和最终计划的 `card_count`，长度与 `card_durations` 一致；每张严格为 3 或 4 帧，所有 `asset` 均存在，所有 `role` 均为 `carousel`，且不得与 `bookMeta.title` 相同。示例数组只展示字段形态，实际必须写完整计划数量。`keyword_mask_style` 只有在内容包确认图中查看蒙版边缘、字形和重心并确认后，才能从生成器的 `custom_review_required` 改成 `custom_reviewed`。`opening.keyword` 必须与最新 `mask-keyword-vNNN.json.keyword` 完全一致且恰好两个汉字，`keyword_mask_asset` 必须与其 `alpha_mask` 逐像素一致。

## 验收

逐帧查看 0–6 秒：

1. 先检查内容包 `mask-keyword-vNNN.json` 已为 `confirmed`，关键词恰好两个汉字；直接查看第一阶段确认图，并逐像素确认最终 `keyword_mask_asset` 没有换词或换字形。再单独查看 `mask_source_image_asset` 和 `mask_source_video_asset`：两者都在 `08A-片头遮罩素材/`，源视频保留源图构图，且与正文图片、视频没有路径、内容或叙事重复。
2. 开头必须有 3 帧目标书主画面预闪，第 4 帧进入黑底钩子。
3. 情绪句使用杨任东竹石体 Heavy；中央关键词使用毛笔字形，字内必须有与展开桥段同源的运动。
4. 横线先延长到全宽，再向上下展开，不是淡入。
5. 查看最终 `carousel-plan-vNNN.json`：来源必须是 `voice_actual`，轮播张数与时长按书名首字时码计算；逐张确认每卡严格 3–4 帧、首帧轻放大/柔焦、末帧收稳，卡间全部硬切。
6. 目标书不出现在快速轮播，而是与书名首字同帧独立锁定；不能比计划提前 1 帧以上。
7. 目标真实书封清楚可见并展示 0.65–0.85 秒；书名从该封面页第 1 帧起就在封面上方安全区出现，10–14 帧内由大到小收稳。逐帧确认书名动画全程保留封面，没有切到另一页。
8. 书名落位后，逐帧确认书名、封面文字、封面边缘和背景同时低幅形变，峰值后连续恢复。不得出现可见水珠、下落轨迹、飞溅、椭圆/同心圆轮廓或高光环。水滴音与波浪触发误差不超过 1 帧；水波结束后继续保持书封，直到正文首字才切主画面。逐帧确认书名朗读期间从未出现下一镜头。
9. 书名重音与锁定点同步；正文严格对齐 `body_start_seconds`，书名说完后有呼吸，音乐和旁白没有断点。
10. 最终片的中央关键词使用审核过的毛笔字蒙版，不接受系统楷体预览直出。
