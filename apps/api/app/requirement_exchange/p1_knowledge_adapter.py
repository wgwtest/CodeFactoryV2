from __future__ import annotations

from typing import Any, Mapping

from app.archive_knowledge.contracts import P1CleanSystemOutputContract, P1KnowledgeSupplyExport
from app.archive_knowledge.fixtures import get_p1_system_output
from app.xx_p1_sim.service import XXP1SimService


EXPECTED_P1_KNOWLEDGE_SUPPLY_CONTRACT_VERSION = "P1KnowledgeSupplyExport.v1"
EXPECTED_P1_CLEAN_SYSTEM_OUTPUT_CONTRACT_VERSION = "P1CleanSystemOutputContract.v1"


class P1KnowledgeAdapter:
    def bind_requirement_authoring_knowledge(self, provider_id: str, domain_id: str) -> dict | None:
        return XXP1SimService().bind_requirement_authoring_knowledge(provider_id, domain_id)

    def get_formal_knowledge_supply(self) -> dict[str, Any]:
        payload = get_p1_system_output().data
        self.validate_knowledge_supply_contract(payload)
        return payload.model_dump(mode="json")

    def get_clean_system_output_contract(
        self,
        archive_id: str,
        publication_snapshot_id: str,
        archive_knowledge_service: Any,
    ) -> P1CleanSystemOutputContract:
        payload = archive_knowledge_service.get_system_output_contract(archive_id, publication_snapshot_id)
        self.validate_clean_system_output_contract(payload)
        return payload

    def validate_knowledge_supply_contract(self, payload: Mapping[str, Any] | P1KnowledgeSupplyExport) -> None:
        if isinstance(payload, P1KnowledgeSupplyExport):
            contract_version = payload.contract_version
        else:
            contract_version = payload.get("contract_version")
        if contract_version != EXPECTED_P1_KNOWLEDGE_SUPPLY_CONTRACT_VERSION:
            raise ValueError(
                "Unsupported P1 knowledge supply contract: "
                f"{contract_version!r}; expected {EXPECTED_P1_KNOWLEDGE_SUPPLY_CONTRACT_VERSION!r}"
            )

    def validate_clean_system_output_contract(
        self,
        payload: Mapping[str, Any] | P1CleanSystemOutputContract,
    ) -> None:
        if isinstance(payload, P1CleanSystemOutputContract):
            contract_version = payload.contract_version
            forbidden_sources = payload.adapter_contract.forbidden_sources
        else:
            contract_version = payload.get("contract_version")
            adapter_contract = payload.get("adapter_contract") or {}
            forbidden_sources = adapter_contract.get("forbidden_sources", [])

        if contract_version != EXPECTED_P1_CLEAN_SYSTEM_OUTPUT_CONTRACT_VERSION:
            raise ValueError(
                "Unsupported P1 clean system output contract: "
                f"{contract_version!r}; expected {EXPECTED_P1_CLEAN_SYSTEM_OUTPUT_CONTRACT_VERSION!r}"
            )
        if "runtime_temporary_nodes" not in forbidden_sources:
            raise ValueError("P1 clean system output contract must forbid runtime temporary nodes")

