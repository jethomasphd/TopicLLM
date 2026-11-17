"""Bundle original Study 1 data and explicitly retained software-test fixtures."""
from pathlib import Path
from shutil import copy2,copytree
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildWithData(build_py):
    def run(self):
        super().run()
        source=Path(__file__).parent/'docs/data'
        target=Path(self.build_lib)/'dtm_pipeline/data'
        target.mkdir(parents=True,exist_ok=True)
        names=['demonstration_corpus.csv','demonstration_benchmark.csv','demonstration_ground_truth.csv','demonstration_stopwords.txt','study.json','study-demo.json','synthetic-integrity.json']
        for name in names: copy2(source/name,target/name)
        copytree(source/'study1',target/'study1',dirs_exist_ok=True)

setup(cmdclass={'build_py':BuildWithData})
