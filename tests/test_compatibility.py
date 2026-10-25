from backend.agents.group1_input.compatibility_agent import (
    check_compatibility, derive_constraints, detect_cpu_socket,
)


def test_socket_detection():
    assert detect_cpu_socket("AMD Ryzen 5 5600X") == "AM4"
    assert detect_cpu_socket("AMD Ryzen 7 7800X3D") == "AM5"
    assert detect_cpu_socket("Intel Core i5-13600K") == "LGA1700"


def test_cpu_board_mismatch():
    r = check_compatibility({"cpu": "Ryzen 7 7800X3D", "motherboard": "ASUS B550"})
    assert not r.ok


def test_ddr_mismatch():
    r = check_compatibility({"cpu": "Ryzen 7 7800X3D", "ram": "16GB DDR4 3200"})
    assert not r.ok


def test_psu_too_weak():
    r = check_compatibility({"gpu": "RTX 4070 Ti", "psu_watts": 550})
    assert not r.ok


def test_compatible_build():
    r = check_compatibility({
        "cpu": "Ryzen 5 5600X", "motherboard": "MSI B550", "ram": "DDR4 16GB",
        "gpu": "RTX 3060", "psu_watts": 650,
    })
    assert r.ok


def test_derive():
    attrs = {c.attribute for c in derive_constraints("PC com Ryzen 7 7800X3D e RTX 4070")}
    assert {"cpu_socket", "ram_type", "psu_watts"} <= attrs