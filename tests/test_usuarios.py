"""Almacenamiento de usuarios: que se guarde hasheado y que no salga de la base."""

import sqlite3

import pytest

import base_usuarios
from seguridad import es_hash, verificar_password


@pytest.fixture
def base_temporal(tmp_path, monkeypatch):
    """Apunta el modulo a una base vacia para no tocar la real."""
    ruta = tmp_path / "usuarios.db"
    monkeypatch.setattr(base_usuarios, "DB_PATH", str(ruta))
    base_usuarios.crear_tabla()
    return str(ruta)


def _password_guardada(ruta, username):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    fila = conexion.execute(
        "SELECT password FROM usuarioau WHERE username = ?", (username,)
    ).fetchone()
    conexion.close()
    return fila["password"] if fila else None


def test_el_registro_guarda_la_contrasena_hasheada(base_temporal):
    base_usuarios.agregar_usuario(
        {"nombre": "ana", "email": "ana@example.com", "password": "secreta123", "edad": 30}
    )

    guardada = _password_guardada(base_temporal, "ana")
    assert es_hash(guardada)
    assert "secreta123" not in guardada
    assert verificar_password("secreta123", guardada)


def test_el_registro_no_devuelve_la_contrasena(base_temporal):
    creado = base_usuarios.agregar_usuario(
        {"nombre": "ana", "email": "ana@example.com", "password": "secreta123", "edad": 30}
    )

    assert "password" not in creado
    assert creado["nombre"] == "ana"
    assert creado["id"] > 0


def test_el_listado_no_expone_contrasenas(base_temporal):
    """GET /usuarios no pide autenticacion, asi que no puede devolverlas."""
    base_usuarios.agregar_usuario(
        {"nombre": "ana", "email": "ana@example.com", "password": "secreta123", "edad": 30}
    )
    base_usuarios.agregar_usuario(
        {"nombre": "luis", "email": "luis@example.com", "password": "otraclave", "edad": 41}
    )

    usuarios = base_usuarios.obtener_usuarios()

    assert len(usuarios) == 2
    assert all("password" not in u for u in usuarios)


def test_el_listado_usa_los_nombres_de_campo_publicos(base_temporal):
    """En la base las columnas son username y correo; fuera son nombre y email."""
    base_usuarios.agregar_usuario(
        {"nombre": "ana", "email": "ana@example.com", "password": "secreta123", "edad": 30}
    )

    usuario = base_usuarios.obtener_usuarios()[0]

    assert usuario["nombre"] == "ana"
    assert usuario["email"] == "ana@example.com"
    assert usuario["edad"] == 30
