.PHONY: run test clean

run:
	docker compose up --build

test:
	pytest

clean:
	docker compose down --remove-orphans
	rm -rf data/work/convert/* data/work/process/* data/output/*