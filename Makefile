# Requires GNU Make; on Windows use Git Bash or `nmake`-compatible usage is not supported.
PYTHON ?= python
export PYTHONPATH := src

.PHONY: import-check editable test

# Verify package imports without editable install
import-check:
	$(PYTHON) -c "import structural_tree_app; from structural_tree_app.main import bootstrap_example; print('import-check: ok')"

test:
	$(PYTHON) -m pytest tests/ -q

# Optional: pip install -e . then import-check can also use system python
editable:
	$(PYTHON) -m pip install -e .
