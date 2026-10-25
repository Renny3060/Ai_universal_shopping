import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_COMMIT = "7873de5"


def ok(msg):
    print(f"[OK]    {msg}")


def fail(msg):
    print(f"[FALHA] {msg}")


def run(cmd):
    p = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def check_init():
    f = ROOT / "backend" / "__init__.py"
    if not f.exists():
        fail("backend/__init__.py nao existe")
    elif f.stat().st_size == 0:
        ok("backend/__init__.py vazio")
    else:
        fail(f"backend/__init__.py tem {f.stat().st_size} bytes (deve estar vazio; "
             "mover o conteudo para db/init_db.py)")


def check_empty_files():
    esperados_vazios = {
        "main.py", "crew.py", "vendor_filter.py", "warranty.py",
        "favorites.py", "profile.py", "search.py",
    }
    vazios = [
        str(p.relative_to(ROOT)) for p in (ROOT / "backend").rglob("*.py")
        if p.stat().st_size == 0 and p.name != "__init__.py"
    ]
    inesperados = [v for v in vazios if Path(v).name not in esperados_vazios]
    if inesperados:
        fail("ficheiros vazios inesperados: " + ", ".join(inesperados))
    else:
        ok(f"sem ficheiros vazios inesperados ({len(vazios)} vazios previstos)")


def check_env_and_config():
    env = ROOT / ".env"
    if not env.exists():
        fail(".env nao existe")
        return
    txt = env.read_text(encoding="utf-8", errors="replace")
    for chave in ("OLLAMA_BASE_URL", "OLLAMA_MODEL", "MAX_PAGES", "CACHE_TTL_MINUTES"):
        (ok if chave in txt else fail)(f".env contem {chave}")
    cfg = (ROOT / "backend" / "config.py").read_text(encoding="utf-8", errors="replace")
    (ok if "max_pages" in cfg.lower() else fail)("config.py referencia max_pages")


def check_ollama():
    try:
        from backend.config import settings
        url = settings.ollama_base_url.rstrip("/") + "/api/tags"
        with urllib.request.urlopen(url, timeout=3) as r:
            body = r.read().decode("utf-8", errors="replace")
        ok("Ollama a correr")
        (ok if settings.ollama_model in body else fail)(
            f"modelo {settings.ollama_model} instalado")
    except Exception as e:
        fail(f"Ollama inacessivel ({type(e).__name__}); correr 'ollama serve'")


def check_git():
    code, out = run(["git", "log", "--oneline", "-5"])
    if code != 0:
        fail("git log falhou: " + out.strip())
        return
    print(out.strip())
    first = out.strip().splitlines()[0] if out.strip() else ""
    (ok if first.startswith(EXPECTED_COMMIT) else fail)(
        f"ultimo commit comeca em {EXPECTED_COMMIT}")
    _, status = run(["git", "status", "--short"])
    if status.strip():
        fail("alteracoes por commitar (Fase 11?):\n" + status.strip())
    else:
        ok("working tree limpa")


def check_price_tracker():
    f = ROOT / "backend" / "services" / "price_tracker.py"
    if not f.exists():
        fail("price_tracker.py nao encontrado")
        return
    txt = f.read_text(encoding="utf-8", errors="replace")
    if "taxes=0.0" in txt.replace(" ", ""):
        fail("price_tracker grava taxes=0.0 fixo (historico sem impostos)")
    else:
        ok("price_tracker nao fixa taxes=0.0")


def check_tests():
    code, out = run([sys.executable, "-m", "pytest", "tests", "-q"])
    ultima = out.strip().splitlines()[-1] if out.strip() else ""
    (ok if code == 0 else fail)(f"pytest: {ultima}")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    for fn in (check_init, check_empty_files, check_env_and_config, check_ollama,
               check_git, check_price_tracker, check_tests):
        print(f"\n--- {fn.__name__} ---")
        try:
            fn()
        except Exception as e:
            fail(f"{fn.__name__} rebentou: {type(e).__name__}: {e}")