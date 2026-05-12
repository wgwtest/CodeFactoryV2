export interface P1NavigationEntry {
  key: string;
  title: string;
  route: string;
  owner_line: string;
  status: "r0_shell" | "existing_page" | "to_build";
  contract_refs: string[];
}

export interface P1WorkLine {
  line_id: string;
  title: string;
  responsibility: string;
  input_contracts: string[];
  output_contracts: string[];
  verification: string[];
  suggested_parallel_owner: string;
}

export interface P1RefactorBootstrap {
  refactor_id: string;
  title: string;
  goal: string;
  navigation: P1NavigationEntry[];
  work_lines: P1WorkLine[];
  next_parallel_threads: number;
}
