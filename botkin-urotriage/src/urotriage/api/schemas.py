from typing import List, Optional

from pydantic import BaseModel, Field


class PatientInput(BaseModel):
    age: Optional[float] = Field(None, ge=0, le=130, description="Возраст, лет")
    sex: Optional[str] = Field(None, max_length=20, description="Пол: Мужской/Женский или 1/0")
    temp: Optional[float] = Field(None, ge=25, le=45, description="Температура тела, °C")
    bp_sys: Optional[float] = Field(None, ge=20, le=300, description="Систолическое АД, мм рт. ст.")
    bp_dia: Optional[float] = Field(None, ge=10, le=200, description="Диастолическое АД, мм рт. ст.")
    pulse: Optional[float] = Field(None, ge=10, le=300, description="Пульс, уд/мин")
    creatinine: Optional[float] = Field(None, ge=0, le=5000, description="Креатинин крови, мкмоль/л")
    urea: Optional[float] = Field(None, ge=0, le=200, description="Мочевина крови, ммоль/л")
    crp: Optional[float] = Field(None, ge=0, le=1000, description="С-реактивный белок, мг/л")
    hemoglobin: Optional[float] = Field(None, ge=10, le=250, description="Гемоглобин, г/л")
    wbc: Optional[float] = Field(None, ge=0, le=200, description="Лейкоциты крови, ×10⁹/л")
    residual_urine_ml: Optional[float] = Field(None, ge=0, le=5000, description="Объём остаточной мочи по УЗИ, мл")
    diagnosis_text: Optional[str] = Field(None, max_length=20000, description="Диагноз при поступлении (свободный текст)")
    complaints_text: Optional[str] = Field(None, max_length=20000, description="Жалобы при поступлении (свободный текст)")
    imaging_text: Optional[str] = Field(None, max_length=20000, description="Заключения УЗИ/КТ (свободный текст)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "age": 74,
                "sex": "Мужской",
                "temp": 38.4,
                "bp_sys": 140,
                "bp_dia": 85,
                "pulse": 96,
                "creatinine": 156,
                "urea": 12.1,
                "crp": 84,
                "hemoglobin": 128,
                "wbc": 14.2,
                "residual_urine_ml": 650,
                "diagnosis_text": "Острая задержка мочи на фоне ДГПЖ",
                "complaints_text": "невозможность самостоятельного мочеиспускания, выраженная боль",
                "imaging_text": "Двусторонний гидронефроз, остаточная моча 650 мл",
            }
        }
    }


class FiredCriterion(BaseModel):
    code: str = Field(..., description="Код критерия")
    zone: str = Field(..., description="Зона критерия: red/yellow")
    message: str = Field(..., description="Человекочитаемое объяснение критерия")


class RuleResult(BaseModel):
    zone: str = Field(..., description="Зона по правилу: green/yellow/red")
    rule_version: str = Field(..., description="Версия правила")
    fired_criteria: List[FiredCriterion] = Field(..., description="Сработавшие критерии")
    missing_fields: List[str] = Field(..., description="Незаполненные ключевые поля")
    data_quality_warnings: List[str] = Field(..., description="Предупреждения о качестве данных")


class TopFeature(BaseModel):
    feature: str = Field(..., description="Имя признака")
    value: Optional[object] = Field(None, description="Значение признака у пациента")
    importance: float = Field(..., description="Глобальная важность признака для ML-модели")
    kind: str = Field(..., description="Тип объяснения (global_importance)")


class MLResult(BaseModel):
    probability: Optional[float] = Field(None, description="Калиброванная вероятность escalation_proxy")
    proxy_zone: Optional[str] = Field(None, description="Высокий/низкий ML-риск относительно порога")
    action: str = Field(..., description="Действие ML: none/upgrade_to_yellow/model_unavailable")
    message: str = Field(..., description="Пояснение к действию ML")
    top_features: List[TopFeature] = Field(..., description="Топ признаков, влияющих на ML")
    explanations_available: bool = Field(..., description="Доступны ли ML-объяснения")


class Versions(BaseModel):
    model_config = {"protected_namespaces": ()}

    rule_version: str
    model_version: Optional[str]
    threshold_version: str
    schema_version: str
    sklearn_version: str


class PredictResponse(BaseModel):
    final_zone: str = Field(..., description="Итоговая зона светофора: green/yellow/red")
    final_reason: str = Field(..., description="Причина итоговой зоны")
    rule: RuleResult
    ml: MLResult
    versions: Versions
    disclaimers: List[str] = Field(..., description="Клинические и методологические оговорки")


class BatchRequest(BaseModel):
    patients: List[PatientInput] = Field(
        ..., min_length=1, max_length=500,
        description="Список пациентов для пакетной оценки (от 1 до 500 за запрос)",
    )


class BatchResponse(BaseModel):
    results: List[PredictResponse]


class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str = Field(..., description="Состояние сервиса")
    model_loaded: bool = Field(..., description="Загружена ли ML-модель")
    versions: Versions


class SchemaResponse(BaseModel):
    input_fields: List[str] = Field(..., description="Поля входной формы")
    ml_features: List[str] = Field(..., description="Признаки ML-модели")
    zones: List[str] = Field(..., description="Возможные зоны светофора")
    versions: Versions
