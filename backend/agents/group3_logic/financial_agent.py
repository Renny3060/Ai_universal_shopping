from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct
from backend.services.tax_calculator import calc_taxes


def apply_costs(results: list[ProductResult], store_cfgs: dict) -> list[RankedProduct]:
    out: list[RankedProduct] = []
    for r in results:
        cfg = store_cfgs.get(r.store, {})
        warnings: list[str] = []

        shipping = r.shipping
        if shipping is None:
            free_over = cfg.get("free_shipping_over")
            flat = cfg.get("shipping_flat")
            if free_over is not None and r.price >= free_over:
                shipping = 0.0
            elif flat is not None:
                shipping = float(flat)
        if shipping is None:
            warnings.append("Portes desconhecidos (não incluídos no total).")

        own = [n.lower() for n in cfg.get("own_seller_names", [])]
        if own and r.seller_name and r.seller_name.strip().lower() not in own:
            warnings.append(
                f"Vendido por {r.seller_name} (vendedor externo): portes e prazo podem diferir da loja."
            )

        if cfg.get("private_listings"):
            warnings.append("Anúncio de particular: garantia e devolução não garantidas.")
            
        taxes, notes = calc_taxes(
            r.price,
            shipping or 0.0,
            cfg.get("region", "PT"),
            cfg.get("duty_rate", 0.0),
            cfg.get("low_value_flat_duty", 0.0),
        )
        warnings += notes

        total = round(r.price + (shipping or 0.0) + taxes, 2)
        out.append(RankedProduct(
            product=r, shipping=shipping, taxes=taxes, total_cost=total, warnings=warnings,
        ))
    return out