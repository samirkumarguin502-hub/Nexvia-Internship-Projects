from pydantic import BaseModel, Field


class LabelPrediction(BaseModel):
    label: str
    probability: float = Field(ge=0, le=1)


class InferenceResponse(BaseModel):
    study_id: str
    status: str
    model_name: str | None = None
    model_version: str | None = None
    predicted_label: str | None = None

    # Legacy field retained for compatibility.
    # This contains a raw sigmoid score, not a calibrated probability.
    calibrated_probability: float | None = None

    predictions: dict[str, float] = Field(default_factory=dict)
    top_predictions: list[LabelPrediction] = Field(default_factory=list)
    probability_note: str | None = None

    gradcam_url: str | None = None
    segmentation_url: str | None = None

    disclaimer: str = (
        "Educational/research output only; not for clinical use."
    )