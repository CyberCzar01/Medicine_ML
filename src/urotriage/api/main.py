from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from urotriage.config import CORS_ORIGINS, ML_FEATURES
from urotriage import service
from urotriage.api.schemas import (
    PatientInput,
    PredictResponse,
    BatchRequest,
    BatchResponse,
    HealthResponse,
    Versions,
    SchemaResponse,
)

app = FastAPI(
    title="Urotriage API",
    version="4.0.0",
    description=(
        "Светофор поддержки решения врача-уролога при ОЗМ/ДГПЖ. "
        "Зона определяется прозрачным клиническим правилом; ML — вспомогательный "
        "детектор скрытого риска (может только повысить green до yellow)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/predict", response_model=PredictResponse, summary="Оценить одного пациента", tags=["predict"])
def predict(patient: PatientInput):
    return service.predict(patient.model_dump())


@app.post("/predict/batch", response_model=BatchResponse, summary="Оценить список пациентов", tags=["predict"])
def predict_batch(request: BatchRequest):
    results = service.predict_batch([p.model_dump() for p in request.patients])
    return {"results": results}


@app.get("/health", response_model=HealthResponse, summary="Проверка состояния сервиса", tags=["meta"])
def health():
    return {"status": "ok", "model_loaded": service.model_loaded(), "versions": service.versions()}


@app.get("/version", response_model=Versions, summary="Версии правила/модели/схемы", tags=["meta"])
def version():
    return service.versions()


@app.get("/schema", response_model=SchemaResponse, summary="Метаданные входа и признаков", tags=["meta"])
def schema():
    return {
        "input_fields": list(PatientInput.model_fields.keys()),
        "ml_features": ML_FEATURES,
        "zones": ["green", "yellow", "red"],
        "versions": service.versions(),
    }
