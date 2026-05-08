# TortIA Mundialista — Makefile
# Comandos útiles para desarrollo y despliegue

.PHONY: install dev-backend dev-frontend train test lint clean

# ── Setup ─────────────────────────────────────────────────────────────────────

install:
	@echo "📦 Instalando dependencias..."
	cd backend && pip install -r requirements.txt
	cd frontend && npm install
	cp -n backend/.env.example backend/.env || true
	@echo "✅ Listo. Edita backend/.env con tus API keys."

# ── Desarrollo ────────────────────────────────────────────────────────────────

dev-backend:
	@echo "🚀 Arrancando FastAPI en http://localhost:8000"
	cd backend && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "🌐 Arrancando React en http://localhost:5173"
	cd frontend && npm run dev

dev:
	@echo "🎯 Arrancando backend y frontend en paralelo..."
	$(MAKE) -j2 dev-backend dev-frontend

# ── ML Pipeline ───────────────────────────────────────────────────────────────

train:
	@echo "🧠 Entrenando modelos..."
	cd backend && python -m scripts.train

train-tune:
	@echo "🔬 Entrenando con búsqueda de hiperparámetros (lento)..."
	cd backend && python -m scripts.train --tune --n-trials 50

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	cd backend && pytest tests/ -v --tb=short

test-cov:
	cd backend && pytest tests/ --cov=. --cov-report=html
	@echo "Coverage report: backend/htmlcov/index.html"

# ── Build ─────────────────────────────────────────────────────────────────────

build-frontend:
	cd frontend && npm run build

# ── Limpieza ──────────────────────────────────────────────────────────────────

clean:
	find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find backend -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/dist
	@echo "🧹 Limpieza completa."

# ── Info ──────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "TortIA Mundialista — Comandos disponibles:"
	@echo ""
	@echo "  make install       Instala todas las dependencias"
	@echo "  make dev           Arranca backend + frontend en paralelo"
	@echo "  make dev-backend   Solo FastAPI (puerto 8000)"
	@echo "  make dev-frontend  Solo React (puerto 5173)"
	@echo "  make train         Entrena los modelos ML"
	@echo "  make train-tune    Entrena con Optuna (más lento, mejor resultado)"
	@echo "  make test          Corre los tests"
	@echo "  make build-frontend Construye el frontend para producción"
	@echo "  make clean         Elimina archivos temporales"
	@echo ""
