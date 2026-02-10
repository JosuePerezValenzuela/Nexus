from datetime import date

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

# Importacion de los modelos para poder hacer consultas
from app.models.patient import Patient


class PatientService:
    async def get_patient_history(
        self,
        session: AsyncSession,
        name_query: str | None = None,
        patient_id: int | None = None,
    ) -> str:  # noqa: E501
        """
        Busca un paciente por nombre
          - Si es unico: Devuelve el reporte clinico completo.
          - Si hay homonimos: Devuelve una lista para desambiguar
        y genera un reporte clinico en texto para que el Agente IA pueda leerlo
        y analizarlo
        """
        # Busqueda por id
        if patient_id:
            patient = await session.get(Patient, patient_id)
            if not patient:
                return f" Error: No existe ningun paciente con el ID {patient_id}."
            return self._generate_full_report(patient)

        # 1. Busqueda en Base de datos por nombre
        if name_query:
            statement = select(Patient).where(
                col(Patient.full_name).ilike(f"%{name_query}%")
            )
            result = await session.exec(statement)
            results = result.all()

            # Caso A: No existe
            if not results:
                return f" No se encontro ningun paciente con el nombre '{name_query}'."

            # Caso B: Ambiguedad
            if len(results) > 1:
                msg = f" Encontre {len(results)} pacientes con el nombre '{name_query}' Por favor, se mas especifico (menciona el ID):\n"  # noqa: E501
                for p in results:
                    age = self._calculate_age(p.birth_date)
                    msg += f" - ID: {p.id} | Nombre: {p.full_name} | Edad: {age} años\n"
                return msg

            # Caso C: paciente Unico (Exito)
            patient = results[0]
            return self._generate_full_report(patient)

        return " Debes proporcionar un nombre o un ID para buscar."

    def _generate_full_report(self, patient: Patient) -> str:
        """
        Genera el texto detallado de un paciente especifico.
        """
        age = self._calculate_age(patient.birth_date)

        report = (
            f"## FICHA DEL PACIENTE (ID: {patient.id}**\n)"
            f"Nombre: {patient.full_name}\n"
            f"Edad: {age} años ({patient.birth_date})\n"
            f"Sexo: {patient.gender}\n"
            f"Antecedentes Familiares: {patient.family_history}\n"
            f"--------------------------------------------\n"
            f"**ESTADO ACTUAL**\n"
            f"Diagnostico Base: {patient.diagnosis}\n"
            f"Medicacion: {patient.current_medication or 'Ninguna reportada'}\n"
            f"--------------------------------------------\n"
            f" **EVOLUCION CLINICA (Historial)**\n"
        )

        if not patient.records:
            report += " (Sin registros de mediciones previas)\n"
        else:
            sorted_records = sorted(patient.records, key=lambda x: x.date)
            for rec in sorted_records:
                report += f" Fecha: {rec.date}\n"
                report += f" Glucosa Ayunas: {rec.fasting_glucose} mg/dL\n"
                if rec.post_prandial_glucose:
                    report += (
                        f" Glucosa Post-Prandial: {rec.post_prandial_glucose} mg/dL\n"  # noqa: E501
                    )
                if rec.hba1c:
                    control = "(Controlado)" if rec.hba1c < 7.0 else "(Fuera de meta)"
                    report += f" HbA1c: {rec.hba1c}% {control}\n"
                report += f" Peso: {rec.weight_kg} kg (IMC: {rec.bmi})\n"
                if rec.notes:
                    report += f" Nota Medica: {rec.notes}\n"
                report += "\n"

        return report

    def _calculate_age(self, born: date) -> int:
        today = date.today()
        return (
            today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        )  # noqa: E501


patient_service = PatientService()
