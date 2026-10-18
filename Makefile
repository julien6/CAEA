.DEFAULT_GOAL := help

.PHONY: help verify-artifact unpack-artifact paper paper-clean inspect
paper:
	cd paper/icaart && latexmk -pdf -interaction=nonstopmode -halt-on-error submission.tex
paper-clean:
	cd paper/icaart && latexmk -c submission.tex
inspect:
	git status --short

# Scientific tests and analysis execute in Slurm via poc/scripts/*.sh, never here.

help:
	@echo "Reviewer artifact: make verify-artifact or make unpack-artifact"
	@echo "See docs/REPRODUCIBILITY.md for Slurm-based scientific reproduction."
verify-artifact:
	python3 tools/review_artifact.py
unpack-artifact:
	python3 tools/review_artifact.py --unpack
