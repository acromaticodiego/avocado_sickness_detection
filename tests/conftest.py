"""
Configuracion comun de las pruebas.

Las pruebas unitarias solo tocan funciones puras de camara.py (umbral de
enfermedad, supresion de cajas solapadas, firma de color, ajuste de caja), pero
importar ese modulo arrastra ultralytics, que a su vez arrastra torch. Para que
la suite corra rapido y sin GPU ni modelo, si ultralytics no esta instalado se
sustituye por un doble minimo: asi las pruebas unitarias siguen siendo validas
en un entorno ligero, y donde ultralytics si esta se usa el real, que es lo que
necesitan las pruebas de integracion.
"""

import os
import sys
import types

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "yolov8", "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def _instalar_doble_de_ultralytics():
    modulo = types.ModuleType("ultralytics")

    class YOLO:
        """Doble de YOLO: se construye sin cargar pesos y no predice nada."""

        def __init__(self, *args, **kwargs):
            self.names = {0: "sano", 1: "sarna-negra", 2: "antracnosis"}

        def __call__(self, *args, **kwargs):
            raise RuntimeError(
                "Esta prueba necesita el modelo real; deberia estar marcada como integracion."
            )

        track = __call__

    modulo.YOLO = YOLO
    sys.modules["ultralytics"] = modulo


try:
    import ultralytics  # noqa: F401
except ImportError:
    _instalar_doble_de_ultralytics()
