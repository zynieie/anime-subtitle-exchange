# anime-subtitle-exchange

## Overview

BD、REMUX 这类高质量片源经常不带外挂字幕，而 WebRip / WEB-DL 之类的流媒体压制通常有字幕组的内封或内嵌轨。这个 Skill 做的事就是：从流媒体片源里把字幕轨抠出来，贴到目标视频旁边，PotPlayer 通过同名规则自动加载。

源字幕的样式和时间轴原样保留，不做任何修改。依赖只有 ffmpeg 和 Python 标准库，全程走本地路径（比如 CloudDrive2 挂载的 `L:` 盘），不涉及网络传输。

## Trigger Words

**English:** subtitle bridge, subtitle mounting, subtitle extraction, subtitle transfer.

**中文（字面触发别名）:** 字幕桥接、字幕挂载、字幕提取、字幕搬家、字幕互通.

## Workflow

```
[1] 输入目标视频路径
[2] 在 <BANGUMI_DIR> 下找匹配的字幕源
[3] ffprobe 探测字幕轨
[4] 按优先级选最佳轨
[5] ffmpeg 提取并转 ASS
[6] 改名为 <target_video_stem>.ass，复制到目标视频旁边
[7] 播放器自动加载
```

## 字幕轨优先级

匹配逻辑：拿下面的标签去对比字幕流的 `tags.title` 字段。这些标签是字幕组打的，必须原样保留，不能改。

| 等级 | 标签（原样保留） | 含义 |
|---|---|---|
| S | `简日双语`, `繁日双语`, `简繁日内封`, `简繁日内封字幕` | 中日双语，外挂轨 |
| A | `简日内嵌`, `繁日内嵌` | 中日双语，内嵌轨 |
| B | `简繁内封`, `简繁内封字幕` | 纯中文字幕，外挂轨 |
| C | `简体内嵌`, `繁体内嵌` | 纯中文字幕，内嵌轨 |

完整标签表在代码内部，不对外公开。

## 字幕组优先级

字幕组之间的排名不写在这里——列出来容易引战，而且对实际使用没有帮助。具体实现在 `bangumi_magnet.py` 的 `SUBGROUP_PRIORITY` 里，只在字幕类型优先级相同时才用到。

## 命名规则

输出文件名：`<target_video_stem>.ass`，放在目标视频同目录下，PotPlayer 靠同名规则自动拾取。

## 异常处理

| 情况 | 怎么办 |
|---|---|
| 目标视频不存在 | 直接停，前置条件不满足 |
| 字幕源不存在 | 让用户换一个源 |
| 字幕源是 RAW | 让用户换（RAW 一般没字幕） |
| 字幕源有硬字幕 | 让用户换（OCR 不做） |
| 时长差 > 30s | 警告一下，不中断流程 |
| 多个候选字幕轨 | 列出来让用户选 |
| ffprobe 挂了 | 报错，跳过当前文件 |
| ffmpeg 转换失败 | 保留原文件，报告失败原因 |

## Limitations

不改字幕样式（源文件的 Style 块和时间轴原样保留），不做硬字幕 OCR，不转码视频，不自动搜索网络字幕源，不自动收集 ASS `{\fn...}` 引用的外挂字体。

## 依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| `ffmpeg` | 7.0.2+ | 视频/字幕处理 |
| `ffprobe` | 7.0.2+ | 流信息探测 |
| Python | 3.8+ | 脚本运行时 |
| Python 标准库 | 内置 | `subprocess`, `shutil`, `re`, `json`, `pathlib` |

路径占位符：
- `<FFMPEG_BIN>` — ffmpeg 可执行文件的绝对路径
- `<FFPROBE_BIN>` — ffprobe 可执行文件的绝对路径
- `<BANGUMI_DIR>` — 存放目标视频和字幕源的根目录

## 项目结构

```
anime-subtitle-exchange/
├── SKILL.md                  # 本文件
├── README.md                 # API 参考和详细文档
└── examples/
    └── default_workflow.md   # 完整示例
```
