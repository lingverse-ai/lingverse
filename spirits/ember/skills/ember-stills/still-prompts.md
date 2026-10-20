# 静帧提示词与核对表

## 1. 提示词骨架（英文；花括号按 shots.md 和 CHARACTER LOCK 填）
```
{SHOT_SIZE} of the same person from the reference images, {ACTION}, in {SCENE}.
{CHARACTER_LOCK_FULL_TEXT}
Composition: subject in the {LEFT|CENTER|RIGHT} third, 16:9, {CAMERA_HEIGHT}, leave headroom, room for big text on the {OPPOSITE} side.
Look: {LOOK_LINE}. Realistic photo, natural skin texture, no beauty smoothing.
Strictly no text, no letters, no signs with words, no logos, no watermark. Correct hands with five fingers.
```
要点：
- 锁定清单**全文**每次都贴，不要缩写（模型看不到上一张）。
- 想要后面图生视频动起来好看：静帧里就给出「动作的中间态」，如 `mid-stride, one foot lifted`、`turning head toward camera`。
- 竖版要用：主体放中间三分之一（`subject centered`）。

## 2. 示例（虚构项目，霓虹街头）
```
Low angle full body shot of the same person from the reference images, walking toward the camera mid-stride, one foot lifted,
on a subway platform at night as a train rushes past with motion blur.
CHARACTER LOCK: short black undercut; oversized black hoodie, hood up, no logo; black knee-length cargo shorts, never long pants;
black crew socks; black low-top sneakers, plain white sole, no logo; plain black headphones around the neck in EVERY shot; slim build, never stretched.
Composition: subject centered, 16:9, camera at knee height, room for big text on both sides.
Look: gritty neon night, 35mm film grain, crushed blacks, cyan and magenta practical lights. Realistic photo, natural skin texture.
Strictly no text, no letters, no signs with words, no logos, no watermark. Correct hands with five fingers.
```
流萤预热片（方块世界，IP = 发光的萤火虫）：
```
Wide shot of the firefly mascot from the reference images glowing softly, hovering above a voxel forest at night,
tiny cubes of light floating around, Minecraft-like voxel world but original, vibrant cyan, magenta and gold palette,
cinematic lighting, 16:9, subject centered. No text, no logos.
```

## 3. 逐项核对表（每张都过一遍，复制到 `$P/stills/CHECK.md` 打勾）
| # | 项 | 怎么看 | 不过怎么办 |
|---|---|---|---|
| 1 | 下装长度 | 对照锁定清单（短裤/长裤） | 提示词开头加 `IMPORTANT: knee-length shorts, NOT long pants` |
| 2 | 鞋、袜 | 颜色、高低帮、有无 logo | 同上写进开头 |
| 3 | 必带配饰 | 耳机/眼镜/链子/手表都在 | 写 `in EVERY shot`；构图别切掉脖子手腕 |
| 4 | 脸 | 和 `face.png` 并排看：脸型、眼距、发型 | 换更近的景别重出；脸小于画面 1/10 时不判脸 |
| 5 | 眼镜 | 形状、颜色一致 | 写清 `black thick rectangular frames` |
| 6 | 手 | 五指、没有多余的手 | 改动作让手入兜或出画 |
| 7 | 字和 logo | 衣服、招牌、屏幕、车身 | 能裁就标「需裁切」，否则重出 |
| 8 | 体型 | 没被拉长、头身比正常 | `never stretch or distort the body` |
| 9 | 风格 | 和 LOOK 一致，色调和其他张一致 | 把 LOOK 行原样贴进去 |
| 10 | 构图 | 主体位置和 shots.md 一致，留了放字的空间 | 改 Composition 行 |

## 4. 常见问题
- 两张参考图冲突（三视图衣服和照片不同）：以三视图为准，照片只管脸。
- 夜景脸太黑：加 `face lit by a soft neon key light`。
- 每张色调乱：精剪会统一调色，但静帧阶段就要把 LOOK 行一字不改地贴。
