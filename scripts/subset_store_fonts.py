"""Rebuild web fonts from the locked Fontsource packages (requires fonttools[woff])."""

from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "apps/store-web"
DEST = STORE / "src/assets/fonts"
DEST.mkdir(parents=True, exist_ok=True)
licenses = []
for name in ("inter", "fraunces"):
    source = STORE / "node_modules/@fontsource-variable" / name
    subset.main(
        [
            str(source / "files" / f"{name}-latin-wght-normal.woff2"),
            f"--output-file={DEST / (name + '-latin.woff2')}",
            "--flavor=woff2",
            "--unicodes=U+0020-007E,U+00A0-00FF,U+2000-206F,U+20A0-20CF",
            "--no-hinting",
        ]
    )
    output = DEST / (name + "-latin.woff2")
    font = TTFont(output)
    # The web design uses weights 400 through 700, including intermediate 550/650.
    font = instantiateVariableFont(font, {"wght": (400, 700)}, inplace=True)
    font.flavor = "woff2"
    font.save(output)
    licenses.append(name.title() + "\n\n" + (source / "LICENSE").read_text())
(STORE / "public/font-licenses.txt").write_text("\n\n".join(licenses))
