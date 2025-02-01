import random


def obtener_clima(ciudad: str) -> str:
    """Obtiene el clima actual de una ciudad dada.

    ------
    Parameters:
        ciudad: Nombre de la ciudad de la que se desea obtener el clima.
    """
    return f"El clima en {ciudad} es {random.randint(18, 42)}°C."
