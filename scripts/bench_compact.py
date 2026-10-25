"""Compara o modo normal e o compacto da classificação por LLM: tempo e concordância.
Não usa a cache. Uso: python -m scripts.bench_compact"""
import sys
import time

from backend.agents.group3_logic import category_llm as m

TITULOS = [
    "Computador portátil de 14 polegadas, 16 GB RAM 256 GB SSD, Windows 11",
    "Portátil Dell Latitude 5410 i5 8th Ger. 16Gb RAM",
    "Kit Memória RAM Kingston Fury 16GB DDR4 3200MHz",
    "SSD Kingston NV2 1TB NVMe M.2",
    "Smartphone Xiaomi Redmi Note 12 8GB RAM 256GB",
    "Monitor LG UltraGear 27 polegadas 144Hz",
    "Fonte de alimentação Corsair RM750e 750W 80 Plus Gold",
    "PC Gaming Ryzen 5 5600 RTX 4060 16GB torre",
    "MacBook Air M1 8GB 256GB",
    "Cabo HDMI 2.1 2 metros",
    "Placa Gráfica ASUS Dual GeForce RTX 5060 OC 8GB",
    "Pasta térmica Arctic MX-4 4g",
    "Tablet Samsung Galaxy Tab A9 4GB 64GB",
    "Portátil Lenovo ThinkPad T490 i5 16GB RAM 256GB SSD",
    "Memória RAM SODIMM Crucial 8GB DDR4 2666MHz para portátil",
    "Computador de secretária HP Elite i5 16GB 512GB SSD",
    "Disco SSD Samsung 970 EVO Plus 500GB",
    "Caixa de PC ATX Sharkoon com janela",
    "Processador AMD Ryzen 5 5600X",
    "Portátil HP Probook 640 G5 i5 16GB 240GB SSD",
]


def run(compact: bool):
    m.COMPACT_OUTPUT = compact
    out, t0 = {}, time.time()
    for i in range(0, len(TITULOS), m.BATCH_SIZE):
        chunk = TITULOS[i:i + m.BATCH_SIZE]
        for it in m._ask(chunk).items:
            out[chunk[it.id]] = it.category
    return out, time.time() - t0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    print("A aquecer o modelo...")
    m._ask(TITULOS[:2])
    normal, t_n = run(False)
    compacto, t_c = run(True)
    dif = [(t, normal.get(t), compacto.get(t)) for t in TITULOS if normal.get(t) != compacto.get(t)]
    print(f"normal:   {t_n:.1f} s  ({len(normal)} classificados)")
    print(f"compacto: {t_c:.1f} s  ({len(compacto)} classificados)")
    print(f"diferenças: {len(dif)}")
    for t, a, b in dif:
        print(f"  {t[:60]} | normal={a} | compacto={b}")
