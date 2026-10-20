# 角色圣经模板与提示词

## 1. 三视图 turnaround.png（16:9，带主人照片作参考图）
```
Character turnaround sheet of the person in the reference photos, full body, three views side by side:
front view, three-quarter view, back view. Same outfit in all views: {OUTFIT}.
Plain pure white background, even studio light, neutral standing pose, arms relaxed,
realistic photo style, sharp focus, consistent proportions, no text, no logos, no watermark.
Keep the face exactly like the reference: {FACE_NOTES}.
```
## 2. 脸部参考 face.png（1:1）
```
Face reference sheet of the person in the reference photos: one front close-up and one three-quarter close-up,
side by side, soft even light, plain light grey background, natural skin texture (no beauty smoothing),
same hairstyle {HAIR}, same glasses {GLASSES}. Realistic photo, no text, no logos.
```
## 3. 姿势 poses.png（16:9）
```
Pose sheet of the same character (see references), white background, 5 poses in a row:
standing confident, walking mid-stride (one foot lifted), crouching, reaching toward camera, looking back over shoulder.
Same outfit {OUTFIT}, consistent face and build, no text, no logos.
```
## 4. 表情 expressions.png（16:9）
```
Expression sheet of the same character (see references), head and shoulders, 5 expressions:
calm, confident smirk, laughing, focused, surprised. Same hair and glasses, soft light, white background, no text.
```
## 5. 没有照片也没有 IP：原创 IP
先问主人 3 件事：物种/形态（人、动物、物件拟人）、主色（2 种）、气质（酷/暖/怪）。
```
Original mascot character design, {SPECIES}, {COLORS} color scheme, {MOOD} personality,
simple readable silhouette, works small as an avatar, full body turnaround front / side / back,
white background, clean 3D toy style, no text, no logos.
```
出 3 个方案拼成一张让主人挑；挑定后按第 1～4 节出资产。

## 6. CHARACTER LOCK 模板（英文给模型，中文给主人）
```
CHARACTER LOCK (every shot, no exceptions)
- hair: {HAIR}
- face: {FACE_NOTES}            # 如 round face, short beard, no freckles
- glasses: {GLASSES}            # 或 none
- top: {TOP}, no logo
- outer: {OUTER}, no logo
- bottom: {BOTTOM} — {LENGTH}, never {WRONG_LENGTH}
- socks: {SOCKS}
- shoes: {SHOES}, no logo
- accessories: {ACC} — in EVERY shot
- build: {BUILD}; never stretch or distort the body
- banned: real brand logos, text on clothes, extra accessories, {OWNER_BANS}
LOOK: {LOOK_LINE}
RULE: every still is generated with TWO references attached: turnaround.png + face.png.
```
例（虚构）：
```
- hair: short black undercut
- top: oversized black hoodie, hood up, no logo
- bottom: black knee-length cargo shorts, never long pants
- accessories: plain black headphones around the neck — in EVERY shot
- shoes: black low-top sneakers, plain white sole, no logo
LOOK: gritty neon night street, 35mm film grain, crushed blacks, cyan and magenta practical lights
```

## 7. 常见跑偏（v11 实测）
| 跑偏 | 怎么防 |
|---|---|
| 短裤变长裤 | 锁定清单写 `never long pants`，静帧核对时第一项看下装 |
| 配饰消失（耳机、手表） | 写 `in EVERY shot`；QC 每格都看 |
| 衣服上乱出字/logo | 每条写 `no logo`；出了就重出，裁不掉就不用 |
| 3 秒后脸、眼镜变形 | 动态只用前 2.5 秒（见 ember-clips） |
| 皮肤太光滑像塑料 | 提示词写 `natural skin texture, no beauty smoothing`；精剪加颗粒 |
