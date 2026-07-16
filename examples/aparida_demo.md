# 实战案例 · 通用模板

> 创建：2026-07-17
> 验证：✅ **BD 路径下出现正确的 `.ass` = 成功**

## 🎯 实战目标

把带字幕的流媒体版字幕，提取为 ASS 文件，挂到目标视频（BD / RAW / 其他）同目录。

---

## 📥 输入

### 目标视频（老公提供）

老公示例（已验证可用）：
```
<BD_DIR>/
├── [<RELEASE_GROUP>][<TITLE>][<EP01>][1080P][BDRip][HEVC-10bit][FLACx2].mkv
├── [<RELEASE_GROUP>][<TITLE>][<EP02>][1080P][BDRip][HEVC-10bit][FLAC].mkv
├── ...
```

### 字幕源（自动查 L 盘）

```
<STREAM_DIR>/
├── [<SUBGROUP>] <TITLE> - <EP> [WebRip 1080p HEVC-10bit AAC SRTx2].mkv
├── [<SUBGROUP>] <TITLE> - <EP> [WebRip 1080p HEVC-10bit AAC SRTx2].mkv
├── ...
```

> ⚠️ 流媒体版标题里通常有字幕组 + 集数 + WebRip/ABEMA 等关键词

---

## 🔧 关键工具

| 工具 | 真实路径（老公 L 盘环境） |
|---|---|
| **ffmpeg** | `C:\Program Files\ffmpeg-7.0.2-essentials_build\ffmpeg-7.0.2-essentials_build\bin\ffmpeg.exe` |
| **ffprobe** | 同上目录的 `ffprobe.exe` |

---

## 🚀 7 步执行（老公"跑默认"流程）

### Step 1：AI 问老公 → BD（默认）

> 老公原话："默认看的是 BD"

### Step 2：老公提供目标视频路径

```
L:\番剧\<BD_DIR>\
```

### Step 3：AI 自动查 L 盘找字幕源

匹配规则：
- 目录名含 `WebRip` / `ABEMA` / `Baha` / `CR` 等流媒体关键词
- 标题关键词与目标视频匹配（番剧名/罗马名）

### Step 4：ffprobe 解析字幕源 → 选 S 级中日字幕轨

```python
import subprocess, json

def ffprobe_streams(video_path: str) -> list:
    """返回所有 stream 列表"""
    ffprobe = r'C:\Program Files\ffmpeg-7.0.2-essentials_build\ffmpeg-7.0.2-essentials_build\bin\ffprobe.exe'
    cmd = [ffprobe, '-v', 'error', '-show_streams', '-of', 'json', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return json.loads(result.stdout)['streams']

# 实际执行结果（老公的 LoliHouse 01 mkv）：
# [0] video      hevc
# [1] audio      aac     lang=jpn
# [2] subtitle   subrip  lang=chi  title=简体    ← 选这个
# [3] subtitle   subrip  lang=chi  title=繁体
```

### Step 5：ffmpeg 提取字幕 → SRT 转 ASS

```python
import subprocess
from pathlib import Path

def extract_subtitle_to_ass(video_path: str, subtitle_stream_index: int, output_ass: str):
    """提取字幕轨 → 直接转为 ASS（保留字幕源结构）"""
    ffmpeg = r'C:\Program Files\ffmpeg-7.0.2-essentials_build\ffmpeg-7.0.2-essentials_build\bin\ffmpeg.exe'
    cmd = [
        ffmpeg, '-y',
        '-i', video_path,
        '-map', f'0:s:{subtitle_stream_index}',
        '-c:s', 'ass',  # 强制转 ASS（即使源是 SRT）
        output_ass
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg failed: {result.stderr[:500]}')
    return output_ass

# 实际执行：流 2（简体）→ ASS（37.9 KB）
# 字幕源：<STREAM_DIR>/[<SUBGROUP>] - 01 [WebRip ... SRTx2].mkv
# 输出：<TMP_ASS>
```

### Step 6：cp ASS 到目标视频同目录（同主文件名）

```python
import shutil
from pathlib import Path

def mount_ass_to_target(target_video: str, ass_path: str):
    """重命名 ASS 为目标视频主文件名，挂到同目录"""
    target_dir = Path(target_video).parent
    target_stem = Path(target_video).stem  # 不含扩展名
    dest = target_dir / f'{target_stem}.ass'
    shutil.copy(ass_path, dest)
    return str(dest)

# 实际执行：
# BD: <TARGET_DIR>/[<GROUP>][<TITLE>][01][1080P][BDRip][HEVC-10bit][FLACx2].mkv
# ASS: <TARGET_DIR>/[<GROUP>][<TITLE>][01][1080P][BDRip][HEVC-10bit][FLACx2].ass  ← 新增
```

### Step 7：阶段性验证

老公原话："**BD 的路径下只要出现了正确的 ass 就算成功了**"

```bash
ls -la <TARGET_DIR>/*.ass
# 期望：<TARGET_DIR>/[<GROUP>][<TITLE>][01][...].ass
```

✅ **验证结果**：BD 目录出现 `<TARGET_DIR>/[<GROUP>][<TITLE>][01][1080P][BDRip][HEVC-10bit][FLACx2].ass`（37.9 KB）

---

## 📋 老公原话映射

| 老公原话 | skill 中的实现 |
|---|---|
| "BD 的路径下只要出现了正确的 ass 就算成功" | Step 7 验证：`ls <TARGET_DIR>/*.ass` |
| "流的第 N 集 ass 对 BD 的第 N 集" | Step 5-6：流媒体 ep 编号与 BD ep 编号对应 |
| "BD 的名字末尾.ass 就可以了" | Step 6：`<target_stem>.ass` |
| "需要和 bd 放在同文件夹" | Step 6：`shutil.copy` 到 `target_dir` |
| "BD 的特殊小语种给常规流看，开放这个选项" | **本实战未触发**（老公的 LoliHouse 只有简繁中） |
| "字幕样式完全不需要修改" | Step 5：`-c:s ass` 直接转换，不编辑 |
| "当前版本字幕样式完全不需要修改，就按照字幕源的" | 同上 |
| "开放一个选项收藏字幕" | （未来扩展）导出字幕存档到独立文件夹 |

---

## ⚠️ 本实战老公指定的边界（老公原话 Q5-Q9）

老公强调的限制：
- ❌ **不修改字幕样式**（保留字幕源原样）
- ❌ **不下载任何东西**（老公已下载好）
- ❌ **不修改目标视频**（不重封装）
- ❌ **不做硬字幕 OCR**（LoliHouse 是外挂字幕 SRT，OK）
- ✅ **S 级优先**（中日 > 仅中文 > 其他）

---

## 🔄 实战验证日志

```
$ ffmpeg -i "<STREAM_DIR>/01.mkv" -map 0:s:0 -c:s ass temp.ass
✅ 提取成功 37.9 KB ASS

$ cp temp.ass <TARGET_DIR>/<BD 主文件名>.ass
✅ ASS 已挂载到 BD 同目录

$ ls <TARGET_DIR>/*.ass
✅ <TARGET_DIR>/[<GROUP>][<TITLE>][01][1080P][BDRip][HEVC-10bit][FLACx2].ass 存在

# 验证：PotPlayer 打开 BD 即可看到中文字幕
```

---

## 📂 实战相关的具体素材（老公的 Aparida）

**目标视频（BD）**：
- `<TARGET_DIR_01>` = `L:\番剧\[DBD-Raws][脱离了A级队伍的我...][01-09TV][1080P][BDRip][HEVC-10bit][FLAC][MKV]`
- `<TARGET_DIR_02>` = `L:\番剧\[DBD-Raws][脱离了A级队伍的我...][10-17TV+特典映像][1080P][BDRip][HEVC-10bit][FLAC][MKV]`

**字幕源（流媒体）**：
- `<STREAM_DIR>` = `L:\番剧\[LoliHouse] Aparida [01-24][WebRip 1080p HEVC-10bit AAC]`
- 每集：`[<SUBGROUP>] Aparida - <EP> [WebRip 1080p HEVC-10bit AAC SRTx2].mkv`
- 字幕类型：SRTx2（简体 + 繁体）

**实战结果**：
- BD 01：`<TARGET_DIR_01>/[DBD-Raws][A Rank Party o Ridatsu Shita Ore wa][01][1080P][BDRip][HEVC-10bit][FLACx2].ass` ✅ 已挂载

---

## 🎓 给未来 AI 的复用提示

这个实战是**通用模板**——其他番剧只需替换占位符：

| 占位符 | 含义 | 例子 |
|---|---|---|
| `<TARGET_DIR>` | 目标视频目录（BD / RAW / 其他） | `L:\番剧\某番剧_BD` |
| `<STREAM_DIR>` | 字幕源目录（流媒体版） | `L:\番剧\某番剧_WebRip` |
| `<RELEASE_GROUP>` | 字幕组标签（如 DBD-Raws） | `[DBD-Raws]` |
| `<SUBGROUP>` | 流媒体版字幕组（如 LoliHouse） | `[LoliHouse]` |
| `<TITLE>` | 番剧名（中日 / 罗马名） | `Aparida` |
| `<EP>` | 集数 | `01` |

**复用步骤**：
1. 替换占位符为具体番剧的值
2. 跑 `ffprobe` 选 S 级中日字幕轨
3. 跑 `ffmpeg` 提取 + 转换 ASS
4. cp 到目标视频同目录
5. 验证 `ls <TARGET_DIR>/*.ass`