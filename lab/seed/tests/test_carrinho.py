from loja.carrinho import Carrinho, Item


def test_carrinho_vazio():
    assert Carrinho().total() == 0.0


def test_total_com_imposto():
    c = Carrinho()
    c.adicionar(Item("caneta", 2.50, quantidade=4))
    c.adicionar(Item("caderno", 20.0))
    assert c.subtotal() == 30.0
    assert c.total() == 33.0
