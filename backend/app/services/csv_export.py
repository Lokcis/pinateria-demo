"""Archivos CSV que abre Excel en espanol: UTF-8 con BOM, punto y coma como separador (Adendo v3, RF-066)."""

import csv
import io
from collections.abc import Iterable, Sequence
from decimal import Decimal

SEPARADOR = ";"
_INICIOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def celda_segura(valor: object) -> str:
    """Convierte un valor a texto de celda y evita que Excel lo interprete como una formula.

    Los textos que escribe la gente (descripcion, beneficiario, motivo) pueden empezar por `=`, `+`, `-` o `@`;
    Excel los ejecutaria como formula al abrir el archivo. Se antepone un apostrofo, que Excel no muestra.
    Los numeros no se tocan (un monto negativo no es un texto escrito por una persona).

    Args:
        valor: Valor de la celda. None queda como cadena vacia.

    Returns:
        str: El texto de la celda.
    """
    if valor is None:
        return ""
    if isinstance(valor, (int, float, Decimal)):
        return str(valor)
    texto = str(valor)
    return "'" + texto if texto.startswith(_INICIOS_DE_FORMULA) else texto


def generar_csv(encabezados: Sequence[str], filas: Iterable[Sequence[object]]) -> str:
    """Arma el contenido de un CSV con BOM y punto y coma.

    Args:
        encabezados: Titulos de las columnas.
        filas: Una secuencia de valores por fila, en el orden de `encabezados`.

    Returns:
        str: El archivo completo; se entrega codificado en UTF-8 (el BOM va al inicio).
    """
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=SEPARADOR, lineterminator="\r\n")
    escritor.writerow(encabezados)
    for fila in filas:
        escritor.writerow([celda_segura(valor) for valor in fila])
    return "﻿" + salida.getvalue()
