.PHONY: install test panel mcp demo docker

install:
	pip install -r requirements-dev.txt

test:
	python -m pytest

panel:
	python -m uvicorn web.app:app --port 8600 --reload

mcp:
	python server.py

demo:
	python scripts/demo_traffic.py

docker:
	docker compose up --build
