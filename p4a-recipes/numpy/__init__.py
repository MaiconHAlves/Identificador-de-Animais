import glob
from os.path import join
from pythonforandroid.recipes.numpy import NumpyRecipe as _NumpyRecipe


class NumpyRecipe(_NumpyRecipe):
    # pypi.python.org decommissioned; use GitHub archive instead
    url = 'https://github.com/numpy/numpy/archive/v{version}.tar.gz'
    patches = ['patches/remove-default-paths.patch']

    def build_compiled_components(self, arch):
        # numpy/core/setup.py's check_math_capabilities() calls check_func with
        # call=True, which compiles AND runs a test binary.  During arm64
        # cross-compilation on an x86_64 host the run step always fails.
        # Changing call=True → call=False turns it into a link-only check.
        # We use glob because the GitHub archive extracts to numpy-1.26.4/ which
        # p4a renames to numpy/, so the inner package sits at numpy/numpy/core/.
        matches = glob.glob(
            join(self.get_build_dir(arch.arch), '**', 'numpy', 'core', 'setup.py'),
            recursive=True,
        )
        if matches:
            setup_path = matches[0]
            with open(setup_path) as f:
                content = f.read()
            if 'call=True' in content:
                with open(setup_path, 'w') as f:
                    f.write(content.replace('call=True', 'call=False'))
        super().build_compiled_components(arch)


recipe = NumpyRecipe()
