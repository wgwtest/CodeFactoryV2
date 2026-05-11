# P2 Brainstorming Lab 原型 v2 自检记录

**时间：** 2026-05-01 12:33:41

**对象：**
- `DOC/CODEX_DOC/08_原型与附图/2026-05-01-123341-CodeFactoryV2-P2-Brainstorming-Lab原型-v2/`

## 1. 自检范围

本次自检覆盖：

- 原型 HTML 源文件
- 三张 `1920 x 1080` 评审截图
- 原型包 README
- 原型与附图目录索引

## 2. 用户批注回归

| 批注 | v2 修正 |
| --- | --- |
| 左侧三个对象看不懂，像页面目录 | 左侧改为真实 Lab 对象树：组织器配置、会话、当前 Turn、Provider 调用日志 |
| 单轮态左侧没有选中对象 | `03 当前 Turn 单轮循环` 中选中 `当前 Turn turn-0007` |
| 单轮输入输出应对应当前输入对象 | 单轮页左侧改为 `当前 Turn 输入 / 输出对象`，展示 Turn ID、所属会话、回答对象、用户输入、规范化解释和本轮输出摘要 |
| 可插拔组织器应是更上一级 | `01 组织器配置入口` 前置为第一张图，先配置组织器再进入 Lab 会话 |

## 3. 命令记录

生成截图：

```bash
base="$PWD/DOC/CODEX_DOC/08_原型与附图/2026-05-01-123341-CodeFactoryV2-P2-Brainstorming-Lab原型-v2"
for item in \
  "plugin|01-1920x1080-组织器配置入口.png" \
  "lab|02-1920x1080-Lab会话工作台.png" \
  "turn|03-1920x1080-当前Turn单轮循环.png"; do
  state="${item%%|*}"
  name="${item#*|}"
  corepack pnpm --dir apps/web exec playwright screenshot \
    --viewport-size=1920,1080 \
    "file://$base/source/p2-brainstorming-lab-prototype.html#$state" \
    "$base/$name"
done
```

确认截图尺寸：

```bash
file DOC/CODEX_DOC/08_原型与附图/2026-05-01-123341-CodeFactoryV2-P2-Brainstorming-Lab原型-v2/*.png
```

结果：

- `01-1920x1080-组织器配置入口.png`：`1920 x 1080`
- `02-1920x1080-Lab会话工作台.png`：`1920 x 1080`
- `03-1920x1080-当前Turn单轮循环.png`：`1920 x 1080`

## 4. 人工视觉检查

已用本地图片查看三张截图。

检查结论：

- 三个状态画面已正确分离。
- 未发现空白画面。
- 未发现主内容互相重叠。
- 组织器配置已前置为第一张图。
- 左侧对象树不再是原型图目录。
- 单轮页已聚焦当前 Turn 输入对象。

## 5. 剩余风险

- 本版为静态原型，不验证真实模型调用。
- 本版不验证真实滚动、交互和响应式布局。
- 本版不验证正式工作台接入效果。
