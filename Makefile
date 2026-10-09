.PHONY: help dev backend-dev frontend-dev install test eval up down clean

help:
	@echo "Available commands:"
	@echo "  make dev          - Run both backend and frontend locally"
	@echo "  make backend-dev  - Run FastAPI with reload on port 8000"
	@echo "  make frontend-dev - Run Vite React frontend on port 5173"
	@echo "  make eval         - Run benchmark evaluation suite & generate HTML report"
	@echo "  make clean        - Remove caches and generated artifacts"

dev:
	@echo "Starting development environment..."
	(cd backend && uvicorn app.main:app --reload --reload-dir app --port 8000) & (cd frontend && npm run dev)

backend-dev:
	cd backend && uvicorn app.main:app --reload --reload-dir app --port 8000

frontend-dev:
	cd frontend && npm run dev

eval:
	cd backend && PYTHONPATH=. python3 app/eval/run_eval.py && python3 app/eval/report.py && python3 app/eval/adversarial.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf backend/data/*.db backend/data/chroma
