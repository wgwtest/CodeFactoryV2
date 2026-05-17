# P3 Requirement to SDD Dify Workflow Converter

This converter is the CodeFactoryV2 P3-side adapter for a Dify workflow.

Current branch responsibilities:

- Build the Dify workflow request from a frozen P2 requirement package.
- Call `/v1/workflows/run`.
- Parse `data.outputs.result_json`.
- Validate the P3 design converter protocol output.
- Return a draft software design document, draft SoftwareDesignPackage, traceability, gaps, review findings, and P4 projection candidate.

Dify workspace responsibilities are defined in:

```text
DOC/CODEX_DOC/03_规范与流程/04_转换器协作流程/01-P3-需规转软设-Dify工作流创建执行文档.md
```

Do not store real Dify API keys in this plugin directory.
