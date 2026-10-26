from loja.precos import com_imposto


def test_com_imposto():
    assert com_imposto(100.0) == 110.0


def test_com_imposto_arredonda():
    assert com_imposto(0.05) == 0.06
