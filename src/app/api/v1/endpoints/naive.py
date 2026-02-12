from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.limiter import limiter
from app.core.session import get_db
from app.services.naive_service import naiveRAGService

router = APIRouter()


# Definimos el esquema de entrada (input)
class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str


@router.post("/naive", response_model=ChatResponse)
@limiter.limit("7/hour; 10/day")  # type: ignore
async def chat_naive(
    request: Request, body: ChatRequest, session: AsyncSession = Depends(get_db)
):
    """
    Endpoint para chatear con el modo Naive RAG(baseline)
    """
    response = await naiveRAGService.answer_question(session, body.query)
    return response
