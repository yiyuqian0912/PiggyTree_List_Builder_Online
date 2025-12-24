# 🐷 PiggyTree - Fantasy Sports Entry Builder

A web app for building **Underdog Fantasy Pick'em** entries with player lookup and team/opponent auto-fill.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-2.0+-green)

## ✨ Features

- **Player Lookup** - Type a name, auto-fills team/opponent/position via ESPN API
- **Drag & Drop** - Move entries between levels (1-4)
- **Sort by Multiplier** - Find the best value picks
- **Export CSV** - Download entries for reference
- **Load from File** - Import JSON or CSV entries

## 🚀 Deploy to Web

### Option 1: Render.com (Recommended - Free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) and sign up
3. Click **New → Web Service**
4. Connect your GitHub repo
5. Render auto-detects settings from `render.yaml`
6. Click **Create Web Service**
7. Your app will be live at `https://piggytree-xxxx.onrender.com`

### Option 2: Railway.app (Free)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) and sign up
3. Click **New Project → Deploy from GitHub repo**
4. Select your repo
5. Railway auto-detects Python/Flask
6. Your app will be live instantly

### Option 3: Heroku ($5/mo)

```bash
# Install Heroku CLI
brew install heroku/brew/heroku

# Login and create app
heroku login
heroku create piggytree

# Deploy
git push heroku main

# Open app
heroku open
```

### Option 4: Fly.io (Free tier)

```bash
# Install flyctl
brew install flyctl

# Login and launch
fly auth login
fly launch

# Deploy
fly deploy
```

## 🏃 Run Locally

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/piggytree.git
cd piggytree

# Install dependencies
pip install -r requirements.txt

# Run
python app.py

# Open http://localhost:5000
```

## 📁 Project Structure

```
piggytree-web/
├── app.py              # Flask backend
├── templates/
│   └── index.html      # Frontend UI
├── requirements.txt    # Python dependencies
├── Procfile           # Heroku/Render config
├── render.yaml        # Render.com config
├── runtime.txt        # Python version
└── entries.json       # Saved entries (auto-created)
```

## ⚠️ Note on Data Persistence

Free hosting services typically have **ephemeral storage** - data resets on redeploy. For persistent storage, you could:
- Use a database (PostgreSQL, MongoDB)
- Store in browser localStorage (client-side only)
- Export/Import CSV files manually

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main UI |
| `/api/lookup-player` | POST | Look up player info |
| `/api/entries` | GET | Get all entries |
| `/api/entries` | POST | Add/update entry |
| `/api/entries/<id>` | DELETE | Delete entry |
| `/api/export-csv` | GET | Download CSV |
| `/api/teams` | GET | Get all teams |
| `/api/categories` | GET | Get stat categories |

## 🤝 Contributing

Pull requests welcome!

## 📄 License

MIT License
