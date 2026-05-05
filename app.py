from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import pandas as pd
import os
import json
from io import BytesIO

app = FastAPI(title="Retail ETL API", version="1.0")

DATA_PATH = "data.csv"


# -------------------------------
# Utility Functions
# -------------------------------

def load_data():
    """Load and clean dataset safely"""
    if not os.path.exists(DATA_PATH):
        return pd.DataFrame()   # ✅ prevents crash on Render

    df = pd.read_csv(DATA_PATH)

    # Convert to numeric safely
    df["Quantity Sold"] = pd.to_numeric(df["Quantity Sold"], errors="coerce")
    df["Unit Price"] = pd.to_numeric(df["Unit Price"], errors="coerce")

    # Drop invalid rows
    df = df.dropna()

    return df


# -------------------------------
# Response Model (optional)
# -------------------------------

class SalesData(BaseModel):
    Order_ID: int
    Store_ID: str
    Product_ID: str
    Product_Category: str
    Quantity_Sold: float
    Unit_Price: float


# -------------------------------
# Routes
# -------------------------------

@app.get("/")
def root():
    return {"message": "FastAPI ETL is running 🚀"}   # ✅ fixed


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/data")
def get_all_data():
    df = load_data()
    if df.empty:
        return {"message": "No data available. Upload file first."}
    return df.to_dict(orient="records")


@app.get("/data/store/{store_id}")
def get_store_data(store_id: str):
    df = load_data()

    if df.empty:
        raise HTTPException(status_code=404, detail="No data available")

    filtered = df[df["Store ID"] == store_id]

    if filtered.empty:
        raise HTTPException(status_code=404, detail="Store not found")

    return filtered.to_dict(orient="records")


@app.get("/summary")
def get_summary():
    df = load_data()

    if df.empty:
        return {"message": "No data available"}

    df["Total Sales"] = df["Quantity Sold"] * df["Unit Price"]

    summary = (
        df.groupby("Product Category")["Total Sales"]
        .sum()
        .reset_index()
    )

    return summary.to_dict(orient="records")


# -------------------------------
# Upload API (CSV + JSON support)
# -------------------------------

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()

        try:
            # Try CSV
            df = pd.read_csv(BytesIO(content))
        except:
            # Try JSON
            data = json.loads(content)
            df = pd.DataFrame(data)

        required_cols = ["Store ID", "Product ID", "Quantity Sold", "Unit Price"]

        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Missing column: {col}")

        # Save file
        df.to_csv(DATA_PATH, index=False)

        return {"message": "File uploaded successfully ✅"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# Run for Render
# -------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
