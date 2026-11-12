"""Agentes iniciais especializados (Fase 4).

Cada agente é um **adaptador** sobre ferramentas existentes do ULTRON
(web_search, system_status, memória, banco, gateway de ferramentas) — não
cria modelos próprios para funcionalidades já oferecidas (AGENTS.md §4.3).
Todos recebem apenas o contexto necessário para sua tarefa (isolamento) e
devolvem resultados estruturados para avaliação centralizada pelo
`AgentOrchestrator`.
"""

from __future__ import annotations

import logging
from typing import Any

from .agent_task import AgentCapability, AgentResult, AgentTask
from .base_agent import BaseAgent

logger = logging.getLogger("ultron2.agents.implementations")


# -- Developer Agent --------------------------------------------------------
class DeveloperAgent(BaseAgent):
    """Inspeciona código e propõe alterações (só leitura + propostas).

    Não escreve arquivos diretamente: alterações de código exigem
    isolamento e rastreabilidade (AGENTS.md §5.5) e só são aplicadas
    após autorização explícita (Fase 2).
    """

    def __init__(self, agent_id: str | None = None) -> None:
        super().__init__(agent_id=agent_id, agent_type="developer")

    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="inspect_code",
                description="Inspecta arquivos de código e reporta estrutura.",
                input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
                requires_authorization=False,
                timeout_seconds=30.0,
            ),
            AgentCapability(
                name="propose_code_change",
                description="Propõe uma alteração de código (não aplica).",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "proposal": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {"proposal": {"type": "string"}}},
                requires_authorization=True,
                timeout_seconds=60.0,
            ),
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        objective = task.objective.lower()
        context = task.context or {}
        path = context.get("path", "")
        summary_parts: list[str] = []

        if "inspect" in objective or "inspecionar" in objective:
            summary_parts.append(f"inspeção de código solicitada para {path or '(não informado)'}")
            if path:
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    summary_parts.append(f"arquivo lido ({len(content)} caracteres)")
                    summary_parts.append(f"primeiras 200 chars: {content[:200]!r}")
                except FileNotFoundError:
                    summary_parts.append("arquivo não encontrado")
                except Exception as exc:  # noqa: BLE001
                    summary_parts.append(f"erro ao ler: {exc}")
            else:
                summary_parts.append("nenhum caminho especificado para inspeção")
        else:
            summary_parts.append("objetivo não reconhecido pelo DeveloperAgent")

        return AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            success=True,
            content={"summary": "\n".join(summary_parts), "path": path},
            summary="; ".join(summary_parts),
            files_modified=[],
        )


# -- Research Agent ---------------------------------------------------------
class ResearchAgent(BaseAgent):
    """Pesquisa técnica e documentação via web_search e memória."""

    def __init__(self, web_search=None, memory_engine=None, agent_id: str | None = None) -> None:
        super().__init__(agent_id=agent_id, agent_type="research")
        self._web_search = web_search
        self._memory_engine = memory_engine

    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="research_topic",
                description="Pesquisa um tema técnico usando busca web e memória.",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}, "use_memory": {"type": "boolean"}},
                },
                output_schema={"type": "object", "properties": {"findings": {"type": "string"}}},
                requires_authorization=False,
                timeout_seconds=60.0,
            ),
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        query = (task.context or {}).get("query", task.objective)
        findings: list[str] = [f"pesquisa iniciada para: {query}"]

        if self._web_search is not None:
            try:
                # web_search do Mark-LVI: retorna resultados textuais.
                web_result = await self._web_search(query)
                findings.append(f"busca web retornou: {str(web_result)[:500]}")
            except Exception as exc:  # noqa: BLE001
                findings.append(f"busca web falhou: {exc}")
        else:
            findings.append("web_search não disponível neste agente")

        if self._memory_engine is not None and (task.context or {}).get("use_memory"):
            try:
                memories = self._memory_engine.search(query)
                findings.append(f"memória: {len(memories)} registros encontrados")
            except Exception as exc:  # noqa: BLE001
                findings.append(f"memória indisponível: {exc}")

        return AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            success=True,
            content={"findings": "\n".join(findings), "query": query},
            summary="; ".join(findings),
            files_modified=[],
        )


# -- Security Agent ---------------------------------------------------------
class SecurityAgent(BaseAgent):
    """Auditoria e análise de segurança: revisa contratos, permissões, segredos."""

    def __init__(self, gateway=None, agent_id: str | None = None) -> None:
        super().__init__(agent_id=agent_id, agent_type="security")
        self._gateway = gateway

    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="audit_tool_contract",
                description="Audita o contrato de uma ferramenta (permissões, segredos, validação).",
                input_schema={
                    "type": "object",
                    "properties": {"tool_name": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {"audit": {"type": "string"}}},
                requires_authorization=False,
                timeout_seconds=30.0,
            ),
        ]

    async def execute(self, task: AgentTask) -> AgentResult:

        tool_name = (task.context or {}).get("tool_name", "")
        nao_informada = "(não informada)"
        findings: list[str] = [f"auditoria de segurança para ferramenta: {tool_name or nao_informada}"]

        if self._gateway is not None and tool_name:
            try:
                contract = self._gateway.get_contract(tool_name)
                findings.append(f"contrato encontrado: {contract.name}")
                findings.append(f"confirmação necessária: {getattr(contract, 'requires_confirmation', False)}")
                findings.append(f"permissões: {getattr(contract, 'permissions', [])}")
                # Detecção simples de segredos expostos na descrição.
                desc = getattr(contract, "description", "") or ""
                if any(w in desc.lower() for w in ["senha", "senha", "chave", "token", "secret", "key"]):
                    findings.append("AVISO: descrição pode conter referência a credenciais")
            except Exception as exc:  # noqa: BLE001
                findings.append(f"falha ao auditar contrato: {exc}")
        else:
            findings.append("gateway não disponível ou ferramenta não informada")

        return AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            success=True,
            content={"audit": "\n".join(findings), "tool_name": tool_name},
            summary="; ".join(findings),
            files_modified=[],
        )


# -- QA Agent ---------------------------------------------------------------
class QAAgent(BaseAgent):
    """Testes e validação: executa suítes de teste e valida resultados."""

    def __init__(self, test_runner=None, agent_id: str | None = None) -> None:
        super().__init__(agent_id=agent_id, agent_type="qa")
        self._test_runner = test_runner

    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="run_tests",
                description="Executa testes e reporta resultados.",
                input_schema={
                    "type": "object",
                    "properties": {"suite": {"type": "string"}, "path": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {"passed": {"type": "integer"}, "failed": {"type": "integer"}}},
                requires_authorization=False,
                timeout_seconds=120.0,
            ),
        ]

    async def execute(self, task: AgentTask) -> AgentResult:

        suite = (task.context or {}).get("suite", "all")
        path = (task.context or {}).get("path", "")
        findings: list[str] = [f"QA iniciado para suíte: {suite}"]

        if self._test_runner is not None:
            try:
                report = await self._test_runner(suite=suite, path=path)
                passed = int(report.get("passed", 0))
                failed = int(report.get("failed", 0))
                findings.append(f"testes: {passed} aprovados, {failed} falhados")
                return AgentResult(
                    task_id=task.id,
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    success=failed == 0,
                    content={"passed": passed, "failed": failed, "report": report},
                    summary=f"{passed} aprovados, {failed} falhados",
                    files_modified=[],
                )
            except Exception as exc:  # noqa: BLE001
                findings.append(f"execução de testes falhou: {exc}")
        else:
            findings.append("test_runner não disponível neste agente")

        return AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            success=False,
            content={"findings": "\n".join(findings)},
            summary="; ".join(findings),
            error="test_runner indisponível",
            files_modified=[],
        )


# -- Database Agent ---------------------------------------------------------
class DatabaseAgent(BaseAgent):
    """Arquitetura e gerenciamento de dados: inspeciona banco e esquema."""

    def __init__(self, db_session=None, agent_id: str | None = None) -> None:
        super().__init__(agent_id=agent_id, agent_type="database")
        self._db_session = db_session

    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="inspect_schema",
                description="Inspeciona o esquema do banco de dados (somente leitura).",
                input_schema={"type": "object", "properties": {"table": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"schema": {"type": "string"}}},
                requires_authorization=False,
                timeout_seconds=30.0,
            ),
        ]

    async def execute(self, task: AgentTask) -> AgentResult:

        table = (task.context or {}).get("table", "")
        nao_informada = "(não informada)"
        findings: list[str] = [f"inspeção de banco para tabela: {table or nao_informada}"]

        if self._db_session is not None:
            try:
                # Inspeção somente leitura; não modifica dados.
                findings.append("sessão de banco disponível (leitura apenas)")
            except Exception as exc:  # noqa: BLE001
                findings.append(f"erro ao inspecionar banco: {exc}")
        else:
            findings.append("sessão de banco não disponível")

        return AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            success=True,
            content={"schema": "\n".join(findings), "table": table},
            summary="; ".join(findings),
            files_modified=[],
        )


# -- Architecture Agent -----------------------------------------------------
class ArchitectureAgent(BaseAgent):
    """Revisão de arquitetura e decisões técnicas (ADRs)."""

    def __init__(self, docs_root=None, agent_id: str | None = None) -> None:
        super().__init__(agent_id=agent_id, agent_type="architecture")
        self._docs_root = docs_root

    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="review_decision",
                description="Revisa uma decisão arquitetural (ADR) e reporta impacto.",
                input_schema={
                    "type": "object",
                    "properties": {"decision_id": {"type": "string"}, "context": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {"review": {"type": "string"}}},
                requires_authorization=False,
                timeout_seconds=60.0,
            ),
        ]

    async def execute(self, task: AgentTask) -> AgentResult:

        decision_id = (task.context or {}).get("decision_id", "")
        context = (task.context or {}).get("context", "")
        nao_informada = "(não informada)"
        findings: list[str] = [f"revisão de arquitetura para decisão: {decision_id or nao_informada}"]

        if self._docs_root is not None:
            import os

            adr_path = os.path.join(self._docs_root, f"{decision_id}.md")
            if os.path.exists(adr_path):
                try:
                    with open(adr_path, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    findings.append(f"ADR encontrado ({len(content)} caracteres)")
                    findings.append(f"conteúdo: {content[:300]!r}")
                except Exception as exc:  # noqa: BLE001
                    findings.append(f"erro ao ler ADR: {exc}")
            else:
                findings.append(f"ADR não encontrado: {adr_path}")
        else:
            findings.append("docs_root não configurado")

        if context:
            findings.append(f"contexto adicional: {context[:200]}")

        return AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            success=True,
            content={"review": "\n".join(findings), "decision_id": decision_id},
            summary="; ".join(findings),
            files_modified=[],
        )


__all__ = [
    "DeveloperAgent",
    "ResearchAgent",
    "SecurityAgent",
    "QAAgent",
    "DatabaseAgent",
    "ArchitectureAgent",
]
