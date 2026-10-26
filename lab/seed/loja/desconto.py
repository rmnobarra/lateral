def aplicar_desconto(valor, percentual):
    if not 0 <= percentual <= 100:
        raise ValueError("percentual fora de [0, 100]")
    return round(valor * (1 - percentual / 100), 2)
