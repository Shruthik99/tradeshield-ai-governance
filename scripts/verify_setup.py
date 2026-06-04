"""
Day 1 verification script.
Run this to confirm all packages are installed correctly.

Usage: python scripts/verify_setup.py
"""

import sys

def check_import(module_name, display_name=None):
    """Try importing a module and report success/failure."""
    name = display_name or module_name
    try:
        __import__(module_name)
        print(f"  ✓ {name}")
        return True
    except ImportError as e:
        print(f"  ✗ {name} — {e}")
        return False

def main():
    print("=" * 50)
    print("TradeShield — Setup Verification")
    print("=" * 50)
    print()

    all_ok = True

    # Core agent framework
    print("Agent Framework:")
    all_ok &= check_import("google.adk", "google-adk")
    all_ok &= check_import("google.genai", "google-genai")
    print()

    # Data processing
    print("Data Processing:")
    all_ok &= check_import("pandas", "pandas")
    all_ok &= check_import("numpy", "numpy")
    all_ok &= check_import("pydantic", "pydantic")
    all_ok &= check_import("yfinance", "yfinance")
    print()

    # Phoenix tracing
    print("Phoenix Tracing:")
    all_ok &= check_import("openinference.instrumentation.google_adk", "openinference-adk")
    all_ok &= check_import("openinference.instrumentation", "openinference-core")
    all_ok &= check_import("opentelemetry.sdk", "opentelemetry-sdk")
    all_ok &= check_import("opentelemetry.exporter.otlp", "opentelemetry-exporter-otlp")
    print()

    # API server
    print("API Server:")
    all_ok &= check_import("fastapi", "fastapi")
    all_ok &= check_import("uvicorn", "uvicorn")
    all_ok &= check_import("dotenv", "python-dotenv")
    print()

    # HTTP
    print("HTTP:")
    all_ok &= check_import("requests", "requests")
    all_ok &= check_import("httpx", "httpx")
    print()

    # Testing
    print("Testing:")
    all_ok &= check_import("pytest", "pytest")
    print()

    # Config check
    print("Project Config:")
    try:
        from tradeshield.config import SEEDED_TICKERS, FACTOR_WEIGHTS
        print(f"  ✓ config loaded — {len(SEEDED_TICKERS)} tickers, {len(FACTOR_WEIGHTS)} factors")
    except Exception as e:
        print(f"  ✗ config — {e}")
        all_ok = False
    print()

    # Python version
    print(f"Python: {sys.version}")
    print()

    # Final result
    print("=" * 50)
    if all_ok:
        print("✓ ALL CHECKS PASSED — Ready to build TradeShield!")
    else:
        print("✗ SOME CHECKS FAILED — Fix the errors above before continuing.")
    print("=" * 50)

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
