from pydantic import BaseModel, EmailStr, Field


class UsuarioBase(BaseModel):
    """Datos publicos de un usuario. La contrasena no entra aqui a proposito."""
    nombre: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    edad: int = Field(..., ge=0, le=120)  # edad entre 0 y 120


class UsuarioCreate(UsuarioBase):
    """Modelo para crear usuarios: es el unico que acepta la contrasena."""
    password: str = Field(..., min_length=4)


class UsuarioDB(UsuarioBase):
    """
    Modelo de salida, con el id que asigna la base de datos.

    Antes heredaba tambien el campo password, de modo que GET /usuarios
    devolvia la contrasena de todos los usuarios a cualquiera que llamara al
    endpoint. Al quedarse fuera del modelo, FastAPI ya no la puede serializar.
    """
    id: int
