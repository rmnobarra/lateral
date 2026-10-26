"""Preços e impostos. Valores monetários em reais (float)."""

ALIQUOTA_IMPOSTO = 0.10


def com_imposto(valor: float) -> float:
    """Valor acrescido do imposto, arredondado em centavos."""
    return round(valor * (1 + ALIQUOTA_IMPOSTO), 2)
