from fastapi import APIRouter, Depends, HTTPException, status
from app.api.auth import get_current_user
from app.models.user import UserInDB
from pydantic import BaseModel
import openai
from app.config import settings

router = APIRouter()


class AIGenerationRequest(BaseModel):
    prompt: str


class AIGenerationResponse(BaseModel):
    caption: str
    hashtags: list[str]


@router.post("/ai/generate", response_model=AIGenerationResponse)
async def generate_content(
    request: AIGenerationRequest, current_user: UserInDB = Depends(get_current_user)
):
    """
    Generate social media content using OpenAI
    """
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a social media content creator. Generate an engaging caption and relevant hashtags based on the given prompt.",
                },
                {
                    "role": "user",
                    "content": f"{request.prompt}\n\nCreate a compelling caption and 3-5 relevant hashtags. Return as JSON with 'caption' and 'hashtags' keys.",
                },
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        result = AIGenerationResponse.model_validate_json(content)

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation failed: {str(e)}",
        )
