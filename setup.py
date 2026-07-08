from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys, os, glob, re
import setuptools

here = os.path.dirname(os.path.abspath(__file__))


def _load_local_build_config():
    """Read the optional [tool.skgeom] table from pyproject.toml.

    Provides default CGAL/Boost locations so `pip install .` works without
    manually exporting CGAL_INCLUDE_DIR / BOOST_ROOT. Returns {} if the table,
    the file, or a TOML parser is unavailable.
    """
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # backport for older Pythons
        except ImportError:
            return {}
    try:
        with open(os.path.join(here, 'pyproject.toml'), 'rb') as f:
            return tomllib.load(f).get('tool', {}).get('skgeom', {})
    except (OSError, ValueError):
        return {}


_local_cfg = _load_local_build_config()


def _resolve_path(env_var, cfg_key):
    """Environment variable wins; otherwise fall back to pyproject config."""
    value = os.getenv(env_var) or _local_cfg.get(cfg_key)
    return os.path.expanduser(value) if value else None


class get_pybind_include(object):
    """Helper class to determine the pybind11 include path
    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked. """

    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)

include_dirs = [
    "./include/",
    "./src/docs/",
    # Path to pybind11 headers
    get_pybind_include(),
    get_pybind_include(user=True),
]

library_dirs = []
cgal_libs = ["CGAL", "CGAL_Core"]
boost_mt = False

# Allow explicitly pointing at a CGAL include tree (e.g. a header-only 5.x
# release) to override whatever is found on the system. Prepended so its
# headers win over any other CGAL install on the include path. Comes from the
# CGAL_INCLUDE_DIR env var or the [tool.skgeom] table in pyproject.toml.
cgal_include_override = _resolve_path('CGAL_INCLUDE_DIR', 'cgal-include-dir')

conda_prefix = os.getenv('CONDA_PREFIX')
if not conda_prefix:
    conda_prefix = os.getenv('MINICONDAPATH')

if cgal_include_override:
    include_dirs.insert(0, cgal_include_override)
    cgal_include = os.path.join(cgal_include_override, 'CGAL')
elif conda_prefix:
    cgal_include = os.path.join(conda_prefix, 'include', 'CGAL')

    if not os.path.exists(cgal_include):
        cgal_include = os.path.join(conda_prefix, 'Library', 'include', 'CGAL')
        include_dirs.append(os.path.join(conda_prefix, 'Library', 'include'))
elif os.path.exists('/usr/include/CGAL/'):
    cgal_include = '/usr/include/CGAL/'
elif os.path.exists('/opt/homebrew/include/CGAL/'):
    cgal_include = '/opt/homebrew/include/CGAL/'
else:
    cgal_include = '/usr/local/include/CGAL/'

cgal_version = None
if os.path.exists(os.path.join(cgal_include, 'version.h')):
    with open(os.path.join(cgal_include, 'version.h'), 'r') as f:
        m = re.search(r'#define\s+CGAL_VERSION\s+([\d\.]+)', f.read())
        if m:
            cgal_version = tuple(map(int, m.group(1).split('.')))

if cgal_version:
    print("Found CGAL version: " + '.'.join(map(str, cgal_version)))
else:
    print("Could not determine CGAL version.")
    cgal_version = (5, 0)

if cgal_version >= (5, 0):
    cgal_libs = []  # header only now.

if conda_prefix:

    if sys.platform.startswith('win'):
        prefix = os.path.join(sys.prefix, 'Library\\')
    else:
        prefix = sys.prefix

    print("Looking for CGAL in: ", prefix)

    extra_link_args = []
    if sys.platform == 'darwin' and cgal_version < (5, 0):
        extra_link_args = ['-Wl,-rpath', '-Wl,%s' % os.path.abspath(prefix)]


    if sys.platform == 'win32':
        library_dir = os.path.join(prefix, 'lib')

        if cgal_version < (5, 0):
            # currently we also need to add the apparently windows specific suffix here, it's unclear if this is
            # necessary if CGAL is installed not from CONDA.
            # suffix = "-vc140-mt-4.14.1"
            adjusted_cgal_libs = []
            for lib in cgal_libs:
                candidates = glob.glob(os.path.join(library_dir, lib) + '*.lib')
                if not candidates:
                    raise RuntimeError("Library not found [[{}]]".format(lib))
                c = os.path.basename(candidates[0])
                c = os.path.splitext(c)[0]
                adjusted_cgal_libs.append(c)
            cgal_libs = adjusted_cgal_libs
            print("Names of adjusted CGAL libs: ", adjusted_cgal_libs)

        library_dirs = [library_dir]
        print("Looking for libraries in ", library_dirs)

    if cgal_version < (5, 0):
        include_dirs.insert(1, os.path.join(prefix, 'include'))

if sys.platform == 'darwin':
    boost_mt = bool(
        glob.glob('/usr/local/lib/libboost*-mt*') +
        glob.glob('/opt/homebrew/lib/libboost*-mt*')
    )
    include_dirs += ['/usr/local/include', '/opt/homebrew/include']
    library_dirs += ['/usr/local/lib', '/opt/homebrew/lib']

# Allow pointing at a specific Boost install (e.g. a keg-only Homebrew
# boost@1.85 that is contemporary with CGAL 5.x). Prepended so its headers
# and libraries win over any newer system Boost on the path. Comes from the
# BOOST_ROOT env var or the [tool.skgeom] table in pyproject.toml.
boost_root = _resolve_path('BOOST_ROOT', 'boost-root')
if boost_root:
    include_dirs.insert(0, os.path.join(boost_root, 'include'))
    library_dirs.insert(0, os.path.join(boost_root, 'lib'))
    # Some Boost builds (incl. Homebrew's) ship thread/atomic only with the
    # multi-threaded "-mt" suffix, so detect it from this specific tree.
    boost_mt = bool(glob.glob(os.path.join(boost_root, 'lib', 'libboost*-mt*')))

ext_modules = [
    Extension(
        'skgeom._skgeom',
        [
            'src/simplification.cpp',
            'src/polygon_set.cpp',
            'src/skgeom.cpp',
            'src/kernel.cpp',
            'src/polygon.cpp',
            'src/global_functions.cpp',
            'src/boolean.cpp',
            'src/convex_hull.cpp',
            'src/visibility.cpp',
            'src/arrangement.cpp',
            'src/principal_component_analysis.cpp',
            'src/minkowski.cpp',
            'src/polyhedron.cpp',
            'src/aabb_tree.cpp',
            'src/voronoi_delaunay.cpp',
            'src/optimal_transport.cpp',
            'src/skeleton.cpp',
            'src/inscribed.cpp'
        ],
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=cgal_libs + ['mpfr',
                   'gmp',
                   'boost_thread-mt' if boost_mt else 'boost_thread',
                   'boost_atomic-mt' if boost_mt else 'boost_atomic',
                   # boost_system is header-only in modern Boost (>=1.69) and
                   # ships no library to link against, so it is omitted here.
                   'boost_date_time',
                   'boost_chrono'],
        language='c++'
    ),
]


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    extra = ['-stdlib=libc++'] if sys.platform == 'darwin' else []
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
        f.write('int main (int argc, char **argv) { return 0; }')
        try:
            compiler.compile([f.name], extra_postargs=[flagname] + extra)
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14/17] compiler flag.
    The newer version is prefered over c++11 (when it is available).
    """
    flags = ['-std=c++17', '-std=c++14', '-std=c++11']

    for flag in flags:
        if has_flag(compiler, flag): return flag

    raise RuntimeError('Unsupported compiler -- at least C++11 support '
                       'is needed!')


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""
    c_opts = {
        'msvc': ['/EHsc', '/std:c++14'],
        'unix': [],
    }
    l_opts = {
        'msvc': [],
        'unix': [],
    }

    if sys.platform == 'darwin':
        darwin_opts = ['-stdlib=libc++', '-mmacosx-version-min=10.14']
        c_opts['unix'] += darwin_opts
        l_opts['unix'] += darwin_opts

    def initialize_options(self):
        super(BuildExt, self).initialize_options()
        self.debug = False
        self.parallel = True

    def build_extensions(self):
        ct = self.compiler.compiler_type
        opts = self.c_opts.get(ct, [])
        link_opts = self.l_opts.get(ct, [])
        if ct == 'unix':
            opts.append('-DVERSION_INFO="%s"' % self.distribution.get_version())
            opts.append(cpp_flag(self.compiler))
            if has_flag(self.compiler, '-fvisibility=hidden'):
                opts.append('-fvisibility=hidden')
            opts.append('-DCGAL_DEBUG=1')
        elif ct == 'msvc':
            opts.append('/DVERSION_INFO=\\"%s\\"' % self.distribution.get_version())
            opts.append('/DCGAL_DEBUG=1')
        for ext in self.extensions:
            ext.extra_compile_args = opts
            ext.extra_link_args = link_opts

        build_ext.build_extensions(self)

version_ns = {}
with open(os.path.join(here, 'skgeom', '_version.py')) as f:
    exec(f.read(), {}, version_ns)

# Static metadata (name, dependencies, packages, …) lives in pyproject.toml.
# setup.py only provides what must be computed at build time: the C++ extension
# modules and the version read from skgeom/_version.py.
setup(
    version=version_ns['__version__'],
    ext_modules=ext_modules,
    cmdclass={'build_ext': BuildExt},
    zip_safe=False,
)
