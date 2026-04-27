import glob
import os
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
            # Disable runtime execution in two places:
            # 1. check_func kwarg: call=True → call=False
            # 2. check_funcs_once dict comprehension: (f, True) → (f, False)
            #    This dict is passed as call= to config.check_funcs_once which
            #    runs ARM64 binaries on the x86_64 host during cross-compilation.
            patched = content.replace('call=True', 'call=False')
            patched = patched.replace(
                'call = dict([(f, True) for f in funcs_name])',
                'call = dict([(f, False) for f in funcs_name])',
            )
            if patched != content:
                with open(setup_path, 'w') as f:
                    f.write(patched)
        # Disable AVX-512 dispatch — WSL2 virtual CPU does not expose AVX-512
        # and g++ fails to compile simd_qsort.dispatch.avx512_skx.cpp.
        os.environ['CPU_BASELINE'] = 'min'
        os.environ['CPU_DISPATCH'] = ''
        super().build_compiled_components(arch)


recipe = NumpyRecipe()
