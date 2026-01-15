import base64
import io
import json
import os
import re
from typing import List

import matplotlib
import torch

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.image as mpimg
import math
import numpy as np
import pandas as pd
import wfdb
import ecg_plot
import duckdb
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from metriclib.data import Dataset
from metriclib.report import Report

app = FastAPI()

# Resolve data directory relative to repository root (parent of backend/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Backend-local temp directory stays inside backend/data/temp
BACKEND_DIR = os.path.dirname(__file__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    global con
    con = duckdb.connect()


class CsvDataset(Dataset):
    def __init__(
        self, name, df: pd.DataFrame, mapping: dict, metadata_df: pd.DataFrame = None
    ):
        super().__init__(name)
        self.df = df
        self.mapping = mapping

    def __len__(self):
        return len(self.df.index)

    def __getitem__(self, idx):
        row = self.df.iloc[idx].to_dict()

        result = {}
        for key, value in self.mapping.items():
            field = row.get(value)
            result[key] = field

        if "model_input" not in self.mapping:
            return None, 0, result

        try:
            x = wfdb.rdsamp(
                row[
                    list(self.mapping.keys())[
                        list(self.mapping.values()).index("model_input")
                    ]
                ]
            )
        except Exception as e:
            x = 0
            model_input_col = self.mapping["model_input"]
            img_path = row.get(model_input_col)
            img_path = os.path.join(DATA_DIR, img_path)
            img = mpimg.imread(img_path)
            if img.ndim == 2:
                img = img[:, :, None]
            img_chw = np.transpose(img, (2, 0, 1)).astype(np.float32)
            x = torch.from_numpy(img_chw)

        return (
            x,
            0,
            result,
        )


class DatasetRequest(BaseModel):
    name: str
    mapping: dict


class DatasetFilterRequest(BaseModel):
    name: str
    query: str


class ImageRequest(BaseModel):
    name: str
    index: str


class ReportRequest(BaseModel):
    dataset_names: List[str]
    mappings: List[dict]
    queries: List[str] = []


@app.get("/api/files")
async def list_files():
    """List available CSV files in the repository-level data folder (non-recursive)."""
    data_dir = DATA_DIR
    if not os.path.exists(data_dir):
        return JSONResponse(content=[])
    files = []
    for entry in os.listdir(data_dir):
        path = os.path.join(data_dir, entry)
        if os.path.isfile(path) and entry.lower().endswith(".csv"):
            files.append(entry)

    files.sort()
    return JSONResponse(content=files)


@app.get("/api/upload_file")
async def upload_file_existing(name: str):
    """Return metadata for an existing CSV file (compat with former upload response)."""
    data_dir = DATA_DIR
    file_path = os.path.join(data_dir, name)

    df = pd.read_csv(file_path)
    return JSONResponse(
        content={
            "message": "File selected successfully!",
            "filename": name,
            "features": len(df.columns),
            "rows": len(df),
            "missing_values": int(df.isnull().sum().values.sum()),
            "cols": df.columns.tolist()[0:5],
        }
    )


@app.get("/api/file_metadata")
async def get_file_metadata(name: str):
    data_dir = DATA_DIR
    file_path = os.path.join(data_dir, name)
    if not os.path.exists(file_path):
        return {"error": "File not found."}

    if not name.endswith(".csv"):
        return {"error": "Unsupported file type. Please upload a CSV or Excel file."}

    df = pd.read_csv(file_path)
    return {
        "features": len(df.columns),
        "rows": len(df),
        "missing_values": int(df.isnull().sum().values.sum()),
        "cols": df.columns.tolist()[0:5],
    }


@app.post("/api/dataset")
async def create_dataset(request: DatasetRequest):
    data_dir = DATA_DIR
    file_path = os.path.join(data_dir, request.name + ".csv")

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found."})

    df = pd.read_csv(file_path)

    con.register(request.name, df)

    dataset = CsvDataset(name=request.name, df=df, mapping=request.mapping)

    metadata_df = dataset.get_metadata()
    metadata_df.replace([np.inf, -np.inf], np.nan, inplace=True)

    if "idx" in metadata_df.columns:
        return JSONResponse(status_code=422, content={"error": "Unprocessable Entity"})

    metadata_df.insert(0, "idx", metadata_df.index)

    metadata_df.fillna("", inplace=True)

    return JSONResponse(content=metadata_df.to_dict(orient="records"))


@app.get("/api/dataset")
async def get_dataset(name: str, query: str, mapping: str):
    data_dir = DATA_DIR
    file_path = os.path.join(data_dir, name)
    query_str = process_query(query)

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found."})

    metadata_df = con.execute(f"SELECT * FROM {name.replace('.csv', '')}").df()
    metadata_df.replace([np.inf, -np.inf], np.nan, inplace=True)

    if query_str.strip() and query_str != "":
        metadata_df = metadata_df[metadata_df.eval(query_str)]

    metadata_df.fillna("", inplace=True)

    return JSONResponse(content=metadata_df.to_dict(orient="records"))


def process_query(query):
    query_str = query.replace(" AND ", " & ").replace(" OR ", " | ")
    query_str = query_str.replace("[", "").replace("]", "").replace("\xa0", " ")
    query_str = re.sub(r"(\w+)\s*==\s*null", r"\1 != \1", query_str)
    query_str = re.sub(r"(\w+)\s*!=\s*null", r"\1 == \1", query_str)

    return query_str


@app.get("/api/data")
async def get_data(name, header=False):
    data_dir = DATA_DIR

    file_path = os.path.join(data_dir, name)

    if not os.path.exists(file_path):
        return {"error": "File not found."}

    if not name.endswith(".csv"):
        return {"error": "Unsupported file type. Please upload a CSV or Excel file."}

    if header:
        return {"cols": pd.read_csv(file_path, nrows=0).columns.tolist()}

    data = pd.read_csv(file_path).to_dict(orient="records")
    return {"data": data}


def safe_serialize(obj):
    """Return a JSON-serializable version of the object, or skip it."""

    if isinstance(obj, np.generic):
        return obj.item()

    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj

    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            serialized = safe_serialize(v)
            if serialized is not None:
                clean[k] = serialized
        return clean

    if isinstance(obj, (list, tuple)):
        clean = []
        for item in obj:
            serialized = safe_serialize(item)
            if serialized is not None:
                clean.append(serialized)
        return clean

    if hasattr(obj, "__dict__"):
        return safe_serialize(obj.__dict__)
    return None


def convert_figures(obj):
    if isinstance(obj, dict):
        return {k: convert_figures(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_figures(v) for v in obj]
    elif hasattr(obj, "to_plotly_json"):
        return convert_figures(obj.to_plotly_json())
    elif isinstance(obj, np.ndarray):
        return convert_figures(obj.tolist())
    elif isinstance(obj, np.generic):
        return obj.item()
    return obj


@app.post("/api/report")
async def create_report(request: ReportRequest):
    datasets = []
    for i, name in enumerate(request.dataset_names):
        metadata_df = con.execute(f"SELECT * FROM {name.replace('.csv', '')}").df()
        datasets.append(
            CsvDataset(df=metadata_df, name=name, mapping=request.mappings[i])
        )

    report = Report(datasets)
    for i in range(len(request.mappings)):
        if "sex" in request.mappings[i].keys():
            report.add_metric(
                name=f"variety_sex",
                metric_name="HillNumbers",
                metric_config={"column": "sex", "q": 2, "types": [0, 1]},
                dataset_name=request.dataset_names[i],
            )

        if "age" in request.mappings[i].keys():
            report.add_metric(
                name=f"variety_age",
                metric_name="IQR",
                metric_config={
                    "column": "age",
                },
                dataset_name=request.dataset_names[i],
            )
            report.add_metric(
                name=f"variety_age",
                metric_name="Range",
                metric_config={
                    "column": "age",
                },
                dataset_name=request.dataset_names[i],
            )

        if "created_at" in request.mappings[i].keys():
            report.add_metric(
                name=f"currency",
                metric_name="CurrencyHeinrich",
                metric_config={"created_at_field": "created_at", "A": 1e-9},
                dataset_name=request.dataset_names[i],
            )

    if all("sex" in mapping.keys() for mapping in request.mappings):
        report.add_chart(
            name="variety_sex",
            chart_type="categorical_bar_chart",
            chart_config={"field": "sex"},
        )

    if all("age" in mapping.keys() for mapping in request.mappings):
        report.add_chart(
            name="variety_age",
            chart_type="continuous_bar_chart",
            chart_config={"field": "age"},
        )

    if all("created_at" in mapping.keys() for mapping in request.mappings):
        report.add_chart(
            name="currency",
            chart_type="categorical_bar_chart",
            chart_config={"field": "created_at"},
        )

    metrics, charts, scores = report.generate()
    metrics = safe_serialize(metrics)

    charts = convert_figures(charts)
    return JSONResponse(
        content={"metrics": metrics, "charts": charts, "scores": scores}
    )


@app.get("/api/scores")
async def get_scores(index):
    return JSONResponse(
        content={
            "representativeness": 0.6,
            "measurement_error": 1.0,
            "timeliness": 0.75,
            "informativeness": 0.85,
            "consistency": 0.95,
        }
    )


@app.get("/api/image")
def get_image(index: str, name: str):
    metadata_df = pd.read_csv(os.path.join(DATA_DIR, name))

    file_path = os.path.join(DATA_DIR, name)
    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404, content={"error": f"File {name}.csv not found."}
        )

    x = wfdb.rdsamp(
        os.path.join(DATA_DIR, metadata_df["filename_hr"].iloc[int(index)])
    )[0].T

    ecg_plot.plot_12(x, sample_rate=500)

    fig = plt.gcf()

    # Render to PNG in memory
    buf = io.BytesIO()
    FigureCanvas(fig).print_png(buf)
    plt.close(fig)

    img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {"image_base64": img_base64}
