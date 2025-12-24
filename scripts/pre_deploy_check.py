#!/usr/bin/env python3
"""
Script de verificación pre-deploy para MedFlix.
Ejecuta validaciones críticas antes de desplegar a producción.

Uso: python scripts/pre_deploy_check.py
"""
import sys
import os
import subprocess
from pathlib import Path

# Colores para output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

checks_passed = 0
checks_failed = 0
warnings = 0


def print_status(status: str, message: str):
    global checks_passed, checks_failed, warnings
    if status == "OK":
        print(f"{GREEN}✅ PASS{RESET}: {message}")
        checks_passed += 1
    elif status == "FAIL":
        print(f"{RED}❌ FAIL{RESET}: {message}")
        checks_failed += 1
    else:
        print(f"{YELLOW}⚠️ WARN{RESET}: {message}")
        warnings += 1


def check_env_file():
    """Verifica que existe .env con variables requeridas."""
    env_path = Path(".env")
    if not env_path.exists():
        print_status("FAIL", ".env no existe")
        return False
    
    required_vars = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_DB"
    ]
    
    with open(env_path) as f:
        content = f.read()
    
    missing = [v for v in required_vars if v not in content]
    if missing:
        print_status("FAIL", f"Variables faltantes en .env: {missing}")
        return False
    
    print_status("OK", ".env configurado correctamente")
    return True


def check_syntax():
    """Verifica sintaxis de archivos Python críticos."""
    critical_files = [
        "app/main.py",
        "app/exceptions.py",
        "app/config.py",
        "app/schemas.py",
        "services/database.py",
        "services/metadata_enricher.py"
    ]
    
    errors = []
    for f in critical_files:
        if Path(f).exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", f],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                errors.append(f)
    
    if errors:
        print_status("FAIL", f"Errores de sintaxis en: {errors}")
        return False
    
    print_status("OK", "Sintaxis de archivos críticos OK")
    return True


def check_requirements():
    """Verifica que requirements.txt existe y tiene dependencias clave."""
    req_path = Path("requirements.txt")
    if not req_path.exists():
        print_status("FAIL", "requirements.txt no existe")
        return False
    
    with open(req_path) as f:
        content = f.read().lower()
    
    required = ["fastapi", "sqlalchemy", "pydantic"]
    missing = [r for r in required if r not in content]
    
    if missing:
        print_status("WARN", f"Dependencias no listadas: {missing}")
        return True  # Warning, not failure
    
    print_status("OK", "requirements.txt completo")
    return True


def check_dockerfile():
    """Verifica que Dockerfile existe."""
    if not Path("Dockerfile").exists():
        print_status("WARN", "Dockerfile no existe")
        return True
    
    print_status("OK", "Dockerfile existe")
    return True


def check_migrations():
    """Verifica que hay migraciones de Alembic."""
    migrations_dir = Path("migrations/versions")
    if not migrations_dir.exists():
        print_status("WARN", "No hay directorio de migraciones")
        return True
    
    migrations = list(migrations_dir.glob("*.py"))
    if len(migrations) == 0:
        print_status("WARN", "No hay archivos de migración")
        return True
    
    print_status("OK", f"{len(migrations)} migración(es) encontrada(s)")
    return True


def check_no_debug():
    """Verifica que DEBUG no esté en True en producción."""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path) as f:
            content = f.read()
        
        if "DEBUG=true" in content.lower() or "DEBUG=1" in content:
            print_status("WARN", "DEBUG está habilitado en .env")
            return True
    
    print_status("OK", "Modo DEBUG deshabilitado")
    return True


def check_secrets():
    """Verifica que no hay secretos hardcodeados obvios."""
    dangerous_patterns = [
        "password123",
        "secret123",
        "admin123",
        "12345678"
    ]
    
    files_to_check = ["app/main.py", "app/config.py", ".env"]
    issues = []
    
    for f in files_to_check:
        if Path(f).exists():
            with open(f) as file:
                content = file.read().lower()
                for pattern in dangerous_patterns:
                    if pattern in content:
                        issues.append(f"{f}: contiene '{pattern}'")
    
    if issues:
        print_status("WARN", f"Posibles secretos inseguros: {issues}")
        return True
    
    print_status("OK", "No se detectaron secretos obvios")
    return True


def run_tests():
    """Ejecuta tests con pytest."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print_status("FAIL", f"Tests fallaron:\n{result.stdout}\n{result.stderr}")
        return False
    
    print_status("OK", "Tests pasaron")
    return True


def main():
    print("\n" + "="*60)
    print("🚀 MedFlix Pre-Deploy Verification")
    print("="*60 + "\n")
    
    # Cambiar al directorio del proyecto
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Ejecutar verificaciones
    print("📋 Verificaciones de configuración:")
    check_env_file()
    check_no_debug()
    check_secrets()
    
    print("\n📦 Verificaciones de código:")
    check_syntax()
    check_requirements()
    check_dockerfile()
    check_migrations()
    
    print("\n🧪 Verificaciones de tests:")
    run_tests()
    
    # Resumen
    print("\n" + "="*60)
    print(f"📊 RESUMEN: {GREEN}{checks_passed} passed{RESET}, "
          f"{RED}{checks_failed} failed{RESET}, "
          f"{YELLOW}{warnings} warnings{RESET}")
    print("="*60)
    
    if checks_failed > 0:
        print(f"\n{RED}❌ NO LISTO PARA DEPLOY - Corregir errores antes de continuar{RESET}\n")
        sys.exit(1)
    elif warnings > 0:
        print(f"\n{YELLOW}⚠️ REVISAR WARNINGS antes de deploy{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{GREEN}✅ LISTO PARA DEPLOY{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
