import time

from backend.agents.group3_logic.category_llm import classify_titles

# Títulos de exemplo escritos por mim para testar (não vêm das lojas).
# O "esperado" é a minha avaliação do que seria correto.
CASOS = [
    ('Placa Gráfica MSI NVIDIA GeForce RTX 5060 "Blackwell" Ventus 2X OC 8G GDDR7 DLSS4', "graphics_card"),
    ("Tarjeta Grafica Zotac Rtx 5060 Solo 8gb", "graphics_card"),
    ("Portátil Gaming ASUS TUF F15 RTX 4060 16GB 512GB SSD", "laptop"),
    ("Torre PC Gaming Ryzen 5 RTX 4060 16GB 1TB SSD", "desktop_pc"),
    ("Caixa ATX Tower NZXT H5 Flow", "other"),
    ("SSD Kingston NV3 1TB M.2 NVMe", "ssd"),
    ("Memória RAM Corsair Vengeance 16GB DDR5 6000MHz", "ram"),
    ("Processador AMD Ryzen 5 7600X", "cpu"),
    ("Suporte para placa gráfica anti-sag", "other"),
    ('Monitor LG UltraGear 27" 165Hz', "monitor"),
    ("Fonte de Alimentação Corsair RM750e 750W", "psu"),
    ("Placa-Mãe ASUS PRIME B650M-A", "motherboard"),
]

titulos = [t for t, _ in CASOS]

for ronda in (1, 2):
    t0 = time.time()
    res = classify_titles(titulos)
    print(f"\nRonda {ronda}: {time.time() - t0:.1f} s")

certos = 0
for titulo, esperado in CASOS:
    obtido = res.get(titulo, "(sem resposta)")
    ok = obtido == esperado
    certos += ok
    print(f"{'OK  ' if ok else 'DIFF'} esperado={esperado:<14} obtido={obtido:<14} {titulo[:60]}")
print(f"\n{certos}/{len(CASOS)} iguais ao esperado")