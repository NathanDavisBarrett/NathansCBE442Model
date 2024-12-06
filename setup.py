from setuptools import setup, find_packages

setup(
    name='NathansCBE442Model',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
          'matplotlib',
          'numpy',
          'pyomo',
          'scipy'
      ]
)

#Make sure they've got PyomoTools installed too.