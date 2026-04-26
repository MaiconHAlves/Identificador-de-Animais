from pythonforandroid.recipes.numpy import NumpyRecipe as _NumpyRecipe


class NumpyRecipe(_NumpyRecipe):
    # pypi.python.org decommissioned; numpy 1.26.4 was never published as .zip
    # GitHub archive is the most stable source for any tagged release
    url = 'https://github.com/numpy/numpy/archive/v{version}.tar.gz'


recipe = NumpyRecipe()
