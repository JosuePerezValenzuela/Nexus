from langchain_core.tools import tool  # type: ignore

# Actualizacion del esquema de entrada
from pydantic import BaseModel, Field

from app.core.session import async_session_factory
from app.services.patient_service import patient_service


class PatientSearchInput(BaseModel):
    name: str | None = Field(default=None, description="Nombre del paciente")
    patient_id: int | None = Field(default=None, description="ID unico del paciente")


@tool(args_schema=PatientSearchInput)
async def lookup_patient_history(
    name: str | None = None, patient_id: int | None = None
) -> str:  # noqa: E501
    """
    Busca el historial clinico de un paciente.
    - Si tienes el ID, usalo por encima del nombre (es mas preciso).
    - Si no, busca por nombre.
    """
    async with async_session_factory() as session:
        # Pasamos ambos parametros al servicio
        return await patient_service.get_patient_history(
            session, name_query=name, patient_id=patient_id
        )  # noqa: E501
