"""Bundle only the public Trump tutorial inputs, never dissertation datasets."""
from pathlib import Path
from shutil import copy2, rmtree
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildWithData(build_py):
    def run(self):
        super().run()
        source=Path(__file__).parent/'docs/data/trump'
        build=Path(self.build_lib).resolve()
        target=build/'dtm_pipeline/data'
        if target.exists():
            if not target.is_relative_to(build):raise ValueError('Unsafe package data target')
            rmtree(target)
        destination=target/'trump'
        destination.mkdir(parents=True,exist_ok=True)
        for name in ['corpus.csv','stopwords.txt','manifest.json','README.md']:
            copy2(source/name,destination/name)

setup(cmdclass={'build_py':BuildWithData})
