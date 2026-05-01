# P2 Brainstorming Lab 原型 v3 自检记录

时间：2026-05-01 14:15

## 范围

- 原型目录：`DOC/CODEX_DOC/08_原型与附图/2026-05-01-141500-CodeFactoryV2-P2-Brainstorming-Lab原型-v3/`
- 设计依据：`DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-Brainstorming-Lab状态机与v3原型草案.md`
- 输出截图：
  - `01-1920x1080-组织器配置Tab.png`
  - `02-1920x1080-会话管理Tab.png`
  - `03-1920x1080-当前TurnTab.png`
  - `04-1920x1080-调用日志Tab.png`

## 自检项

1. `#config` 状态标题为“组织器配置”。
2. `#config` 状态包含：
   - `1. 可替换组织器`
   - `2. 启动参数`
   - `3. 稳定契约 / 输出协议`
3. `#config` 状态不显示 `CLI 式问答区`。
4. `#session` 状态标题为“会话管理”，并显示 `CLI 式问答区` 和 `会话摘要 / 过程产物`。
5. `#turn` 状态标题为“当前 Turn 输入 / 输出对象”，并显示 `本轮输入对象` 和 `Brainstorming Service 循环输出`。
6. `#log` 状态标题为“调用日志”，并显示 `Provider 调用列表` 和 `调用详情`。
7. 四个 1920x1080 画板无横向或纵向溢出。
8. 四张截图均已生成且非空。

## 执行命令

```bash
base="$PWD/DOC/CODEX_DOC/08_原型与附图/2026-05-01-141500-CodeFactoryV2-P2-Brainstorming-Lab原型-v3"
for item in \
  "config|01-1920x1080-组织器配置Tab.png" \
  "session|02-1920x1080-会话管理Tab.png" \
  "turn|03-1920x1080-当前TurnTab.png" \
  "log|04-1920x1080-调用日志Tab.png"; do
  state="${item%%|*}"
  name="${item#*|}"
  corepack pnpm --dir apps/web exec playwright screenshot \
    --viewport-size=1920,1080 \
    "file://$base/source/p2-brainstorming-lab-prototype.html#$state" \
    "$base/$name"
done
```

```bash
BASE="$base" corepack pnpm --dir apps/web exec node <prototype-v3-check-script>
```

## 结果

```text
prototype-v3 checks passed
```

## 结论

原型 v3 满足本轮状态机修正要求，可进入用户评审。
