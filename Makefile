size-report:
	@find . -type f -not -path "./.git/*" -printf "%s %p\n" | sort -nr | head -30

PYTHON ?= python3
VERILATOR ?= verilator
RTL_SRCS := $(wildcard rtl/*.v)
BOARD_DEVICE ?=

.PHONY: all validate test test-static test-sim lint audit-arith gen-lut cosim-vectors cosim-gkp sim-axilite sim-packer sim-safety sim-prbs extract-regs cdc-analyze parse-cdc cdc-gate-check cdc-manifest-check lint-verilator lint-verilator-strict check-source-clean clean-generated size-report cdc-signoff-package preboard-check implementation-gate vivado-signoff-package vivado-bitstream source-package proof-package proof-package-local proof-package-board proof-package-strict proof-manifest-local proof-manifest-board validate-release validate-release-local validate-release-board validate-release-strict make-validate-log release-prereqs release-prereqs-local release-validate release-validate-local release-validate-board release-proof-local board-smoke

all:
	@echo "Available targets: validate, test, lint, audit-arith, gen-lut, cosim-vectors, cosim-gkp, sim-axilite, sim-packer, sim-safety, extract-regs, cdc-analyze, parse-cdc, cdc-gate-check, lint-verilator, clean-generated, size-report, cdc-signoff-package, preboard-check, implementation-gate, vivado-signoff-package, vivado-bitstream, source-package, proof-package-local, proof-package-board, release-prereqs, release-validate"

# Keep tests before generated heavy artifacts are recreated, otherwise compact-package
# tests correctly fail.
validate: clean-generated check-source-clean test lint gen-lut extract-regs cdc-analyze
	@echo "Validation completed. Note: this does not replace Vivado elaboration/timing."

test:
	PYTHONPATH=. $(PYTHON) -m unittest discover -s tests

test-static:
	PYTHONPATH=. $(PYTHON) -m unittest tests.test_packet_parser tests.test_golden_model tests.test_soft_weight_model tests.test_rtl_sanity_check_behavior

test-sim:
	$(MAKE) sim-axilite
	$(MAKE) sim-packer
	$(MAKE) sim-safety
	$(MAKE) sim-prbs
	$(MAKE) cosim-gkp

lint:
	$(PYTHON) scripts/rtl_sanity_check.py

audit-arith:
	$(PYTHON) scripts/audit_rtl_arithmetic.py

gen-lut:
	$(PYTHON) scripts/generate_reciprocal_lut.py

extract-regs:
	$(PYTHON) scripts/extract_register_map.py

cdc-analyze: extract-regs
	$(PYTHON) scripts/analyze_cdc_crossings.py

lint-verilator:
	@if command -v $(VERILATOR) >/dev/null 2>&1; then \
		$(VERILATOR) --lint-only -Wall --timing $(RTL_SRCS); \
	else \
		echo "Verilator not installed; skipping lint-verilator"; \
	fi

lint-verilator-strict:
	@if command -v $(VERILATOR) >/dev/null 2>&1; then \
		$(VERILATOR) --lint-only -Wall --timing \
			--top-module waveform_brain_axi4lite_cdc_top \
			-Wno-fatal \
			-Wno-MULTITOP \
			-Wno-PINCONNECTEMPTY \
			-Wno-PINMISSING \
			-Wno-TIMESCALEMOD \
			-Wno-EOFNEWLINE \
			-Wno-DECLFILENAME \
			$(RTL_SRCS); \
	else \
		echo "Verilator not installed; release lint requires it"; \
		exit 1; \
	fi

parse-cdc:
	@if [ -f reports/cdc_critical.rpt ]; then \
		$(PYTHON) scripts/parse_cdc_report.py reports/cdc_critical.rpt --json-out reports/cdc_critical_summary.json; \
	else \
		echo "reports/cdc_critical.rpt not found; run Vivado report_cdc first."; \
	fi

cdc-gate-check:
	@if [ -f reports/cdc_full.rpt ]; then \
		$(PYTHON) scripts/parse_cdc_report.py reports/cdc_full.rpt --json-out reports/cdc_full_summary.json; \
	else \
		echo "reports/cdc_full.rpt not found; run Vivado report_cdc first."; \
	fi
	@if [ -f reports/cdc_critical.rpt ]; then \
		$(PYTHON) scripts/parse_cdc_report.py reports/cdc_critical.rpt --json-out reports/cdc_critical_summary.json --fail-on-critical; \
	else \
		echo "reports/cdc_critical.rpt not found; run Vivado report_cdc first."; \
	fi
	$(MAKE) cdc-manifest-check

cdc-manifest-check:
	$(PYTHON) scripts/verify_cdc_manifest.py

cosim-vectors:
	$(PYTHON) scripts/generate_gkp_cosim_vectors.py --count 64

cosim-gkp:
	$(PYTHON) scripts/run_gkp_cosim.py

sim-axilite:
	$(PYTHON) scripts/run_axilite_regfile_sim.py

sim-packer:
	$(PYTHON) scripts/run_packer_axis_sim.py

sim-safety:
	$(PYTHON) scripts/run_safety_monitor_sim.py

sim-prbs:
	$(PYTHON) scripts/run_prbs_datapath_sim.py

clean-generated:
	$(PYTHON) scripts/clean_generated_artifacts.py

check-source-clean:
	$(PYTHON) scripts/check_source_tree_clean.py

cdc-signoff-package:
	$(PYTHON) scripts/package_cdc_signoff.py

preboard-check:
	$(PYTHON) scripts/preboard_check.py --mode proof

implementation-gate:
	$(PYTHON) scripts/implementation_gate.py

vivado-signoff-package:
	$(PYTHON) scripts/package_vivado_signoff.py

vivado-bitstream:
	@if command -v vivado >/dev/null 2>&1; then \
		vivado -mode batch -source scripts/waveform_brain_bitstream.tcl; \
	else \
		echo "Vivado not installed; cannot run bitstream/report flow"; \
		exit 1; \
	fi

source-package:
	$(PYTHON) scripts/build_release_archive.py --mode source

proof-package:
	$(PYTHON) scripts/build_release_archive.py --mode proof-local

proof-package-local:
	$(PYTHON) scripts/build_release_archive.py --mode proof-local

proof-package-board:
	$(PYTHON) scripts/build_release_archive.py --mode proof-board

proof-package-strict:
	$(PYTHON) scripts/build_release_archive.py --mode proof-board

proof-manifest-local:
	$(PYTHON) scripts/generate_proof_manifest.py --mode proof-local

proof-manifest-board:
	$(PYTHON) scripts/generate_proof_manifest.py --mode proof-board

validate-release:
	$(MAKE) validate-release-local

validate-release-local:
	@latest_src=$$(ls -t dist/*-source-*.zip 2>/dev/null | head -1); \
	if [ -z "$$latest_src" ]; then \
		echo "No source archive found in dist/. Run make source-package first."; \
		exit 1; \
	fi; \
	$(PYTHON) scripts/validate_release_archive.py "$$latest_src" --mode source
	@latest_proof=$$(ls -t dist/*-proof-local-*.zip 2>/dev/null | head -1); \
	if [ -z "$$latest_proof" ]; then \
		echo "No proof archive found in dist/. Run make proof-package-local first."; \
		exit 1; \
	fi; \
	$(PYTHON) scripts/validate_release_archive.py "$$latest_proof" --mode proof-local

validate-release-strict:
	$(MAKE) validate-release-board

validate-release-board:
	@latest_src=$$(ls -t dist/*-source-*.zip 2>/dev/null | head -1); \
	if [ -z "$$latest_src" ]; then \
		echo "No source archive found in dist/. Run make source-package first."; \
		exit 1; \
	fi; \
	$(PYTHON) scripts/validate_release_archive.py "$$latest_src" --mode source
	@latest_proof=$$(ls -t dist/*-proof-board-*.zip 2>/dev/null | head -1); \
	if [ -z "$$latest_proof" ]; then \
		echo "No proof archive found in dist/. Run make proof-package-board first."; \
		exit 1; \
	fi; \
	$(PYTHON) scripts/validate_release_archive.py "$$latest_proof" --mode proof-board

make-validate-log:
	$(PYTHON) scripts/run_make_validate_with_log.py

release-prereqs:
	$(PYTHON) scripts/check_release_prereqs.py --mode proof-board

release-prereqs-local:
	$(PYTHON) scripts/check_release_prereqs.py --mode proof-local


release-validate-local:
	$(MAKE) make-validate-log
	$(MAKE) preboard-check
	$(MAKE) sim-axilite
	$(MAKE) sim-packer
	$(MAKE) sim-safety
	$(MAKE) sim-prbs
	$(MAKE) release-prereqs-local
	$(MAKE) proof-manifest-local
	$(MAKE) source-package
	$(MAKE) proof-package-local
	$(MAKE) validate-release-local
	@echo "release-validate-local complete"

release-validate-board:
	@if [ -z "$(BOARD_DEVICE)" ]; then \
		echo "BOARD_DEVICE is required for board proof flow (example: make release-validate-board BOARD_DEVICE=<device-id>)"; \
		exit 1; \
	fi
	$(MAKE) make-validate-log
	$(MAKE) preboard-check
	$(MAKE) sim-axilite
	$(MAKE) sim-packer
	$(MAKE) sim-safety
	$(MAKE) sim-prbs
	$(MAKE) vivado-bitstream
	$(MAKE) implementation-gate
	$(MAKE) board-smoke BOARD_DEVICE="$(BOARD_DEVICE)"
	$(MAKE) release-prereqs
	$(MAKE) proof-manifest-board
	$(MAKE) source-package
	$(MAKE) proof-package-board
	$(MAKE) validate-release-board
	@echo "release-validate-board complete"

release-validate: release-validate-board
	@echo "release-validate complete"

release-proof-local: release-validate-local
	@echo "release-proof-local complete"

board-smoke:
	@if [ -z "$(BOARD_DEVICE)" ]; then \
		echo "BOARD_DEVICE is required for board-smoke"; \
		exit 1; \
	fi
	$(PYTHON) board_tests/run_board_smoke.py --device "$(BOARD_DEVICE)" --reports-dir reports
