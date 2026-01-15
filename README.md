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
conda env create -f environment.yml

conda activate metric-backend
```

### 3. Install `MetricLib`
Navigate to the `MetricLib` [repository](https://gitlab1.ptb.de/martin.seyferth/MetricLib) and run
```
pip install -e .
```

### 3. Start the backend server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000

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
npm install

yarn install
```

### 3. Start the development server

```bash
npm run dev

yarn dev
```