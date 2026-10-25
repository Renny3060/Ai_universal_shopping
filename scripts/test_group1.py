import sys

from rich import print_json

from backend.agents.group1_input.pipeline import run_group1

texto = " ".join(sys.argv[1:]) or (
    "PC gaming até 1500€ com gráfica RTX 4060, 16GB de RAM e SSD de 1TB. "
    "De preferência processador AMD Ryzen 5 5600X. Novo."
)

print("A processar:", texto, "\n")
resultado = run_group1(texto)
print_json(resultado.model_dump_json())