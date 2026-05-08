# ⚽ TortIA Mundialista — WC2026 Prediction Engine

> Motor de predicción en tiempo real para la Copa del Mundo 2026 usando Machine Learning.
> Predicciones de resultado (W/D/L), marcador exacto y bracket probabilístico via Monte Carlo.

[![CI/CD](https://github.com/cvtrujillo/TortIA_Mundialista/actions/workflows/deploy.yml/badge.svg)](https://github.com/cvtrujillo/TortIA_Mundialista/actions)
[![Frontend](https://img.shields.io/badge/Frontend-GitHub%20Pages-blue)](https://cvtrujillo.github.io/TortIA_Mundialista/)

## 🏗️ Stack

| Capa | Tecnología |
|------|-----------|
| Backend API | FastAPI + Uvicorn |
| ML Models | Dixon-Coles Poisson + XGBoost |
| Simulación | Monte Carlo (10k iteraciones) |
| Frontend | React + Vite + Tailwind CSS |
| Charts | Recharts |
| Deploy API | AWS Lambda + Mangum |
| Deploy Web | GitHub Pages |

## 🚀 Inicio rápido

### 1. Clonar y configurar

```bash
git clone https://github.com/cvtrujillo/TortIA_Mundialista.git
cd TortIA_Mundialista
make install
```

### 2. Configurar API keys

```bash
cp backend/.env.example backend/.env
# Editar backend/.env con tu token de football-data.org
```

Obtén tu token gratuito en: https://www.football-data.org/

### 3. Entrenar los modelos

```bash
make train
# Con búsqueda de hiperparámetros (tarda ~30min):
# make train-tune
```

### 4. Arrancar en desarrollo

```bash
make dev
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:5173
```

## 📁 Estructura del proyecto

```
TortIA_Mundialista/
├── backend/
│   ├── api/               # FastAPI endpoints
│   ├── etl/               # Ingesta y feature engineering
│   │   └── sources/       # Football-Data.org + FBref
│   ├── models/            # Poisson + XGBoost + HybridPredictor
│   ├── simulation/        # Monte Carlo tournament
│   ├── scripts/           # train.py
│   ├── tests/             # pytest
│   └── artifacts/         # Modelos serializados (gitignored)
├── frontend/
│   └── src/
│       ├── components/    # MatchPredictor, TeamCard, BracketView
│       ├── pages/         # Home, Tournament
│       ├── hooks/         # React Query hooks
│       └── api/           # Axios client
├── .github/workflows/     # CI/CD
└── Makefile               # Comandos de desarrollo
```

## 🧠 Modelos

### Dixon-Coles Poisson
Estima fuerza ofensiva/defensiva por equipo via MLE. Produce una matriz 9×9 de probabilidades de marcador con corrección para marcadores bajos (ρ ≈ -0.13).

### XGBoost Classifier
Clasificador 3-clases (W/D/L) sobre 19 features contextuales: Elo, xG, PPG rolling, altitud, descanso, viaje, H2H. Calibrado con regresión isotónica.

### Ensemble
```
P_final = 0.55 × P_xgb + 0.45 × P_poisson
```
α tuneado en Copa América 2024 + Euro 2024 (Brier score: 0.214 vs baseline 0.287).

## 🔧 Variables de entorno (GitHub Secrets)

Para el deploy completo configura estos secrets en tu repo:

| Secret | Descripción |
|--------|-------------|
| `VITE_API_BASE_URL` | URL del Lambda (ej: `https://xxx.lambda-url.us-east-1.on.aws`) |
| `FOOTBALL_DATA_TOKEN` | Token football-data.org |
| `RAPIDAPI_KEY` | Key RapidAPI (opcional) |
| `AWS_ACCESS_KEY_ID` | IAM con permisos Lambda + S3 |
| `AWS_SECRET_ACCESS_KEY` | Secret del IAM |
| `LAMBDA_URL` | URL pública del Lambda |
| `S3_BUCKET` | Bucket para artifacts |

Para activar el deploy de Lambda, añade una variable de repositorio:
- `DEPLOY_LAMBDA = true`

## 📊 API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Status de la API |
| `POST` | `/predict/match` | Predicción de partido |
| `POST` | `/predict/knockout` | Predicción eliminatoria |
| `POST` | `/predict/live-update` | Ingestar resultado en vivo |
| `POST` | `/tournament/simulate` | Simulación Monte Carlo |
| `GET` | `/tournament/groups` | Grupos WC2026 |
| `GET` | `/teams/{team}/stats` | Stats de equipo |
| `GET` | `/teams/rankings/elo` | Ranking Elo |

Documentación interactiva: `http://localhost:8000/docs`

## 🏆 GitHub Pages

El frontend se despliega automáticamente en cada push a `main`:
**https://cvtrujillo.github.io/TortIA_Mundialista/**

Para activar GitHub Pages en tu repo:
1. Settings → Pages → Source: **GitHub Actions**

## 📝 Licencia

MIT © Carol Trujillo
