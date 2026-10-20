# 图生视频提示词与 QC 细则

## 1. Grok Imagine 提示词骨架（首帧 = 静帧，提示词只写「怎么动」）
```
{CAMERA_MOVE}. The person stays mostly still: {SMALL_ACTION}.
{ALIVE_LINE}
Keep identity, outfit and accessories exactly as in the first frame; {MUST_KEEP}.
Realistic 35mm footage, natural light behavior, no color grading, no text, no logos, no lip sync, mouth closed, no 360 orbit, no morphing.
```
- `{CAMERA_MOVE}` 从 storyboard-template 的运镜词表里挑一个，**一条只写一个运动**。
- `{SMALL_ACTION}`：`slowly raises chin and looks into the lens`、`turns head slightly to the left`、`walks toward camera with real steps, feet lifting off the ground`。
- `{ALIVE_LINE}`：`He blinks naturally and breathes, subtle head movement, not a mannequin.`
- `{MUST_KEEP}`：把锁定清单里最容易丢的 2～3 项写上，如 `black headphones stay around the neck, knee-length shorts stay shorts`。

## 2. 按镜头类型的现成提示词
| 类型 | 提示词 |
|---|---|
| 铺垫远景 | `Slow push-in from a wide shot. The person stands still with his back to the camera, hood up, city lights flicker. Keep outfit exactly as the first frame. Realistic 35mm footage, no color grading, no text, no lip sync.` |
| 特写抬眼 | `Very slow push-in on the face. He slowly raises his eyes to the lens and blinks once, mouth closed. Keep face and glasses exactly as the first frame. Realistic 35mm footage, no color grading, no text, no lip sync.` |
| 走向镜头 | `Camera dollies backward at walking speed. He walks toward the camera with real steps, feet lifting off the ground, arms swinging naturally. Keep shorts and headphones exactly as the first frame. No gliding, no lip sync, no text.` |
| 横移 | `Lateral tracking shot, camera slides left to right past him while he leans on the wall, slight head turn toward camera. No text, no lip sync, no color grading.` |
| 大落点 crash zoom | `Sudden fast crash zoom from medium shot into his face, then holds. He stays still, eyes on the lens. Keep glasses and face exactly as the first frame. No text, no lip sync.` |
| 桶滚 | `Camera barrel-rolls 90 degrees clockwise on the beat while pushing in, he stays still and centered, headphones stay visible. No text, no lip sync.` |
| dolly zoom | `Dolly zoom (vertigo effect): the background stretches away while he stays the same size, still and centered. No text, no lip sync.` |
| IP/萤火虫 | `Slow orbit of 60 degrees around the glowing firefly mascot, its light pulses softly, tiny voxel particles drift upward. Keep the mascot design exactly as the first frame. No text, no logos.` |

## 3. Seedance（可选，主人自己的账号）
- 模式：图生视频（首帧）或「全能参考」；720p、16:9、5 秒、一次一个镜头。
- 上传 `stills/<号>.png` 作为 @Image1，提示词同第 1 节，开头加 `The person from @Image1`，并加 `Keep identity exactly as @Image1`。
- **不要上传音频做对口型**（v11 试过：嘴型难看，最后全部弃用）。
- 生成后把 mp4 发回，按同号存进 `clips/`。

## 4. QC 判定细则（QC 表每格都看）
| 看什么 | 判不过的样子 | v11 坑号 |
|---|---|---|
| 人活不活 | 像照片、完全不眨眼 | 1、17 |
| 下装 | 短裤中途变长裤 | 12 |
| 配饰 | 耳机/眼镜消失、翻滚后出画 | 9、13 |
| 脸、眼镜 | 3 秒后变形、换脸 | 11 |
| 嘴 | 无故张嘴、叹气、像在说话 | 8 |
| 走路 | 脚不离地平移 | 16 |
| 字和 logo | 背景/道具上冒出乱码字 | 4 |
| 运动 | 原地不动（会像幻灯片） | 10 |
可用窗口取「从 0 开始第一个出问题之前」；若问题只在开头 0.5s，可用 `src_start=0.5`。

## 5. 记账
每条生成记一行到 `$P/clips/LOG.md`：号、工具（Imagine/Seedance）、提示词、第几次、结果。重做时在旧提示词上改，不从零写。
