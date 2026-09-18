"""
Conteo de extremo a extremo con el modelo real y una camara falsa.

Necesita ultralytics, torch y el fichero de pesos, asi que esta marcada como
integracion y no corre por defecto:

    pytest -m integracion
"""

import cv2
import numpy as np
import pytest

import camara
from control_model import ControlModel

pytestmark = pytest.mark.integracion


class CamaraFalsa:
    """Reproduce la interfaz de cv2.VideoCapture sobre una lista de fotogramas."""

    def __init__(self, fotogramas):
        self._fotogramas = fotogramas
        self._siguiente = 0

    def isOpened(self):
        return True

    def read(self):
        if self._siguiente >= len(self._fotogramas):
            return False, None
        fotograma = self._fotogramas[self._siguiente]
        self._siguiente += 1
        return True, fotograma.copy()

    def set(self, *args):
        pass

    def release(self):
        pass


@pytest.fixture
def foto_de_aguacate():
    ruta = camara.os.path.join(camara.UPLOADS_DIR, "5d72fec430ca42e3b21771d29c315f0e.jpg")
    if not camara.os.path.exists(ruta):
        pytest.skip("no hay una foto de aguacate de referencia en uploads/")
    return cv2.resize(cv2.imread(ruta), (640, 480))


def _recolorear(imagen):
    """Otro fruto: mismo contorno, color distinto, para que el modelo lo siga viendo."""
    hsv = cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV).astype(np.int16)
    hsv[:, :, 0] = (hsv[:, :, 0] + 60) % 180
    hsv[:, :, 2] = (hsv[:, :, 2] * 0.55).astype(np.int16)
    return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)


def _contar(monkeypatch, fotogramas):
    monkeypatch.setattr(camara.cv2, "VideoCapture",
                        lambda *args, **kwargs: CamaraFalsa(fotogramas))
    control = ControlModel()
    manager = camara.CamaraManager(control, camara_index=0)
    manager.camaras_disponibles = [0]

    generador = manager.generar_frames()
    for _ in fotogramas:
        try:
            next(generador)
        except StopIteration:
            break
    return control.get_contadores()


def test_el_mismo_fruto_no_se_cuenta_dos_veces(monkeypatch, foto_de_aguacate):
    if camara.model is None:
        pytest.skip("modelo YOLO no disponible")

    contadores = _contar(monkeypatch, [foto_de_aguacate] * 20)

    assert contadores["total"] == 1


def test_cambiar_el_fruto_suma_una_unidad_nueva(monkeypatch, foto_de_aguacate):
    """El tracker reutiliza el ID; la firma de color es la que detecta el cambio."""
    if camara.model is None:
        pytest.skip("modelo YOLO no disponible")

    otro = _recolorear(foto_de_aguacate)
    contadores = _contar(monkeypatch, [foto_de_aguacate] * 8 + [otro] * 8)

    assert contadores["total"] == 2
