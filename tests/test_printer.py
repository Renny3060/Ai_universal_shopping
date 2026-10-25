from backend.agents.group3_logic.categories import classify_title


def test_impressora():
    assert classify_title("Impressora Epson Workforce WF-110W Wireless") == "printer"
    assert classify_title("Impressora Portátil HP OfficeJet 250") == "printer"


def test_portatil_continua_laptop():
    assert classify_title("Portátil Vanwin 15.6 Intel Pentium Gold 16GB RAM") == "laptop"