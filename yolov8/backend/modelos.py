from pydantic import BaseModel, EmailStr, Field

class UsuarioBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    edad: int = Field(..., ge=0, le=120)  # edad entre 0 y 120
    password: str = Field(..., min_length=4)  # <- agregar

class UsuarioCreate(UsuarioBase):
    """Modelo para crear usuarios (sin id)."""
    pass

class UsuarioDB(UsuarioBase):
    """Modelo que incluye el id (cuando el usuario ya está guardado en la BD)."""
    id: int