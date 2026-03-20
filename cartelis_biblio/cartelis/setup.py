from setuptools import setup, find_packages

setup(
    name="cartelis",              # nom sur PyPI (doit être unique)
    version="1.7.0",
    author="Adam El Hachimi",
    author_email="adam.elhachimi@cartelis.com",
    description="Normalisation des noms et prénoms (nettoyage, patterns, détection d’anomalies)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/vous/ma-biblio",
    packages=find_packages(),      # trouve automatiquement vos paquets
    package_data={"cartelis.name_normalizer": ["data/*.csv", "data/*.xlsx"]},  # inclut les fichiers de données
    python_requires=">=3.8",
    install_requires=[             # vos dépendances externes, ex:
        # "requests>=2.28",
        # "numpy>=1.21",
    ],

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)