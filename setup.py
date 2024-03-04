import setuptools
import impl.constants

setuptools.setup(
    name="onectf",
    version=impl.constants.version,
    packages=setuptools.find_packages(),
    install_requires=[x.strip() for x in open("requirements.txt").readlines()],
    entry_points={
        'console_scripts': [
            'onectf = main:main',
        ],
    },
)