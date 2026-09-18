"""Hasheo y verificacion de contrasenas."""

from seguridad import es_hash, hashear_password, verificar_password


def test_el_hash_no_contiene_la_contrasena():
    hash_ = hashear_password("secreta123")
    assert "secreta123" not in hash_
    assert es_hash(hash_)


def test_la_contrasena_correcta_valida():
    assert verificar_password("secreta123", hashear_password("secreta123"))


def test_una_contrasena_incorrecta_no_valida():
    assert not verificar_password("otra", hashear_password("secreta123"))


def test_dos_hashes_de_la_misma_contrasena_son_distintos():
    """bcrypt incorpora una sal distinta en cada hash."""
    assert hashear_password("secreta123") != hashear_password("secreta123")


def test_la_contrasena_antigua_en_texto_plano_sigue_validando():
    """Compatibilidad con los usuarios creados antes del hasheo."""
    assert verificar_password("claveenplano", "claveenplano")
    assert not verificar_password("otra", "claveenplano")


def test_se_distingue_lo_hasheado_de_lo_que_no():
    assert es_hash(hashear_password("x1234"))
    assert not es_hash("claveenplano")
    assert not es_hash("")
    assert not es_hash(None)


def test_un_valor_guardado_vacio_o_invalido_nunca_valida():
    assert not verificar_password("x", "")
    assert not verificar_password("x", None)
    # Cadena con pinta de hash pero corrupta: bcrypt lanza y se traduce a fallo
    assert not verificar_password("x", "$2b$12$corrupto")
