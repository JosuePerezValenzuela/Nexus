from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.session import get_db
from app.services.naive_service import naiveRAGService

router = APIRouter()


# Definimos el esquema de entrada (input)
class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str


@router.post("/naive", response_model=ChatResponse)
async def chat_naive(request: ChatRequest, session: AsyncSession = Depends(get_db)):
    """
    Endpoint para chatear con el modo Naive RAG(baseline)
    """
    response = await naiveRAGService.answer_question(session, request.query)
    return response
