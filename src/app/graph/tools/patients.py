from langchain_core.tools import tool  # type: ignore

# Actualizacion del esquema de entrada
from pydantic import BaseModel, Field
from sqlmodel import Session  # type: ignore

from app.core.session import engine
from app.services.patient_service import patient_service


class PatientSearchInput(BaseModel):
    name: str | None = Field(default=None, description="Nombre del paciente")
    patient_id: int | None = Field(default=None, description="ID unico del paciente")


@tool(args_schema=PatientSearchInput)
def lookup_patient_history(
    name: str | None = None, patient_id: int | None = None
) -> str:  # noqa: E501
    """
    Busca el historial clinico de un paciente.
    - Si tienes el ID, usalo por encima del nombre (es mas preciso).
    - Si no, busca por nombre.
    """
    with Session(engine) as session:
        # Pasamos ambos parametros al servicio
        return patient_service.get_patient_history(
            session, name_query=name, patient_id=patient_id
        )  # noqa: E501
