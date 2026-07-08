#!/usr/bin/env bash
#
# Build & install scikit-geometry (skgeom) from source on macOS (Apple Silicon)
# into a local uv virtual environment.
#
# Background: this project targets CGAL 5.x and pybind11 2.x. Current Homebrew
# ships CGAL 6.x + Boost 1.90 + pybind11 3.x, none of which it compiles against.
# So we pin a known-good toolchain:
#   * CGAL 5.6.3  – header-only, downloaded to ~/.local/opt (no system install)
#   * boost@1.85  – keg-only Homebrew formula, contemporary with CGAL 5.6
#   * pybind11 2.13.x – still allows keep_alive on def_property
# GMP/MPFR come from Homebrew and are ABI-stable.
#
# setup.py has been patched to honor the CGAL_INCLUDE_DIR and BOOST_ROOT env
# vars used below.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CGAL_VER="5.6.3"
CGAL_HOME="$HOME/.local/opt/CGAL-${CGAL_VER}"
BOOST_ROOT="/opt/homebrew/opt/boost@1.85"

echo ">> Installing Homebrew C++ dependencies..."
brew install gmp mpfr boost@1.85

echo ">> Fetching header-only CGAL ${CGAL_VER} (if needed)..."
if [ ! -d "${CGAL_HOME}/include/CGAL" ]; then
  mkdir -p "$HOME/.local/opt"
  curl -fL -o "/tmp/CGAL-${CGAL_VER}.tar.xz" \
    "https://github.com/CGAL/cgal/releases/download/v${CGAL_VER}/CGAL-${CGAL_VER}.tar.xz"
  tar xf "/tmp/CGAL-${CGAL_VER}.tar.xz" -C "$HOME/.local/opt"
  rm -f "/tmp/CGAL-${CGAL_VER}.tar.xz"
fi

echo ">> Creating uv virtual environment (.venv)..."
cd "$REPO"
uv venv --python 3.12 .venv

echo ">> Building and installing skgeom..."
# CGAL/Boost locations come from the [tool.skgeom] table in pyproject.toml, so
# no env vars are needed. They can still be overridden here if your paths
# differ, e.g.:
#   CGAL_INCLUDE_DIR="${CGAL_HOME}/include" BOOST_ROOT="${BOOST_ROOT}" \
uv pip install --python .venv .

echo ">> Verifying..."
.venv/bin/python -c "import skgeom as sg; print('skgeom', sg.__version__, 'OK:', sg.Point2(5,3))"

cat <<'DONE'

Done. To use it:
    source .venv/bin/activate
    python -c "import skgeom as sg; print(sg.Point2(1,2))"
DONE
