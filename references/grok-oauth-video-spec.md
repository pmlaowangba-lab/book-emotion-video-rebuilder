# Grok 会员 OAuth 图生视频规格

## 目录

- 用途与边界
- 授权模式
- 能力预检
- 镜头选择
- 提示词约束
- 异步生成与落盘
- 质量检查
- 回退策略
- 产物契约

## 用途与边界

Codex App 内置 `image_gen` 负责正文静态关键帧；Grok 只把每张会进入成片的无文字关键帧增强为克制的轻动态镜头。Grok 不负责生书封、生轮播卡、生成带文字画面、设计片头或重写分镜。Remotion 不参与视频生成和镜头动画；FFmpeg 只负责规格化 Grok 片段，字幕、转场、配音、BGM 和所有素材最终写入可编辑剪映草稿。

- `image-generation-vNNN.json.shots` 中每张 `shot-NN.png` 都必须进入图生视频计划，不设 3 张上限，并继承逐字稿段 ID和口播。真实配音未完成时使用脚本预估时码生成原始视频；汇合后再写入实际配音起止点和目标时长。
- 目标书主画面若是无文字 Grok 生成图，也必须生成动态版；真实书封展示页保持模板动画，不送入 Grok。
- 源图必须是 `08-正文画面/vNNN/target-hero.png` 或 `shot-NN.png`。
- 必须给 `grok_generate_video` 传 `source_image`；不使用纯文生视频替代已锁定画面。
- 不生成粒子、视差、光斑或其他独立特效视频。

## 授权模式

固定使用：

```json
{
  "auth_mode": "membership_oauth_only",
  "billing_mode": "subscription_allowance",
  "api_key_fallback": false,
  "auto_top_up": false
}
```

- 只通过已安装的本地 MCP `grok-local` 使用 X/Grok 会员 OAuth 登录态。
- 认证预检调用 `grok-local/grok_status`；图生视频调用 `grok-local/grok_generate_video`。
- OAuth 不可用时不得静默改用 xAI API Key。
- 不自动购买额度，不开启自动充值，不执行可能产生额外按量费用的回退。
- access token、refresh token、ID token、authorization header、client secret 只留在已有安全凭证存储中，不得写入项目 JSON、请求快照、Skill、终端输出或日志。
- OAuth 的持久化和刷新全部交给 Grok CLI。不得直接读取、复制或解析 `~/.grok/auth.json`。

## 能力预检

每个项目第一次运行 Grok 步骤时：

1. 调用 `grok-local/grok_status` 检查本地 OAuth 登录态和默认模型。
2. 使用第一张已验收的非成片测试图做一次低额度能力探测；只有实际返回本地 MP4 才算图生视频可用。
3. 确认返回文件存在、可被 `ffprobe` 读取且没有返回认证、额度或工具不可用错误。
4. 如能取得会员用量信号，确认当前未触发周期用量上限。

只把不敏感结果写入 `oauth-check-vNNN.json`：检查时间、是否已登录、是否成功刷新、授权范围是否满足、模型 ID 列表、能力状态和失败类型。不写 token 原文或 header。

失败类型使用 `not_authenticated`、`refresh_failed`、`video_scope_missing`、`model_unavailable`、`membership_limit` 或 `service_error`。

## 镜头选择

所有进入成片的无文字正文图都要动态化。为每张图从现有构图里选一种最安全的动作，优先级如下：

1. 水面、草叶、窗帘、树影、云影或柔光极轻变化。
2. 人物衣角或头发末端轻微摆动，身体和头部保持稳定。
3. 远处车辆、动物或剪影沿原有方向缓慢移动，数量和形态不变。
4. 只有环境无法合理运动时，才允许 0%→1% 的极慢单向推近。

禁止选择：

- 真实书封、书名页、轮播卡或任何含文字的画面。
- 正脸近景、嘴部特写、手部特写或高密度复杂物体。
- 人物或动物占画面过大、无法在不变形的情况下动态化的镜头；这类图先回到分镜改为远景，而不是直接要求模型做大动作。

## 提示词约束

```text
Use the provided image as the exact first-frame reference. Preserve the exact
subject identity, face, anatomy, clothing, object count, composition, crop,
colors, lighting, texture, and title/subtitle safe areas. Keep the camera locked.
Create one continuous restrained shot. Only animate: <one subtle slow action>.
Motion amplitude must remain minimal and secondary to the narration.
No walking toward camera, no turning around, no large limb movement, no lip or
expression change, no camera pan, tilt, orbit, handheld shake, dramatic zoom,
parallax, focus pull, new people, new objects, text, cuts, transition, flicker,
morphing, anatomy change, weather change, or style drift.
```

每次请求只写一种允许动作。不写“cinematic movement”“dynamic camera”“dramatic”之类会放大动作的词，不写叙事续写，不要求人物说话，不让模型自由设计下一个镜头。

## 异步生成与落盘

1. 任一 `shot-NN.png` 返回并通过单张质检后，立即调用 `grok-local/grok_generate_video`，必须传绝对 `source_image`；不得等待全部图片完成。
2. 固定 `resolution: 720p`、`aspect_ratio: 2:3`。真实配音未完成时按脚本预估区间选择档位：不超过 6.9 秒用 6 秒，否则用 10 秒。
3. 成功后立即把返回文件复制为 `shot-NN-raw.mp4`，不依赖会话临时目录。
4. 第一次质量不合格时，只允许收紧动作提示词再重试 1 次，不通过就回退。
5. 原始结果先落盘。四分支汇合并取得实际配音时码后，再将 2:3 结果居中裁切为 3:4，并规格化为 1080×1440、30fps 的 `shot-NN-final.mp4`，不覆盖原文件。
6. 目标镜头比生成片短时只做首尾裁剪；目标镜头比生成片长时允许 0.90–1.15 倍轻微变速，仍不足的尾部用最后稳定帧配合最多 1% 的缓慢推近补足。禁止倒放、循环或重复动作。

最终片段使用 1080×1440、30fps，`target_duration_seconds` 必须等于该镜头 `voice_end - voice_start`，实际时长误差不超过 0.05 秒。Grok 的 6/10 秒只是原始生成档位；规格化时只允许等比裁切、尺寸适配、帧率转换、克制变速、首尾裁剪或短暂首尾定帧，不得循环人物动作。`sceneTrack` 可为叠化扩大画面区间，但不得修改该镜头的口播责任区间。

## 质量检查

每个片段逐帧检查主人物与构图漂移、新增物体或文字、人脸和手部畸变、切镜与闪烁、字幕安全区和 Grok 水印，并额外检查：

- 第一帧与源图主体位置、人数、物体数、衣服和调色一致。
- 全片只有计划中的一种低幅动作，没有人物明显位移、转身、靠近镜头或大幅肢体动作。
- 镜头保持固定；若出现摇移、环绕、明显变焦或景深拉焦，直接失败。
- 25% 手机预览能感到“活着”，但运动不会抢走字幕和旁白注意力。

水印处理只有两种：

- `accepted`：保持原样并接受用于本地预览。
- `fallback`：放弃该片段，使用源静态图的 FFmpeg 微动。

不得删除、遮挡、裁掉或模糊 Grok 水印。用户不接受水印时，直接回退。

## 回退策略

OAuth 不可用、视频端点无权、无模型、会员用量已满、超时、限流、质量不合格或水印不可接受时，切换 `ffmpeg_fallback`。

单张失败不等于整个项目失败。生成 `fallback-vNNN.json`，逐张记录 `source`、两次尝试、失败原因和使用的连续微动类型，再继续完成片头和视觉审核包。不得静默遗漏图片，不得冒充真实画面内运动。只有全部图片都因认证、模型或额度不可用而失败时，才把计划总模式写为 `ffmpeg_fallback`；用户明确要求 Grok 不得回退时设为 `blocked`。

## 产物契约

```text
09-Grok视频/
├─ oauth-check-vNNN.json
├─ grok-video-plan-vNNN.json
├─ fallback-vNNN.json
└─ vNNN/
   ├─ shot-NN-request.json
   ├─ shot-NN-raw.mp4
   ├─ shot-NN-final.mp4
   └─ shot-NN-qc.json
```

`oauth-check-vNNN.json` 最少包含：

```json
{
  "auth_mode": "membership_oauth_only",
  "billing_mode": "subscription_allowance",
  "api_key_fallback": false,
  "auto_top_up": false,
  "checked_at_utc": "2026-08-01T00:00:00Z",
  "logged_in": true,
  "refresh_succeeded": true,
  "scope_ok": true,
  "models": ["video-model-id"],
  "status": "available"
}
```

`grok-video-plan-vNNN.json` 最少包含 `mode`、`model`、`timing_basis` 和 `selected_shots`。原始生成阶段使用 `timing_basis: script_estimated`，每项至少包含 `id`、`source`、`script_segment_ids`、`narration_text`、`estimated_voice_start`、`estimated_voice_end`、`raw_duration_bucket_seconds`、`status`、`attempts` 和 `video_started_at_utc`。四分支汇合后改为 `timing_basis: voice_actual`，补齐 `voice_start`、`voice_end`、`target_duration_seconds`、最终 `output` 和 `qc`；这些字段必须和生图记录及 `timing-bind-vNNN.json` 一致。失败项使用 `status: fallback`。部分镜头回退时使用 `mixed`，全部回退时 `model` 为 `null` 并使用 `ffmpeg_fallback`。`fallback-vNNN.json` 逐张记录 `source`、`reason_code`、`reason_detail` 和 FFmpeg 微动类型。

官方对接参考：

- `https://docs.x.ai/developers/rest-api-reference/inference/videos`
- `https://docs.x.ai/developers/rest-api-reference/inference/models`
- `https://docs.x.ai/developers/model-capabilities/video/generation`
- `https://docs.x.ai/grok/faq`
