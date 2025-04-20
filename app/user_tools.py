from app.utils.tool_utils import user_tool
import random


@user_tool
def obtener_clima(ciudad: str) -> str:
    """Obtiene el clima actual de una ciudad dada.
    ------
    Parameters:
        ciudad: Nombre de la ciudad de la que se desea obtener el clima.
    """
    return f"El clima en {ciudad} es {random.randint(18, 42)}°C."


@user_tool
def precio_de_platillo(platillo: str) -> str:
    """Obtiene el precio de un platillo dado.
    ------
    Parameters:
        platillo: Nombre del platillo del que se desea obtener el precio.
    """
    return f"El precio de {platillo} es ${random.randint(100, 500)}."


@user_tool
def calcular_interes(cantidad: float, tasa: float, tiempo: int) -> str:
    """
    Calcula el interés de una cantidad dada a una tasa de interés anual durante un tiempo específico.
    """
    interes = cantidad * (tasa / 100) * tiempo
    return (
        f"El interés para una cantidad de {cantidad} a una tasa de {tasa}% "
        f"durante {tiempo} años es {round(interes, 2)}."
    )
