# 事件驱动并行生产规格

## 目录

- [两个阶段](#两个阶段)
- [唯一前置屏障](#唯一前置屏障)
- [调度模型](#调度模型)
- [实时进度](#实时进度)
- [核心依赖图](#核心依赖图)
- [逐素材推进](#逐素材推进)
- [运行记录](#运行记录)
- [审核规则](#审核规则)

## 两个阶段

前期只完成主题、情绪方向、逐字稿和分镜语义，用户确认后生成唯一的剧本锁。后期是一个连续的并行生产阶段：系统维护依赖图和就绪队列，任何任务的依赖满足后立即执行，不等待同组其他素材。

## 唯一前置屏障

后期生产只能依赖已确认的 `script-vNNN.json`。先生成 `03-逐字稿/script-lock-vNNN.json`：

```json
{
  "script": "03-逐字稿/script-v001.json",
  "script_sha256": "64位小写哈希",
  "segment_ids": ["viewer-expression-01"],
  "timing_basis": "script_estimated",
  "locked_at_utc": "2026-08-02T08:00:00Z"
}
```

剧本锁定后不得在后期任务内部改文案。文案变化时生成新版本，旧运行和旧后代任务全部标记 `stale`。

## 调度模型

使用 `dependency_ready_queue`，不要把四个资源组误当成四条必须整体完成的流水线。`voice`、`body_visual`、`opening`、`subtitle_music` 只用于资源归类和进度展示；真正调度粒度是任务节点。

任务状态使用 `pending`、`running`、`completed`、`fallback`、`blocked` 或 `stale`。调度循环固定为：

1. 找出所有依赖均为 `completed` 或 `fallback` 的 `pending` 任务。
2. 立即并发派发全部就绪任务，不等待同资源组任务。
3. 任一任务完成后立刻重新计算就绪队列。
4. 单个任务失败时只阻塞它的后代；无依赖关系的任务继续执行。
5. 有具名回退方案时，把失败节点改为 `fallback`，立即释放后代。

任务从依赖满足到实际开始默认不得超过 30 秒。超过 30 秒必须记录限流、工具占用或授权阻塞原因，不得声称“立即推进”。

## 实时进度

每次任务进入 `running`、`completed`、`fallback`、`blocked` 或 `stale` 后，立即更新生产记录并运行：

```bash
python3 <skill_root>/scripts/render_progress.py \
  --pipeline <project>/07-分镜/parallel-pipeline-vNNN.json \
  --json-output <project>/07-分镜/progress-state-vNNN.json \
  --markdown-output <project>/07-分镜/progress-vNNN.md
```

JSON 是页面和自动化的实时数据源，Markdown 是本地可读面板。两份文件都必须原子替换，禁止让页面读到半个 JSON。进度至少展示：

- 当前阶段与任务完成数，不只展示一个模糊百分比。
- 四个资源组的完成、运行、等待和阻塞数量。
- 每个 `shot-NN` 当前完成到图片、质检、原始视频还是最终视频。
- 正在执行、依赖已满足、仍在等待、最近完成和发生回退的任务。

Codex 执行时还必须通过 commentary 实时向用户展示。任务状态变化时立即更新；长任务没有状态变化时，每 60 秒发送一次心跳。单次更新保持简短，例如：

```text
生产进度 58%（7/12）
正在：shot-02.video_raw、voice.generate
刚完成：shot-01.video_raw
已就绪：shot-01.video_final（等待 timing.bind 时不列为已就绪）
阻塞：无
```

进度消息只报告真实落盘状态，禁止用预计完成冒充完成，也不得为了展示进度中断正在运行的任务。

## 核心依赖图

```text
script-lock
├─ voice.generate ────────────────┐
│                                 ├─ timing.bind
├─ subtitle.content ──────────────┤
├─ bgm.prepare ───────────────────┤
├─ opening.assets ────────────────┤
└─ shot-NN.image                  │
   └─ shot-NN.image_qc            │
      └─ shot-NN.video_raw        │
         └────────────────────────┴─ shot-NN.video_final

timing.bind + subtitle.content ───── subtitle.timed
voice.generate + bgm.prepare ─────── audio.mix
opening.assets + timing.bind ─────── opening.final
全部 final 节点 ──────────────────── final.assembly
```

其中：

- `shot-NN.image` 只依赖剧本锁和该镜头语义，不依赖配音成品。
- `shot-NN.image_qc` 只依赖自己的图片。
- `shot-NN.video_raw` 只依赖自己的图片质检，不等待其他图片。
- `shot-NN.video_final` 才同时依赖自己的原始视频和 `timing.bind`。
- 字幕内容、BGM 预处理、片头素材可以提前完成；只有最终时码、混音和装配依赖真实配音。

## 逐素材推进

所有正文图和片头遮罩图可以同时提交，但“批次”只用于请求管理，不是执行屏障：

1. 任一正文图片返回，立即质检该图片。
2. 通过后立即生成该镜头的 6 秒或 10 秒原始动态视频。
3. 其他图片仍在生成时，已经完成的镜头继续向前推进。
4. 图片失败只进入失败集合，不阻塞其他镜头。
5. 配音真实时码返回后，已经完成原始视频的镜头立即规格化；尚未完成的镜头稍后自行进入该节点。

## 运行记录

写入 `07-分镜/parallel-pipeline-vNNN.json`：

```json
{
  "mode": "event_driven_dag_after_content_lock",
  "scheduler": "dependency_ready_queue",
  "script_lock": "03-逐字稿/script-lock-v001.json",
  "dispatch_policy": "dispatch_when_dependencies_completed",
  "progression_policy": "advance_each_asset_immediately",
  "failure_scope": "descendants_only",
  "progress": {
    "json": "07-分镜/progress-state-v001.json",
    "markdown": "07-分镜/progress-v001.md",
    "heartbeat_seconds": 60
  },
  "tasks": [
    {
      "id": "voice.generate",
      "resource_group": "voice",
      "depends_on": [],
      "status": "completed",
      "started_at_utc": "2026-08-02T08:00:01Z",
      "completed_at_utc": "2026-08-02T08:03:10Z"
    },
    {
      "id": "shot-01.image",
      "resource_group": "body_visual",
      "depends_on": [],
      "status": "completed",
      "started_at_utc": "2026-08-02T08:00:02Z",
      "completed_at_utc": "2026-08-02T08:02:00Z"
    },
    {
      "id": "shot-01.image_qc",
      "resource_group": "body_visual",
      "depends_on": ["shot-01.image"],
      "status": "completed",
      "started_at_utc": "2026-08-02T08:02:01Z",
      "completed_at_utc": "2026-08-02T08:02:05Z"
    },
    {
      "id": "shot-01.video_raw",
      "resource_group": "body_visual",
      "depends_on": ["shot-01.image_qc"],
      "status": "completed",
      "started_at_utc": "2026-08-02T08:02:06Z",
      "completed_at_utc": "2026-08-02T08:04:30Z"
    },
    {
      "id": "timing.bind",
      "resource_group": "voice",
      "depends_on": ["voice.generate"],
      "status": "completed",
      "started_at_utc": "2026-08-02T08:03:11Z",
      "completed_at_utc": "2026-08-02T08:03:13Z"
    },
    {
      "id": "shot-01.video_final",
      "resource_group": "body_visual",
      "depends_on": ["shot-01.video_raw", "timing.bind"],
      "status": "completed",
      "started_at_utc": "2026-08-02T08:04:31Z",
      "completed_at_utc": "2026-08-02T08:04:50Z"
    }
  ],
  "join": {
    "status": "completed",
    "actual_timing_source": "05-配音/timing-v001.json",
    "timing_binding": "07-分镜/timing-bind-v001.json",
    "joined_at_utc": "2026-08-02T08:08:21Z"
  }
}
```

每个进入成片的镜头都必须包含 `image → image_qc → video_raw → video_final` 四个节点。验证器检查依赖存在、时间顺序、就绪延迟、独立任务真实重叠和最终装配时机。没有这些事件记录，不得声称已并行加速。

## 审核规则

后期生产是一个连续阶段，中间不因某个资源组完成而请求确认。声音和视觉素材都完成、真实时码已绑定并生成联合预览后，才把 `sound_package` 与 `visual_package` 一起设为 `awaiting_confirmation`。用户确认后进入时间轴和最终成片。
