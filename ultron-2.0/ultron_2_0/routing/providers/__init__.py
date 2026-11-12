"""Provedores de modelo do pacote routing.

Exporta provedores disponíveis para uso com o `ModelRouter`.
"""

from .nvidia_nim import DEFAULT_MODEL, API_BASE_URL, NVIDIAProvider, PROVIDER_ID

__all__ = ["NVIDIAProvider", "PROVIDER_ID", "DEFAULT_MODEL", "API_BASE_URL"]
