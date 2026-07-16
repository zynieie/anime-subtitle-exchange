# Subtitle-Bridge · 详细文档

> 版本：v1 · 2026-07-17
> 状态：企划中（老公反馈已整合，待最终命名）

## 🗣️ 白话讲讲（老公对完全不懂技术的朋友解释时用）

> 想象你买了**筷子**（目标视频，可以是 BD / RAW / 屏幕录像 / 其他），但吃饭还得有**饭**（字幕）。
>
> 如果只下视频没有字幕，那筷子没饭吃——空欢喜。
>
> 流媒体版（WebRip / WEB-DL）通常自带**中文字幕**（因为字幕组做了外挂或内嵌）。
>
> 本 skill = 把流媒体版的"饭"（字幕）**挖出来**，**盛到筷子旁边**（同名挂载到目标视频同目录）。
>
> PotPlayer（老公的播放器）会自动加载这个字幕，按一下就能看 目标视频 + 中英日字幕。
>
> **目标端很灵活**：BD / RAW / 屏幕录像 / 其他原画——都能挂！

---

## 🎯 完整 Skill 流程（7 步）

### Step 1 — AI 问老公：看目标视频（BD）还是流媒体？

```
AI: 老公要看 目标视频（默认 BD） 还是 流媒体？
    [1] 目标视频（BD / RAW / 屏幕录像）— 高画质，需要外挂字幕
    [2] 流媒体 — 自带字幕，但画质 1080p 封顶
    选哪个？直接回数字就行。
```

**默认行为**：选目标视频（老公原话："默认看的是 BD"）

---

### Step 2 — 老公提供 BD 路径 → AI 用 ffprobe 解析

老公输入：
```
L:\番剧\[DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][1080P][BDRip][HEVC-10bit][FLAC][MKV]
```

**AI 调用 ffprobe**：

依赖：
- **ffprobe**：`C:\Program Files\ffmpeg-7.0.2-essentials_build\bin\ffprobe.exe`
- Python 标准库：`subprocess`, `json`

代码片段：
```python
import subprocess, json, re
from pathlib import Path

def probe_bd(bd_path: str) -> dict:
    """解析 BD 文件的集数列表 + 时长 + 字幕信息"""
    cmd = [
        r'C:\Program Files\ffmpeg-7.0.2-essentials_build\bin\ffprobe.exe',
        '-v', 'error',
        '-print_format', 'json',
        '-show_format', '-show_streams',
        bd_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return json.loads(result.stdout)

def parse_episodes(bd_path: str) -> list:
    """从 BD 文件名解析集数（10-17TV+特典映像 → [10..17]）"""
    name = Path(bd_path).stem
    m = re.search(r'\[(\d+)-(\d+)(?:TV)?\]', name)
    if m:
        return list(range(int(m.group(1)), int(m.group(2)) + 1))
    # 单集：找 [01] [02] 这种
    m2 = re.search(r'\[(\d+)\]', name)
    if m2:
        return [int(m2.group(1))]
    return []
```

跨平台注意：
- Windows：`r'C:\Program Files\ffmpeg-7.0.2-essentials_build\bin\ffprobe.exe'`
- macOS/Linux：`/usr/local/bin/ffprobe` 或 `ffprobe`（PATH 找）

---

### Step 3 — AI 引导到字幕源

**AI 自动查老公 L 盘**（可能不用问老公）：

```python
def find_streaming_in_Lbang(bd_basename: str, l_bang_dir: str = r'L:\番剧') -> list:
    """在 L:\番剧 下找同名流媒体版（关键词匹配）"""
    candidates = []
    keywords = ['LoliHouse', 'ABEMA', 'WebRip', 'WEB-DL']  # 流媒体特征
    # 简单版：从 bd_basename 提取关键词（如 "Aparida"、"A-Rank Party"）
    search_keys = extract_search_keys(bd_basename)
    
    for f in Path(l_bang_dir).iterdir():
        if any(kw in f.name for kw in keywords):
            if any(sk in f.name for sk in search_keys):
                candidates.append(str(f))
    return candidates
```

**AI 给老公报告**：
```
AI: 找到 2 个可能的字幕源（流媒体版）：
    [1] [LoliHouse] Aparida [01-24][WebRip 1080p HEVC-10bit AAC]   ← 整季+简繁内封
    [2] [Dynamis One] A-Rank Party... - 09 (ABEMA...).mp4   ← 单集日语外挂
    
    老公要用哪个？
```

**如果没找到**：
```
AI: L 盘上没找到流媒体版。老公要不要换源？
    - 去蜜柑找（推荐 LoliHouse/桜都/喵萌 这几个字幕组的字幕版）
    - 去 nyaa 找（海外组 BD + 内嵌字幕）
    - 都不行的话，本 skill 不适合这部番
```

---

### Step 4 — AI 用 ffmpeg 提取字幕

**字幕源选择（基于 Q6 "中日优先"）**：

```python
# 字幕类型优先级（S 级 = 中日）
SUBTITLE_TYPE_PRIORITY = {
    '简日双语': 1,    # S 级：简中+日语
    '繁日双语': 2,
    '简繁日内封': 3,
    '简繁日内封字幕': 3,
    '简日内嵌': 4,    # A 级
    '繁日内嵌': 5,
    '简繁内封': 6,    # B 级（仅中文外挂）
    '简体双语': 99,   # D 级（简中+英语，不是日语！）
}

# 字幕组品牌优先级（红榜）
SUBGROUP_PRIORITY = {
    '桜都字幕组': 1,
    '喵萌奶茶屋': 2,
    'LoliHouse': 3,
    '千夏字幕组': 4,
    '绿茶字幕组': 5,
    # ...
}

def choose_best_subtitle(streaming_path: str) -> int:
    """选择最优字幕流（S 级优先，同级字幕组品牌优先）"""
    streams = probe_bd(streaming_path)
    subtitles = [s for s in streams['streams'] if s['codec_type'] == 'subtitle']
    
    # 优先：中日 S 级 → A 级 → B 级
    for st_name, st_prio in sorted(SUBTITLE_TYPE_PRIORITY.items(), key=lambda x: x[1]):
        for sub in subtitles:
            tags = sub.get('tags', {})
            title = tags.get('title', '')
            if st_name in title:
                # 同类型内，选字幕组品牌最好的
                sg = get_subgroup_from_filename(streaming_path)
                if sg is None or SUBGROUP_PRIORITY.get(sg, 50) <= 5:
                    return sub['index']
    return subtitles[0]['index'] if subtitles else None
```

**ffmpeg 提取**：

```python
def extract_subtitle(video_path: str, stream_index: int, output_path: str):
    """提取字幕到 ASS 文件（保留原样式）"""
    ffmpeg = r'C:\Program Files\ffmpeg-7.0.2-essentials_build\bin\ffmpeg.exe'
    cmd = [
        ffmpeg, '-y',
        '-i', video_path,
        '-map', f'0:s:{stream_index}',  # 字幕流索引
        '-c', 'copy',                     # 不重编码，保留原样式
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg failed: {result.stderr[:500]}')
    return output_path
```

---

### Step 5 — 导出 ASS（保留字幕源原样）

**不修改字幕样式**（老公原话："当前版本字幕样式完全不需要修改，就按照字幕源的"）

代码片段（上面 `extract_subtitle` 已经做了）：
- `-c copy` 保留原始 ASS 格式
- 不删除任何 Style 行
- 不修改时间轴
- 老公以后想"复刻"样式时，可以把 ASS 喂给 AI

---

### Step 6 — 重命名 + 挂载到 BD 同目录

**命名规则**（老公原话 Q5）：`<BD 主文件名>.ass`（仅扩展名变化）

**集数对应**（Q7）：流第一集 ASS 对 BD 第一集（一对一）

```python
def mount_subtitle_to_bd(bd_path: str, ass_path: str, episode_num: int = None):
    """重命名 ASS 为 BD 主文件名，挂到 BD 同目录"""
    bd_dir = Path(bd_path).parent
    bd_stem = Path(bd_path).stem  # 不含扩展名
    
    # 如果是多集 BD（如 10-17TV+特典），且流媒体是单集：
    # 把单集 ASS 复制 N 份到 BD 同目录
    if episode_num is None:
        # 整季挂一份（BD 是整季的话）
        dest = bd_dir / f'{bd_stem}.ass'
        shutil.copy(ass_path, dest)
        return str(dest)
    
    # 单集对应（如果 BD 是单集）
    dest = bd_dir / f'{bd_stem}.ass'
    shutil.copy(ass_path, dest)
    return str(dest)
```

**老公给的示例**：
```
BD: [DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][1080P][BDRip][HEVC-10bit][FLAC][MKV]
ASS 输出: [DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][1080P][BDRip][HEVC-10bit][FLAC].ass

位置：L:\番剧\[DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][1080P][BDRip][HEVC-10bit][FLAC][MKV] 同目录
```

---

### Step 7 — 报告老公

```
AI: ✅ 完成！
    BD: L:\番剧\[DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][...][MKV]
    ASS: L:\番剧\[DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][...].ass
    
    字幕类型: 简繁内封（仅中文，B 级）
    字幕组: LoliHouse
    时长匹配: ✅ (BD 23:41 / 流媒体 23:39，差 2 秒)
    
    PotPlayer 打开 BD 即可看到中文字幕 ✅
    
    老公可以：
    - 直接看（BD + 中文字幕）
    - 如果想要日语外挂，从 LoliHouse 整季版里提日语外挂（虽然 LoliHouse 没有日语）
    - 老公说 BD 缺的小语种可以加，本 skill 也支持
    
    继续下一部番？
```

---

## ⚠️ 失败场景（老公 Q9 原话整合）

| 场景 | AI 处理 | 给老公的话 |
|---|---|---|
| BD 完全缺失 | 不是受众 | "老公需要先下 BD，本 skill 不适合没有 BD 的情况" |
| 流媒体版缺失 | 提示换源 | "L 盘没找到流媒体版，要不要去蜜柑找字幕版？" |
| 流媒体是 RAW | 提示换源 | "RAW 没字幕，需要换带字幕的版本" |
| 流媒体是硬字幕 | 提示换源 | "硬字幕 OCR 暂不支持，换个外挂字幕版本" |
| 时长差异过大 | 警告 | "BD EP01 时长 23:41 / 流媒体 23:05，差异 36 秒，确认是否同集？" |
| L 盘有多个流媒体版 | 让老公选 | "找到 3 个流媒体版：[1]/[2]/[3]，老公选哪个？" |

**白话比喻**（老公 Q9 原话）：
- "不能买了枪无敌人可大无猎可售" → 没 BD 视频，没法做
- "不能买了筷子无饭可吃" → 没字幕源，没法做
- "不能买了电脑无电可用" → 有 BD 没流媒体版，没法做
- "什么都没有就不是本 skill 的受众" → 直接拒绝，提示换源

---

## 🔗 关键技术决策

| 决策点 | 选择 | 来源 |
|---|---|---|
| 字幕类型优先级 | S 级（中日）> A 级 > B 级 | `bangumi_magnet.py` |
| 字幕组品牌优先级 | 桜都 > 喵萌 > LoliHouse > ... | `bangumi_magnet.py` |
| 默认目标 | BD | 老公原话 |
| 默认字幕 | 中日（S 级） | 老公 Q6 原话 |
| ASS 命名 | `<BD主文件名>.ass` | 老公 Q5 原话 |
| 字幕样式 | 不修改 | 老公 Q8 原话 |
| 集数对应 | 1:1（不齐取交集） | 老公 Q7 原话 |
| 失败处理 | 不是受众就拒绝 | 老公 Q9 原话 |

---

## 🛠️ 技术栈（老公要求"塞代码 + 标记库"）

| 工具 | 用途 | 路径 / 安装 |
|---|---|---|
| **ffmpeg 7.0.2** | 视频/字幕处理 | `C:\Program Files\ffmpeg-7.0.2-essentials_build\bin\ffmpeg.exe` |
| **ffprobe** | 视频信息查询 | 同上目录的 `ffprobe.exe` |
| **Python 3.8+** | 自动化脚本 | 系统 PATH |
| **标准库** | `subprocess`, `os`, `re`, `json`, `shutil`, `glob`, `pathlib` | 内置 |
| **可选：pymediainfo** | 更稳定的 MKV 解析 | `pip install pymediainfo` |
| **PotPlayer** | 老公的播放器（同名挂载规则） | 已装 |

---

## 📚 完整示例

### 示例：Aparida BD 挂字幕

**输入**（老公）：
```
L:\番剧\[DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][1080P][BDRip][HEVC-10bit][FLAC][MKV]
```

**AI 自动执行**：
1. ffprobe 解析 → 10-17 集 + 特典映像，时长约 23:41/集
2. 在 L 盘找到 `[LoliHouse] Aparida [01-24][WebRip 1080p HEVC-10bit AAC]`（整季+简繁内封）
3. ffmpeg 提取 LoliHouse 的简繁内封字幕 → ASS
4. 重命名为 `<BD 主文件名>.ass`，挂到 BD 同目录
5. 报告老公 ✅

**输出**：
```
L:\番剧\[DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][1080P][BDRip][HEVC-10bit][FLAC][MKV]
L:\番剧\[DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][1080P][BDRip][HEVC-10bit][FLAC].ass  ← 新增
```

PotPlayer 打开 BD → 自动加载 .ass → 中文字幕显示 ✅

---

## 🔄 持续改进

老公说"塞代码 + 标记库"是为了**兼容不同电脑**。本 skill 的代码片段都是标准库 + ffmpeg，理论上跨平台可跑。

**已知限制**（待解决）：
- 暂不支持硬字幕 OCR
- 暂不支持自动找字幕源（老公提供）
- 多语种合并（中日英 4 种语种合并到一个 ASS）暂未实现

**下一版计划**：
- v2：加上实战案例 `examples/aparida_demo.md`
- v3：把代码片段整理成可独立运行的 `scripts/` 目录

---

## 📂 项目文件

```
D:\project\Skills\追番skills\skill 企划\bd-subtitle-bridge\
├── SKILL.md                      ← skill 触发提示（短）
├── README.md                     ← 本文件（详细流程 + 代码）
└── examples/
    └── (待添加) aparida_demo.md  ← 实战案例
```

**企划过程文档**（保留作为参考）：
```
D:\project\Skills\追番skills\skill 企划\_讨论\
├── 01_爱芮的问题.md      ← 第一轮问题（Q1-Q4）
├── 02_爱芮的复述.md      ← 老公反馈后的复述
├── 03_爱芮的追问.md      ← 第二轮问题（Q5-Q9）
├── 04_老公原话记录.md    ← Q5-Q9 原话完整保留
└── 05_爱芮拆解分析.md    ← 基于原话的结构化拆解
```