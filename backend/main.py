import base64
from datetime import date, datetime
import io
import json
import os
import re
from typing import List, Optional

import matplotlib
import torch

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.image as mpimg
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
import math

from metriclib.data import Dataset
from metriclib.report import Report
from metriclib.metric import TabularMetric

from custom_metrics import CustomMetric

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


def dataset_key(name: str) -> str:
    return name.replace(".csv", "")


def load_table_with_fallback(primary_table: str, fallback_table: str) -> pd.DataFrame:
    """Load primary DuckDB table, fallback to alternate table if missing."""
    try:
        return con.execute(f"SELECT * FROM {primary_table}").df()
    except duckdb.Error:
        return con.execute(f"SELECT * FROM {fallback_table}").df()


def sanitize_metadata_for_duckdb(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize object columns so DuckDB sees stable scalar types per column."""
    cleaned = df.copy()
    object_cols = cleaned.select_dtypes(include=["object"]).columns

    for col in object_cols:

        def _coerce(v):
            if v is None:
                return None
            if isinstance(v, (list, tuple, dict, set, np.ndarray)):
                if isinstance(v, np.ndarray):
                    v = v.tolist()
                if isinstance(v, set):
                    v = list(v)
                return json.dumps(v, default=str)
            if isinstance(v, np.generic):
                return v.item()
            return v

        cleaned[col] = cleaned[col].map(_coerce)

    return cleaned


class CsvDataset(Dataset):
    def __init__(
        self,
        name,
        df: pd.DataFrame,
        mapping: dict,
        metadata_df: pd.DataFrame = None,
        metadata_df_processed: pd.DataFrame = None,
        labels: List = None,
    ):
        if labels is not None:
            if isinstance(labels, pd.DataFrame):
                raise TypeError(
                    "CsvDataset labels must already be a list of tensors, not a dataframe"
                )
            labels = [
                (
                    label.detach().clone().to(dtype=torch.float32)
                    if isinstance(label, torch.Tensor)
                    else torch.tensor(label, dtype=torch.float32)
                )
                for label in labels
            ]
        super().__init__(name, metadata_df_processed, labels)
        self.df = df
        self.mapping = mapping

    def __len__(self):
        return len(self.df.index)

    def __getitem__(self, idx):
        row = self.df.iloc[idx].to_dict()

        result = {}
        label_keys = [k for k, v in self.mapping.items() if v == "label"]
        labels = torch.tensor(
            pd.to_numeric(
                pd.Series([row.get(k) for k in label_keys]), errors="coerce"
            ).to_numpy(dtype=np.float32),
            dtype=torch.float32,
        )
        for value, key in self.mapping.items():
            if key == "other" or key == "label":
                field = row.get(value)
                result[value] = field
            else:
                field = row.get(value)
                result[key] = field

        if "model_input" not in self.mapping.values():
            return None, labels, result

        try:
            x = wfdb.rdsamp(
                os.path.join(
                    DATA_DIR,
                    row[
                        list(self.mapping.keys())[
                            list(self.mapping.values()).index("model_input")
                        ]
                    ],
                )
            )[0].T
        except Exception as e:
            model_input_col = list(self.mapping.keys())[
                list(self.mapping.values()).index("model_input")
            ]
            img_path = row.get(model_input_col)
            img_path = os.path.join(DATA_DIR, img_path)
            img = mpimg.imread(img_path)
            if img.ndim == 2:
                img = img[:, :, None]
            img_chw = np.transpose(img, (2, 0, 1)).astype(np.float32)
            x = torch.from_numpy(img_chw)

        return (
            x,
            labels,
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
    use_case: Optional[str] = None


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
            "cols": df.columns.tolist(),
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
        "cols": df.columns.tolist(),
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
    metadata_df = sanitize_metadata_for_duckdb(dataset.get_metadata())

    con.register(
        f"{request.name}_mapping",
        pd.DataFrame(request.mapping.items(), columns=["key", "value"]),
    )
    con.register(f"{request.name}_metadata_processed", metadata_df)
    con.register(f"{request.name}_metadata_processed_base", metadata_df)
    label_columns = [
        column for column, role in request.mapping.items() if role == "label"
    ]
    labels_df = (
        df.loc[:, label_columns].copy()
        if label_columns
        else pd.DataFrame({"_label": [None] * len(df)})
    )
    con.register(f"{request.name}_labels", labels_df)
    con.register(f"{request.name}_labels_base", labels_df)
    numeric_cols = metadata_df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        metadata_df.loc[:, numeric_cols] = metadata_df.loc[:, numeric_cols].replace(
            [np.inf, -np.inf], np.nan
        )

    if "idx" in metadata_df.columns:
        return JSONResponse(status_code=422, content={"error": "Unprocessable Entity"})

    metadata_df.insert(0, "idx", metadata_df.index)

    return JSONResponse(content=safe_serialize(metadata_df.to_dict(orient="records")))


@app.get("/api/dataset")
async def get_dataset(name: str, query: str, mapping: str):
    key = dataset_key(name)
    query_str = process_query(query)

    metadata_df_processed = con.execute(
        f"SELECT * FROM {key}_metadata_processed_base"
    ).df()

    labels_df = con.execute(f"SELECT * FROM {key}_labels_base").df()

    if query_str.strip() and query_str != "":
        metadata_df_processed = metadata_df_processed[
            metadata_df_processed.eval(query_str)
        ]
        common_idx = metadata_df_processed.index.intersection(labels_df.index)
        metadata_df_processed = metadata_df_processed.loc[common_idx]
        labels_df = labels_df.loc[common_idx]

    con.register(f"{key}_metadata_processed", metadata_df_processed)
    con.register(f"{key}_labels", labels_df)

    mapping_df = con.execute(f"SELECT * FROM {key}_mapping").df()

    metadata_df_processed.insert(0, "idx", metadata_df_processed.index)

    numeric_cols = metadata_df_processed.select_dtypes(include=[np.number]).columns

    if len(numeric_cols) > 0:
        metadata_df_processed.loc[:, numeric_cols] = metadata_df_processed.loc[
            :, numeric_cols
        ].replace([np.inf, -np.inf], np.nan)

    mapping_cols = set(mapping_df["key"]).union(set(mapping_df["value"]))
    metadata_df_processed = metadata_df_processed[
        [
            col
            for col in metadata_df_processed.columns
            if col == "idx" or col in mapping_cols
        ]
    ]

    return JSONResponse(
        content=safe_serialize(metadata_df_processed.to_dict(orient="records"))
    )


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
    """Return a JSON-serializable version of the object."""

    if obj is None:
        return None

    # Pandas missing datetime value
    if obj is pd.NaT:
        return None

    if isinstance(obj, np.generic):
        return safe_serialize(obj.item())

    if isinstance(obj, (float, np.floating)):
        # Convert NaN/Inf to JSON null
        if not math.isfinite(float(obj)):
            return None
        return float(obj)

    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)

    if isinstance(obj, (int, np.integer)):
        return int(obj)

    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()

    if isinstance(obj, str):
        return obj

    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            serialized = safe_serialize(v)
            if serialized is not _SAFE_SERIALIZE_SKIP:
                clean[k] = serialized
        return clean

    if isinstance(obj, (list, tuple)):
        clean = []
        for item in obj:
            serialized = safe_serialize(item)
            clean.append(None if serialized is _SAFE_SERIALIZE_SKIP else serialized)
        return clean

    if isinstance(obj, np.ndarray):
        return safe_serialize(obj.tolist())

    if hasattr(obj, "__dict__"):
        return safe_serialize(obj.__dict__)
    return _SAFE_SERIALIZE_SKIP


_SAFE_SERIALIZE_SKIP = object()


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
        key = dataset_key(name)
        n_label_targets = sum(1 for v in request.mappings[i].values() if v == "label")
        metadata_df = con.execute(f"SELECT * FROM {key}").df()
        labels_df = con.execute(f"SELECT * FROM {key}_labels_base").df()
        print(f"Loaded dataset {name} with {len(metadata_df)} rows.")
        if request.queries and i < len(request.queries):
            query_str = process_query(request.queries[i])
            if query_str.strip() and query_str != "":
                metadata_df = metadata_df[metadata_df.eval(query_str)]
                common_idx = metadata_df.index.intersection(labels_df.index)
                metadata_df = metadata_df.loc[common_idx]
                labels_df = labels_df.loc[common_idx]

        if labels_df.empty:
            labels = []
        elif n_label_targets > 1 and labels_df.shape[1] > 1:
            labels = [
                torch.tensor(row, dtype=torch.float32)
                for row in labels_df.iloc[:, :n_label_targets]
                .apply(pd.to_numeric, errors="coerce")
                .fillna(0)
                .to_numpy(dtype=np.float32)
                .tolist()
            ]
        else:
            labels = [
                torch.tensor(
                    (
                        pd.to_numeric(
                            pd.Series(
                                value.tolist()
                                if isinstance(value, np.ndarray)
                                else (
                                    value.detach().cpu().numpy().tolist()
                                    if isinstance(value, torch.Tensor)
                                    else value
                                )
                            ),
                            errors="coerce",
                        )
                        .fillna(0)
                        .to_numpy(dtype=np.float32)
                        if isinstance(value, (list, tuple, np.ndarray, torch.Tensor))
                        else pd.to_numeric(pd.Series([value]), errors="coerce")
                        .fillna(0)
                        .to_numpy(dtype=np.float32)
                    ),
                    dtype=torch.float32,
                )
                for value in labels_df.iloc[:, 0].tolist()
            ]

        processed_metadata_df = con.execute(
            f"SELECT * FROM {key}_metadata_processed"
        ).df()
        datasets.append(
            CsvDataset(
                df=metadata_df,
                name=name,
                mapping=request.mappings[i],
                metadata_df_processed=processed_metadata_df,
                labels=labels,
            )
        )

    report = Report(datasets)

    for i in range(len(request.mappings)):
        if "label" in request.mappings[i].values():
            if len([v for v in request.mappings[i].values() if v == "label"]) > 1:
                report.add_metric(
                    name=f"class_balance",
                    metric_name="MultiClassGeneralizedImbalanceRatio",
                    metric_config={"column": "labels"},
                    dataset_name=request.dataset_names[i],
                )
            else:
                report.add_metric(
                    name=f"class_balance",
                    metric_name="MultiLabelGeneralizedImbalanceRatio",
                    metric_config={"column": "labels"},
                    dataset_name=request.dataset_names[i],
                )

        if "sex" in request.mappings[i].values():
            report.add_metric(
                name=f"variety_sex",
                metric_name="HillNumbers",
                metric_config={"column": "sex", "q": 2, "types": [0, 1]},
                dataset_name=request.dataset_names[i],
            )

        if "age" in request.mappings[i].values():
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

        if "height" in request.mappings[i].values():
            report.add_metric(
                name=f"variety_height",
                metric_name="IQR",
                metric_config={
                    "column": "height",
                },
                dataset_name=request.dataset_names[i],
            )

        if "weight" in request.mappings[i].values():
            report.add_metric(
                name=f"variety_weight",
                metric_name="IQR",
                metric_config={
                    "column": "weight",
                },
                dataset_name=request.dataset_names[i],
            )

        if "device" in request.mappings[i].values():
            report.add_metric(
                name=f"variety_device",
                metric_name="HillNumbers",
                metric_config={
                    "column": "device",
                    "q": 2,
                    "types": datasets[i].df["device"].unique().tolist(),
                },
                dataset_name=request.dataset_names[i],
            )

        if "site" in request.mappings[i].values():
            report.add_metric(
                name=f"variety_site",
                metric_name="HillNumbers",
                metric_config={
                    "column": "site",
                    "q": 2,
                    "types": datasets[i].df["site"].unique().tolist(),
                },
                dataset_name=request.dataset_names[i],
            )

        if (
            "sex" in request.mappings[i].values()
            and "label" in request.mappings[i].values()
            and len([v for v in request.mappings[i].values() if v == "label"]) > 1
        ):
            report.add_chart(
                name="coverage_label_sex",
                chart_type="mosaique_label_chart",
                chart_config={
                    "proportion_field": "sex",
                    "category_field": "labels",
                    "name": request.dataset_names[i],
                    "index": i,
                },
            )

        report.add_metric(
            name="dataset_size",
            metric_name="DatasetSize",
            metric_config={},
            dataset_name=request.dataset_names[i],
        )

        if "model_input" in request.mappings[i].values():
            report.add_metric(
                name="resolution",
                metric_name="Resolution",
                metric_config={},
                dataset_name=request.dataset_names[i],
            )

            if request.use_case == "ECG diagnosis":
                report.add_metric(
                    name="sample_entropy",
                    metric_name="SampleEntropy",
                    metric_config={},
                    dataset_name=request.dataset_names[i],
                )

        if "created_at" in request.mappings[i].values():
            report.add_metric(
                name="currency",
                metric_name="CurrencyHeinrich",
                metric_config={"created_at_field": "created_at"},
                dataset_name=request.dataset_names[i],
            )

        if (
            "sex" in request.mappings[i].values()
            and "device" in request.mappings[i].values()
        ):
            report.add_metric(
                name="MMD",
                metric_name="MMD",
                metric_config={"groups": {"sex": [0, 1]}, "feature_cols": ["device"]},
                dataset_name=request.dataset_names[i],
            )

        if (
            "sex" in request.mappings[i].values()
            and "label" in request.mappings[i].values()
        ):
            report.add_metric(
                name="coverage_label_sex",
                metric_name="MultiClassDemographicParity",
                metric_config={"protected_attribute": "sex"},
                dataset_name=request.dataset_names[i],
            )

        feature_columns = [
            v
            for k, v in request.mappings[i].items()
            if v in ["sex", "device", "site", "ethnicity", "nurse"]
        ]

        if len(feature_columns) > 0 and "label" in request.mappings[i].values():
            report.add_metric(
                name="correlations",
                metric_name="PearsonCorrelation",
                metric_config={"feature_columns": feature_columns},
                dataset_name=request.dataset_names[i],
            )

        report.add_metric(
            name="metadata_completeness",
            metric_name="MetadataCompleteness",
            metric_config={},
            dataset_name=request.dataset_names[i],
        )

        for metric in TabularMetric.registry.values():
            if issubclass(metric, CustomMetric):
                report.add_metric(
                    name=metric().dimension,
                    metric_name=metric.__name__,
                    metric_config={},
                    dataset_name=request.dataset_names[i],
                )

    if all("weight" in mapping.values() for mapping in request.mappings):
        report.add_chart(
            name="variety_weight",
            chart_type="continuous_bar_chart",
            chart_config={"field": "weight"},
        )

    if all("device" in mapping.values() for mapping in request.mappings):
        report.add_chart(
            name="variety_device",
            chart_type="categorical_bar_chart",
            chart_config={"field": "device"},
        )

    if all(
        "model_input" in request.mappings[i].values()
        for i in range(len(request.mappings))
    ):
        report.add_chart(
            name="sample_entropy",
            chart_type="continuous_bar_chart",
            chart_config={"field": "sample_entropy", "n_buckets": 10},
        )

    if all("site" in mapping.values() for mapping in request.mappings):
        report.add_chart(
            name="variety_site",
            chart_type="categorical_bar_chart",
            chart_config={"field": "site"},
        )

    if all("sex" in mapping.values() for mapping in request.mappings):
        report.add_chart(
            name="variety_sex",
            chart_type="categorical_bar_chart",
            chart_config={"field": "sex"},
        )

    if all("age" in mapping.values() for mapping in request.mappings):
        report.add_chart(
            name="variety_age",
            chart_type="continuous_bar_chart",
            chart_config={"field": "age"},
        )

    if all("height" in mapping.values() for mapping in request.mappings):
        report.add_chart(
            name="variety_height",
            chart_type="continuous_bar_chart",
            chart_config={"field": "height"},
        )

    if all("created_at" in mapping.values() for mapping in request.mappings):
        report.add_chart(
            name="currency",
            chart_type="categorical_bar_chart",
            chart_config={"field": "created_at"},
        )

    if all("label" in mapping.values() for mapping in request.mappings):
        report.add_chart(
            name="class_balance",
            chart_type="label_bar_chart",
            chart_config={},
        )

    if len(feature_columns) > 0 and all(
        "label" in mapping.values() for mapping in request.mappings
    ):
        report.add_chart(
            name="correlations",
            chart_type="label_heatmap",
            chart_config={"feature_columns": feature_columns},
        )

    metrics, charts, scores = report.generate()

    for dataset in report.datasets:
        key = dataset_key(dataset.name)
        sanitized = sanitize_metadata_for_duckdb(dataset.metadata)
        con.register(f"{key}_metadata_processed", sanitized)
        base_df = con.execute(f"SELECT * FROM {key}_metadata_processed_base").df()
        new_cols = [c for c in sanitized.columns if c not in base_df.columns]
        if new_cols:
            for col in new_cols:
                base_df[col] = np.nan
                base_df.loc[sanitized.index.intersection(base_df.index), col] = (
                    sanitized.loc[sanitized.index.intersection(base_df.index), col]
                )
            con.register(f"{key}_metadata_processed_base", base_df)

    payload = {
        "metrics": metrics,
        "charts": convert_figures(charts),
        "scores": scores,
    }
    return JSONResponse(content=safe_serialize(payload))


@app.get("/api/scores")
async def get_scores(index):
    return JSONResponse(
        content={
            "representativeness": 0.0,
            "measurement_error": 0.0,
            "timeliness": 0.0,
            "informativeness": 0.0,
            "consistency": 0.0,
        }
    )


@app.get("/api/image")
def get_image(index: str, name: str, mapping: str, use_case: str = None):
    metadata_df = metadata_df = con.execute(
        f"SELECT * FROM {name.replace('.csv', '')}"
    ).df()

    if use_case != "ECG diagnosis":
        raise ValueError("Unsupported use case for image retrieval")

    mapping = json.loads(mapping)
    model_input_col = list(mapping.keys())[list(mapping.values()).index("model_input")]

    file_path = os.path.join(DATA_DIR, name)
    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404, content={"error": f"File {name}.csv not found."}
        )

    x = wfdb.rdsamp(
        os.path.join(DATA_DIR, metadata_df[model_input_col].iloc[int(index)])
    )[0].T

    ecg_plot.plot_12(x, sample_rate=x.shape[1] / 10)

    fig = plt.gcf()

    # Render to PNG in memory
    buf = io.BytesIO()
    FigureCanvas(fig).print_png(buf)
    plt.close(fig)

    img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {"image_base64": img_base64}
