from __future__ import annotations

import json
from pathlib import Path

from app.tool_hub.models import GeneratedArtifactBundle, ToolRecipe


def _normalize_dependency_version(version: str) -> str:
    digits = "".join(char if (char.isdigit() or char == ".") else " " for char in version).split()
    if not digits:
        return version
    return digits[0].split(".")[0]


def _render_component_tsx(component_name: str) -> str:
    return f"""import type {{ ColumnsType }} from "antd/es/table";
import {{ Button, Input, Space, Table }} from "antd";
import type {{ ReactNode }} from "react";
import {{ useMemo, useState }} from "react";

export type QueryTableFilter = {{
  key: string;
  label: string;
  placeholder?: string;
}};

export type QueryTableWidgetProps<T extends object> = {{
  title?: ReactNode;
  columns: ColumnsType<T>;
  filters?: QueryTableFilter[];
  dataSource: T[];
  rowKey: string | ((record: T) => string);
  onSearch?: (values: Record<string, string>) => void;
  extraActions?: ReactNode;
}};

export function {component_name}<T extends object>(props: QueryTableWidgetProps<T>) {{
  const [queryValues, setQueryValues] = useState<Record<string, string>>({{}});
  const filters = props.filters ?? [];

  const filterBar = useMemo(
    () =>
      filters.map((filter) => (
        <Input
          key={{filter.key}}
          placeholder={{filter.placeholder ?? filter.label}}
          value={{queryValues[filter.key] ?? ""}}
          onChange={{(event) =>
            setQueryValues((current) => ({{ ...current, [filter.key]: event.target.value }}))
          }}
        />
      )),
    [filters, queryValues],
  );

  return (
    <Space direction="vertical" size={16} style={{{{ width: "100%" }}}}>
      <Space wrap>
        {{filterBar}}
        <Button type="primary" onClick={{() => props.onSearch?.(queryValues)}}>
          查询
        </Button>
        {{props.extraActions}}
      </Space>
      <Table<T> rowKey={{props.rowKey}} columns={{props.columns}} dataSource={{props.dataSource}} />
    </Space>
  );
}}
"""


QUERY_TABLE_TYPES_TS = """export type QueryTableFilter = {
  key: string;
  label: string;
  placeholder?: string;
};
"""


HOST_EXAMPLE_TSX = """import { QueryTableWidget } from "../src/QueryTableWidget";

const columns = [
  { title: "名称", dataIndex: "name", key: "name" },
  { title: "状态", dataIndex: "status", key: "status" },
];

const dataSource = [{ id: "1", name: "样例记录", status: "active" }];

export function HostPage() {
  return (
    <QueryTableWidget
      title="查询表格样例"
      columns={columns}
      filters={[{ key: "keyword", label: "关键词" }]}
      dataSource={dataSource}
      rowKey="id"
      onSearch={(values) => console.log("search", values)}
    />
  );
}
"""


def render_query_table_widget(recipe: ToolRecipe, artifact_root: Path) -> GeneratedArtifactBundle:
    artifact_root.mkdir(parents=True, exist_ok=True)
    src_dir = artifact_root / "src"
    example_dir = artifact_root / "example"
    src_dir.mkdir(parents=True, exist_ok=True)
    example_dir.mkdir(parents=True, exist_ok=True)

    files = {
        src_dir / f"{recipe.component_name}.tsx": _render_component_tsx(recipe.component_name),
        src_dir / "types.ts": QUERY_TABLE_TYPES_TS,
        example_dir / "HostPage.tsx": HOST_EXAMPLE_TSX,
    }

    runtime_dependencies = [
        f"{name}@{_normalize_dependency_version(version)}"
        for name, version in recipe.peer_dependencies.items()
    ]
    manifest = {
        "tool_form_id": "frontend_component",
        "tool_granularity": "atomic",
        "packaging_type": "source_package",
        "integration_mode": "import_component",
        "dependency_policy": "peer",
        "runtime_dependencies": runtime_dependencies,
        "import_specifier": recipe.package_name,
        "example_host_path": "example/HostPage.tsx",
        "component_name": recipe.component_name,
        "host_constraints": recipe.host_constraints,
    }
    manifest_path = artifact_root / "manifest.json"
    files[manifest_path] = json.dumps(manifest, ensure_ascii=False, indent=2)

    for path, content in files.items():
        path.write_text(content, encoding="utf-8")

    return GeneratedArtifactBundle(
        artifact_root=str(artifact_root),
        manifest_path=str(manifest_path),
        import_specifier=recipe.package_name,
        example_host_path="example/HostPage.tsx",
        files=[str(path.relative_to(artifact_root)) for path in files],
    )
