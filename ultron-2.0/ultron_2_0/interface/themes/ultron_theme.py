"""Tema de identidade visual do ULTRON (INTERFACE.md §7).

Paleta centralizada em tokens CSS-like para a interface desktop:
- Preto profundo como base
- Vermelho escuro e vermelho intenso como cores principais
- Detalhes em vermelho luminoso
- Elementos cibernéticos discretos
- Tipografia técnica e legível
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UltronTheme:
    """Tokens de identidade visual do ULTRON.

    Trocar a identidade é trocar tokens, não dezenas de regras.
    """

    # Cores de fundo
    bg: str = "#050506"
    bg_2: str = "#0b0b0e"
    panel: str = "rgba(17, 17, 21, 0.82)"
    panel_solid: str = "#111114"
    graphite: str = "#26262d"

    # Linhas e bordas
    line: str = "rgba(255, 47, 61, 0.18)"
    line_strong: str = "rgba(255, 47, 61, 0.42)"

    # Vermelhos (identidade ULTRON)
    red_deep: str = "#6e0a10"
    red: str = "#b3121a"
    red_bright: str = "#ff2f3d"
    red_glow: str = "rgba(255, 47, 61, 0.35)"

    # Texto
    text: str = "#ece9e6"
    muted: str = "#9a9490"
    faint: str = "#6d6864"

    # Status
    ok: str = "#3ddc97"
    warn: str = "#ffb020"
    err: str = "#ff5a66"

    # Raio e tipografia
    radius: str = "12px"
    radius_sm: str = "8px"
    mono: str = '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, monospace'
    sans: str = 'system-ui, "Segoe UI", Roboto, "Helvetica Neue", sans-serif'

    def to_stylesheet_vars(self) -> str:
        """Devolve os tokens como variáveis CSS/QSS para uso em QSS."""
        return f"""
        QApplication {{
            --bg: {self.bg};
            --bg-2: {self.bg_2};
            --panel: {self.panel};
            --panel-solid: {self.panel_solid};
            --graphite: {self.graphite};
            --line: {self.line};
            --line-strong: {self.line_strong};
            --red-deep: {self.red_deep};
            --red: {self.red};
            --red-bright: {self.red_bright};
            --red-glow: {self.red_glow};
            --text: {self.text};
            --muted: {self.muted};
            --faint: {self.faint};
            --ok: {self.ok};
            --warn: {self.warn};
            --err: {self.err};
            --radius: {self.radius};
            --radius-sm: {self.radius_sm};
            --mono: {self.mono};
            --sans: {self.sans};
        }}
        """

    def as_dict(self) -> dict[str, str]:
        return {
            "bg": self.bg,
            "bg_2": self.bg_2,
            "panel": self.panel,
            "panel_solid": self.panel_solid,
            "graphite": self.graphite,
            "line": self.line,
            "line_strong": self.line_strong,
            "red_deep": self.red_deep,
            "red": self.red,
            "red_bright": self.red_bright,
            "red_glow": self.red_glow,
            "text": self.text,
            "muted": self.muted,
            "faint": self.faint,
            "ok": self.ok,
            "warn": self.warn,
            "err": self.err,
            "radius": self.radius,
            "radius_sm": self.radius_sm,
            "mono": self.mono,
            "sans": self.sans,
        }


__all__ = ["UltronTheme"]
