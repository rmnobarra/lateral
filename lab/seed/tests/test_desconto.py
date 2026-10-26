import pytest

from loja.desconto import aplicar_desconto


def test_desconto():
    assert aplicar_desconto(200.0, 10) == 180.0


def test_desconto_invalido():
    with pytest.raises(ValueError):
        aplicar_desconto(10.0, 120)
