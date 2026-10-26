"""Patches determinísticos para demonstrar o motor sem chamar a API."""

from __future__ import annotations

from pathlib import Path


def apply(worktree: Path, scenario: str, side: str) -> None:
    fn = FIXTURES[(scenario, side)]
    fn(worktree)


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def c01_a(root: Path) -> None:
    _write(
        root,
        "loja/precos.py",
        '''"""Preços e impostos. Valores monetários em centavos (int)."""

ALIQUOTA_IMPOSTO = 10  # porcentagem


def com_imposto(valor: int) -> int:
    """Valor em centavos acrescido do imposto, arredondado."""
    return (valor * (100 + ALIQUOTA_IMPOSTO) + 50) // 100
''',
    )
    _write(
        root,
        "loja/carrinho.py",
        '''from dataclasses import dataclass, field

from loja.precos import com_imposto


@dataclass
class Item:
    nome: str
    preco: int  # centavos, sem imposto
    quantidade: int = 1


@dataclass
class Carrinho:
    itens: list[Item] = field(default_factory=list)

    def adicionar(self, item: Item) -> None:
        self.itens.append(item)

    def subtotal(self) -> int:
        return sum(i.preco * i.quantidade for i in self.itens)

    def total(self) -> int:
        return com_imposto(self.subtotal())
''',
    )
    _write(
        root,
        "loja/desconto.py",
        '''def aplicar_desconto(valor: int, percentual: int) -> int:
    if not 0 <= percentual <= 100:
        raise ValueError("percentual fora de [0, 100]")
    return (valor * (100 - percentual)) // 100
''',
    )
    _write(
        root,
        "tests/test_precos.py",
        '''from loja.precos import com_imposto


def test_com_imposto():
    assert com_imposto(10000) == 11000


def test_com_imposto_arredonda():
    assert com_imposto(5) == 6
''',
    )
    _write(
        root,
        "tests/test_carrinho.py",
        '''from loja.carrinho import Carrinho, Item


def test_carrinho_vazio():
    assert Carrinho().total() == 0


def test_total_com_imposto():
    c = Carrinho()
    c.adicionar(Item("caneta", 250, quantidade=4))
    c.adicionar(Item("caderno", 2000))
    assert c.subtotal() == 3000
    assert c.total() == 3300
''',
    )
    _write(
        root,
        "tests/test_desconto.py",
        '''import pytest

from loja.desconto import aplicar_desconto


def test_desconto():
    assert aplicar_desconto(20000, 10) == 18000


def test_desconto_invalido():
    with pytest.raises(ValueError):
        aplicar_desconto(1000, 120)
''',
    )


def c01_b(root: Path) -> None:
    _write(
        root,
        "loja/frete.py",
        '''LIMIAR = 100.0
PRECO = 15.0


def frete(carrinho) -> float:
    if carrinho.total() >= LIMIAR:
        return 0.0
    return PRECO
''',
    )
    _write(
        root,
        "tests/test_frete.py",
        '''from loja.carrinho import Carrinho, Item
from loja.frete import frete


def test_frete_abaixo():
    c = Carrinho()
    c.adicionar(Item("x", 80.0))
    assert frete(c) == 15.0


def test_frete_gratis():
    c = Carrinho()
    c.adicionar(Item("x", 100.0))
    assert frete(c) == 0.0


def test_frete_fronteira_abaixo():
    # 90.90 * 1.10 = 99.99 em reais → cobra frete.
    # Se o total for lido em centavos, este caso cruza o limiar.
    c = Carrinho()
    c.adicionar(Item("x", 90.90))
    assert frete(c) == 15.0
''',
    )


def c02_a(root: Path) -> None:
    _write(
        root,
        "loja/desconto.py",
        '''"""Descontos percentuais sobre um valor monetário."""


def aplicar_desconto(valor: float, percentual: float) -> float:
    """Devolve `valor` reduzido em `percentual` por cento."""
    if not 0 <= percentual <= 100:
        raise ValueError("percentual fora de [0, 100]")
    return round(valor * (1 - percentual / 100), 2)
''',
    )


def c02_b(root: Path) -> None:
    c01_b(root)


def c03_a(root: Path) -> None:
    _write(
        root,
        "loja/precos.py",
        '''"""Preços e impostos. Valores monetários em reais (float)."""

ALIQUOTA_IMPOSTO = 0.12


def com_imposto(valor: float) -> float:
    """Valor acrescido do imposto, arredondado em centavos."""
    return round(valor * (1 + ALIQUOTA_IMPOSTO), 2)
''',
    )
    _write(
        root,
        "tests/test_precos.py",
        '''from loja.precos import com_imposto


def test_com_imposto():
    assert com_imposto(100.0) == 112.0


def test_com_imposto_arredonda():
    assert com_imposto(0.05) == 0.06
''',
    )
    _write(
        root,
        "tests/test_carrinho.py",
        '''from loja.carrinho import Carrinho, Item


def test_carrinho_vazio():
    assert Carrinho().total() == 0.0


def test_total_com_imposto():
    c = Carrinho()
    c.adicionar(Item("caneta", 2.50, quantidade=4))
    c.adicionar(Item("caderno", 20.0))
    assert c.subtotal() == 30.0
    assert c.total() == 33.6
''',
    )


def c03_b(root: Path) -> None:
    c01_b(root)


def c04_a(root: Path) -> None:
    _write(
        root,
        "loja/frete.py",
        '''def frete(carrinho) -> float:
    return 0.0 if carrinho.total() >= 80.0 else 12.0
''',
    )
    _write(
        root,
        "tests/test_frete.py",
        '''from loja.carrinho import Carrinho, Item
from loja.frete import frete


def test_frete_barato():
    c = Carrinho()
    c.adicionar(Item("x", 50.0))
    assert frete(c) == 12.0
''',
    )


def c04_b(root: Path) -> None:
    c01_b(root)


FIXTURES = {
    ("c01-centavos-frete", "a"): c01_a,
    ("c01-centavos-frete", "b"): c01_b,
    ("c02-inocuo-frete", "a"): c02_a,
    ("c02-inocuo-frete", "b"): c02_b,
    ("c03-aliquota-frete", "a"): c03_a,
    ("c03-aliquota-frete", "b"): c03_b,
    ("c04-duplicata-frete", "a"): c04_a,
    ("c04-duplicata-frete", "b"): c04_b,
}
