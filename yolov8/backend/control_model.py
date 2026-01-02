from collections import defaultdict
from camara import model      # ⬅️ Ahora se importa desde camara.py
import cv2


class ControlModel:
    def __init__(self):
        if model is None:
            raise RuntimeError("El modelo YOLO no está disponible para procesamiento.")
        
        # Diccionario para almacenar los contadores finales por etiqueta
        self.contadores = defaultdict(int)
        
    def reiniciar_contadores(self):
        """Reinicia todos los contadores a 0."""
        self.contadores = defaultdict(int)

    def incrementar_contador(self, label: str):
        """Incrementa el contador de una etiqueta dada.
           Útil para cuando se detecta un nuevo objeto."""
        self.contadores[label] += 1

    def actualizar_contador(self, old_label: str, new_label: str):
        """Actualiza la clasificación de un objeto que ya ha sido contado.
           Decrementa el contador de la etiqueta antigua y lo incrementa para la nueva."""
        if self.contadores[old_label] > 0:
            self.contadores[old_label] -= 1
        self.contadores[new_label] += 1

    def get_contadores(self):
        """Devuelve los contadores actuales como diccionario, incluyendo total."""
        por_etiqueta = dict(self.contadores)
        total = sum(self.contadores.values())
        return {
            "total": total,
            "por_etiqueta": por_etiqueta
        }