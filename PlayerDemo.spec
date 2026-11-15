# Run on Windows: python -m PyInstaller --noconfirm PlayerDemo.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
data = [(str(root / "assets" / "player"), "assets/player"),
        (str(root / "assets" / "enemies"), "assets/enemies"),
        (str(root / "assets" / "kitchen"), "assets/kitchen"),
        (str(root / "assets" / "ingredients"), "assets/ingredients"),
        (str(root / "assets" / "audio"), "assets/audio")]
hidden = collect_submodules("pyglet")

a = Analysis(
    [str(root / "main.py")], pathex=[str(root)],
    binaries=[], datas=data, hiddenimports=hidden,
    hookspath=[str(root / "tools" / "pyinstaller_hooks")],
    runtime_hooks=[], excludes=["pytest", "tkinter"], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="PlayerDemo", debug=False, strip=False, upx=False, console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PlayerDemo")
