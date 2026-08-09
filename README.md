# 🚦 MARGSETU - Smart City Command Center

MARGSETU (formerly Smart Traffic Flow Optimizer) is an advanced, AI-powered traffic management dashboard and backend system built for the **Hack Devengers 1.0** hackathon. 

Designed for traffic police, control room operators, and emergency coordinators, MARGSETU provides a centralized, real-time command center to monitor, predict, and manipulate urban traffic flow.

---

## 🌟 Key Features

1. **Real-Time Traffic Network Map**
   - An interactive, live-updating SVG node-graph visualization of the city's junctions and roads.
   - Roads dynamically change colors (Green, Amber, Red) based on live congestion metrics.

2. **Smart Signal Optimization**
   - Calculates recommended green-phase durations based on vehicle counts, road capacity, and live congestion ratios.
   - Recommends actionable timing shifts with human-readable explanations.

3. **Emergency Corridor Preemption (The "Hero" Feature)**
   - Calculates the absolute fastest route for emergency vehicles (Ambulances, Firetrucks, Police) considering live congestion.
   - "Activates" a rolling green-light corridor, pre-clearing traffic along the emergency route.

4. **Incident Diversion & Road Closures**
   - Allows operators to instantly mark a road segment as blocked (e.g., due to an accident).
   - Automatically recalculates routing algorithms and pushes flashing visual warnings to the map.

5. **Scenario Simulation (What-If Engine)**
   - Allows operators to simulate traffic spikes (e.g., 2x traffic volume) or severe incidents.
   - Instantly compares "Before" and "After" optimization metrics (wait times, queue lengths, congestion percentages).

6. **Machine Learning Traffic Prediction**
   - Uses historical data and Scikit-Learn to predict future traffic bottlenecks based on time of day and weather conditions.

---

## 🏗️ Architecture & Tech Stack

### Frontend (User Interface)
- **Framework:** React + Vite
- **Styling:** Tailwind CSS v4 (Custom Dark Theme / Glassmorphism)
- **Icons:** Lucide React
- **Hosting:** Vercel

### Backend (API & Engine)
- **Framework:** Python + Flask
- **Routing Engine:** NetworkX (Graph Theory & Dijkstra's Algorithm)
- **Data Processing:** Pandas, NumPy
- **Machine Learning:** Scikit-Learn (Random Forest)
- **Hosting:** Render (Stateful Web Service)

---

## 🚀 How to Run Locally

### Prerequisites
- Node.js (v18+)
- Python (3.10+)

### 1. Start the Backend (Flask)
```bash
# Navigate to the backend directory
cd traffic_optimizer

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```
*The API will start at `http://127.0.0.1:5000`*

### 2. Start the Frontend (React)
Open a new terminal window:
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```
*The UI will be available at `http://localhost:5173`*

---

## 🌍 Production Deployment

MARGSETU is designed as a split-stack deployment:

1. **Frontend (Vercel)**
   - The repository root includes a `vercel.json` file.
   - Simply connect the GitHub repo to Vercel. It will automatically detect the `frontend` folder, install Node modules, build the Vite app, and configure Single-Page Application (SPA) routing.

2. **Backend (Render)**
   - Connect the repository to a new Render **Web Service**.
   - Set the Root Directory to `traffic_optimizer`.
   - Set the Start Command to `gunicorn app:app`.
   - Ensure the Environment Variable `PYTHON_VERSION` is set to `3.11.9` to prevent pandas compilation errors.

3. **Connecting Them**
   - Take the live Render backend URL (e.g., `https://margsetu-backend.onrender.com`).
   - Add it as an Environment Variable in your Vercel project settings under the key `VITE_API_URL`.
   - Redeploy the Vercel frontend.

---

## 📁 Repository Structure

```text
├── frontend/                  # React + Vite UI
│   ├── src/
│   │   ├── api.js             # API communication layer
│   │   ├── components/        # UI panels (NetworkMap, EmergencyPanel, etc.)
│   │   ├── App.jsx            # Main dashboard shell
│   │   └── index.css          # Tailwind v4 configuration
│   └── .env.development       # Local backend URL config
├── traffic_optimizer/         # Python Flask Backend
│   ├── src/                   # Core business logic (routing, signals, ML)
│   ├── data/                  # Traffic datasets (CSV)
│   ├── app.py                 # Flask server & API endpoints
│   └── requirements.txt       # Python dependencies
└── vercel.json                # Vercel deployment configuration
```

---

*Built with ❤️ for Hack Devengers 1.0*
