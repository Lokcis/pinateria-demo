"""Normalizacion de los textos que se registran: primera letra en mayuscula y el resto en minuscula."""


def capitalizar_nombre(texto: str) -> str:
    """Normaliza un nombre: quita espacios sobrantes y deja la primera letra en mayuscula y el resto en minuscula.

    Los espacios repetidos (y los saltos de linea) se reducen a uno solo.

    Args:
        texto: Nombre tal como lo escribio la persona (ej. "  PIÑATA   mickey MOUSE ").

    Returns:
        str: El nombre normalizado (ej. "Piñata mickey mouse"); cadena vacia si solo habia espacios.
    """
    return " ".join(texto.split()).capitalize()


def capitalizar_texto(texto: str) -> str:
    """Normaliza un texto libre (descripcion, nota, motivo): recorta los extremos y aplica la regla de las mayusculas.

    A diferencia de `capitalizar_nombre`, conserva los espacios y saltos de linea del interior.

    Args:
        texto: Texto tal como lo escribio la persona.

    Returns:
        str: El texto con la primera letra en mayuscula y el resto en minuscula; cadena vacia si solo habia espacios.
    """
    return texto.strip().capitalize()
