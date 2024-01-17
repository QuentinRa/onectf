import setuptools
import impl.constants

setuptools.setup(
    name="onectf",
    version=impl.constants.version,
    packages=setuptools.find_packages(),
    install_requires=[
        "beautifulsoup4<=4.12.2",
        "certifi<=2023.11.17",
        "charset-normalizer<=3.3.2",
        "html2text<=2020.1.16",
        "idna<=3.6",
        "pyfiglet<=1.0.2",
        "requests<=2.31.0",
        "soupsieve<=2.5",
        "urllib3<=2.1.0"
    ],
    entry_points={
        'console_scripts': [
            'onectf = main:main',
        ],
    },
)