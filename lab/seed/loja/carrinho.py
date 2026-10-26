from dataclasses import dataclass, field

from loja.precos import com_imposto


@dataclass
class Item:
    nome: str
    preco: float  # reais, sem imposto
    quantidade: int = 1


@dataclass
class Carrinho:
    itens: list[Item] = field(default_factory=list)

    def adicionar(self, item: Item) -> None:
        self.itens.append(item)

    def subtotal(self) -> float:
        return round(sum(i.preco * i.quantidade for i in self.itens), 2)

    def total(self) -> float:
        return com_imposto(self.subtotal())
