VAT_PT = 0.23              # IVA continental
CUSTOMS_THRESHOLD = 150.0  # limite de valor da encomenda para o regime simplificado


def calc_taxes(
    price: float,
    shipping: float = 0.0,
    region: str = "PT",
    duty_rate: float = 0.0,
    low_value_flat_duty: float = 0.0,
) -> tuple[float, list[str]]:
    """Impostos a somar ao preço. Devolve (valor, notas).

    region: 'PT' ou 'EU' (preço já inclui IVA -> 0) | 'NON_EU' (loja fora da UE).
    duty_rate: taxa de direitos aduaneiros do tipo de produto (por defeito 0).
    low_value_flat_duty: direito fixo por encomenda abaixo do limite.
                         CONFIRMAR o valor em vigor antes de usar numa loja extra-UE.
    """
    notes: list[str] = []
    if region != "NON_EU":
        return 0.0, notes

    if price <= CUSTOMS_THRESHOLD:
        duty = low_value_flat_duty
        notes.append("Encomenda extra-UE: IVA cobrado no checkout (se a loja estiver no IOSS).")
    else:
        duty = (price + shipping) * duty_rate
        notes.append(
            "Acima de 150 EUR: IVA e direitos cobrados na alfândega; a transportadora "
            "pode cobrar taxa de desalfandegamento (não incluída)."
        )

    vat = (price + shipping + duty) * VAT_PT
    return round(vat + duty, 2), notes