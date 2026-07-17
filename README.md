# anime-subtitle-exchange

## Overview

BD、REMUX 这类高质量片源经常不带外挂字幕，而 WebRip / WEB-DL 之类的流媒体压制通常有字幕组的内封或内嵌轨。这个 Skill 做的事就是：从流媒体片源里把字幕轨抠出来，贴到目标视频旁边，PotPlayer 通过同名规则自动加载。

源字幕的样式和时间轴原样保留，不做任何修改。依赖只有 ffmpeg 和 Python 标准库，全程走本地路径（比如 CloudDrive2 挂载的 `L:` 盘），不涉及网络传输。

## Trigger Words

**English:** subtitle bridge, subtitle mounting, subtitle extraction, subtitle transfer.

**中文（字面触发别名）:** 字幕桥接、字幕挂载、字幕提取、字幕搬家、字幕互通.

## Applicable Scenarios

- 目标视频是 BD、REMUX、RAW 这类没有外挂字幕的高质量片源
- 本地或挂载盘上有带字幕的流媒体压制（常见标记：`WebRip`、`WEB-DL`、`ABEMA`、`B-Global`）

## Workflow

```
[1] 输入目标视频路径
[2] 在本地或挂载盘上找匹配的字幕源
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

## API Reference

### `ffprobe_streams(video_path)`

探测视频文件的所有流信息。

```python
import subprocess, json

def ffprobe_streams(video_path: str) -> list:
    """Return all stream objects."""
    ffprobe = '<FFPROBE_BIN>'
    cmd = [ffprobe, '-v', 'error', '-show_streams', '-of', 'json', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return json.loads(result.stdout)['streams']
```

### `choose_best_subtitle(streams, source_filename)`

返回优先级最高的字幕轨索引。

```python
def choose_best_subtitle(streams: list, source_filename: str) -> int:
    """Return the index of the highest-priority subtitle track."""
    subtitles = [s for s in streams if s['codec_type'] == 'subtitle']
    SUBTITLE_TYPE_PRIORITY = {
        '简日双语': 1,
        '繁日双语': 2,
        '简繁日内封': 3,
        '简繁日内封字幕': 3,
        '简日内嵌': 4,
        '繁日内嵌': 5,
        '简繁内封': 6,
        '简体双语': 99,
    }
    for st_name, st_prio in sorted(SUBTITLE_TYPE_PRIORITY.items(), key=lambda x: x[1]):
        for sub in subtitles:
            tags = sub.get('tags', {})
            if st_name in tags.get('title', ''):
                return sub['index']
    return subtitles[0]['index'] if subtitles else None
```

### `extract_subtitle_to_ass(video_path, stream_index, output_ass)`

提取字幕轨并转为 ASS，保留源样式。

```python
def extract_subtitle_to_ass(video_path: str, stream_index: int, output_ass: str):
    """Extract a subtitle track to ASS while preserving source styles."""
    ffmpeg = '<FFMPEG_BIN>'
    cmd = [
        ffmpeg, '-y',
        '-i', video_path,
        '-map', f'0:s:{stream_index}',
        '-c:s', 'ass',
        output_ass
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg failed: {result.stderr[:500]}')
    return output_ass
```

### `mount_ass_to_target(target_video, ass_path)`

把 ASS 文件复制到目标视频旁边，靠同名规则让播放器自动加载。

```python
import shutil
from pathlib import Path

def mount_ass_to_target(target_video: str, ass_path: str):
    """Copy an ASS file beside the target video using the same-name rule."""
    target_dir = Path(target_video).parent
    target_stem = Path(target_video).stem
    dest = target_dir / f'{target_stem}.ass'
    shutil.copy(ass_path, dest)
    return str(dest)
```

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
├── SKILL.md                  # 触发提示词和概要
├── README.md                 # 本文件
└── examples/
    └── default_workflow.md   # 完整示例
```
