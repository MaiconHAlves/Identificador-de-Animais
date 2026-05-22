import os
from pythonforandroid.recipes.python3 import Python3Recipe as _Python3Recipe


class Python3Recipe(_Python3Recipe):
    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        # Android Bionic libc (x86_64) lacks setgrent/getgrent/endgrent.
        # configure detects HAVE_GETGRENT via grp.h header presence, but the
        # functions themselves are missing → "implicit declaration" errors with
        # -Werror.  Insert #undef HAVE_GETGRENT before the #ifdef guard so the
        # grp_getgrall_impl block is skipped entirely on Android.
        build_dir = self.get_build_dir(arch.arch)
        grp_path = os.path.join(build_dir, 'Modules', 'grpmodule.c')
        if not os.path.exists(grp_path):
            return
        with open(grp_path) as f:
            src = f.read()
        if 'ANDROID_BIONIC_FIX' in src:
            return
        patched = src
        if '#ifdef HAVE_GETGRENT' in src:
            # Strategy 1: undef before the existing ifdef guard
            patched = src.replace(
                '#ifdef HAVE_GETGRENT',
                '#undef HAVE_GETGRENT /* ANDROID_BIONIC_FIX */\n#ifdef HAVE_GETGRENT',
                1,
            )
        elif 'setgrent()' in src:
            # Strategy 2: code is not guarded — wrap the calls directly
            patched = src.replace(
                '\n    setgrent();\n',
                '\n#ifndef __ANDROID__ /* ANDROID_BIONIC_FIX */\n    setgrent();\n',
            )
            patched = patched.replace(
                '\n    endgrent();\n    return d;\n',
                '\n    endgrent();\n#endif /* __ANDROID__ */\n    return d;\n',
            )
        if patched != src:
            with open(grp_path, 'w') as f:
                f.write(patched)


recipe = Python3Recipe()
