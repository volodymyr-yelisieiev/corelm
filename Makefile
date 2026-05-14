.PHONY: test bench direct-bench demo checksums full clean release-check editable-check wheel-check studio-service studio-desktop studio-build studio-test

test:
	PYTHONPATH=. python -m pytest -q

bench:
	PYTHONPATH=. python -m benches.runner --out reports/benchmark_latest.json --readiness-out reports/publication_readiness.json

direct-bench:
	PYTHONPATH=. python -m services.core_service.corelm_studio.benchmark_cli run --profile-id builtin-runtime-conformance

demo:
	PYTHONPATH=. python -m corelm.cli demo --session examples/demo_session.json

checksums:
	python tools/generate_checksums.py

clean:
	python tools/clean_release_tree.py

editable-check:
	bash tools/validate_local_variants.sh

wheel-check:
	bash tools/validate_local_variants.sh

release-check: test bench demo checksums
	python tools/build_full_spectrum_readiness.py

full: release-check

studio-service:
	PYTHONPATH=. python -m services.core_service.corelm_studio

studio-desktop:
	npm run desktop:dev

studio-build:
	npm run desktop:build

studio-test:
	PYTHONPATH=. python -m pytest -q
	npm run desktop:test
