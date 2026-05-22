import os
from os.path import join
from pythonforandroid.recipes.numpy import NumpyRecipe as _NumpyRecipe


class NumpyRecipe(_NumpyRecipe):
    # pypi.python.org decommissioned; use GitHub archive instead
    url = 'https://github.com/numpy/numpy/archive/v{version}.tar.gz'
    patches = ['patches/remove-default-paths.patch']

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        # npy_math.h declares math wrappers (npy_sqrt, npy_tanh, …) as
        # `static inline` via NPY_INPLACE.  In the HOST build that p4a runs
        # alongside the Android build, GCC 13 generates R_X86_64_PC32
        # relocations for static-inline forward declarations without bodies.
        # The linker then refuses to include them in a shared object
        # (_multiarray_umath.so), reporting "undefined symbol 'npy_sqrt'".
        # Removing `static` makes the declarations extern — resolved normally
        # via -lnpymath at link time — without changing Android runtime behaviour.
        npy_math_h = join(
            self.get_build_dir(arch.arch),
            'numpy', 'core', 'include', 'numpy', 'npy_math.h',
        )
        if os.path.exists(npy_math_h):
            with open(npy_math_h) as f:
                content = f.read()
            patched = content.replace(
                '#define NPY_INPLACE static inline',
                '#define NPY_INPLACE  /* ANDROID_FIX: extern linkage avoids PC32 in .so */',
            )
            if patched != content:
                with open(npy_math_h, 'w') as f:
                    f.write(patched)

    def build_compiled_components(self, arch):
        # NPY_DISABLE_SVML=1: can_link_svml() always returns True on Linux
        # x86_64 regardless of NPY_CPU_DISPATCH.  Without this, numpy tries to
        # load the SVML git submodule which is absent in the GitHub tarball.
        # NPY_CPU_DISPATCH='': compile zero runtime-dispatch variants, avoiding
        # clang-14 rejecting -mavx5124fmaps / -mavx5124vnniw (AVX-512 KNM).
        os.environ['NPY_DISABLE_SVML'] = '1'
        os.environ['NPY_CPU_BASELINE'] = 'min'
        os.environ['NPY_CPU_DISPATCH'] = ''
        os.environ['CPU_BASELINE'] = 'min'   # compat: older numpy
        os.environ['CPU_DISPATCH'] = ''
        # GCC 13 (Ubuntu 24.04) raises -Werror=maybe-uninitialized on avx512pfintrin.h
        # and clang 17 (NDK r26b) rejects undeclared AVX-512 KNM intrinsics.
        # Both are capability-check probes; suppressing the errors lets numpy
        # mark those features as unavailable and continue.
        cflags = os.environ.get('CFLAGS', '')
        if '-Wno-maybe-uninitialized' not in cflags:
            os.environ['CFLAGS'] = cflags + ' -Wno-maybe-uninitialized -Wno-error=maybe-uninitialized'
        super().build_compiled_components(arch)


recipe = NumpyRecipe()
