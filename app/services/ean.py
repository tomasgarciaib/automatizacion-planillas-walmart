"""Generación y validación de códigos EAN-13."""

from __future__ import annotations

import secrets


def _check_digit(first_twelve: list[int]) -> int:
    total = sum(first_twelve[::2]) + 3 * sum(first_twelve[1::2])
    return (10 - total % 10) % 10


def generate_ean13() -> str:
    """Genera un código EAN-13 válido con 12 dígitos aleatorios y checksum."""
    first_twelve = [secrets.randbelow(10) for _ in range(12)]
    return "".join(map(str, first_twelve)) + str(_check_digit(first_twelve))


def generate_ean13_massive(n: int, unique: bool = False) -> list[str]:
    """Genera n códigos EAN-13 y opcionalmente garantiza que sean únicos."""
    if n < 1:
        raise ValueError("number_of_codes debe ser mayor que cero")
    if not unique:
        return [generate_ean13() for _ in range(n)]

    result: list[str] = []
    seen: set[str] = set()
    while len(result) < n:
        code = generate_ean13()
        if code not in seen:
            seen.add(code)
            result.append(code)
    return result


def validate_ean13(code: str) -> bool:
    """Valida longitud, dígitos y checksum de un EAN-13."""
    if len(code) != 13 or not code.isdigit():
        return False
    digits = [int(character) for character in code]
    return _check_digit(digits[:12]) == digits[12]
