"""Verification de l'installation"""
import sys

checks = []
import platform
v = platform.python_version()
checks.append(("Python 3.11+", v >= "3.11", v))

libs = [("pandas","pandas"),("numpy","numpy"),("fastapi","fastapi"),
        ("sqlalchemy","sqlalchemy"),("jose","jose"),("cryptography","cryptography"),
        ("sklearn","sklearn"),("mlflow","mlflow")]

for display, lib in libs:
    try:
        mod = __import__(lib)
        checks.append((display, True, getattr(mod, "__version__", "ok")))
    except ImportError:
        checks.append((display, False, "NON INSTALLE"))

print("\n" + "="*50)
print("  Verification environnement PFE Attijari bank")
print("="*50)
ok = sum(1 for _,o,_ in checks if o)
for name, good, ver in checks:
    print(f"  {'OK' if good else 'MANQUANT':10} {name:<20} {ver}")
print("="*50)
print(f"  {ok}/{len(checks)} composants OK")
if ok < len(checks):
    print("  => pip install -r requirements.txt")
print("="*50 + "\n")
