---
name: book-emotion-video-rebuilder
description: 从一本真实书籍出发，用陌言样例的情绪文案结构和“十二”样例的固定毛笔字遮罩、遮罩阶段同步字幕、按书名真实口播时码动态计算的真实书封轮播、书名口播全程保持真实封面同页、人物侧脸加明亮风景的动态长镜头，生成音画严格同长的情绪读书视频。第一阶段同时锁定主题、逐字稿和只能由两个汉字组成的毛笔遮罩，并生成遮罩确认图供用户审核；确认后后期必须复用同一字形。书名口播固定拆成“今天分享的是”与书名两个节拍，书名前后保留可验证停顿。后期使用事件驱动依赖图自动并行生产，任一素材满足依赖后立即推动对应镜头，不等待同批其他素材。正文动态默认使用 Grok，已完成本机验收时可显式切换 LTX-2.3 本地模型，任何失败都回退确定性轻运动。默认一次性交付 1080×1440 高清 H.264/AAC 成片和基于同一时间轴的可编辑剪映草稿。用户要求制作、复刻、加速、并行生成、继续或修改情绪读书视频，要求第一阶段确认遮罩、两字遮罩、片头字幕、书名停顿与重音、按文案和语速自适应书封数量、念书名时保持封面、图片动态变化、文案对应生图、人物侧脸风景构图、书封轮播、1080p 高清、剪映草稿或双交付时使用。
---

# 情绪读书视频复刻

把每条视频当成独立、可恢复的素材项目。六个内部状态节点仍分目录、分版本落盘，但默认只停三次：内容包、声音与视觉联合包、最终双交付包。时间轴搭建、高清成片和剪映草稿连续生成，中间不索要确认。

## 先读这些规格

- 执行选书、文案、字幕或发布文案前，完整读取 `../../../01-老王写作生成器/4、老王-写作风格/SKILL.md`。
- 生成或重写逐字稿前，必须完整读取 [emotional-script-spec.md](references/emotional-script-spec.md)。该规格源自线程 `019fb90e-e259-7fa0-b0b5-1ce0c8179a03` 的三条陌言样例拆解。
- 制作分镜、片头、字幕、配音或时间轴时，完整读取 [reference-editing-spec.md](references/reference-editing-spec.md)。
- 设计“十二”式片头或明亮动态正文时，完整读取 [shier-template-frame-analysis.md](references/shier-template-frame-analysis.md)。
- 设计 0–5 秒片头时，完整读取 [opening-interaction-spec.md](references/opening-interaction-spec.md)。
- 设计正文画面、逐帧运动、字幕或时间轴时，完整读取 [visual-timeline-spec.md](references/visual-timeline-spec.md)。
- 使用 Grok 会员 OAuth 把静态分镜转成视频时，完整读取 [grok-oauth-video-spec.md](references/grok-oauth-video-spec.md)。
- 准备使用本地 LTX-2.3 把静态分镜转成视频时，完整读取 [local-ltx-video-spec.md](references/local-ltx-video-spec.md)；未通过该规格的本机探针和单镜头验收时不得启用。
- 生成正文关键帧前，完整读取 [image-generation-routing.md](references/image-generation-routing.md)。
- 逐字稿确认后开始声音、视觉、片头和字幕/BGM生产或展示实时进度时，完整读取 [parallel-pipeline-spec.md](references/parallel-pipeline-spec.md)。
- 设计配音、BGM、音效或混音时，完整读取 [sound-design-spec.md](references/sound-design-spec.md)，读取 `assets/bgm-library/library.json` 的本地曲库，并按 [reference-media-index.md](references/reference-media-index.md) 试听本地原片。
- 创建项目、命名或交付文件时，读取 [production-contract.md](references/production-contract.md)。

## 判断当前操作

1. 用户给了书名，但没有项目目录：创建项目并完整执行关卡 1。
2. 用户确认内容包后：生成脚本锁并进入一个连续的事件驱动生产阶段；把所有无依赖任务放入就绪队列，任一素材完成后立即释放并派发它的后代任务。
3. `sound_package` 与 `visual_package` 都完成后：同时设为 `awaiting_confirmation`，交付一次联合审核。用户说“确认”“下一步”或“继续”时同时确认二者，再执行时间轴包。
4. 用户指定某个素材重做：只为该素材生成新版本，将它所在关卡改为 `awaiting_confirmation`，将下游关卡改为 `stale`，不覆盖旧文件。
5. 用户只问进度：只读取清单和验证，不推进生产。

## 确认机制

- 一个关卡内不索要中间确认。自动完成生成、落盘、自检和必要的自动修正。
- 用户审核点的产物齐全并验证通过后，将相关状态一起设为 `awaiting_confirmation`，交付可观看或可试听的审核包，然后停止。
- 只有用户明确说“确认”、“下一步”或“继续”，才把当前关卡改为 `confirmed`。未确认的产物不得被下游使用。
- 内容包仍单独确认；确认后默认跨越声音与视觉的技术边界并行连跑，直到声音包和视觉包都完成才停。不得因为其中一个分支先完成而提前请求确认。
- 内容包必须同时展示两字遮罩确认图。用户确认内容包时，一并确认遮罩文字和字形；先把 `mask-keyword-vNNN.json.review_status` 改为 `confirmed`，再允许后期启动。用户只改遮罩时，重做内容包中的遮罩候选和预览，不重写已确认逐字稿。
- 声音与视觉联合确认后，关卡 4 和关卡 5 必须连续执行：先校验高清成片，再从同一时间轴生成剪映草稿；不得在 MP4 与剪映草稿之间请求确认。最终只交付一次“双交付包”。
- 命中密钥、授权、来源、费用或其他红线时，即使在关卡内也要停止并标记 `blocked`。

## 不可放宽的规则

- 只使用真实存在、书名与作者可核验的书。
- 作者只在书籍核验数据中保留，不进入口播。逐字稿禁止出现作者姓名、“作者认为”、“某某讨论”、“书中写到”、“这本书告诉我们”等讲解腔。
- 书名锚点固定写成“今天分享的是，《书名》。”，并拆成“今天分享的是”与“书名”两个声音节拍。引导句结束到书名首字必须停 0.45–0.65 秒，书名末字到正文首字必须再停 0.45–0.70 秒；书名使用低位、结实、下收的重音，禁止连读成“今天分享的是活着”、上扬成提问或念完立即冲进正文。
- 书封轮播数量禁止写死。配音前按“书名前全部汉字 ÷ 4.56 + 书名前目标停顿”生成估算计划；配音后必须用 `timing-vNNN.json.book_title_delivery.title_start_seconds` 重新规划。目标封面与书名首字同帧进入，每张非目标封面只能占 3–4 帧；真实书封库不足时标记 `blocked` 并扩库，禁止提前展示目标封面或拉长单卡冒充。
- 新写或重写逐字稿必须使用 `entry_mode: direct_theme`。书名锚点结束后直接陈述情绪冲突或核心判断，禁止用“你是不是也这样”“你有没有发现”“你是否也”“有没有过这种时候”“你是不是经常”等确认式提问开场，也禁止先罗列一串泛化生活场景再进入观点。
- 只有找到页码、电子书位置或可核验原文时，才写“书中原话”。否则明确写成“从这本书里读到的一个观点”。
- 不复用对标视频的原句、独特比喻、完整段落或原图。复刻时间机制、布局和情绪曲线，不复制版权素材。
- 真实书封只能来自用户提供、出版社、作者或可追溯的图书页面；禁止用生成模型伪造真实书封。
- 正文生图默认使用 Codex App 内置 `image_gen`，提供方记为 `codex_imagegen`；用户明确指定时才可切换 `grok_local` 或 `apimart`。APIMart 涉及按量费用，禁止作为自动回退。正文轻动态默认使用 `grok-local/grok_generate_video`；只有 `LTX_VIDEO_LOCAL_ROOT` 指向完整模型、探针通过且单镜头已验收时，才可显式改为 `ltx_local`。把实际选择、模型状态和回退原因写入 `manifest.defaults.video_generation` 及镜头 QC，禁止静默换渠道。任何密钥或 token 不写入 Skill、项目文件或日志。
- 中文展示字体默认使用 `assets/fonts/杨任东竹石体-Heavy.ttf`，适用于片头情绪句、书名、作者和中文字幕。中央毛笔关键词仍使用经审核 alpha mask，不用字体文件代替。
- 中央遮罩关键词必须且只能是两个汉字，使用正则 `[\u3400-\u9fff]{2}` 验收。禁止 1 字、3–4 字、完整书名、标点、数字、英文和空格。两个字必须概括本条视频承诺给观众的核心情绪结果，而不是随意截取书名。
- 遮罩段不能只有中央两字。中央 alpha mask 仍只允许两个汉字，但底部必须另设独立口播字幕层，按钩子实测时码整段切换显示。字幕使用杨任东竹石体 Heavy，不进入关键词蒙版，不使用逐字打字机。
- 遮罩文字和实际毛笔 alpha mask 必须在关卡 1 生成并确认。后期 `build_masked_keyword_opening.py` 必须引用内容包已确认的同一张 alpha mask，输出蒙版与内容包候选逐像素一致；禁止第二阶段重新选词、换字体、重画字形或用系统楷体替换。
- 正文生图必须采用 `parallel_individual + parallel_all`：先冻结全部独立分镜提示词和输出路径，再把全部 `shot-NN.png` 同批提交，所有请求提交完成后才统一等待。片头遮罩背景不属于生图批次。每个请求直接生成一张最终独立图片；禁止拼图、母版、网格和二次裁切，禁止先生成 `visual-lock` 再逐张生成，也禁止在循环里逐项 `await`。全部结果统一质检，失败图片只允许组成一个并发补图批次。每张会进入成片的无文字正文图仍必须以自身作为 `source_image` 转成当前已锁定的轻动态通道；真实书封、轮播卡、毛笔字遮罩、字幕图和其他含文字素材不得送入 Grok 或 LTX。单张视频生成失败时最多收紧提示词重试 1 次，仍失败记录 `ffmpeg_fallback` 并使用连续微动，不得静默跳过。Remotion 不参与生视频或镜头动画。
- 内容包确认后必须先生成 `script-lock-vNNN.json`，然后启动 `dependency_ready_queue`。调度单位是任务节点，不是整条资源分支：依赖满足的任务必须立即派发；每张正文图片返回后立即质检，通过后立即开始该镜头原始图生视频，不等待配音或其他图片。真实配音完成前使用脚本预估时长选择 6/10 秒原始档，实际时码就绪后再释放对应最终规格化任务。
- 并行运行必须写入 `07-分镜/parallel-pipeline-vNNN.json`，逐任务记录 `depends_on`、状态和起止时间，并写入 `timing-bind-vNNN.json`。单项失败只阻塞后代，无依赖任务继续推进。没有依赖顺序、就绪延迟和真实重叠证据不得声称已加速。
- 每次任务状态变化后必须立即运行 `scripts/render_progress.py`，原子刷新 `progress-state-vNNN.json` 和 `progress-vNNN.md`。同时通过 commentary 向用户展示总任务数、当前运行、刚完成、已就绪和阻塞项；无变化的长任务最多间隔 60 秒发送一次心跳。禁止只在阶段结束时补写进度。
- 每张正文图必须由其绑定的逐字稿意群推导，默认构图固定为“人物清晰侧脸 + 中远景/远景风景”，风景占画面主要面积。禁止先生成通用氛围图再硬套文案，也禁止用纯风景、背影、正脸近景替代。每张图都要在 `image-generation-vNNN.json.shots` 记录口播文本、逐字稿段 ID、配音起止时间、情绪阶段、完整 prompt 和构图验收字段。
- 正文图片必须通透、清晰、有正常黑白层次和适度色彩分离；禁止雾、霾、白纱感、奶油滤镜、灰白蒙层、低对比泛白、过曝高光和大面积柔焦。女孩默认穿针织衫、衬衫、短外套、轻便上衣或简洁连衣裙，禁止长大衣、及膝/过膝风衣和厚重拖地外套。人物的侧脸神情、身体状态、视线方向及环境的空间、天气、光线和运动线索必须由当前口播推导，不能全片使用同一种忧郁表情和同一类治愈风景。
- 每个正文轻动态片段的最终时长必须由绑定口播的实际配音区间决定，不按 Grok 原始 6 秒或 10 秒直接上轴。时间轴总时长、配音轨终点和最终 MP4 时长必须与 `manifest.duration.locked` 一致，允许误差不超过 0.05 秒。
- 新项目片头遮罩背景固定使用 `assets/opening-mask-video-library/manifest.json` 的默认视频 `seagulls-over-sea-close-v001`：海面和天空同时可见，白色飞鸟近景向上飞。将视频确定性复制为 `08A-片头遮罩素材/vNNN/mask-source-vNNN.mp4`，再生成 `opening-mask-plan-vNNN.json` 和 `10-片头字幕/masked-keyword-expand-vNNN.mp4`。禁止静态遮罩源图，禁止为此环节调用生图、Grok 图生视频或正文素材回退。
- 遮罩与横带展开阶段也必须显示当前配音意群的底部中英字幕；字幕从意群起点整段出现并覆盖 `hook_start` 到 `expand_end`，不得等正文第一帧才开始，也不得用顶部情绪句冒充配音字幕。
- 旁白念到目标书名时必须保持“书名＋真实封面”同页。水波恢复后继续停留在已落位书名的封面页，直到书名念完、书名后停顿结束并到达 `body_voice_start`；这段禁止切换目标主画面、正文第一帧或其他图片。`target-lock` 轨必须引用 `target_cover_title_page_asset`，结束点必须等于 `body_voice_start`。禁止在 `body_voice_start` 之前写入 `hero_cut_at`；历史数据存在该字段时只能删除，或设为不早于 `body_voice_start`。
- Grok 只允许通过已安装的 `grok-local` 使用 `membership_oauth_only`；禁止直接读取 `~/.grok/auth.json`，禁止静默切换 API Key，禁止自动充值或产生额外按量费用，禁止把 OAuth token 写入项目、Skill 或日志。火山引擎 TTS 认证信息从 `assets/volcengine.env` 读取，不写入 Skill 正文或项目 JSON。
- BGM 只能从用户提供的 `assets/bgm-library/library.json` 选择，候选和中选条目都必须满足 `source_scope: user_provided_local_file`、状态可用且本地文件真实存在。禁止补选 Mixkit、程序生成、模型生成、网络下载或其他曲库外音乐；没有合适曲目时标记 `blocked`，等待用户补充。
- 用户要求“只用所给参考音频”视为允许 AI 在该本地曲库内自动选择。中选歌曲带演唱时，仍必须按 [sound-design-spec.md](references/sound-design-spec.md) 的“有人声歌曲例外”做低占比、低人声底床；不得直接循环副歌或让歌词与旁白并列。
- 关卡 4 搭建时间轴后直接输出并校验高清 MP4，随即进入关卡 5，基于同一份已校验时间轴创建剪映草稿。MP4 用于直接观看和发布前审核，剪映草稿用于继续编辑；两者只做一次最终确认。AI 不代替用户公开发布。

## 固定成片参数与自适应时长

- 画布：本 Skill 中“1080p/高清”固定指 1080×1440、3:4、30fps 的竖版主成片，不是 720×960，也不是默认 1080×1920。只有用户明确要求 9:16 时才另建交付规格，禁止静默改画幅。
- 编码：视频固定 H.264、`yuv420p`；音频固定 AAC、48kHz、双声道。最终成片禁止用 720p 占位或只交过程预览。
- 时长：默认使用 `adaptive`，不设最低时长；按市场发布要求，新写或重写的逐字稿成片硬上限为 60 秒，不得通过提速塞进 60 秒。用户明确说“做 30 秒”等要求时使用 `fixed`，且按更短的指定值执行。
- 最终口播语速固定为 **4.56 个汉字/秒**，计算口径为“首个可听汉字起点到最后一个可听汉字终点，包含句间停顿”。源于用户指定原片 `7668678283642779072`：163 个汉字 / 35.78 秒 = 4.556，生产值四舍五入为 4.56。不得按书籍、情绪或时长改速。
- 文案：完整口播推荐 245–268 个汉字，默认目标 256 字，硬上限 270 字。256 字按 4.56 字/秒约 56.14 秒；270 字约 59.21 秒，再留 0.2–0.5 秒尾音，仍能确保成片小于 60 秒。内容本身足够完整时允许低于 245 字，不为凑字数添加重复金句。
- 正文画面：不预设固定数量。先从文案推导心理阶段，再以动态长镜头常见 7–14 秒/组检查密度；相邻内容若人物关系、心理状态、叙事空间、运动方向和象征物功能没有变化，必须合并为同一组。Grok 轻动态只允许一个主要变化：固定镜头下的风、草、水面、窗光、衣角或远景剪影之一；禁止运镜炫技和人物大动作。直接上轴的静态图片使用 `zoom_in`、`zoom_out`、`pan_left`、`pan_right` 交替或具名 `emotional_hold`，不使用旧的循环呼吸曲线。
- 生图一致性由批次提交前冻结的文字版 `style_lock` 保证：人物设定、季节、光线、调色、镜头语言和安全区必须写进每个独立 prompt。不得用“视觉锁定图先生成、后续逐张引用”的串行链路。
- 无片尾、无关注口播、无 Logo 动画。最后一句结束后留 0.2–0.5 秒即停。

## 五个成果关卡、三个审核点

### 关卡 1：内容包

运行：

```bash
python3 <skill_root>/scripts/init_project.py \
  --output-root <skill_root>/output \
  --title "<书名>" \
  --author "<作者>"
```

只有用户明确指定时长时才追加 `--duration <秒数>`。初始化后不停，继续完成书籍核验、情绪选择和逐字稿。

先使用网络查询出版社、作者页面、可搜索电子书或可核验纸书页，锁定：

- 书名、作者、译者、版本、ISBN。
- 封面图片来源与使用状态。
- 3–5 个可做短视频的书中观点。
- 原文引用的页码或电子书位置。

写入 `01-书籍资料/book-vNNN.json`、`sources-vNNN.md` 和 `cover-vNNN.*`。只有书籍身份或观点来源无法核验时才标记 `blocked`。

从书的真实观点中提取：

```text
书中观点 → 观众正在经历的处境 → 想获得的情绪结果 → 能做的一个动作
```

一条视频只允许一种主情绪，例如释怀、自救、清醒、被理解或重新有力量。内部比较观点可信度、观众处境贴合度、情绪张力和可执行动作，自动选择综合得分最高的方向。只把最终方向和选择理由写入 `02-情绪提炼/emotion-map-vNNN.md`，不把多个候选交给用户确认，也不混合情绪。

先写完整情绪弧，不使用对标原句：

1. 情绪认证：直接承诺一种情绪结果，如清醒、释怀或被理解，不在开头讲道理。
2. 书名锚点：固定说“今天分享的是，《书名》。”，不念作者。把“今天分享的是”和书名拆成两个节拍，书名前停 0.45–0.65 秒，书名后停 0.45–0.70 秒；书名低位、结实、句尾下收。书名出现后，正文不再回到书籍介绍。
3. 替观众表达：书名之后第一句直接陈述观众正在发生的内心动作或情绪冲突。使用肯定句，不向观众提问，不请求“对号入座”，不先铺陈多个泛化例子。
4. 压力递进：让处境一步比一步更紧，写身体和行为变化，不使用心理学术语总结。
5. 认知反转：把书中观点消化成口语判断，直接说给观众，不交代“谁说的”和“书里怎么写”。
6. 行动许可：给观众一个当下就能做的动作，语气是允许，不是命令。
7. 身份收口：回扣开头的情绪词，给出一句可独立成立的结尾，说完即停，不补关注引导。

逐字稿必须设置 `script_structure: moyan_emotional_v1` 和 `entry_mode: direct_theme`，正文段落使用 `viewer_expression`、`pressure_escalation`、`cognitive_reversal`、`action_permission` 和 `identity_close` 五个角色。书籍观点只负责事实托底，不能破坏情绪沉浸。

使用下列默认字数预算写稿。字数包含口播中所有汉字，不计标点、英文和数字；书名较长时，从正文预算中等量扣除，不改语速。

| 口播段 | 默认目标字数 | 按 4.56 字/秒的参考时长 | 作用 |
|---|---:|---:|---|
| 情绪认证钩子 | 14 | 3.07 秒 | 直接给情绪结果 |
| 书名锚点 | 12 | 2.63 秒 | “今天分享的是”→停顿→“书名”→停顿，不念作者 |
| 替观众表达 | 46 | 10.09 秒 | 直接进入一个真实内心动作 |
| 压力递进 | 54 | 11.84 秒 | 让处境逐层变紧 |
| 认知反转 | 62 | 13.60 秒 | 给出整条视频的新理解 |
| 行动许可 | 36 | 7.89 秒 | 只给一个当下可做的动作 |
| 身份收口 | 32 | 7.02 秒 | 回扣主情绪，说完即停 |
| **合计** | **256** | **56.14 秒** | 末字后再留 0.2–0.5 秒 |

初稿完成后计算每段和完整口播的汉字数，以固定 4.56 字/秒生成每段 `han_count`、`duration_estimate`、`start_estimate`和 `end_estimate`。完整口播硬上限 270 个汉字，成片硬上限 60 秒；超出时优先删除确认式铺垫、场景枚举、重复解释和同义金句，保留上述七个功能。不允许把语速调快来通过 60 秒验收。

生成：

- `03-逐字稿/script-vNNN.md`
- `03-逐字稿/script-vNNN.json`
- `03-逐字稿/originality-check-vNNN.md`

计算汉字数、`duration_estimate` 和各段占比，把估算值写入脚本 JSON 与 `manifest.duration.estimated`。生成 `originality-check-vNNN.md`，确认没有复用陌言原句、虚构书中原话或伪造引用。

根据主情绪和完整逐字稿确定唯一遮罩词，必须恰好两个汉字，例如“清醒”“自救”“释怀”“边界”。生成实际毛笔黑底白字 alpha 候选 `02-情绪提炼/keyword-brush-mask-vNNN.png`，再运行：

```bash
python3 <skill_root>/scripts/build_content_mask_preview.py \
  --keyword "<两个汉字>" \
  --hook "<情绪钩子，最多两行>" \
  --alpha-mask <project_dir>/02-情绪提炼/keyword-brush-mask-vNNN.png \
  --output <project_dir>/02-情绪提炼/mask-preview-vNNN.png \
  --record <project_dir>/02-情绪提炼/mask-keyword-vNNN.json \
  --version vNNN
```

确认图必须展示真实候选字形和片头情绪句，不得只交文字列表。把上述三个文件登记到 `content_package.artifacts`。第一阶段回复必须写出“遮罩文字：XX（2 字）”，并用绝对路径 Markdown 图片直接展示 `mask-preview-vNNN.png`，与书籍资料、主情绪、开头、逐字稿和预估时长一起等待确认。

产物齐全后先把 `content_package` 设为 `awaiting_confirmation`，再一次验证整个内容包：

```bash
python3 <skill_root>/scripts/validate_package.py \
  --project <project_dir> \
  --stage content_package
```

验证未通过时改回 `working`，在关卡内自动修正并重验。通过后一次交付书籍资料、主情绪、两字遮罩确认图、开头、完整逐字稿和预估时长，等待确认。未展示遮罩图不得声称内容包完成。其他关卡也使用同样的“待确认 → 验证 → 失败回退修正”模式。

### 关卡 2＋3：声音与视觉并行包

内容包确认后，先冻结脚本哈希和分镜语义，再进入同一个后期生产 DAG。声音、视觉、片头和字幕/BGM 是资源组，不是整体等待屏障；系统按任务依赖持续调度。视觉提示词和原始图生视频不依赖实际配音时码，只有最终片段规格化、字幕时码和混音依赖真实配音。

#### 声音分支

先听本地参考原片，不直接生成最终配音：

1. 根据情绪地图选择“清醒型”“被理解型”或“自救型”。
2. 从陌言 01–03 中选择旁白主参考，并听“十二”04–06 中至少两条的前 8 秒，记录钩子、遮罩、轮播、锁书、正文转折和末句的声音行为。
3. 把逐字稿划分为钩子、遮罩展开、动态数量轮播、锁书、处境、转折、释放和末句八个声音环节。
4. 默认使用火山引擎音色 `S_Bkoh3uBT1`。用同一段 40–60 字文案生成至少两个试听版本，两版必须保持 speaker、`speech_rate=10`、标点和最终 4.56 字/秒全部一致，只比较情绪强度或输出稳定性，不得再用不同语速做候选。
5. 只从用户提供的本地 BGM 曲库按主情绪筛选，给两个候选分别制作 12–15 秒样片。禁止用曲库外音乐补足；带演唱的候选必须先压低歌声再进入对比。曲库不足两个可用候选时，用现有一首完成选择并记录候选不足，不伪造第二首。
6. 比较贴脸感、可信度、情绪浓度、可懂度和听觉疲劳，由 AI 自动选择同一固定语速下的稳定表演版本和 BGM，不在候选之间停下。

`S_Bkoh3uBT1` 是读书视频的全局默认音色。只有用户明确指定其他音色，或接口已确认该 speaker 不可用时，才允许替换。替换时在 `voice-selection-vNNN.json` 写入 `selection_mode` 和 `override_reason`。

输出 `04-声音设计/sound-blueprint-vNNN.json`、`voice-selection-vNNN.json`、`reference-listening-vNNN.md`、两个配音试听和 `sound-preview-vNNN.mp4`。随后继续生成全文配音，不在试听后停止。

使用本关卡试听比较后选定的音色和参数，把整篇逐字稿作为一次连续表演生成；可按服务限制分请求，但合成前必须维持同一上下文、音色、速度和响度，禁止按视觉分镜硬切。

- 连续语速：固定 4.56 字/秒，验收容差只允许 ±0.02 字/秒（来自毫秒取整和音频帧边界），这不是可调区间。
- 书名固定节奏：TTS 文本使用“今天分享的是，\n书名。\n正文第一句”，引导句末到书名首字实测 0.45–0.65 秒，书名末字到正文首字实测 0.45–0.70 秒。先用标点和换行在同一次连续生成中实现；模型停顿不足时把两个边界分别补到 0.55 秒和 0.60 秒，再做保持音高的全篇 4.56 字/秒归一并重新测量。禁止拆开重录书名；归一后任一停顿越界必须调整并重验。
- 普通句间停顿：0.35–0.50 秒。
- 大段转折：0.50–0.65 秒。
- 首字从 0.0–0.12 秒开始，不留空片头。
- 保留原始生成文件，不用处理版覆盖原文件。

火山引擎请求参数固定使用 `speech_rate=10`。原始输出后以 TTS 字级时间戳测量“首字→末字”跨度；若不在 4.54–4.58 之间，运行 `scripts/normalize_voice_speed.py` 做保持音高的小幅时长归一，使最终输出回到 4.56。归一倍率超过 ±8% 时不得强压，必须返回检查标点与句式。不允许用调整 `speech_rate`、改情绪预设或按书临时改速来通过校验。

输出 `05-配音/voice-raw-vNNN.wav`、`voice-vNNN.wav` 和 `timing-vNNN.json`。把处理后连续配音的实测时长写入 `manifest.duration.locked`，后续画面、BGM、字幕和时间轴全部服从该值。`adaptive` 模式不因偏离估算值而返工；只有情绪弧不完整、停顿明显异常或内容重复时才重新生成关卡 1 的逐字稿版本。禁止用大幅变速硬压时长。

根据本关卡的声音方案生成或选定一条完整 BGM。保存来源、授权状态、情绪预设和循环方式；再按七个声音环节编写音乐变化。片头结构音固定引用 `assets/sfx-library/manifest.json`：书封轮播默认使用剪映原声 `jianying-carousel-clockwork-v001.mp3`，从轮播开始连续播放并在轮播结束处裁切，不做变速；目标书锁定默认使用剪映原声 `jianying-book-lock-waterdrop-v001.mp3`，在封面水波开始扩散的触发帧播放且只出现一次。两个默认音效都必须复制到项目 `06-配乐音效/` 后再引用，禁止改用旧的参考视频分离音、合成点击、正弦水滴或普通低促音。

使用已锁定配音制作完整声音预览。纯音乐在说话时自动闪避 3–5dB，旁白主观领先 10–14dB。BGM 必须清楚提供情绪底色，不能只在耳机里勉强听见；旁白段的乐器底床默认从 -24至-21 LUFS 起试，比旧基线提高约 2dB。带演唱的曲库歌曲必须拆成“乐器底床＋演唱层”思路处理：保留音乐情绪，让演唱比乐器再低 10–16dB，旁白期间对演唱层额外闪避 4–8dB。歌词不得连续可辨，也不得压低整条 BGM 到失去情绪。

输出 `06-配乐音效/bgm-vNNN.wav`、`music-source-vNNN.md`、必要的 `sfx-*.wav`、`music-cue-vNNN.json` 和 `audio-mix-preview-vNNN.wav`。来源或授权不清时标记 `blocked`。其余情况把已完成的声音任务标记为 `completed`，由调度器继续释放它们的后代；不等待视觉资源组，也不单独请求用户确认。

#### 视觉与片头分支

按 [visual-timeline-spec.md](references/visual-timeline-spec.md) 的自适应算法划分正文画面，不先填写目标数量。先标记每段口播的心理阶段，再合并相邻的同状态内容；只有人物关系、心理状态、叙事空间、运动方向、核心象征物功能或因果阶段发生变化时才新增画面。一组长镜头允许承载 2–5 张字幕卡。每组生成：

- 对应逐字稿段 ID、完整口播文本、实际配音 `voice_start`、`voice_end` 和目标镜头时长。
- `emotional_stage` 与 `visual_change_reason`，说明这一组承担的心理阶段，以及为什么必须在这里换图。
- 开阔风景、人物清晰侧脸的位置与视线方向、文案对应的具体神情和身体状态、清透自然光、清晰青绿与适度暖色、单一运动线索和留白位置。默认只用中远景或远景，风景占主要面积，不生成正脸近景、纯背影或纯风景；女孩不得穿长大衣。
- 中文字幕和不超过一行的英文意译。

先按 [image-generation-routing.md](references/image-generation-routing.md) 冻结文字版 `style_lock`、全部正文独立提示词和输出路径并创建主并发批次：每个正文分镜直接对应一个 `shot-NN.png` 请求。一次性提交全部请求，再统一等待，不得让任何图片依赖另一张图片先完成。输出全部独立 `shot-NN.png` 和 `07-分镜/parallel-image-batch-vNNN.json`；片头固定视频不进入此批次。

图片主批次提交后按返回事件逐张质检。每个通过项立即触发对应原始图生视频，不能等待主批次全部完成；不合格项先收集，主批次结束后统一组成一个 `parallel_failed_only` 补图批次。把首张通过项的路径登记为 `visual_lock`，但不复制、不重生，也不作为同批其他图片的前置参考。最终输出 `07-分镜/storyboard-vNNN.json`、`prompts-vNNN.md`、`image-generation-vNNN.json` 和全部 `08-正文画面/vNNN/shot-NN.png`。`image-generation-vNNN.json` 必须记录每张图的 `source_type`、主批次/补图批次 ID、请求 ID 和预估时码依据。

先读取 `manifest.defaults.video_generation.provider`。使用默认 `grok_cli` 时按 [grok-oauth-video-spec.md](references/grok-oauth-video-spec.md) 调用 `grok_status`；显式使用 `ltx_local` 时按 [local-ltx-video-spec.md](references/local-ltx-video-spec.md) 检查环境变量、模型分片和单镜头验收。未通过预检就直接记录 `ffmpeg_fallback`，不得一边下载模型一边阻塞本条视频。把本关卡内部验收通过且会进入成片的全部 `shot-NN.png` 加入同一提供方的图生视频计划，不再人工挑少数镜头。

对每张计划图片调用 `grok-local/grok_generate_video`，参数必须包含该图片的绝对路径 `source_image`、`aspect_ratio: 2:3`、`resolution: 720p`，并按镜头长度选择 6 秒或 10 秒。提示词只能指定一个低幅自然动作，固定镜头并要求完整保留侧脸、风景、颜色和留白。生成后把返回 MP4 复制到 `09-Grok视频/vNNN/shot-NN-raw.mp4`，再按该镜头 `voice_start`、`voice_end` 对应的目标区间规格化为 1080×1440、30fps 的 `shot-NN-final.mp4`；短素材只允许克制变速或首尾定帧补足，不得循环人物动作。`grok-video-plan-vNNN.json.selected_shots` 必须继承逐字稿段 ID、口播、配音起止点和 `target_duration_seconds`。必须逐帧复核 `shot-NN-qc.json`，将状态设为 `approved` 或 `fallback`，未验收片段不得进入时间轴。

使用 `ltx_local` 时保持同一输出契约：每张图仅指定一种低幅动作，默认 97 帧、24fps、576×768，生成后再规格化到绑定口播时长和 1080×1440、30fps。为兼容当前渲染器，可把验收后的最终 MP4 复制到 `09-Grok视频/vNNN/shot-NN-final.mp4`，但镜头 QC 的 `provider` 必须写 `ltx_local`，不得伪写成 Grok。LTX 不处理任何含文字素材，出现变脸、肢体变化、新物体、闪烁、构图漂移或首尾跳变立即回退 FFmpeg。

- 每张进入成片的正文图都要有一条对应的 `shot-NN-final.mp4` 或一条有原因的回退记录，数量和 source 必须与 `image-generation-vNNN.json.shots` 一致。
- 不处理书封卡、片头轮播、已叠文字图片、人脸近景或手部特写；目标书主画面必须先使用无文字底图生成动态，再在时间轴叠加书名作者。
- 默认固定相机；只允许风、窗光、衣角、草、水面或远处剪影中的一种轻微变化。禁止摇移、环绕、快速推拉、明显景深拉焦、人物转身或走近镜头、嘴型、表情变化、新增人物或物体、文字、切镜、转场和画风漂移。
- OAuth、模型、会员用量、质量或水印策略任一不通过时，记录原因并锁定为 `ffmpeg_fallback`。用户明确要求必须使用 Grok 时才标记 `blocked`。

输出 `09-Grok视频/oauth-check-vNNN.json`、`grok-video-plan-vNNN.json`、已验收的 `vNNN/shot-NN-final.mp4` 和 `shot-NN-qc.json`；回退时输出 `fallback-vNNN.json`。回退不中断本关，用静态图微动继续。

按 [opening-interaction-spec.md](references/opening-interaction-spec.md) 固定生成 `masked_book_carousel`：

1. 读取内容包中已确认的 `mask-keyword-vNNN.json`，确认 `review_status: confirmed`、关键词恰好两个汉字，并直接复用其 `alpha_mask`。本关不得重新选词或重画字形；系统楷体也不得替代已确认蒙版。
2. 读取 `assets/opening-mask-video-library/manifest.json`，取默认 `seagulls-over-sea-close-v001`，核对 SHA-256 后复制为 `08A-片头遮罩素材/vNNN/mask-source-vNNN.mp4`，并写入 `opening-mask-plan-vNNN.json`。新项目不生成 `mask-source-vNNN.png`，不调用图生视频。
3. 确认项目内的 `mask-source-vNNN.mp4` 为 1080×1440、30fps、H.264、`yuv420p`、无音轨，且海面、天空和近景向上飞的白色飞鸟均可见。
4. 运行 `build_masked_keyword_opening.py`，把内容包已确认的 `02-情绪提炼/keyword-brush-mask-vNNN.png` 作为 `--keyword-mask`、`mask-keyword-vNNN.json` 作为 `--content-mask-record` 传入；把同一时间位置的视频同时填入两字关键词和横带展开遮罩，保留生成的 MP4、遮罩 PNG 和元数据 JSON，并逐像素核对输出蒙版与已确认候选一致。
5. 配音前运行 `plan_book_carousel.py --script ...` 生成 `carousel-plan-estimated-vNNN.json`，只用于提前准备足量书封；真实 `timing-vNNN.json` 出现后立即用 `--timing` 重跑并生成 `carousel-plan-vNNN.json`。最终计划的 `timing_source_type` 必须是 `voice_actual`，`target_cover_lead_frames` 默认为 0；目标书封从书名首字起声帧开始展示，不得拿估算计划直接成片。
6. 运行 `build_book_carousel_cards.py --plan <carousel-plan-vNNN.json>`，从真实书封库生成计划要求数量的项目独立全屏卡并排除目标书。每张卡必须做 3–4 帧的 `snap_settle`：入场首帧 103%–104% 轻微放大并带 1–2px 柔焦，随后在本卡剩余帧内快速收稳到 100%；卡间硬切，不滑动、不叠化、不弹跳。连续短促变化形成“咔咔咔后停住”的视觉节奏，不能把静态 PNG 直接连续拼接。
7. 根据连续配音时码先生成片头字幕卡。`captionTrack` 必须从 `hook_start` 开始覆盖两字遮罩与横带展开全过程；字幕在底部安全区整段直接显示，顶部情绪句和中央毛笔字照常保留。渲染时字幕叠加必须发生在片头与正文分支之外，不能只在 `body_voice_start` 之后执行。
8. 片头使用 3 帧目标画面预闪，再按实测时间轴完成遮罩、动态轮播和 `cover_waterwave_then_title_drop` 锁定：旁白先完整说“今天分享的是”，停 0.45–0.65 秒后，齿轮声结束并进入目标真实书封时单独重读书名；书名念完再停 0.45–0.70 秒才进入正文。目标书封必须独立展示 0.65–0.85 秒。书名从目标封面出现的第 1 帧起就必须叠在该封面页上方安全区，在封面始终可见的前提下用 10–14 帧 ease-out 由大到小收稳。从书名首字发音开始，直到书名后停顿结束、正文首字开始前，画面必须始终保持目标真实书封。禁止书名还在朗读时提前切到目标主画面或第一正文镜头，也禁止“先只有封面，切到另一页再出书名”。
9. 先运行 `build_target_cover_title_page.py` 生成封面基底页和书名封面同页定帧。水滴声触发时，必须以“书名＋真实封面＋背景”的同页定帧为输入，对整页做连续位移映射；书名、封面文字、边缘和背景必须同步低幅折射，0.30–0.50 秒内起伏并连续恢复。水波恢复后不切目标主画面，继续保持 `target_cover_title_page_asset` 到 `body_voice_start`；只有正文第一句开始时才切入第一张正文画面。手机预览中看不出“书名口播全程保持封面”的一律判失败。
10. 生成 `opening-vNNN.json` 并逐帧检查 0–6 秒。

片头声音不得重新设计，必须引用 `music-cue-vNNN.json` 的钩子、遮罩、动态轮播区间和锁书配置。发条齿轮声从最终计划的 `carousel_start` 只播放一次原声并在自身自然尾音处结束；轮播比原声长时后段留给 BGM 和旁白，禁止循环、复制、拼接第二遍或按封面数重复触发。原声长于轮播时才在 `carousel_end` 裁切并短淡出。将最终 `carousel-plan-vNNN.json`、`mask-source-vNNN.mp4`、`opening-mask-plan-vNNN.json`、`masked-keyword-expand-vNNN.mp4` 和 `opening-vNNN.json` 全部登记到 `manifest.steps.visual_package.artifacts`，剪映草稿也必须将遮罩源视频保留在 `Resources/local_media/`。

真实 `timing-vNNN.json` 完成后立即生成 `timing-bind-vNNN.json`，逐个释放已经具备原始素材的规格化、字幕时码、片头微调和混音任务；后到素材满足依赖时自行继续，不设“四条分支全部完成才开始”的屏障。全部最终节点完成后，把 `sound_package` 与 `visual_package` 同时设为 `awaiting_confirmation`，一次性交付混音试听、实测时长、0–6 秒片头预览、正文分镜与动态说明。

### 关卡 4：时间轴包

使用配音实际时间轴，不使用预估时间。

- 字幕时码必须来自最终配音的真实逐字/逐词时间戳，不能照搬脚本估算段落。TTS 没有可靠字级时间戳时，必须对最终配音做一次强制对齐或 ASR 词级复测；每张字幕从该意群首个可听字出现，保持到末个可听字结束，静音停顿不提前挂出下一张字幕。
- 中文每卡 5–14 字，最多 16 字，默认一行。
- 字幕在该意群开始时整段直接显示并保持到该意群结束，不使用逐字、打字机、按词跳出或逐渐补全。
- 片头字幕属于同一条 `captionTrack`：必须覆盖遮罩阶段的配音意群，并与正文使用相同的底部字号、字体和整段显示规则；禁止从 `body_voice_start` 才创建第一张字幕。
- 英文是简短意译，与中文同一帧整段出现，不写机械直译。
- 中文字体固定使用 `杨任东竹石体-Heavy.ttf`：顶部书名 88px，作者 44px，中文字幕 60px，片头情绪句 42–48px。英文使用 `Georgia Regular` 32px。白字使用右下 4–5px 黑色偏移阴影，不使用普通黑体、宋体或均匀描边替代。
- 目标书锁定阶段必须在真实封面所在的同一页上显示书名；书名在封面上方安全区由大到小收稳，封面全程保持可见。水波恢复后仍保持书名封面同页，直到书名后停顿结束并到达 `body_voice_start`；不得在念书名中途切到目标主画面或正文第一帧。

输出 `10-片头字幕/subtitles-vNNN.json`、`zh-vNNN.srt` 和 `en-vNNN.srt`，然后直接搭建时间轴和混音。

按 [reference-editing-spec.md](references/reference-editing-spec.md)、[opening-interaction-spec.md](references/opening-interaction-spec.md) 和 [visual-timeline-spec.md](references/visual-timeline-spec.md) 搭建。固定要求：

- 片头海报卡继续使用片头规格定义的硬切。正文记忆碎片和强转折使用具名硬切，情绪连续段落才使用 0.12–0.30 秒短淡化；三个及以上正文转场不得全部使用同一种类型。
- 直接上轴的静态图片和具名回退图片必须使用 `zoom_in`、`zoom_out`、`pan_left`、`pan_right` 或 `emotional_hold`。缩放范围分别为 1.00→1.10–1.13、1.10–1.13→1.00、保持 1.08–1.13 横移不超过画宽 4%、1.00→1.025；前四类相邻不得重复，`emotional_hold` 只用于停顿、记忆定格或末句。
- 静态图片必须放入覆盖全画布且 `overflow: hidden`、`fit: cover` 的容器，只变换 `inner_image`，不得移动整个镜头层；逐帧验收不得露黑边。已验收的 Grok 轻动态片段默认不再叠加缩放或平移。
- 新画面在新语义开始前 0.1–0.2 秒进入；硬切发生在语义切点。
- 时间轴以剪映草稿为主交付；FFmpeg 只用于 Grok 素材规格化和可选过程预览。不使用 Remotion 生视频或制作镜头动画。
- 时间轴必须分为 `sceneTrack`、`captionTrack`、`accentTrack` 和 `transitionTrack`，不得让字幕和图片一一绑定。
- `timeline.duration`、配音轨 `end`、正文最后一组的 `voice_end` 和最终 MP4 时长全部取 `manifest.duration.locked`；正文第一组 `voice_start` 必须等于 `opening.body_voice_start`。相邻口播区间不得留缝或重叠，场景叠化只能发生在画面区间，不得改变口播区间。
- 每个 `sceneTrack` 项必须继承其 `source_still` 对应的逐字稿段 ID、口播、`voice_start` 和 `voice_end`。`short_fade` 场景可以按 0.12–0.30 秒稍作重叠，`hard_cut` 不重叠；两者都必须完整包住自己的口播区间。
- 只引用声音与视觉联合审核中已确认的配音、BGM、音效和动态画面，不在时间轴阶段临时更换。
- 背景音乐全程连续；默认无歌词且人声进入时自动闪避 3–5dB。用户点名有人声歌曲时，只引用已确认的低人声处理版，闪避 5–8dB。
- 成片目标 -10.5至-9.5 LUFS，LRA 2–4 LU，真峰值不得超过 -1 dBTP。

输出 `11-时间轴/timeline-vNNN.json`。随即从同一份时间轴直接输出 `12-预览/final-video-vNNN.mp4`，不在时间轴和最终视频之间索要确认。

最终视频必须是 1080×1440、3:4、30fps，包含完整画面和最终混音，时长与锁定配音误差不超过 0.05 秒。生成后运行：

```bash
python3 <skill_root>/scripts/validate_package.py \
  --project <video_dir> \
  --video <video_dir>/12-预览/final-video-vNNN.mp4
```

验证通过后打开最终视频，抽查片头、正文动态镜头、最长字幕、转场、声音和结尾。此时只把 `timeline_package` 与 `final_video` 记为内部校验通过，不停下、不请求确认，立即执行关卡 5。

### 关卡 5：剪映草稿

基于关卡 4 已校验的同一份 `timeline-vNNN.json` 创建剪映草稿；禁止把已经烘焙的 MP4 当成唯一素材导入剪映。片头图、静态分镜、Grok 片段、书名、作者、中文字幕、英文字幕、配音、BGM 和音效必须在草稿中保持独立轨道。

先在 `timeline-vNNN.json` 写入 `openingTrack`、`sceneTrack`、`captionTrack`、`audioTrack` 和 `bookMeta`，再运行：

```bash
<videocut_root>/.venv/bin/python \
  <skill_root>/scripts/create_jianying_draft.py \
  --project <video_dir> \
  --timeline <video_dir>/11-时间轴/timeline-vNNN.json \
  --name "<书名>_情绪读书_vNNN"
```

把草稿路径和结构验收写入 `13-剪映草稿/draft-vNNN.json`，再运行：

```bash
python3 <skill_root>/scripts/validate_package.py \
  --project <video_dir> \
  --stage jianying_draft \
  --video <video_dir>/12-预览/final-video-vNNN.mp4 \
  --draft <jianying_draft_dir>
```

草稿验收检查入口、轨道、片段、时间码、`Resources/local_media/`、交付规格和与高清成片共用时间轴的证据。草稿报告必须写入 `delivery_profile: 1080p_3x4_editable`、高清成片绝对路径、`same_timeline_as_video_master: true` 和 `flattened_final_mp4: false`。在剪映抽查 0–5 秒、Grok 片段、最长字幕、转场和结尾。无法实际打开剪映时，只能报告“草稿结构验收通过”，不得写“剪映视觉已通过”。通过后把 `timeline_package`、`final_video` 与 `jianying_draft` 一起设为 `awaiting_confirmation`，一次性交付高清 MP4、时间轴 JSON 和真实剪映草稿路径，等待最终确认。

`create_jianying_draft.py` 必须把 `杨任东竹石体-Heavy.ttf` 复制到草稿 `Resources/local_fonts/`。当前剪映草稿库只支持内置字体枚举：最终 MP4 和过程预览必须实际用该 TTF 渲染；剪映草稿报告必须写 `font_binding: requires_jianying_local_font_activation`，用户在剪映内激活本地字体后再绑定文字轨。未激活前不得声称剪映文字轨已使用该字体。

## 每步交付

前两个审核点每次只报告；最终审核点必须把高清成片和剪映草稿合并为一个双交付包：

1. 本次执行的关卡与状态：`awaiting_confirmation`、`confirmed` 或 `blocked`。
2. 本次新生成文件的绝对路径。
3. 验证结果；失败时只说当前阻塞。
4. 下一关名称，并明确本次已停止、等待用户确认；最终双交付完成后不再拆出单独的草稿确认。
