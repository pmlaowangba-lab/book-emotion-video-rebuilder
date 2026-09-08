# book-emotion-video-rebuilder

从一本真实书籍出发，自动生成 **情绪读书短视频** 的 Agent Skill。复刻陌言式情绪文案结构 +「十二」式毛笔遮罩片头，输出 1080×1440 竖版成片与可编辑剪映草稿。

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)

**支持：** Claude Code、Codex、Cursor 及其他支持 Skills 的 Agent。

---

## 这条流水线解决什么问题

传统做一条读书短视频，要在文案、配音、分镜、生图、动效、字幕、配乐之间来回切换，且音画很难严格对齐。

本 Skill 把整条链路收成 **可恢复的项目目录**：

```text
选书核验 → 情绪提炼 + 两字遮罩确认 → 逐字稿锁定
    → 并行：TTS 配音 / 分镜生图 / Grok 轻动态 / 片头轮播
    → 时间轴 → 1080×1440 MP4 + 剪映草稿
```

核心约束（不可放宽）：

| 维度 | 规则 |
| --- | --- |
| 画幅 | 1080×1440、30fps、H.264/AAC |
| 语速 | 固定 4.56 汉字/秒，成片 ≤ 60 秒 |
| 片头遮罩 | 仅两个汉字的毛笔 alpha mask，关卡 1 确认后后期复用 |
| 正文画面 | 人物侧脸 + 明亮自然山水，**禁止城市/室内** |
| 书封 | 真实封面轮播，念书名时保持封面同页 |
| BGM | 仅用户本地曲库，不开网络下载 |

---

## 快速开始

### 1. 安装 Skill

```bash
# Claude Code / Codex
git clone https://github.com/pmlaowangba-lab/book-emotion-video-rebuilder.git
# 将目录链接或复制到你的 skills 路径

# 或 skills.sh（若已上架）
npx -y skills add pmlaowangba-lab/book-emotion-video-rebuilder
```

### 2. 配置依赖

```bash
# TTS：复制模板并填入火山引擎凭据
cp assets/volcengine.env.example assets/volcengine.env

# 字体：下载杨任东竹石体 Heavy 放入 assets/fonts/
# BGM：按 assets/bgm-library/README.md 添加本地 MP3
# 片头遮罩视频：按 assets/opening-mask-video-library/manifest.json 从 Pexels 下载
```

### 3. 创建项目

在 Agent 中说：

```text
用 book-emotion-video-rebuilder 为《活着》做一条情绪读书视频
```

或手动初始化：

```bash
python3 scripts/init_project.py \
  --output-root ./output \
  --title "活着" \
  --author "余华"
```

### 4. 审核节奏

默认 **3 次人工确认**：

1. **内容包** — 逐字稿 + 两字遮罩确认图
2. **声音与视觉联合包** — 配音、分镜图、片头素材
3. **双交付包** — 高清 MP4 + 剪映草稿

---

## 流水线结构

```text
<书名>_YYYYMMDD_情绪读书视频/
├─ 01-书籍资料/          # 封面、ISBN、观点来源
├─ 02-情绪提炼/          # 情绪地图、两字遮罩 alpha
├─ 03-逐字稿/            # 锁定稿、原创性检查
├─ 04-声音设计/          # 音色、情绪指令
├─ 05-配音/              # TTS、时码 timing
├─ 06-配乐音效/          # BGM 选择、混音
├─ 07-分镜/              # 分镜计划、并行批次
├─ 08-正文画面/          # 独立分镜图 shot-NN.png
├─ 08A-片头遮罩素材/     # 海鸥海面默认遮罩源
├─ 09-Grok视频/          # 图生视频计划与 QC
├─ 10-片头字幕/          # 轮播卡、遮罩展开、字幕
├─ 11-时间轴/            # timeline JSON
├─ 12-预览/              # QC 预览
└─ 13-剪映草稿/          # 可继续编辑的草稿
```

规格文档在 [`references/`](references/)，入口规则在 [`SKILL.md`](SKILL.md)。

---

## 案例展示

下面两个案例来自真实生产项目，素材已脱敏整理到 [`examples/`](examples/)，展示 **文案 → 遮罩 → 分镜 → 成片预览** 全链路。

### 案例 1：《活着》

| 项目 | 内容 |
| --- | --- |
| 遮罩关键词 | **活着**（两字毛笔 alpha，关卡 1 确认） |
| 情绪类型 | 治愈型 — 重新有力气把今天过完 |
| 口播字数 | ~200 字，语速 4.56 字/秒 |
| 正文镜头 | 5 组人物侧脸 + 自然山水 |

**完整口播（节选）：**

> 愿你看完这段，重新有力气，把今天过完。
>
> 今天分享的是——《活着》。
>
> 有时候你已经累到不想解释。消息不想回，委屈不想说，连难过都要挑一个没人看见的时候，一个人安静地咽回去。
>
> ……能把普通的一天继续过下去，从来都不是认输，是生命在你身上还没有松手。

**流水线快照：**

| 阶段 | 产物 | 文件 |
| --- | --- | --- |
| 书籍资料 | 真实书封 | [`cover.jpg`](examples/case-01-huozhe/cover.jpg) |
| 情绪提炼 | 两字遮罩确认 | [`mask-keyword.png`](examples/case-01-huozhe/mask-keyword.png) |
| 片头 | 书名 + 封面同页 | [`target-cover-page.png`](examples/case-01-huozhe/target-cover-page.png) |
| 正文分镜 | 侧脸山水 shot-01 | [`shot-01.png`](examples/case-01-huozhe/shots/shot-01.png) |
| 正文分镜 | 侧脸山水 shot-03 | [`shot-03.png`](examples/case-01-huozhe/shots/shot-03.png) |
| 成片预览 | 18 秒带配音混音预览 | [`preview.mp4`](examples/case-01-huozhe/preview.mp4) |

<details>
<summary>查看全部正文分镜（5 张）</summary>

- [`shot-01.png`](examples/case-01-huozhe/shots/shot-01.png)
- [`shot-02.png`](examples/case-01-huozhe/shots/shot-02.png)
- [`shot-03.png`](examples/case-01-huozhe/shots/shot-03.png)
- [`shot-04.png`](examples/case-01-huozhe/shots/shot-04.png)
- [`shot-05.png`](examples/case-01-huozhe/shots/shot-05.png)

</details>

---

### 案例 2：《钢铁是怎样炼成的》

| 项目 | 内容 |
| --- | --- |
| 遮罩关键词 | **自救**（概括核心情绪结果，非书名截取） |
| 情绪类型 | 自救型 — 从拿回一个小决定开始 |
| 口播字数 | 257 汉字，估算 ~56 秒 |
| 正文镜头 | 8 组人物侧脸 + 自然山水 |

**完整口播：**

> 人被打倒以后，还能把力量一点点拿回来。
>
> 今天分享的是，《钢铁是怎样炼成的》。
>
> 真正耗尽人的，往往不是一次失败。是想说的话又咽回去，想做的事又往后推。等别人同意，等时机合适，等到最后，连自己要什么都懒得问了。
>
> 日子照常往前走，身体却越来越沉。计划写了又划掉，消息打好又删掉。一次次退让以后，连迈出第一步都觉得费劲。
>
> 可只要还愿意替自己做一个决定，就没有被生活彻底拿走。钢要经过火烧、锤打和冷却，才有扛住重量的硬度。人受过的伤不会消失，但选择还在。
>
> 今天别逼自己马上振作。把那件拖了很久、又确实想做的事，先做十分钟。这十分钟，是你亲手拿回来的决定。
>
> 力量不会一下回来。它会从这十分钟里，慢慢回到你身上。

**流水线快照：**

| 阶段 | 产物 | 文件 |
| --- | --- | --- |
| 书籍资料 | 真实书封 | [`cover.jpg`](examples/case-02-steel/cover.jpg) |
| 情绪提炼 | 遮罩预览（确认用） | [`mask-keyword.png`](examples/case-02-steel/mask-keyword.png) |
| 情绪提炼 | Alpha 蒙版原图 | [`mask-alpha.png`](examples/case-02-steel/mask-alpha.png) |
| 片头 | 书名封面页 | [`target-cover-page.png`](examples/case-02-steel/target-cover-page.png) |
| 正文分镜 | 侧脸山水 shot-02 | [`shot-02.png`](examples/case-02-steel/shots/shot-02.png) |
| 正文分镜 | 侧脸山水 shot-06 | [`shot-06.png`](examples/case-02-steel/shots/shot-06.png) |
| 成片预览 | 18 秒带配音混音预览 | [`preview.mp4`](examples/case-02-steel/preview.mp4) |

<details>
<summary>查看全部正文分镜（8 张）</summary>

- [`shot-01.png`](examples/case-02-steel/shots/shot-01.png) … [`shot-08.png`](examples/case-02-steel/shots/shot-08.png)

</details>

---

## 外部工具依赖

| 工具 | 用途 | 是否必须 |
| --- | --- | --- |
| Python 3.10+ | 脚本流水线 | 是 |
| ffmpeg | 渲染、混音、编码 | 是 |
| 火山引擎 TTS | 配音 | 是 |
| Codex / Grok image_gen | 正文分镜生图 | 推荐 |
| grok-local CLI | 图生轻动态视频 | 推荐（失败回退 ffmpeg 微动） |
| LTX-2.3 本地 | 可选图生视频通道 | 否 |
| 剪映 | 导入草稿继续编辑 | 否 |

环境检查：

```bash
python3 scripts/check_environment.py
```

---

## 目录说明

| 路径 | 说明 |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Agent 执行规则（主入口） |
| [`references/`](references/) | 文案、视觉、声音、并行流水线等规格 |
| [`scripts/`](scripts/) | 初始化、渲染、验证、剪映导出脚本 |
| [`assets/`](assets/) | 书封库、BGM 元数据、片头遮罩清单 |
| [`examples/`](examples/) | 两个完整案例的脱敏素材 |
| [`agents/openai.yaml`](agents/openai.yaml) | Codex / OpenAI 兼容接口描述 |

---

## 许可证

本项目采用 **[CC BY-NC 4.0](LICENSE)**（署名 + 非商业）。

- ✅ 个人学习、研究、非盈利内容创作
- ✅ Fork、修改、二次分发（需署名并沿用相同协议）
- ❌ 商业售卖、付费课程打包、代运营服务等商业用途

案例中的书籍封面、配乐版权归各自权利人所有，仅作流水线演示，不构成授权转载。

---

## 作者

[pmlaowangba](https://github.com/pmlaowangba-lab) — AI 产品经理实战导师

如有问题或改进建议，欢迎提 Issue。
