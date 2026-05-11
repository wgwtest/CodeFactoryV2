# P2 Brainstorming Lab 原型 v1 自检记录

**时间：** 2026-05-01 12:08:54

**对象：**
- `DOC/CODEX_DOC/08_原型与附图/2026-05-01-120854-CodeFactoryV2-P2-Brainstorming-Lab原型-v1/`

## 1. 自检范围

本次自检覆盖：

- 原型 HTML 源文件
- 三张 `1920 x 1080` 评审截图
- 原型包 README
- 原型与附图目录索引

## 2. 命令记录

生成截图：

```bash
base="$PWD/DOC/CODEX_DOC/08_原型与附图/2026-05-01-120854-CodeFactoryV2-P2-Brainstorming-Lab原型-v1"
for item in \
  "lab|01-1920x1080-独立BrainstormingLab首页.png" \
  "turn|02-1920x1080-单轮循环运行态.png" \
  "plugin|03-1920x1080-可插拔组织器替换态.png"; do
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
file DOC/CODEX_DOC/08_原型与附图/2026-05-01-120854-CodeFactoryV2-P2-Brainstorming-Lab原型-v1/*.png
```

结果：

- `01-1920x1080-独立BrainstormingLab首页.png`：`1920 x 1080`
- `02-1920x1080-单轮循环运行态.png`：`1920 x 1080`
- `03-1920x1080-可插拔组织器替换态.png`：`1920 x 1080`

格式检查：

```bash
git diff --check
```

结果：通过。

## 3. 人工视觉检查

已用本地图片查看三张截图。

检查结论：

- 三个状态画面已正确分离。
- 未发现空白画面。
- 未发现主内容互相重叠。
- 未发现按钮文字明显溢出。
- 首页能表达独立 Lab、会话配置、CLI 问答和过程浮现。
- 单轮循环态能表达服务端读取状态、调用 Provider、校验输出的过程。
- 可插拔组织器替换态能表达 `Brainstorming` 可替换，且正式 P2 文档能力保持稳定。

## 4. 剩余风险

- 本版为静态原型，不验证真实模型调用。
- 本版不验证真实滚动、交互和响应式布局。
- 本版不验证正式工作台接入效果。

上述风险应在后续实现 `P2 Brainstorming Lab` 时通过前后端测试补齐。
