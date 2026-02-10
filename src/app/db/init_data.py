import logging
from datetime import date, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# Importacion de los modelos
from app.models.patient import ClinicalRecord, Patient

logger = logging.getLogger(__name__)


async def init_db(session: AsyncSession) -> None:
    """
    Funcion idempotente para sembrar datos iniciales.
    Si ya existen pacientes, no hacemos nada
    """
    # Verificacion si ya existen datos
    patients = await session.exec(select(Patient).limit(1))
    patient = patients.first()
    if patient:
        logger.info(" La base de datos ya tiene pacientes, Seeder omitido.")
        return

    logger.info(" Sembrando datos medicos de prueba (Seeding)...")

    # Caso 1: Diabetes tipo 2 Descompensada (Carlos)
    p1 = Patient(
        full_name="Carlos Mamani",
        birth_date=date(1965, 5, 20),
        gender="M",
        family_history=True,
        diagnosis="Diabetes Tipo 2",
        current_medication="Glibenclamida 5mg",
    )

    # Historial evolutivo
    r1_old = ClinicalRecord(
        date=date.today() - timedelta(days=90),
        fasting_glucose=180.0,
        hba1c=8.2,
        weight_kg=85.0,
        height_cm=165.0,
        notes="Polidipsia y poliuria marcada.",
    )

    r1_new = ClinicalRecord(
        date=date.today(),
        fasting_glucose=195.0,
        hba1c=None,
        weight_kg=86.5,
        height_cm=165.0,
        notes="Paciente no adherente al tratamiento. Riesgo alto.",
    )

    # Vinculacion
    p1.records = [r1_old, r1_new]

    # Caso 2: Prediabetes (Juana)
    p2 = Patient(
        full_name="Juana Quispe",
        birth_date=date(1980, 8, 15),
        gender="F",
        family_history=True,
        diagnosis="Prediabetes",
        current_medication=None,
    )

    r2 = ClinicalRecord(
        date=date.today() - timedelta(days=10),
        fasting_glucose=115.0,
        hba1c=5.9,
        weight_kg=78.0,
        height_cm=155.0,
        waist_circumference=98.0,
        notes="Se indica dieta hipocalorica y ejercicio.",
    )

    p2.records = [r2]

    # Caso 3: Sano (Roberto)
    p3 = Patient(
        full_name="Roberto Vaca",
        birth_date=date(1995, 1, 10),
        gender="M",
        family_history=False,
        diagnosis="Sano",
        current_medication=None,
    )

    r3 = ClinicalRecord(
        date=date.today(),
        fasting_glucose=85.0,
        hba1c=4.8,
        weight_kg=70.0,
        height_cm=175.0,
        notes="Control anual normal.",
    )

    p3.records = [r3]

    # Guardado en bloque

    session.add(p1)
    session.add(p2)
    session.add(p3)
    await session.commit()

    logger.info(" Seeding completado exitosamente.")
