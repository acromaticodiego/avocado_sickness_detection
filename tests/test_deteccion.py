"""
Reglas de deteccion y conteo de camara.py.

Son las cuatro decisiones de las que depende que el conteo sea correcto:
el umbral de enfermedad, la supresion de cajas solapadas, la firma de color
que distingue un fruto de otro, y el ajuste de la caja al contorno real.
"""

import cv2
import numpy as np
import pytest

import camara


# --------------------------------------------------------------------------
# Umbral de enfermedad: por debajo del 70% el fruto se cuenta como sano
# --------------------------------------------------------------------------

@pytest.mark.parametrize("etiqueta, confianza, esperado", [
    ("antracnosis", 0.96, "antracnosis"),
    ("antracnosis", 0.70, "antracnosis"),   # el umbral entra
    ("antracnosis", 0.69, "sano"),
    ("sarna-negra", 0.85, "sarna-negra"),
    ("sarna-negra", 0.55, "sano"),
    ("sano", 0.31, "sano"),                 # a un fruto sano no le afecta
])
def test_una_enfermedad_dudosa_se_cuenta_como_sana(etiqueta, confianza, esperado):
    assert camara.clasificar_deteccion(etiqueta, confianza) == esperado


def test_el_umbral_de_enfermedad_es_configurable():
    assert camara.clasificar_deteccion("antracnosis", 0.80, umbral=0.90) == "sano"
    assert camara.clasificar_deteccion("antracnosis", 0.80, umbral=0.50) == "antracnosis"


# --------------------------------------------------------------------------
# Supresion de cajas solapadas: una caja por fruto
# --------------------------------------------------------------------------

def _deteccion(track_id, conf, caja, label="antracnosis"):
    return {"track_id": track_id, "conf": conf, "caja": caja, "label": label}


def test_dos_cajas_sobre_el_mismo_fruto_se_reducen_a_una():
    """Geometria tomada de un caso real: IoU 0.52, contencion 0.89."""
    conservadas = camara.suprimir_solapadas([
        _deteccion(94, 0.83, (67, 102, 428, 352)),
        _deteccion(89, 0.99, (228, 87, 430, 364)),
    ])

    assert len(conservadas) == 1
    assert conservadas[0]["track_id"] == 89, "gana la caja de mayor confianza"


def test_la_caja_que_sobrevive_recuerda_a_la_que_absorbio():
    """El track absorbido hace falta para heredar su conteo y no duplicar el fruto."""
    conservadas = camara.suprimir_solapadas([
        _deteccion(94, 0.83, (67, 102, 428, 352)),
        _deteccion(89, 0.99, (228, 87, 430, 364)),
    ])

    absorbidas = [d["track_id"] for d in conservadas[0]["absorbidas"]]
    assert absorbidas == [94]


def test_dos_frutos_vecinos_no_se_fusionan():
    """Aguacates pegados en la bandeja: se rozan, pero son dos unidades."""
    conservadas = camara.suprimir_solapadas([
        _deteccion(1, 0.80, (100, 100, 250, 300), "sano"),
        _deteccion(2, 0.75, (230, 100, 380, 300), "sano"),
    ])

    assert len(conservadas) == 2


def test_una_caja_contenida_en_otra_se_descarta():
    """Una lesion detectada dentro del fruto no es un fruto aparte."""
    conservadas = camara.suprimir_solapadas([
        _deteccion(5, 0.90, (100, 100, 400, 400), "sano"),
        _deteccion(6, 0.72, (180, 180, 280, 280), "antracnosis"),
    ])

    assert len(conservadas) == 1
    assert conservadas[0]["track_id"] == 5


def test_cajas_separadas_se_conservan_todas():
    conservadas = camara.suprimir_solapadas([
        _deteccion(1, 0.9, (0, 0, 100, 100)),
        _deteccion(2, 0.8, (200, 200, 300, 300)),
        _deteccion(3, 0.7, (400, 0, 500, 100)),
    ])

    assert len(conservadas) == 3


def test_sin_detecciones_no_falla():
    assert camara.suprimir_solapadas([]) == []


def test_el_solape_de_cajas_identicas_es_total():
    iou, contencion = camara._solape((0, 0, 100, 100), (0, 0, 100, 100))
    assert iou == pytest.approx(1.0)
    assert contencion == pytest.approx(1.0)


def test_el_solape_de_cajas_disjuntas_es_cero():
    assert camara._solape((0, 0, 50, 50), (100, 100, 150, 150)) == (0.0, 0.0)


# --------------------------------------------------------------------------
# Firma de color: distinguir un aguacate de otro dentro del mismo track
# --------------------------------------------------------------------------

def _fruto(color_bgr, tamano=(200, 200)):
    """Imagen con un fruto de color plano sobre fondo claro."""
    imagen = np.full((tamano[1], tamano[0], 3), 235, np.uint8)
    cv2.ellipse(imagen, (tamano[0] // 2, tamano[1] // 2),
                (60, 80), 0, 0, 360, color_bgr, -1)
    return imagen


def test_el_mismo_fruto_se_reconoce_entre_fotogramas():
    imagen = _fruto((40, 160, 40))
    caja = (40, 20, 160, 180)

    similitud = camara.similitud_firmas(
        camara.firma_color(imagen, caja),
        camara.firma_color(imagen.copy(), caja),
    )

    assert similitud > camara.UMBRAL_SIMILITUD_FRUTO


def test_dos_frutos_distintos_no_se_confunden():
    caja = (40, 20, 160, 180)
    verde = camara.firma_color(_fruto((40, 160, 40)), caja)
    oscuro = camara.firma_color(_fruto((30, 40, 120)), caja)

    assert camara.similitud_firmas(verde, oscuro) < camara.UMBRAL_SIMILITUD_FRUTO


def test_una_caja_vacia_no_produce_firma():
    imagen = _fruto((40, 160, 40))
    assert camara.firma_color(imagen, (50, 50, 50, 50)) is None


def test_sin_firma_previa_se_asume_el_mismo_fruto():
    """No hay con que comparar, asi que no se puede afirmar que haya cambiado."""
    assert camara.similitud_firmas(None, None) == 1.0


# --------------------------------------------------------------------------
# Ajuste de la caja al contorno real del fruto
# --------------------------------------------------------------------------

def _imagen_con_fruto():
    """Fruto de 120x280 px centrado: ocupa de y=60 a y=340."""
    imagen = np.full((400, 400, 3), 240, np.uint8)
    cv2.ellipse(imagen, (200, 200), (80, 140), 0, 0, 360, (40, 160, 40), -1)
    return imagen


def test_la_caja_se_expande_hasta_cubrir_el_fruto_entero():
    """El modelo devuelve media caja; el ajuste la lleva al contorno completo."""
    imagen = _imagen_con_fruto()
    media_caja = (120, 60, 280, 200)          # solo la mitad superior del fruto

    ajustada = camara.ajustar_caja_al_objeto(imagen, media_caja, margen=1.5)

    assert ajustada[3] >= 330, "debe alcanzar la base del fruto, en y=340"
    assert ajustada[0] <= media_caja[0] and ajustada[1] <= media_caja[1]
    assert ajustada[2] >= media_caja[2], "nunca se hace mas pequena que la del modelo"


def test_la_expansion_no_pasa_de_la_region_de_busqueda():
    """
    El margen acota cuanto puede crecer la caja, y es la salvaguarda que impide
    que una mala segmentacion se lleve medio fotograma. El precio es que con una
    caja del modelo mucho mas pequena que el fruto la expansion se queda corta:
    aqui el fruto acaba en y=340 pero la region de busqueda termina en y=305.
    """
    imagen = _imagen_con_fruto()
    media_caja = (120, 60, 280, 200)

    ajustada = camara.ajustar_caja_al_objeto(imagen, media_caja, margen=0.75)

    assert ajustada[3] > media_caja[3], "crece, pero"
    assert ajustada[3] <= 305, "no puede pasar del limite de la region"


def test_sin_fruto_que_segmentar_se_respeta_la_caja_del_modelo():
    """Fondo uniforme: no hay contorno fiable, asi que no se toca nada."""
    imagen = np.full((300, 300, 3), 240, np.uint8)
    caja = (100, 100, 200, 200)

    assert camara.ajustar_caja_al_objeto(imagen, caja) == caja


def test_una_caja_degenerada_se_devuelve_igual():
    imagen = np.full((300, 300, 3), 240, np.uint8)
    assert camara.ajustar_caja_al_objeto(imagen, (50, 50, 50, 50)) == (50, 50, 50, 50)


# --------------------------------------------------------------------------
# Etiquetas: no deben pisarse entre si dentro de un fotograma
# --------------------------------------------------------------------------

def test_las_etiquetas_de_frutos_vecinos_no_se_superponen():
    fotograma = np.full((480, 640, 3), 40, np.uint8)
    ocupados = []

    camara.dibujar_deteccion(fotograma, (60, 120, 300, 400), "#12  Sano  94%",
                             camara.color_de_clase("sano"), ocupados=ocupados)
    camara.dibujar_deteccion(fotograma, (150, 118, 390, 398), "#13  Antracnosis  88%",
                             camara.color_de_clase("antracnosis"), ocupados=ocupados)

    assert len(ocupados) == 2
    assert not camara._se_solapan(ocupados[0], ocupados[1])


def test_cada_clase_tiene_su_color():
    assert camara.color_de_clase("sano") != camara.color_de_clase("antracnosis")
    assert camara.color_de_clase("sano") != camara.color_de_clase("sarna-negra")
    assert camara.color_de_clase("desconocida") == camara.COLOR_PENDIENTE
