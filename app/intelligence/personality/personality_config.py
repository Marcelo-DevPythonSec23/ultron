"""Configuração e renderização de personalidade do assistente ULTRON."""

from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_TEMPLATE_PATH = Path(__file__).parent / "system_prompt.txt"


class PersonalityConfig(BaseModel):
    """Configurações declarativas de identidade e comportamento conversacional."""

    name: str = Field(default="ULTRON", description="Nome do assistente")
    language: str = Field(
        default="Português do Brasil (pt-BR)", description="Idioma padrão de resposta"
    )
    tone: str = Field(
        default="direto, analítico e técnico", description="Tom e estilo de comunicação"
    )
    scientific_rigor: str = Field(
        default="alto", description="Nível de rigor científico e precisão técnica"
    )
    skepticism: str = Field(
        default="moderado a crítico", description="Nível de pensamento crítico e questionamento"
    )
    verbosity: str = Field(
        default="conciso e estruturado", description="Nível de detalhamento e prolixidade"
    )
    custom_instructions: str | None = Field(
        default=None, description="Instruções adicionais anexadas ao prompt mestre"
    )

    def render_system_prompt(self, template_content: str | None = None) -> str:
        """Renderiza o prompt de sistema substituindo as variáveis de personalidade."""
        template = template_content
        if template is None:
            if DEFAULT_TEMPLATE_PATH.exists():
                template = DEFAULT_TEMPLATE_PATH.read_text(encoding="utf-8")
            else:
                template = "Você é {name}, um assistente inteligente. Responda em {language} com tom {tone}."

        rendered = template.format(
            name=self.name,
            language=self.language,
            tone=self.tone,
            scientific_rigor=self.scientific_rigor,
            skepticism=self.skepticism,
            verbosity=self.verbosity,
        )

        if self.custom_instructions:
            rendered += f"\n\nInstruções Especiais:\n{self.custom_instructions}"

        return rendered.strip()
