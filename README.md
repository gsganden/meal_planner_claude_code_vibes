# Recipe Chat Assistant

## Running Locally

### Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your Google AI API key: GOOGLE_API_KEY="your-key-here"

# Start backend
python -m uvicorn src.main:app --reload --port 8000
```

### Frontend Setup
```bash
# Install dependencies
cd frontend_app
npm install

# Start frontend
npm run dev
```

### Quick Start Script
```bash
# Start both servers with logging
./restart_servers.sh
```

Access the app at http://localhost:3000