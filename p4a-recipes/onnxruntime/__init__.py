"""
p4a recipe: onnxruntime 1.16.3 para Android arm64/x86_64.

Wheel confirmado disponível no PyPI:
  aarch64: onnxruntime-1.16.3-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (5.8 MB)
  x86_64:  onnxruntime-1.16.3-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

Nota: hostpython3 do p4a não tem pip — usa python3.11 do sistema (que tem pip instalado).
"""
import os
import subprocess
from pythonforandroid.recipe import Recipe
from pythonforandroid.logger import info


class OnnxruntimeRecipe(Recipe):
    version = '1.16.3'
    name = 'onnxruntime'
    depends = ['python3']
    site_packages_name = 'onnxruntime'
    call_hostpython_via_targetpython = False
    install_in_hostpython = False

    def should_build(self, arch):
        site = self.ctx.get_site_packages_dir(arch)
        return not os.path.exists(os.path.join(site, 'onnxruntime'))

    def build_arch(self, arch):
        info(f'[onnxruntime] Instalando {self.version} para {arch.arch}')
        site = self.ctx.get_site_packages_dir(arch)

        platform_map = {
            'arm64-v8a':   'manylinux_2_17_aarch64',
            'x86_64':      'manylinux_2_17_x86_64',
            'armeabi-v7a': 'manylinux_2_17_armv7l',
        }
        platform = platform_map.get(arch.arch, 'manylinux_2_17_aarch64')

        # Usar python3.11 do sistema (tem pip); hostpython3 do p4a não tem.
        subprocess.check_call([
            'python3.11', '-m', 'pip', 'install',
            '--no-deps', '--no-compile',
            '--target', site,
            '--platform', platform,
            '--python-version', '3.11',
            '--only-binary', ':all:',
            f'onnxruntime=={self.version}',
        ])
        info(f'[onnxruntime] OK — {platform} wheel instalado em {site}')


recipe = OnnxruntimeRecipe()
