from fastapi import APIRouter

router = APIRouter()


@router.post("/signup")
async def signup():
    """
    Sign up endpoint - placeholder for Supabase Auth integration.
    Supabase handles auth on frontend, this is for any backend-specific logic.
    """
    return {"message": "Use Supabase Auth on frontend"}


@router.post("/login")
async def login():
    """
    Login endpoint - placeholder for Supabase Auth integration.
    """
    return {"message": "Use Supabase Auth on frontend"}
