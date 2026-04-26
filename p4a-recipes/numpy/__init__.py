from pythonforandroid.recipes.numpy import NumpyRecipe as _NumpyRecipe


class NumpyRecipe(_NumpyRecipe):
    # pypi.python.org was decommissioned; packages from 2024+ only exist on pypi.org
    url = 'https://pypi.org/packages/source/n/numpy/numpy-{version}.zip'


recipe = NumpyRecipe()
