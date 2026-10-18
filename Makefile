.DEFAULT_GOAL := help

.PHONY: help verify-artifact unpack-artifact paper paper-diagram paper-supplement paper-legacy inspect
paper: paper-diagram paper-supplement
	cd paper/icaart && latexmk -pdf -interaction=nonstopmode -halt-on-error research.tex
	cd paper/icaart && latexmk -pdf -interaction=nonstopmode -halt-on-error submission.tex
paper-supplement:
	cd paper/icaart && latexmk -pdf -interaction=nonstopmode -halt-on-error supplementary.tex
paper-diagram:
	cd paper/icaart/figures && latexmk -pdf -interaction=nonstopmode -halt-on-error caea_overview_standalone.tex
paper-legacy:
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
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
