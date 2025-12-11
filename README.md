# Full Stack Application

A full stack web application with FastAPI backend and Vue.js frontend.

## Project Structure

```
.
├── backend/
│   ├── environment.yml
│   └── main.py
├── frontend/
│   ├── src/
│   └── package.json
└── README.md
```

## Prerequisites

- Python 3.8 or higher
- Node.js 16.x or higher
- npm or yarn package manager
- pip package manager

## Backend Setup (FastAPI)

### 1. Navigate to the backend directory

```bash
cd backend
```

### 2. Create and activate the conda environment

```bash
# Create environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate metric-backend
```

### 3. Start the backend server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the run script
python main.py
```

The API will be available at `http://localhost:8000`

## Frontend Setup (Vue.js)

### 1. Navigate to the frontend directory

```bash
cd frontend
```

### 2. Install dependencies

```bash
# Using npm
npm install

# Or using yarn
yarn install
```

### 3. Start the development server

```bash
# Using npm
npm run dev

# Or using yarn
yarn dev
```