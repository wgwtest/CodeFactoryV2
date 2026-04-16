# 双语知识投影 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为已发布知识对象补充稳定的双语投影字段，并在知识图谱详情中展示中文解释、英文原名、缩写和中文化状态。

**Architecture:** 不修改正式抽取链，新增一个后端双语投影函数层，基于知识对象原名、别名、解释和证据生成 `language_projection`。前端只消费这个新字段，不依赖其内部生成方式。

**Tech Stack:** FastAPI, Python, React, TypeScript, Ant Design, Vitest, pytest

---

## Scope

本计划对应 [2026-04-16-bilingual-knowledge-projection-design.md](/home/wgw/CodexProject/CodeFactoryV2/docs/superpowers/specs/2026-04-16-bilingual-knowledge-projection-design.md)。

本轮只做发布态知识详情的双语投影与展示，不引入新的翻译任务编排，也不改变正式抽取/重建链。

## File Structure

- Create: `apps/api/app/archive_knowledge/language_projection.py` - 双语投影计算函数
- Modify: `apps/api/app/archive_knowledge/service.py` - 在知识对象详情和列表中注入 `language_projection`
- Modify: `apps/api/tests/test_archive_knowledge_api.py` - 双语投影 API 契约测试
- Modify: `apps/web/src/lib/api.ts` - 补充 `language_projection` 类型
- Modify: `apps/web/src/components/KnowledgeGraph.tsx` - 图谱详情显示双语投影
- Modify: `apps/web/src/test/KnowledgeGraphPage.test.tsx` - 图谱详情双语展示测试
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md` - 将 `P1.3.6` 写回总蓝图

## Task 1: 定义后端双语投影契约

**Files:**
- Create: `apps/api/app/archive_knowledge/language_projection.py`
- Modify: `apps/api/tests/test_archive_knowledge_api.py`

- [ ] 先写 API 红测，断言知识详情返回 `language_projection`
- [ ] 运行 `PYTHONPATH=apps/api uv run pytest apps/api/tests/test_archive_knowledge_api.py -q -k language_projection`
- [ ] 以最小规则实现 `display_name_zh / display_name_en / acronym / aliases_zh / aliases_en / description_zh / evidence_summary_zh / translation_status / translation_confidence`
- [ ] 再次运行同一条测试，确认通过

## Task 2: 将双语投影接入知识图谱详情

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/components/KnowledgeGraph.tsx`
- Modify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`

- [ ] 先写前端红测，断言知识详情抽屉能显示“中文主名 / 英文原名 / 缩写 / 中文化状态”
- [ ] 运行 `cd apps/web && npm test -- --run src/test/KnowledgeGraphPage.test.tsx`
- [ ] 以最小改动接入详情卡片，不改动图谱主流程
- [ ] 再次运行同一条测试，确认通过

## Task 3: 写回主设计节点

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`

- [ ] 在 `P1.3` 下新增 `P1.3.6 双语术语标准化与中文映射`
- [ ] 明确这层是治理/展示增强层，不改变正式抽取主链
- [ ] 自检术语、节点编号和上下游依赖描述是否一致

## Verification

- [ ] Run `PYTHONPATH=apps/api uv run pytest apps/api/tests/test_archive_knowledge_api.py -q`
- [ ] Run `cd apps/web && npm test -- --run src/test/KnowledgeGraphPage.test.tsx`
- [ ] Run `cd apps/web && npx tsc --noEmit`

## Self-Review

- [ ] 确认没有把“全文先翻译再抽取”写入正式主链
- [ ] 确认 `language_projection` 是增强字段，不覆盖原始 `name / aliases / evidence`
- [ ] 确认 `P1.3.6` 的输入输出边界与 `P1.4 / P1.5` 关系表述一致
