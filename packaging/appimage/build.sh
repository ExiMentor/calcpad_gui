#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CORE="${CALCPADCE_SOURCE:-$HOME/Projekte/CalcpadCE}"

BUILD="$ROOT/build/appimage"
APPDIR="$BUILD/Calcpad-GUI.AppDir"
CORE_OUT="$BUILD/calcpad-core"
TOOLS="$ROOT/build/tools"

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml")"
OUTPUT="$ROOT/Calcpad-GUI-${VERSION}-x86_64.AppImage"

echo "========================================"
echo " Calcpad GUI AppImage $VERSION"
echo "========================================"
echo "GUI:  $ROOT"
echo "Core: $CORE"
echo

rm -rf "$BUILD"

mkdir -p \
    "$APPDIR/usr/bin" \
    "$APPDIR/usr/lib/calcpad-gui" \
    "$APPDIR/usr/lib/calcpad-core" \
    "$APPDIR/usr/share/applications" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
    "$CORE_OUT" \
    "$TOOLS"

echo "== Building Calcpad Core =="

dotnet publish \
    "$CORE/Calcpad.Cli/Calcpad.Cli.csproj" \
    -c Release \
    -r linux-x64 \
    --self-contained true \
    -p:PublishSingleFile=true \
    -o "$CORE_OUT"

cp -a "$CORE_OUT/." "$APPDIR/usr/lib/calcpad-core/"

# Debug symbols are not needed for distribution.
find "$APPDIR/usr/lib/calcpad-core" -name '*.pdb' -delete

echo
echo "== Installing Calcpad GUI =="

cp -a "$ROOT/calcpad_gui" "$APPDIR/usr/lib/calcpad-gui/"
cp "$ROOT/packaging/appimage/AppRun" "$APPDIR/AppRun"

cat > "$APPDIR/usr/bin/calcpad-gui" <<'LAUNCHER'
#!/bin/bash
APPDIR="$(cd "$(dirname "$0")/../.." && pwd)"

export CALCPAD_CLI="$APPDIR/usr/lib/calcpad-core/Cli"
export PYTHONPATH="$APPDIR/usr/lib/calcpad-gui${PYTHONPATH:+:$PYTHONPATH}"

cd "$APPDIR/usr/lib/calcpad-core"

exec python3 -m calcpad_gui "$@"
LAUNCHER

cp "$ROOT/packaging/calcpad-gui.desktop" \
   "$APPDIR/calcpad-gui.desktop"

cp "$ROOT/packaging/calcpad-gui.desktop" \
   "$APPDIR/usr/share/applications/calcpad-gui.desktop"

cp "$ROOT/assets/calcpadce-logo.png" \
   "$APPDIR/calcpad-gui.png"

cp "$ROOT/assets/calcpadce-logo.png" \
   "$APPDIR/usr/share/icons/hicolor/256x256/apps/calcpad-gui.png"

chmod +x \
    "$APPDIR/AppRun" \
    "$APPDIR/usr/bin/calcpad-gui" \
    "$APPDIR/usr/lib/calcpad-core/Cli"

# Ensure all AppImage users can read directories/resources and execute binaries.
chmod -R a+rX "$APPDIR"

echo
echo "== Preparing appimagetool =="

APPIMAGETOOL="$TOOLS/appimagetool.AppImage"

if [ ! -x "$APPIMAGETOOL" ]; then
    wget -O "$APPIMAGETOOL" \
        https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "$APPIMAGETOOL"
fi

echo
echo "== Building AppImage =="

rm -f "$OUTPUT"

ARCH=x86_64 \
APPIMAGE_EXTRACT_AND_RUN=1 \
"$APPIMAGETOOL" \
    "$APPDIR" \
    "$OUTPUT"

chmod +x "$OUTPUT"

echo
echo "========================================"
echo " Build complete"
echo "========================================"
echo
ls -lh "$OUTPUT"
echo
echo "Run:"
echo "  $OUTPUT"
