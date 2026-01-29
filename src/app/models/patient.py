from datetime import date

from sqlmodel import Field, Relationship, SQLModel  # type: ignore


# Tabla 1: Paciente
class Patient(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(index=True)
    birth_date: date
    gender: str  # "M", "F"

    # Factores de Riesgo Estaticos
    family_history: bool = Field(
        default=False, description="Antecedentes familiares de diabetes"
    )

    # Estado actual
    diagnosis: str = Field(
        default="Sin Diagnostico"
    )  # Ej: "Prediabetes", "DM2", "Sano"

    current_medication: str | None = None

    # Relacion: Un paciente tiene muchas mediciones
    records: list["ClinicalRecord"] = Relationship(back_populates="patient")


# Tabla 2: Las Mediciones
class ClinicalRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    date: date

    # Glucemia
    fasting_glucose: float = Field(description="Glucosa en ayunas (mg/dL)")
    post_prandial_glucose: float | None = Field(
        default=None, description="Hemoglobina Glicosilaba (%)"
    )

    # Antropometria (Para calculo de riesgo cardiovascular)
    weight_kg: float
    height_cm: float
    waist_circumference: float | None = None

    # Foreign key
    patient_id: int = Field(foreign_key="patient.id")
    patient: Patient | None = Relationship(back_populates="records")

    @property
    def bmi(self) -> float:
        """
        Calcula indice de masa corporal al vuelo
        """
        height_m = self.height_cm / 100
        return round(self.weight_kg / (height_m**2), 2)
