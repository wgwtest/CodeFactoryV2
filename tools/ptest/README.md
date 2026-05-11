# P-Test

P-Test is a cross-stage static test analysis report template. It does not start tested systems, call models, read databases, or make intelligent judgments in the browser.

The formal `analysis.json` contract is maintained in:

```text
DOC/CODEX_DOC/03_规范与流程/01_数据规范/04-P-Test-analysis-json数据规范.md
```

The intended flow is:

```text
test plan metrics
  -> execution records and evidence
  -> Codex or human-assisted analysis
  -> analysis.json
  -> static HTML report
```

## Files

```text
tools/ptest/
  README.md
  examples/
    p2-six-round-sample.analysis.json
  schemas/
    analysis.schema.json
  templates/
    report.html
    report.css
    report.js
    report.mjs
  tests/
    report.test.mjs
```

## Open A Report

For a report directory, place these files together:

```text
report.html
report.css
report.js
report.mjs
analysis.json
```

Then open `report.html` in a browser. If browser file loading blocks automatic `analysis.json` fetch, use the file picker in the page to load the JSON manually.

For the bundled sample:

```bash
node tools/ptest/bin/build-sample-report.mjs
```

Open `tools/ptest/dist/p2-six-round-sample/report.html`.

To build the cross-stage contract demo:

```bash
node tools/ptest/bin/build-sample-report.mjs cross-stage-demo
```

Open `tools/ptest/dist/cross-stage-demo/report.html`.

## Verify

```bash
node --test tools/ptest/tests/report.test.mjs
```

## Boundary

Metrics must come from the corresponding test plan. The template renders whatever is present in `analysis.json`; it must not encode P2-specific business rules or invent metrics.
