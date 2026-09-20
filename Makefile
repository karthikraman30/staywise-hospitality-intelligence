.PHONY: all build download powerbi validate demo notebook pg-create pg-load pg-quality pg-validate db-up db-load db-quality db-validate db-down db-sqlite clean

PROJECT_ROOT := $(CURDIR)
PGDATABASE ?= staywise
PSQL := psql -d $(PGDATABASE) -v ON_ERROR_STOP=1

all: build powerbi

build:
	python3 scripts/build_staywise.py

powerbi:
	python3 scripts/build_powerbi_project.py

download:
	python3 scripts/build_staywise.py --download-only

validate:
	python3 scripts/validate_outputs.py
	python3 scripts/validate_dashboard.py

demo:
	python3 scripts/serve_dashboard.py

notebook:
	jupyter nbconvert --to notebook --execute --inplace notebooks/StayWise_Analysis_Notebook.ipynb

db-sqlite:
	python3 scripts/load_sqlite.py

# Local PostgreSQL (no Docker). Set PGUSER/PGPASSWORD or use ~/.pgpass; see .env.example.
pg-create:
	createdb $(PGDATABASE) || true

pg-load:
	$(PSQL) -f sql/01_schema.sql
	$(PSQL) -f sql/02_load_data.sql
	$(PSQL) -f sql/04_metric_views.sql
	$(PSQL) -f sql/05_powerbi_views.sql

pg-quality:
	$(PSQL) -f sql/03_quality_checks.sql

pg-validate:
	STAYWISE_PSQL_MODE=local python3 scripts/validate_database.py

# Docker PostgreSQL (alternative when no local server is available).
db-up:
	docker run --name staywise-postgres --detach --rm -e POSTGRES_DB=staywise -e POSTGRES_USER=staywise -e POSTGRES_PASSWORD=staywise -p 54329:5432 -v "$(PROJECT_ROOT):/workspace:ro" postgres:16-alpine

db-load:
	docker exec -i -w /workspace staywise-postgres psql -U staywise -d staywise -v ON_ERROR_STOP=1 -f sql/01_schema.sql
	docker exec -i -w /workspace staywise-postgres psql -U staywise -d staywise -v ON_ERROR_STOP=1 -f sql/02_load_data.sql
	docker exec -i -w /workspace staywise-postgres psql -U staywise -d staywise -v ON_ERROR_STOP=1 -f sql/04_metric_views.sql
	docker exec -i -w /workspace staywise-postgres psql -U staywise -d staywise -v ON_ERROR_STOP=1 -f sql/05_powerbi_views.sql

db-quality:
	docker exec -i -w /workspace staywise-postgres psql -U staywise -d staywise -v ON_ERROR_STOP=1 -f sql/03_quality_checks.sql

db-validate:
	python3 scripts/validate_database.py

db-down:
	-docker rm -f staywise-postgres

clean:
	find data/processed outputs excel -maxdepth 2 -type f -delete

