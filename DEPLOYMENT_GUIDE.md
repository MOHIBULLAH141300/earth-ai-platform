# EarthAI Platform - Complete Deployment & Usage Guide

## 🌍 Overview

EarthAI Platform is an advanced AI-driven system for Earth system modeling, environmental hazard prediction, and climate analysis. It integrates:

- **Real-time Chatbot Interface** - Natural language interaction with the system
- **Task Orchestration Engine** - Automated pipeline management
- **Literature Integration** - Latest research automatically incorporated
- **ML/DL/RL Models** - Ensemble learning for predictions
- **Interactive Visualizations** - Web-based mapping and charting
- **Monitoring & Deployment** - Production-ready infrastructure

---

## 📋 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   User Interface Layer                       │
│        (React Frontend + Chatbot Interface)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│            API Gateway (FastAPI)                            │
│  ✓ Chatbot Processing                                       │
│  ✓ Task Management                                          │
│  ✓ Literature Integration                                   │
│  ✓ Model Serving                                            │
└────┬─────────────┬──────────────┬──────────────┬────────────┘
     │             │              │              │
┌────▼──┐   ┌────▼─────┐  ┌─────▼────┐  ┌────▼────┐
│ Data  │   │  Models  │  │ Research │  │ Modeling│
│Layer  │   │  Engine  │  │ Scraper  │  │ Services│
└───────┘   └──────────┘  └──────────┘  └─────────┘
     │             │              │              │
└────┬─────────────┬──────────────┬──────────────┘
     │
┌────▼──────────────────────────────────────────┐
│   Infrastructure Layer                        │
│  Redis │ PostgreSQL │ Celery │ MLflow        │
└───────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.11+
- Node.js 18+ (for frontend development)
- 8GB RAM minimum

### 1. Clone & Configure

```bash
# Navigate to project
cd earth-ai-platform

# Create environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Start with Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Check service status
docker-compose ps
```

### 3. Access the Platform

Once all services are running:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | - |
| **API Docs** | http://localhost:8000/api/docs | - |
| **Grafana** | http://localhost:3001 | admin/admin |
| **Prometheus** | http://localhost:9091 | - |
| **MLflow** | http://localhost:5000 | - |
| **PgAdmin** | http://localhost:5050 | admin@earthai.com/admin |

---

## 💬 Chatbot Interface Usage

### Example Interactions

1. **Landslide Susceptibility Prediction**
   ```
   User: "Predict landslide risk for the Himalayas region from 2023 to 2024"
   Bot: Detects intent → Creates task → Starts pipeline
   ```

2. **Research Literature Search**
   ```
   User: "Show me latest research on flood prediction using deep learning"
   Bot: Scrapes ArXiv, DOAJ → Returns top papers with insights
   ```

3. **Custom Model Training**
   ```
   User: "Train a neural network to predict crop yields in Africa"
   Bot: Collects data → Trains model → Shows results
   ```

### Supported Task Types

- `landslide_susceptibility` - Landslide hazard mapping
- `flood_prediction` - Flood risk analysis
- `earthquake_damage` - Earthquake impact assessment
- `drought_monitoring` - Drought tracking
- `crop_yield_prediction` - Agricultural forecasting
- `climate_analysis` - Climate trend analysis

---

## 📊 Task Management

### Creating a Task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "task_type": "landslide_susceptibility",
    "parameters": {
      "bounds": {
        "min_lon": 75.5,
        "max_lon": 88.3,
        "min_lat": 26.8,
        "max_lat": 35.5
      },
      "date_range": {
        "start_date": "2023-01-01",
        "end_date": "2024-01-01"
      },
      "data_sources": ["sentinel", "modis"]
    },
    "priority": "high"
  }'
```

### Monitoring Task Progress

```bash
# Get task status
curl http://localhost:8000/api/tasks/{task_id}

# Get task execution logs
curl http://localhost:8000/api/tasks/{task_id}/logs

# Real-time updates via WebSocket
wscat -c ws://localhost:8000/ws/tasks/{task_id}
```

### Cancel a Task

```bash
curl -X POST http://localhost:8000/api/tasks/{task_id}/cancel
```

---

## 🔍 Literature Integration

### Automatic Literature Scraping

The system automatically scrapes research from:
- **ArXiv** - Latest AI/ML papers
- **DOAJ** - Open access journals
- **RSS Feeds** - Real-time research updates

### Search Literature

```bash
# Search knowledge base
curl "http://localhost:8000/api/literature/search?topic=landslide+susceptibility&limit=10"

# Get insights for task type
curl http://localhost:8000/api/literature/insights/landslide_susceptibility

# Trigger manual scraping
curl -X POST http://localhost:8000/api/literature/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "topics": ["landslide", "deep learning"],
    "days_back": 7,
    "max_results": 50
  }'
```

---

## 🗺️ Visualizations

### Generate Visualizations

```bash
curl -X POST http://localhost:8000/api/visualizations/create \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-uuid",
    "output_format": "map",
    "include_metrics": true
  }'
```

### Supported Formats
- `map` - Interactive geospatial maps
- `chart` - Statistical visualizations
- `table` - Data tables
- `report` - PDF/HTML reports

---

## 🔧 System Configuration

### Environment Variables

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=production

# Database
POSTGRES_DB=earthai
POSTGRES_USER=earthai
POSTGRES_PASSWORD=secure-password

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Google Earth Engine (for satellite data)
GEE_PROJECT_ID=your-gee-project

# API Keys (optional)
ARXIV_API_KEY=
OPENWEATHER_API_KEY=
```

---

## 📈 Monitoring & Logging

### Prometheus Metrics

Access http://localhost:9091 to view:
- API response times
- Task queue length
- Model training progress
- Database queries
- Memory/CPU usage

### Grafana Dashboards

Pre-configured dashboards at http://localhost:3001:
- System Health
- Task Performance
- Model Accuracy
- Resource Utilization

### Logs

View logs in real-time:

```bash
# API server logs
docker-compose logs -f api

# Celery worker logs
docker-compose logs -f celery-worker

# Database logs
docker-compose logs -f postgres
```

---

## 🧪 Testing & Development

### Run Tests

```bash
# Unit tests
pytest tests/ -v

# Integration tests
pytest tests/integration/ -v

# Coverage report
pytest tests/ --cov=services --cov-report=html
```

### Development Mode

```bash
# Without Docker (local development)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run API server
python api/enhanced_api.py

# In another terminal - run Celery worker
celery -A api.enhanced_api worker --loglevel=info
```

---

## 📡 API Endpoints Reference

### Chatbot
- `POST /api/chat` - Send message
- `GET /api/chat/history/{user_id}` - Get conversation history

### Tasks
- `POST /api/tasks` - Create new task
- `GET /api/tasks/{task_id}` - Get task status
- `GET /api/tasks/user/{user_id}` - List user tasks
- `POST /api/tasks/{task_id}/cancel` - Cancel task
- `GET /api/tasks/{task_id}/logs` - Get execution logs

### Literature
- `POST /api/literature/scrape` - Scrape research
- `GET /api/literature/search` - Search papers
- `GET /api/literature/insights/{task_type}` - Get research insights

### Models
- `POST /api/models/train` - Train model
- `POST /api/models/predict` - Make predictions
- `GET /api/models` - List available models

### Visualizations
- `POST /api/visualizations/create` - Create visualization
- `GET /api/visualizations/{viz_id}` - Get visualization

### System
- `GET /api/system/status` - System health
- `GET /api/system/health` - Health check
- `GET /api/users/{user_id}/analytics` - User analytics

---

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Rebuild images
docker-compose build --no-cache

# Scale workers
docker-compose up -d --scale celery-worker=3

# Execute commands in container
docker-compose exec api python -c "import services; print('OK')"

# Clean up volumes
docker-compose down -v
```

---

## 🚨 Troubleshooting

### Service Connection Issues

```bash
# Check if services are running
docker-compose ps

# Restart specific service
docker-compose restart api

# Check service logs for errors
docker-compose logs api | tail -50
```

### Database Issues

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U earthai -d earthai

# Reset database
docker-compose down -v
docker-compose up postgres
```

### Memory Issues

```bash
# Check resource usage
docker stats

# Limit container resources
# Edit docker-compose.yml and add:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

---

## 📚 Advanced Features

### Custom Model Integration

Add custom models in `services/ml_dl_training_pipeline.py`:

```python
class CustomModel(BaseModel):
    def predict(self, X):
        # Your model implementation
        pass
```

### Extending the Chatbot

Add new intents in `services/chatbot_nlp.py`:

```python
custom_patterns = {
    CustomIntentType.NEW_FEATURE: [r"pattern1", r"pattern2"]
}
```

### Scheduling Tasks

Configure periodic tasks in `config/celery_config.py`:

```python
app.conf.beat_schedule = {
    'scrape-literature': {
        'task': 'services.literature_scraper.scrape_latest',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}
```

---

## 🤝 Contributing

To contribute improvements:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

---

## 📞 Support

For issues, questions, or suggestions:
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check docs/README.md
- **Email**: support@earthai-platform.com

---

## 🎯 Next Steps

1. **Explore the Dashboard** - Get familiar with the UI
2. **Try a Quick Task** - Start with a landslide prediction
3. **Review Literature** - Check latest research insights
4. **Configure Custom Tasks** - Set up domain-specific workflows
5. **Scale to Production** - Deploy on cloud (AWS, GCP, Azure)

---

Happy modeling! 🚀
