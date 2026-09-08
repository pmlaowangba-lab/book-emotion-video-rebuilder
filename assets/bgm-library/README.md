# BGM 曲库

本 Skill 的 BGM **只允许使用用户自行提供的本地文件**，见 `library.json` 中的 `source_scope: user_provided_local_file`。

## 首次使用

1. 将你合法持有的 MP3 文件放入本目录。
2. 按 `library.json` 中 `tracks` 数组的格式追加条目，填写 `id`、`title`、`artist`、`file`、`emotion_tags` 等字段。
3. 确保 `status` 为 `available`，且 `file` 指向真实存在的本地路径。

开源仓库**不包含**任何音乐文件。案例视频中的配乐来自老王本地曲库，仅供演示流水线结构。
