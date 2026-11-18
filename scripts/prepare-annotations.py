"""Checkout entry point; the installed wheel supplies the same implementation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dtm_pipeline.annotation_cli import main
if __name__=='__main__':main()
