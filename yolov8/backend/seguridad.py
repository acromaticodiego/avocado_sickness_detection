"""
Hash y verificacion de contrasenas.

Hasta ahora las contrasenas se guardaban en texto plano y el login las
comparaba con un WHERE password = ? en SQL. Aqui se centraliza el hasheo con
bcrypt, que ya incorpora la sal en el propio hash.

La verificacion acepta tambien las contrasenas antiguas en texto plano para no
dejar fuera a los usuarios que ya existen: cuando una de esas entra bien, el
endpoint de ingreso la reescribe hasheada, asi que la base se migra sola a
medida que la gente va entrando.
"""

import hmac

import bcrypt

# Prefijos que usa bcrypt en sus hashes
PREFIJOS_BCRYPT = ("$2a$", "$2b$", "$2y$")


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def es_hash(valor) -> bool:
    """Indica si el valor guardado ya esta hasheado."""
    return isinstance(valor, str) and valor.startswith(PREFIJOS_BCRYPT)


def verificar_password(password: str, guardado) -> bool:
    if not guardado or not isinstance(guardado, str):
        return False

    if es_hash(guardado):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), guardado.encode("utf-8"))
        except ValueError:
            return False

    # Usuario anterior al hasheo. Se compara en tiempo constante para no filtrar
    # informacion por el tiempo de respuesta.
    return hmac.compare_digest(password, guardado)
