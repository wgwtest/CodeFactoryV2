from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class P1NavigationEntry(BaseModel):
    key: str
    title: str
    route: str
    owner_line: str
    status: Literal["r0_shell", "existing_page", "to_build"]
    contract_refs: list[str] = Field(default_factory=list)


class P1WorkLine(BaseModel):
    line_id: str
    title: str
    responsibility: str
    input_contracts: list[str] = Field(default_factory=list)
    output_contracts: list[str] = Field(default_factory=list)
    verification: list[str] = Field(default_factory=list)
    suggested_parallel_owner: str


class P1RefactorBootstrap(BaseModel):
    refactor_id: str
    title: str
    goal: str
    navigation: list[P1NavigationEntry] = Field(default_factory=list)
    work_lines: list[P1WorkLine] = Field(default_factory=list)
    next_parallel_threads: int
