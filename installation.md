
### 
```
Install dependencies 
brew install gmp mpfr boost@1.85
mkdir -p ~/.local/opt && curl -fL https://github.com/CGAL/cgal/releases/download/v5.6.3/CGAL-5.6.3.tar.xz | tar xJ -C ~/.local/opt

[tool.skgeom] hardcodes ~/.local/opt/CGAL-5.6.3 and /opt/homebrew/opt/boost@1.85. On a machine where those paths differ, override them 

  CGAL_INCLUDE_DIR=/some/other/CGAL/include BOOST_ROOT=/some/boost \
    pip install "git+https://github.com/npretor/scikit-geometry@macos-source-build"

uv pip install "git+https://github.com/npretor/scikit-geometry"
# or plain pip:
pip install "git+https://github.com/npretor/scikit-geometry"
# or 
 pip install "git+https://github.com/npretor/scikit-geometry@macos-source-build"
```