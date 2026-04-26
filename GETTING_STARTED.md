# 🚀 EarthAI Platform - Getting Started (5 Minutes)

## ⚡ Quick Start (Docker)

### Step 1: Prerequisites
```bash
# Ensure Docker and Docker Compose are installed
docker --version
docker-compose --version
```

### Step 2: Clone & Configure
```bash
cd earth-ai-platform
cp .env.example .env
# Edit .env if needed (optional for demo)
```

### Step 3: Start Services
```bash
docker-compose up -d
```

### Step 4: Wait for Services
```bash
# Check status (wait 30-60 seconds for all services)
docker-compose ps

# View logs if needed
docker-compose logs -f api
```

### Step 5: Access Platform
| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/api/docs |
| **Grafana** | http://localhost:3001 (admin/admin) |

---

## 💬 Try the Chatbot

### Example 1: Simple Prediction
```
Go to: http://localhost:3000 → "Chatbot" tab
Type: "Predict landslide risk for the mountains"
Click: Send

Expected: Bot recognizes intent, suggests next steps
```

### Example 2: Research Search
```
Type: "Show me recent papers on deep learning for predictions"
Click: Send

Expected: Bot searches literature database, returns results
```

### Example 3: Create Task
```
Type: "Train a model to predict floods in my region"
Click: Send → "Proceed" button

Expected: Task created, appears in Dashboard
```

---

## 📊 Monitor Task Progress

1. Go to: **Tasks** tab
2. Click on any task to see:
   - Real-time progress bar
   - Pipeline stage status
   - Execution logs
   - Estimated completion time

---

## 📈 View System Status

1. Go to: **System Status** tab
2. See:
   - System health percentage
   - Active tasks count
   - Service status (all green = good)
   - Resource usage (CPU, Memory)

---

## 🗺️ Visualize Results

1. Go to: **Visualizations** tab
2. Select a completed task
3. Choose format:
   - 🗺️ **Map** - Interactive geospatial map
   - 📊 **Charts** - Statistical visualizations
   - 📋 **Table** - Data table
   - 📄 **Report** - PDF report

---

## 🔧 Troubleshooting

### Services won't start?
```bash
# Check Docker
docker-compose logs api

# Try rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Want to stop everything?
```bash
docker-compose down
```

### Need to reset database?
```bash
docker-compose down -v
docker-compose up -d
```

---

## 📚 Learn More

- **Full Setup Guide**: See `DEPLOYMENT_GUIDE.md`
- **API Documentation**: Open `http://localhost:8000/api/docs`
- **Architecture Details**: See `README.md`
- **Build Summary**: See `BUILD_SUMMARY.md`

---

## 🎯 What You Can Do

✅ **With Chatbot:**
- Ask for predictions (landslide, flood, drought, earthquake, crop yield)
- Search for latest research papers
- Get recommendations for data sources
- Train custom models

✅ **With Dashboard:**
- See system statistics
- Track task history
- View user analytics
- Monitor resource usage

✅ **With Tasks:**
- Create new analysis tasks
- Monitor real-time progress
- View execution logs
- Cancel if needed

✅ **With Visualizations:**
- View results on interactive maps
- Generate charts and graphs
- Export results as reports
- Download datasets

---

## 🔐 Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| Grafana | admin | admin |
| PgAdmin | admin@earthai.com | admin |
| API | (no auth needed for demo) | - |

---

## 📞 Need Help?

1. **API Documentation**: http://localhost:8000/api/docs
2. **System Status**: http://localhost:3001/d/earthai (Grafana)
3. **Logs**: `docker-compose logs [service-name]`
4. **Documentation**: See DEPLOYMENT_GUIDE.md

---

## 🎓 Example Workflows

### Workflow 1: Landslide Risk Analysis
```
Dashboard → Quick Start → 🏔️ Landslide Susceptibility
→ Task created → Monitoring → Results ready
→ Visualizations → View map
```

### Workflow 2: Research & Model Training
```
Chatbot → "Find research on flood prediction"
→ Browse papers → "Train model with insights"
→ Task created → Monitor progress
→ Download results
```

### Workflow 3: Custom Analysis
```
Chatbot → Describe your analysis need
→ Chatbot suggests task type
→ Review parameters → Proceed
→ Monitor in Tasks tab
→ View results when complete
```

---

## ⚙️ System Components

The platform includes:

- **API Server**: FastAPI (http://localhost:8000)
- **Frontend**: React (http://localhost:3000)
- **Chatbot**: NLP-powered conversation
- **Database**: PostgreSQL
- **Cache**: Redis
- **Workers**: Celery (background jobs)
- **Monitoring**: Prometheus + Grafana
- **ML Tracking**: MLflow
- **Admin**: PgAdmin for database

---

## ✨ Key Features

🤖 **AI Chatbot** - Natural language task creation  
📚 **Literature Integration** - Auto-updated research  
🔄 **Task Orchestration** - Automated pipelines  
📊 **Visualizations** - Interactive maps & charts  
📈 **Real-time Monitoring** - WebSocket updates  
🐳 **Docker Ready** - One-command deployment  
🔍 **Full Observability** - Logs, metrics, traces  

---

## 🎉 Next Steps

1. **Explore the UI** - Click around, see what's available
2. **Try a Task** - Create a landslide prediction task
3. **Check Monitoring** - View system status and logs
4. **Read Documentation** - Deep dive into features
5. **Deploy to Cloud** - When ready for production

---

**Happy analyzing! 🌍🚀**

For detailed setup, see `DEPLOYMENT_GUIDE.md`  
For technical details, see `README.md`
