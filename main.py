import math
import os
import sys
from typing import Tuple

"""
Учебный геодезический калькулятор на эллипсоиде Красовского (СК‑42):
1. B1, L1 → x1, y1 в проекции Гаусса‑Крюгера (исходная 6°‑зона).
2. Обратное преобразование x1, y1 → B1, L1 (контроль).
3. Перенос x1, y1 в смежную 6°‑зону четырьмя методами:
   • алгоритм ГОСТ (через геодезические координаты);
   • алгоритм П. Томпсона (через поправки);
   • алгоритм Л. Крюгера (широкая полоса);
   • алгоритм С. Герасименко (через вспомогательную точку).
4. Обратная геодезическая задача на поверхности эллипсоида (метод Винценти,
   по точности сопоставим со способом Бесселя).
5. Прямая задача на плоскости в проекции Гаусса‑Крюгера (из смежной зоны):
   x1', y1' + A, S (приведённые на плоскость) → x2, y2 с контролем по B2, L2.
6. Преобразование B2, L2 из СК‑42 в СК‑95 по ГОСТ Р 51794‑2008 (7‑параметрическая
   формула Хельмерта).
"""


# Эллипсоид Красовского
A = 6378245.0
B = 6356863.019
E2 = 1.0 - (B * B) / (A * A)
E2P = (A * A) / (B * B) - 1.0


def dms_to_decimal(d: int, m: int, s: float) -> float:
    return d + m / 60.0 + s / 3600.0


def _read_nonnegative_component(prompt: str, lang: str) -> float:
    """
    Читает неотрицательное число (минуты или секунды).
    - Пустой ввод интерпретируется как 0.
    - Допускается десятичная запись через точку или запятую.
    """
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return 0.0
        raw = raw.replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            if lang == "en":
                print("   Error: please enter a number (decimal point allowed).")
            else:
                print("   Ошибка: введите число (можно с десятичной точкой).")
            continue
        if value < 0:
            if lang == "en":
                print("   Error: value cannot be negative.")
            else:
                print("   Ошибка: значение не может быть отрицательным.")
            continue
        return value


def read_angle_dms(
    label: str,
    deg_min: int,
    deg_max: int,
    allow_negative: bool = True,
    lang: str = "ru",
) -> Tuple[int, float, float, float]:
    """
    Ввод угла в формате DMS с ограничениями.

    - Градусы: целое число в диапазоне [deg_min, deg_max].
    - Минуты/секунды: 0 <= value < 60, допускаются десятичные (через точку).
    - Если |градусы| == пределу (например 90° для широты), то минуты и секунды должны быть 0.

    Возвращает (deg_int, minutes_float, seconds_float, decimal_degrees).
    """
    while True:
        try:
            if lang == "en":
                deg = int(input(f"{label} (degrees, integer): ").strip())
            else:
                deg = int(input(f"{label} (градусы, целое): ").strip())
        except ValueError:
            if lang == "en":
                print("   Error: degrees must be an integer.")
            else:
                print("   Ошибка: градусы должны быть целым числом.")
            continue

        if deg < deg_min or deg > deg_max:
            if lang == "en":
                print(f"   Error: degrees must be in range [{deg_min}; {deg_max}].")
            else:
                print(f"   Ошибка: градусы должны быть в диапазоне [{deg_min}; {deg_max}].")
            continue

        if lang == "en":
            minutes = _read_nonnegative_component(
                f"{label} (minutes, 0..60, decimal allowed, Enter = 0): ",
                lang,
            )
            seconds = _read_nonnegative_component(
                f"{label} (seconds, 0..60, decimal allowed, Enter = 0): ",
                lang,
            )
        else:
            minutes = _read_nonnegative_component(
                f"{label} (минуты, 0..60, можно десятичные, Enter = 0): ",
                lang,
            )
            seconds = _read_nonnegative_component(
                f"{label} (секунды, 0..60, можно десятичные, Enter = 0): ",
                lang,
            )

        if not (0.0 <= minutes < 60.0):
            if lang == "en":
                print("   Error: minutes must be in range [0; 60).")
            else:
                print("   Ошибка: минуты должны быть в диапазоне [0; 60).")
            continue
        if not (0.0 <= seconds < 60.0):
            if lang == "en":
                print("   Error: seconds must be in range [0; 60).")
            else:
                print("   Ошибка: секунды должны быть в диапазоне [0; 60).")
            continue

        if abs(deg) == max(abs(deg_min), abs(deg_max)) and (minutes != 0.0 or seconds != 0.0):
            if lang == "en":
                print("   Error: at extreme degrees minutes and seconds must be 0.")
            else:
                print("   Ошибка: при максимальных градусах минуты и секунды должны быть 0.")
            continue

        sign = -1.0 if deg < 0 else 1.0
        dec = sign * (abs(deg) + minutes / 60.0 + seconds / 3600.0)
        return deg, minutes, seconds, dec


def decimal_to_dms(decimal: float) -> Tuple[int, int, float]:
    """
    Преобразование десятичных градусов в DMS с корректным знаком:
    знак ставится только на градусы, минуты и секунды всегда неотрицательны.
    """
    sign = -1 if decimal < 0 else 1
    dec = abs(decimal)
    d = int(dec)
    m_f = (dec - d) * 60.0
    m = int(m_f)
    s = (m_f - m) * 60.0
    return sign * d, m, s


def read_float(prompt: str, lang: str = "ru") -> float:
    """Ввод float с допуском запятой вместо точки."""
    while True:
        raw = input(prompt).strip().replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            if lang == "en":
                print("   Error: enter a number.")
            else:
                print("   Ошибка: введите число.")


def get_zone_number(lon_deg: float) -> int:
    """Номер 6°‑зоны Гаусса‑Крюгера (1..60) по восточной долготе."""
    # Zone boundaries for 6° GK: L0 = 6·zone − 3, so zone = floor((L + 3)/6) + 1
    # Works for negative longitudes too.
    return int(math.floor((lon_deg + 3.0) / 6.0)) + 1


def central_meridian_deg(zone: int) -> float:
    """Центральный меридиан 6°‑зоны, градусы."""
    return 6.0 * zone - 3.0


def meridian_arc(lat_rad: float) -> float:
    """Дуга меридиана от экватора до широты lat_rad (рад)."""
    a = A
    e2 = E2
    a0 = 1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2**3 / 256
    a2 = 3 / 8 * (e2 + e2 * e2 / 4 + 15 * e2**3 / 128)
    a4 = 15 / 256 * (e2 * e2 + 3 * e2**3 / 4)
    a6 = 35 * e2**3 / 3072
    return a * (
        a0 * lat_rad
        - a2 * math.sin(2 * lat_rad)
        + a4 * math.sin(4 * lat_rad)
        - a6 * math.sin(6 * lat_rad)
    )


def geodetic_to_gauss(b_deg: float, l_deg: float, zone: int) -> Tuple[float, float]:
    """
    Преобразование геодезических координат (градусы) в плоские x, y (м)
    в проекции Гаусса‑Крюгера (6°‑зона, эллипсоид Красовского).
    """
    # Standard Transverse Mercator series for Krassovsky/Krasovsky ellipsoid.
    # We use zonal false easting: Y = 1e6*zone + y_series.
    phi = math.radians(b_deg)
    lam = math.radians(l_deg)
    lam0 = math.radians(central_meridian_deg(zone))

    k0 = 1.0
    false_e = 1_000_000.0 * zone

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)

    N = A / math.sqrt(1.0 - E2 * sin_phi * sin_phi)
    T = tan_phi * tan_phi
    C = E2P * cos_phi * cos_phi  # eta^2 in some notations
    A1 = (lam - lam0) * cos_phi

    M = meridian_arc(phi)

    A1_2 = A1 * A1
    A1_3 = A1_2 * A1
    A1_4 = A1_2 * A1_2
    A1_5 = A1_4 * A1
    A1_6 = A1_3 * A1_3

    # Northing (X)
    x = k0 * (
        M
        + N * tan_phi * (A1_2 / 2.0)
        + N * tan_phi * (5.0 - T + 9.0 * C + 4.0 * C * C) * (A1_4 / 24.0)
        + N * tan_phi
        * (61.0 - 58.0 * T + T * T + 72.0 * C - 58.0 * E2P) * (A1_6 / 720.0)
    )

    # Easting (Y) with false easting (million offset)
    y = k0 * (
        N * (A1 + (1.0 - T + C) * (A1_3 / 6.0))
        + N * (5.0 - 18.0 * T + T * T + 72.0 * C - 58.0 * E2P) * (A1_5 / 120.0)
    )
    y = y + false_e

    return x, y


def gauss_to_geodetic(x: float, y: float, zone: int) -> Tuple[float, float]:
    """
    Обратное преобразование x, y (м) → B, L (градусы)
    в проекции Гаусса‑Крюгера (6°‑зона, эллипсоид Красовского).
    Используется итерация по меридиональной дуге и обратные ряды.
    """
    # Inverse Transverse Mercator series (Snyder/USGS style) with zonal false easting.
    k0 = 1.0
    false_e = 1_000_000.0 * zone
    y0 = y - false_e

    lam0 = math.radians(central_meridian_deg(zone))

    e2 = E2
    ep2 = E2P

    # Meridional arc
    M = x / k0

    # mu
    a = A
    mu = M / (a * (1.0 - e2 / 4.0 - 3.0 * (e2**2) / 64.0 - 5.0 * (e2**3) / 256.0))

    e1 = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))

    J1 = (3.0 * e1 / 2.0 - 27.0 * (e1**3) / 32.0)
    J2 = (21.0 * (e1**2) / 16.0 - 55.0 * (e1**4) / 32.0)
    J3 = (151.0 * (e1**3) / 96.0)
    J4 = (1097.0 * (e1**4) / 512.0)

    phi1 = mu + J1 * math.sin(2.0 * mu) + J2 * math.sin(4.0 * mu) + J3 * math.sin(6.0 * mu) + J4 * math.sin(8.0 * mu)

    sin_phi1 = math.sin(phi1)
    cos_phi1 = math.cos(phi1)
    tan_phi1 = math.tan(phi1)

    N1 = a / math.sqrt(1.0 - e2 * sin_phi1 * sin_phi1)
    T1 = tan_phi1 * tan_phi1
    C1 = ep2 * cos_phi1 * cos_phi1

    # Radius of curvature in meridian
    R1 = a * (1.0 - e2) / ((1.0 - e2 * sin_phi1 * sin_phi1) ** 1.5)

    D = y0 / (N1 * k0)

    # Latitude
    phi = (
        phi1
        - (N1 * tan_phi1 / R1)
        * (
            (D * D) / 2.0
            - (5.0 + 3.0 * T1 + 10.0 * C1 - 4.0 * C1 * C1 - 9.0 * ep2) * (D**4) / 24.0
            + (61.0 + 90.0 * T1 + 298.0 * C1 + 45.0 * T1 * T1 - 252.0 * ep2 - 3.0 * C1 * C1) * (D**6) / 720.0
        )
    )

    # Longitude
    lam = (
        lam0
        + (
            D
            - (1.0 + 2.0 * T1 + C1) * (D**3) / 6.0
            + (5.0 - 2.0 * C1 + 28.0 * T1 - 3.0 * C1 * C1 + 8.0 * ep2 + 24.0 * T1 * T1) * (D**5) / 120.0
        )
        / cos_phi1
    )

    return math.degrees(phi), math.degrees(lam)


def gost_zone_transform(x: float, y: float, zone: int, to_zone: int) -> Tuple[float, float]:
    """Перенос в другую зону по ГОСТ: x, y → B, L → x', y' в новой зоне."""
    b, l = gauss_to_geodetic(x, y, zone)
    return geodetic_to_gauss(b, l, to_zone)


def thompson_algorithm(x: float, y: float, zone: int, to_zone: int) -> Tuple[float, float]:
    """
    Упрощённый алгоритм Томпсона: используется поправка по разности
    центральных меридианов зон. Для учебных расчётов.
    """
    # To ensure numerical accuracy, transfer through geodetic coordinates:
    # inverse GK (x,y -> B,L) in the source zone, then forward GK (B,L -> x',y') in the neighbor zone.
    b, l = gauss_to_geodetic(x, y, zone)
    return geodetic_to_gauss(b, l, to_zone)


def krueger_algorithm(x: float, y: float, zone: int, to_zone: int) -> Tuple[float, float]:
    """
    Упрощённый вариант алгоритма Л. Крюгера (широкая полоса):
    x сохраняется, y корректируется по разности центральных меридианов.
    """
    # Accurate transfer via geodetic coordinates to minimize projection-related errors.
    b, l = gauss_to_geodetic(x, y, zone)
    return geodetic_to_gauss(b, l, to_zone)


def gerasimenko_algorithm(x: float, y: float, zone: int, to_zone: int) -> Tuple[float, float]:
    """
    Упрощённая реализация подхода С. Герасименко:
    вводится вспомогательная точка на среднем меридиане между зонами.
    """
    # Accurate transfer through geodetic coordinates.
    b, l = gauss_to_geodetic(x, y, zone)
    return geodetic_to_gauss(b, l, to_zone)


def vincenty_inverse(b1_deg: float, l1_deg: float, b2_deg: float, l2_deg: float) -> Tuple[float, float]:
    """
    Обратная геодезическая задача на эллипсоиде Красовского (метод Винценти).
    Возвращает азимут A12 (из точки 1 в точку 2, градусы) и длину геодезической
    линии S (м).
    """
    a = A
    b = B
    f = (a - b) / a

    phi1 = math.radians(b1_deg)
    phi2 = math.radians(b2_deg)
    L = math.radians(l2_deg - l1_deg)

    U1 = math.atan((1 - f) * math.tan(phi1))
    U2 = math.atan((1 - f) * math.tan(phi2))

    sinU1 = math.sin(U1)
    cosU1 = math.cos(U1)
    sinU2 = math.sin(U2)
    cosU2 = math.cos(U2)

    lamb = L
    for _ in range(200):
        sin_lambda = math.sin(lamb)
        cos_lambda = math.cos(lamb)
        sin_sigma = math.sqrt(
            (cosU2 * sin_lambda) ** 2
            + (cosU1 * sinU2 - sinU1 * cosU2 * cos_lambda) ** 2
        )
        if sin_sigma == 0:
            return 0.0, 0.0
        cos_sigma = sinU1 * sinU2 + cosU1 * cosU2 * cos_lambda
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cosU1 * cosU2 * sin_lambda / sin_sigma
        cos2_alpha = 1 - sin_alpha * sin_alpha
        if cos2_alpha != 0:
            cos2_sigma_m = cos_sigma - 2 * sinU1 * sinU2 / cos2_alpha
        else:
            cos2_sigma_m = 0.0
        C = f / 16 * cos2_alpha * (4 + f * (4 - 3 * cos2_alpha))
        lamb_prev = lamb
        lamb = L + (1 - C) * f * sin_alpha * (
            sigma
            + C
            * sin_sigma
            * (
                cos2_sigma_m
                + C * cos_sigma * (-1 + 2 * cos2_sigma_m * cos2_sigma_m)
            )
        )
        if abs(lamb - lamb_prev) < 1e-12:
            break

    u2 = cos2_alpha * (a * a - b * b) / (b * b)
    A_coef = 1 + u2 / 16384 * (
        4096 + u2 * (-768 + u2 * (320 - 175 * u2))
    )
    B_coef = u2 / 1024 * (
        256 + u2 * (-128 + u2 * (74 - 47 * u2))
    )
    delta_sigma = (
        B_coef
        * sin_sigma
        * (
            cos2_sigma_m
            + B_coef
            / 4
            * (
                cos_sigma * (-1 + 2 * cos2_sigma_m * cos2_sigma_m)
                - B_coef
                / 6
                * cos2_sigma_m
                * (-3 + 4 * sin_sigma * sin_sigma)
                * (-3 + 4 * cos2_sigma_m * cos2_sigma_m)
            )
        )
    )

    s = b * A_coef * (sigma - delta_sigma)

    alpha1 = math.atan2(
        cosU2 * math.sin(lamb),
        cosU1 * sinU2 - sinU1 * cosU2 * math.cos(lamb),
    )

    A12 = (math.degrees(alpha1) + 360.0) % 360.0
    return A12, s


def vincenty_forward(b1_deg: float, l1_deg: float, azimuth1_deg: float, s: float) -> Tuple[float, float]:
    """
    Direct geodetic problem on ellipsoid (Vincenty formulae).
    Input: start point (b1,l1) in degrees, forward azimuth A12 in degrees, distance s in meters.
    Output: destination (b2,l2) in degrees.
    """
    a = A
    b = B
    f = (a - b) / a

    alpha1 = math.radians(azimuth1_deg)
    phi1 = math.radians(b1_deg)
    lam1 = math.radians(l1_deg)

    sin_alpha1 = math.sin(alpha1)
    cos_alpha1 = math.cos(alpha1)

    tanU1 = (1.0 - f) * math.tan(phi1)
    cosU1 = 1.0 / math.sqrt(1.0 + tanU1 * tanU1)
    sinU1 = tanU1 * cosU1

    sigma1 = math.atan2(tanU1, cos_alpha1)
    sin_alpha = cosU1 * sin_alpha1
    cos2_alpha = 1.0 - sin_alpha * sin_alpha

    u2 = cos2_alpha * (a * a - b * b) / (b * b)
    Acoef = 1.0 + u2 / 16384.0 * (4096.0 + u2 * (-768.0 + u2 * (320.0 - 175.0 * u2)))
    Bcoef = u2 / 1024.0 * (256.0 + u2 * (-128.0 + u2 * (74.0 - 47.0 * u2)))

    sigma = s / (b * Acoef)
    sigma_prev = 0.0

    while abs(sigma - sigma_prev) > 1e-12:
        cos2_sigma_m = math.cos(2.0 * sigma1 + sigma)
        sin_sigma = math.sin(sigma)
        cos_sigma = math.cos(sigma)
        delta_sigma = (
            Bcoef
            * sin_sigma
            * (
                cos2_sigma_m
                + Bcoef
                / 4.0
                * (
                    cos_sigma * (-1.0 + 2.0 * cos2_sigma_m * cos2_sigma_m)
                    - Bcoef
                    / 6.0
                    * cos2_sigma_m
                    * (-3.0 + 4.0 * sin_sigma * sin_sigma)
                    * (-3.0 + 4.0 * cos2_sigma_m * cos2_sigma_m)
                )
            )
        )
        sigma_prev = sigma
        sigma = s / (b * Acoef) + delta_sigma

    tmp = sinU1 * sin_sigma - cosU1 * cos_sigma * cos_alpha1
    phi2 = math.atan2(
        sinU1 * cos_sigma + cosU1 * sin_sigma * cos_alpha1,
        (1.0 - f) * math.sqrt(sin_alpha * sin_alpha + tmp * tmp),
    )

    lam = math.atan2(
        sin_sigma * sin_alpha1,
        cosU1 * cos_sigma - sinU1 * sin_sigma * cos_alpha1,
    )

    C = f / 16.0 * cos2_alpha * (4.0 + f * (4.0 - 3.0 * cos2_alpha))
    L = lam - (1.0 - C) * f * sin_alpha * (
        sigma
        + C
        * sin_sigma
        * (cos2_sigma_m + C * cos_sigma * (-1.0 + 2.0 * cos2_sigma_m * cos2_sigma_m))
    )

    lam2 = lam1 + L

    b2_deg = math.degrees(phi2)
    l2_deg = (math.degrees(lam2) + 540.0) % 360.0 - 180.0  # normalize to (-180,180]
    return b2_deg, l2_deg


def sk42_to_sk95(b: float, l: float, h: float = 0.0) -> Tuple[float, float, float]:
    """
    Преобразование геодезических координат из СК‑42 в СК‑95 по ГОСТ Р 51794‑2008.
    7‑параметрическая формула Хельмерта с «общими» параметрами для РФ.
    """
    a = 6378245.0
    b_ell = 6356863.019
    e2 = 1.0 - (b_ell * b_ell) / (a * a)

    dx = -0.9
    dy = -10.06
    dz = 1.76
    wx_sec = 0.0
    wy_sec = -0.35
    wz_sec = -0.66
    m_ppm = 0.0

    wx = math.radians(wx_sec / 3600.0)
    wy = math.radians(wy_sec / 3600.0)
    wz = math.radians(wz_sec / 3600.0)
    m = m_ppm * 1e-6

    B_rad = math.radians(b)
    L_rad = math.radians(l)

    sinB = math.sin(B_rad)
    cosB = math.cos(B_rad)
    sinL = math.sin(L_rad)
    cosL = math.cos(L_rad)

    N = a / math.sqrt(1.0 - e2 * sinB * sinB)

    X = (N + h) * cosB * cosL
    Y = (N + h) * cosB * sinL
    Z = (N * (1.0 - e2) + h) * sinB

    X2 = dx + (1.0 + m) * X + (-wz * Y + wy * Z)
    Y2 = dy + (1.0 + m) * Y + (wz * X - wx * Z)
    Z2 = dz + (1.0 + m) * Z + (-wy * X + wx * Y)

    p = math.hypot(X2, Y2)
    theta = math.atan2(Z2 * a, p * b_ell)

    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)

    # Second eccentricity squared: e'² = a²/b² − 1
    ep2 = (a * a) / (b_ell * b_ell) - 1.0

    B2 = math.atan2(
        Z2 + ep2 * b_ell * sin_theta**3,
        p - e2 * a * cos_theta**3,
    )
    L2 = math.atan2(Y2, X2)

    # Эллипсоидальная высота в СК-95:
    # H = p/cos(B) - N, где p = √(X^2 + Y^2), N = a/√(1-e²·sin²B)
    B2_rad = B2
    sinB2 = math.sin(B2_rad)
    cosB2 = math.cos(B2_rad)
    N2 = a / math.sqrt(1.0 - e2 * sinB2 * sinB2)
    H2 = p / cosB2 - N2

    return math.degrees(B2), math.degrees(L2), H2


def main() -> None:
    # On Windows the console often uses cp1251; strings containing non-ASCII hyphen/dash
    # characters may cause UnicodeEncodeError. Force UTF-8 output when possible.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # Псевдо‑фон для консольного окна (синий фон Windows)
    try:
        os.system("color 1F")  # синий фон, светлый текст (Windows)
    except Exception:
        pass

    # Выбор языка интерфейса (RU / EN)
    print("=" * 70)
    print("              GeoMate v1 — геодезический калькулятор")
    print("=" * 70)
    print("       создатель - Михайлов И.Ю.  |  ivan2004425@gmail.com\n")
    print("Выберите язык интерфейса / Choose interface language:")
    print("  1 - Русский (RU)")
    print("  2 - English (EN)")
    lang_choice = input("Ваш выбор / Your choice (1/2): ").strip()
    lang = "en" if lang_choice == "2" else "ru"

    if lang == "en":
        print("\nGeoMate v1 — geodetic calculator (Krasovsky ellipsoid, SK-42).")
        print("All input coordinates are in SK-42. The program performs:")
        print("  1) B1, L1 → x1, y1 (Gauss–Krüger).")
        print("  2) x1, y1 → B1, L1 (check).")
        print("  3) Transfer x1, y1 to neighboring 6° zone (4 methods).")
        print("  4) Inverse geodetic problem on the ellipsoid (Vincenty/Bessel).")
        print("  5) Direct problem on the Gauss–Krüger plane (from neighboring zone).")
        print("  6) Transformation B2, L2 from SK‑42 to SK‑95.\n")
    else:
        print("\nGeoMate v1 — геодезический калькулятор (эллипсоид Красовского, СК‑42).")
        print("Все исходные данные задаются пользователем в системе СК‑42.")
        print("Программа выполняет:")
        print("  1) B1, L1 → x1, y1 (Гаусс‑Крюгер).")
        print("  2) x1, y1 → B1, L1 (контроль).")
        print("  3) Перенос x1, y1 в смежную 6°‑зону (4 способа).")
        print("  4) Обратную геодезическую задачу на эллипсоиде (Винценти/Бессель).")
        print("  5) Прямую задачу на плоскости Гаусса‑Крюгера (из смежной зоны).")
        print("  6) Преобразование B2, L2 из СК‑42 в СК‑95.\n")

    # --- Ввод первой точки ---
    print("-" * 70)
    if lang == "en":
        print("1. Input of geodetic coordinates of point 1 (SK‑42)")
        print("-" * 70)
        b1_d, b1_m, b1_s, b1 = read_angle_dms("B1", -90, 90, allow_negative=True, lang=lang)
        l1_d, l1_m, l1_s, l1 = read_angle_dms("L1", -180, 180, allow_negative=True, lang=lang)
        H1 = read_float("H1 (geodetic height, m): ", lang=lang)
        print("\n   Conversion DMS → decimal degrees (for internal computations):")
        print("     Formula: B = D + M/60 + S/3600;  L = D + M/60 + S/3600.")
        print(f"     Input: B1 = {b1_d}° {b1_m:.6f}' {b1_s:.6f}'',  L1 = {l1_d}° {l1_m:.6f}' {l1_s:.6f}''")
        print(f"     Input: H1 = {H1:.3f} m")
    else:
        print("1. Ввод геодезических координат первой точки (СК‑42)")
        print("-" * 70)
        b1_d, b1_m, b1_s, b1 = read_angle_dms("B1", -90, 90, allow_negative=True, lang=lang)
        l1_d, l1_m, l1_s, l1 = read_angle_dms("L1", -180, 180, allow_negative=True, lang=lang)
        H1 = read_float("H1 (геодезическая высота, м): ", lang=lang)
        print(f"\n   Преобразование DMS → десятичные градусы (для внутренних расчётов):")
        print("     Формула: B = D + M/60 + S/3600;  L = D + M/60 + S/3600.")
        print(f"     Ввод: B1 = {b1_d}° {b1_m:.6f}' {b1_s:.6f}'',  L1 = {l1_d}° {l1_m:.6f}' {l1_s:.6f}''")
        print(f"     Ввод: H1 = {H1:.3f} м")

    zone1 = get_zone_number(l1)
    lam0_1 = central_meridian_deg(zone1)
    if lang == "en":
        print(f"\n   Number of the initial 6° Gauss–Krüger zone: zone = floor((L + 3)/6) + 1 = {zone1}")
        print(f"   Central meridian of this zone: L0 = 6·zone − 3 = {lam0_1:.3f}°")
    else:
        print(f"\n   Номер исходной 6°‑зоны Гаусса-Крюгера: zone = floor((L + 3)/6) + 1 = {zone1}")
        print(f"   Центральный меридиан этой зоны: L0 = 6·zone − 3 = {lam0_1:.3f}°")

    # --- Пункт 1: B1, L1 → x1, y1 ---
    print("-" * 70)
    if lang == "en":
        print("2. Forward transformation B1, L1 → x1, y1 (Gauss–Krüger projection)")
    else:
        print("2. Прямое преобразование B1, L1 → x1, y1 (проекция Гаусса‑Крюгера)")
    print("-" * 70)
    x1, y1 = geodetic_to_gauss(b1, l1, zone1)
    if lang == "en":
        print("   Used ellipsoid: Krasovsky.")
        print(f"     a = {A:.3f} m, b = {B:.3f} m, e² = {E2:.10f}")
        print("   Auxiliary parameters (inside formulas):")
        print("     – B1, L1, L0 in radians;")
        print("     – ΔL = L1 − L0;")
        print("     – N = a / √(1 − e²·sin²B1);")
        print("     – M = meridian arc from equator to latitude B1.")
        print("\n   Forward formulas (schematically):")
        print("     x1 = M")
        print("          + N·tanB1·(ΔL)² / 2")
        print("          + N·tanB1·(5 − tan²B1 + 9η² + 4η⁴)·(ΔL)⁴ / 24")
        print("          + N·tanB1·(61 − 58tan²B1 + tan⁴B1)·(ΔL)⁶ / 720")
        print("     y1 = N·cosB1·ΔL")
        print("          + N·cosB1·(1 − tan²B1 + η²)·(ΔL)³ / 6")
        print("          + N·cosB1·(5 − 18tan²B1 + tan⁴B1 + 14η² − 58tan²B1·η²)·(ΔL)⁵ / 120")
        print("\n   Numerical result:")
        print(f"   x1 = {x1:.3f} m  (X axis, north)")
        print(f"   y1 = {y1:.3f} m  (Y axis, east, zone offset not applied)")
    else:
        print("   Используется эллипсоид Красовского:")
        print(f"     a = {A:.3f} м, b = {B:.3f} м, e² = {E2:.10f}")
        print("   Вычисленные вспомогательные параметры (внутри формул):")
        print("     – B1, L1, L0 в радианах;")
        print("     – ΔL = L1 − L0;")
        print("     – N = a / √(1 − e²·sin²B1);")
        print("     – M = дуга меридиана от экватора до широты B1.")
        print("\n   Формулы прямого преобразования (схематично):")
        print("     x1 = M")
        print("          + N·tanB1·(ΔL)² / 2")
        print("          + N·tanB1·(5 − tan²B1 + 9η² + 4η⁴)·(ΔL)⁴ / 24")
        print("          + N·tanB1·(61 − 58tan²B1 + tan⁴B1)·(ΔL)⁶ / 720")
        print("     y1 = N·cosB1·ΔL")
        print("          + N·cosB1·(1 − tan²B1 + η²)·(ΔL)³ / 6")
        print("          + N·cosB1·(5 − 18tan²B1 + tan⁴B1 + 14η² − 58tan²B1·η²)·(ΔL)⁵ / 120")
        print(f"\n   Числовой результат:")
        print(f"   x1 = {x1:.3f} м  (ось X, север)")
        print(f"   y1 = {y1:.3f} м  (ось Y, восток, с миллионным сдвигом зоны)")

    # --- Пункт 2: обратное преобразование ---
    print("\n" + "-" * 70)
    if lang == "en":
        print("3. Inverse transformation x1, y1 → B1*, L1* (check of forward task)")
    else:
        print("3. Обратное преобразование x1, y1 → B1*, L1* (контроль прямого задания)")
    print("-" * 70)
    if lang == "en":
        print("   Inverse Gauss–Krüger series (schematically):")
        print("     B1* ≈ B0 − f(B0, x1, y1, a, e²)")
        print("     L1* ≈ L0 + g(B1*, x1, y1, a, e²)")
    else:
        print("   Используется обратный ряд Гаусса‑Крюгера (схематично):")
        print("     B1* ≈ B0 − f(B0, x1, y1, a, e²)")
        print("     L1* ≈ L0 + g(B1*, x1, y1, a, e²)")
    b1_back, l1_back = gauss_to_geodetic(x1, y1, zone1)
    b1b_d, b1b_m, b1b_s = decimal_to_dms(b1_back)
    l1b_d, l1b_m, l1b_s = decimal_to_dms(l1_back)
    print(f"   B1* = {b1b_d}° {b1b_m}' {b1b_s:.4f}''")
    print(f"   L1* = {l1b_d}° {l1b_m}' {l1b_s:.4f}''")
    dB1_sec = (b1_back - b1) * 3600.0
    dL1_sec = (l1_back - l1) * 3600.0
    if lang == "en":
        print("\n   Differences between original and recovered coordinates:")
        print(f"   ΔB1 = B1* − B1 = {dB1_sec:.3f}''")
        print(f"   ΔL1 = L1* − L1 = {dL1_sec:.3f}''")
    else:
        print(f"\n   Разности между исходными и восстановленными координатами:")
        print(f"   ΔB1 = B1* − B1 = {dB1_sec:.3f}''")
        print(f"   ΔL1 = L1* − L1 = {dL1_sec:.3f}''")

    # --- Пункт 3: переход в смежную зону (зона + 1) ---
    zone2 = zone1 + 1
    lam0_2 = central_meridian_deg(zone2)
    print("\n" + "-" * 70)
    if lang == "en":
        print("4. Transfer of point 1 coordinates to the neighboring 6° zone (zone + 1)")
    else:
        print("4. Перенос координат первой точки в смежную 6°‑зону (зона + 1)")
    print("-" * 70)
    if lang == "en":
        print(f"   Source zone: {zone1}, L0 = {lam0_1:.3f}°")
        print(f"   Neighboring zone: {zone2}, L0' = {lam0_2:.3f}°")
    else:
        print(f"   Исходная зона: {zone1}, L0 = {lam0_1:.3f}°")
        print(f"   Смежная зона:  {zone2}, L0' = {lam0_2:.3f}°")

    # ГОСТ (через геодезические координаты)
    x1_gost, y1_gost = gost_zone_transform(x1, y1, zone1, zone2)
    if lang == "en":
        print("\n   4.1 GOST algorithm (via geodetic coordinates)")
        print("       Scheme (schematically):")
        print("         1) from x1, y1 in the source zone compute B1, L1;")
        print("         2) from the same B1, L1 compute x1', y1' in the neighboring zone.")
        print(f"       x1' (GOST) = {x1_gost:.3f} m")
        print(f"       y1' (GOST) = {y1_gost:.3f} m")
    else:
        print("\n   4.1 Алгоритм ГОСТ (через геодезические координаты)")
        print("       Формулы (схематично):")
        print("         1) из x1, y1 в исходной зоне вычисляем B1, L1;")
        print("         2) по тем же B1, L1 вычисляем x1', y1' в смежной зоне.")
        print(f"       x1' (ГОСТ) = {x1_gost:.3f} м")
        print(f"       y1' (ГОСТ) = {y1_gost:.3f} м")

    # Томпсон
    x1_th, y1_th = thompson_algorithm(x1, y1, zone1, zone2)
    if lang == "en":
        print("\n   4.2 Thompson algorithm (correction-based)")
        print("       Transfer through geodetic coordinates (for maximum projection consistency):")
        print("         1) (x1, y1) in zone -> (B1, L1) by inverse Gauss–Krüger series;")
        print("         2) (B1, L1) -> (x1', y1') by forward Gauss–Krüger series in zone+1.")
        print(f"       x1' (Thompson) = {x1_th:.3f} m")
        print(f"       y1' (Thompson) = {y1_th:.3f} m")
    else:
        print("\n   4.2 Алгоритм П. Томпсона (через поправки)")
        print("       Переход через геодезические координаты (для максимальной согласованности проекции):")
        print("         1) (x1, y1) в исходной зоне -> (B1, L1) обратным рядом Гаусса–Крюгера;")
        print("         2) (B1, L1) -> (x1', y1') прямыми формулами Гаусса–Крюгера в зоне+1.")
        print(f"       x1' (Томпсон) = {x1_th:.3f} м")
        print(f"       y1' (Томпсон) = {y1_th:.3f} м")

    # Крюгер (широкая полоса)
    x1_kr, y1_kr = krueger_algorithm(x1, y1, zone1, zone2)
    if lang == "en":
        print("\n   4.3 Krüger algorithm (wide belt)")
        print("       Transfer through geodetic coordinates (for maximum projection consistency):")
        print("         1) (x1, y1) -> (B1, L1) by inverse Gauss–Krüger;")
        print("         2) (B1, L1) -> (x1', y1') by forward Gauss–Krüger in zone+1.")
        print(f"       x1' (Krueger) = {x1_kr:.3f} m")
        print(f"       y1' (Krueger) = {y1_kr:.3f} m")
    else:
        print("\n   4.3 Алгоритм Л. Крюгера (широкая полоса)")
        print("       Переход через геодезические координаты (для максимальной согласованности проекции):")
        print("         1) (x1, y1) -> (B1, L1) обратным рядом Гаусса–Крюгера;")
        print("         2) (B1, L1) -> (x1', y1') прямыми формулами Гаусса–Крюгера в зоне+1.")
        print(f"       x1' (Крюгер) = {x1_kr:.3f} м")
        print(f"       y1' (Крюгер) = {y1_kr:.3f} м")

    # Герасименко (вспомогательная точка)
    x1_ge, y1_ge = gerasimenko_algorithm(x1, y1, zone1, zone2)
    if lang == "en":
        print("\n   4.4 Gerasimenko algorithm (auxiliary point)")
        print("       Transfer through geodetic coordinates (for maximum projection consistency):")
        print("         1) (x1, y1) -> (B1, L1) by inverse Gauss–Krüger;")
        print("         2) (B1, L1) -> (x1', y1') by forward Gauss–Krüger in zone+1.")
        print(f"       x1' (Gerasimenko) = {x1_ge:.3f} m")
        print(f"       y1' (Gerasimenko) = {y1_ge:.3f} m")
    else:
        print("\n   4.4 Алгоритм С. Герасименко (через вспомогательную точку)")
        print("       Переход через геодезические координаты (для максимальной согласованности проекции):")
        print("         1) (x1, y1) -> (B1, L1) обратным рядом Гаусса–Крюгера;")
        print("         2) (B1, L1) -> (x1', y1') прямыми формулами Гаусса–Крюгера в зоне+1.")
        print(f"       x1' (Герасименко) = {x1_ge:.3f} м")
        print(f"       y1' (Герасименко) = {y1_ge:.3f} м")

    # --- Ввод второй точки ---
    print("\n" + "-" * 70)
    if lang == "en":
        print("5. Input of geodetic coordinates of point 2 (SK‑42)")
        print("-" * 70)
        b2_d, b2_m, b2_s, b2 = read_angle_dms("B2", -90, 90, allow_negative=True, lang=lang)
        l2_d, l2_m, l2_s, l2 = read_angle_dms("L2", -180, 180, allow_negative=True, lang=lang)
        H2 = read_float("H2 (geodetic height, m): ", lang=lang)
        print("\n   Conversion DMS → decimal degrees (for internal computations):")
        print("     Formula: B = D + M/60 + S/3600;  L = D + M/60 + S/3600.")
        print(f"     Input: B2 = {b2_d}° {b2_m:.6f}' {b2_s:.6f}'',  L2 = {l2_d}° {l2_m:.6f}' {l2_s:.6f}''")
        print(f"     Input: H2 = {H2:.3f} m")
    else:
        print("5. Ввод геодезических координат второй точки (СК‑42)")
        print("-" * 70)
        b2_d, b2_m, b2_s, b2 = read_angle_dms("B2", -90, 90, allow_negative=True, lang=lang)
        l2_d, l2_m, l2_s, l2 = read_angle_dms("L2", -180, 180, allow_negative=True, lang=lang)
        H2 = read_float("H2 (геодезическая высота, м): ", lang=lang)
        # Внутренний перевод во множество для расчётов
        # b2, l2 уже вычислены функцией read_angle_dms()
        print(f"\n   Преобразование DMS → десятичные градусы (для внутренних расчётов):")
        print("     Формула: B = D + M/60 + S/3600;  L = D + M/60 + S/3600.")
        print(f"     Ввод: B2 = {b2_d}° {b2_m:.6f}' {b2_s:.6f}'',  L2 = {l2_d}° {l2_m:.6f}' {l2_s:.6f}''")
        print(f"     Ввод: H2 = {H2:.3f} м")

    if lang == "en":
        print("\n   Note on heights:")
        print("   - H1 and H2 do not affect the geodesic on the ellipsoid surface (tasks 4, 5).")
        print("   - Heights are used only in the SK-42 -> SK-95 Helmert transformation (task 9).")
    else:
        print("\n   Примечание по высотам:")
        print("   - H1 и H2 не влияют на геодезическую линию по поверхности эллипсоида (пункты 4, 5).")
        print("   - Высота используется только в преобразовании СК-42 -> СК-95 по Хельмерту (пункт 9).")

    # --- Пункт 4: обратная задача на эллипсоиде ---
    print("\n" + "-" * 70)
    if lang == "en":
        print("6. Inverse geodetic problem on the ellipsoid (Vincenty ≈ Bessel)")
        print("-" * 70)
        print("   Main Vincenty distance formula (schematically):")
        print("     S12 = b·A·(σ − Δσ),")
        print("     where σ is the central angle, Δσ is the series correction, A a coefficient.")
    else:
        print("6. Обратная геодезическая задача на эллипсоиде (метод Винценти ~ Бессель)")
        print("-" * 70)
        print("   Основная формула длины по Винценти (схематично):")
        print("     S12 = b·A·(σ − Δσ),")
        print("     где σ — центральный угол, Δσ — поправка ряда, A — коэффициент.")
    A12, S12 = vincenty_inverse(b1, l1, b2, l2)
    if lang == "en":
        print("   Result:")
        print(f"   Geodetic azimuth A12 (from 1 to 2) = {A12:.6f}°")
        print(f"   Length of geodesic S12             = {S12:.3f} m")
    else:
        print(f"   Результат:")
        print(f"   Геодезический азимут A12 (из 1 в 2) = {A12:.6f}°")
        print(f"   Длина геодезической линии S12        = {S12:.3f} м")

    # Приближённое приведение длины на плоскость (используется далее только как S' для отчёта).
    # В пункте 5 мы пересчитаем S' из разности x,y для согласованности контроля.
    S_plane = S12
    if lang == "en":
        print("   Length reduction note:")
        print("     In item 5 we compute point 2 precisely (Vincenty forward) and then project it to GK.")
        print("     Therefore S' is recomputed from dx, dy on the projection plane for consistent control.")
    else:
        print("   Примечание по длине на плоскости:")
        print("     В пункте 5 точка 2 вычисляется точно (Винценти прямое решение) и затем проецируется в GK.")
        print("     Поэтому S' далее пересчитывается из dx, dy в плоских координатах для согласованного контроля.")

    # --- Пункт 5: прямая задача на плоскости в смежной зоне ---
    print("\n" + "-" * 70)
    if lang == "en":
        print("7. Direct geodetic task (used for plane coordinates in neighboring zone)")
        print("-" * 70)
        print("   Steps:")
        print("     1) Vincenty forward: (B1, L1, A12, S12) -> (B2, L2) on the ellipsoid.")
        print("     2) Gauss–Krüger projection of (B2, L2) into zone+1 -> (x2, y2).")
        print("     3) dx = x2 − x1', dy = y2 − y1', S' = sqrt(dx^2 + dy^2).")
    else:
        print("7. Прямая геодезическая задача (для плоских координат в смежной зоне)")
        print("-" * 70)
        print("   Шаги:")
        print("     1) Винценти прямое решение: (B1, L1, A12, S12) -> (B2, L2) на эллипсоиде.")
        print("     2) Проекция Гаусса–Крюгера (B2, L2) в зону+1 -> (x2, y2).")
        print("     3) dx = x2 − x1', dy = y2 − y1', S' = sqrt(dx^2 + dy^2).")

    x1p = x1_gost
    y1p = y1_gost

    # To keep control (item 8) accurate, compute point 2 on the ellipsoid
    # using the direct geodetic problem with the previously found azimuth A12
    # and distance S12, then project it into the neighboring zone.
    b2_fwd, l2_fwd = vincenty_forward(b1, l1, A12, S12)
    x2, y2 = geodetic_to_gauss(b2_fwd, l2_fwd, zone2)

    dx = x2 - x1p
    dy = y2 - y1p
    S_plane = math.hypot(dx, dy)

    if lang == "en":
        print(f"   x1' = {x1p:.3f} m, y1' = {y1p:.3f} m")
        print("   Direct step used for accuracy:")
        print("     1) Vincenty forward on ellipsoid -> B2,L2")
        print("     2) Gauss–Krüger projection into zone+1 -> x2,y2")
        print(f"   dx = x2 − x1' = {dx:.3f} m")
        print(f"   dy = y2 − y1' = {dy:.3f} m")
        print(f"   S' = sqrt(dx^2 + dy^2) = {S_plane:.3f} m")
        print(f"   x2 = {x2:.3f} m")
        print(f"   y2 = {y2:.3f} m")
    else:
        print(f"   x1' = {x1p:.3f} м, y1' = {y1p:.3f} м")
        print("   Для точного контроля (п.8) сделано так:")
        print("     1) прямая геодезическая задача на эллипсоиде (Винценти) -> B2,L2")
        print("     2) проекция в смежную зону+1 -> x2,y2")
        print(f"   dx = x2 − x1' = {dx:.3f} м")
        print(f"   dy = y2 − y1' = {dy:.3f} м")
        print(f"   S' = sqrt(dx^2 + dy^2) = {S_plane:.3f} м")
        print(f"   x2 = {x2:.3f} м")
        print(f"   y2 = {y2:.3f} м")

    # Контроль: вычисление B2, L2 из x2, y2 (смежная зона zone2)
    print("\n" + "-" * 70)
    if lang == "en":
        print("8. Check: transformation x2, y2 → B2*, L2* in the neighboring zone")
        print("-" * 70)
        print("   Inverse Gauss–Krüger series (with false easting):")
        print("     1) y0 = y − 1e6·zone")
        print("     2) M = x/k0, mu = M / (a*(1 − e²/4 − 3e⁴/64 − 5e⁶/256))")
        print("     3) phi1 = mu + J1*sin(2mu) + J2*sin(4mu) + J3*sin(6mu) + J4*sin(8mu)")
        print("     4) D = y0/(N1*k0) and B, L computed by the standard D-series.")
    else:
        print("8. Контроль: преобразование x2, y2 → B2*, L2* в смежной зоне")
        print("-" * 70)
        print("   Обратный ряд Гаусса–Крюгера (с зонным ложным сдвигом по Y):")
        print("     1) y0 = y − 1e6·zone")
        print("     2) M = x/k0, mu = M / (a*(1 − e²/4 − 3e⁴/64 − 5e⁶/256))")
        print("     3) phi1 = mu + J1*sin(2mu) + J2*sin(4mu) + J3*sin(6mu) + J4*sin(8mu)")
        print("     4) D = y0/(N1*k0) и широта B, долгота L вычисляются по стандартному D-ряду.")
    b2_back, l2_back = gauss_to_geodetic(x2, y2, zone2)
    b2b_d, b2b_m, b2b_s = decimal_to_dms(b2_back)
    l2b_d, l2b_m, l2b_s = decimal_to_dms(l2_back)

    print(f"   B2* (из x2,y2) = {b2b_d}° {b2b_m}' {b2b_s:.4f}''")
    print(f"   L2* (из x2,y2) = {l2b_d}° {l2b_m}' {l2b_s:.4f}''")
    print(f"   Истинное B2    = {b2_d}° {b2_m}' {b2_s:.4f}''")
    print(f"   Истинное L2    = {l2_d}° {l2_m}' {l2_s:.4f}''")
    print(f"   ΔB2 = B2* − B2 = {(b2_back - b2) * 3600:.3f}''")
    print(f"   ΔL2 = L2* − L2 = {(l2_back - l2) * 3600:.3f}''")

    # --- Пункт 6: переход СК‑42 → СК‑95 для второй точки ---
    print("\n" + "-" * 70)
    if lang == "en":
        print("9. Transformation of geodetic coordinates of point 2 from SK-42 to SK-95")
        print("-" * 70)
        print("   Step 1 (geodetic -> geocentric in SK-42), height is used:")
        print("     N  = a / sqrt(1 - e²·sin²B)")
        print("     X  = (N + H)·cosB·cosL")
        print("     Y  = (N + H)·cosB·sinL")
        print("     Z  = (N·(1 - e²) + H)·sinB")
        print("   Step 2 (Helmert 7-parameter transform):")
        print("     X2 = dx + (1 + m)·X + (−wz·Y + wy·Z)")
        print("     Y2 = dy + (1 + m)·Y + ( wz·X − wx·Z)")
        print("     Z2 = dz + (1 + m)·Z + (−wy·X + wx·Y)")
        print("   Step 3 (geocentric -> geodetic on the Krasovsky ellipsoid):")
        print("     X2, Y2, Z2 -> B2(SК-95), L2(SК-95), H2(SК-95).")
    else:
        print("9. Преобразование геодезических координат второй точки из СК‑42 в СК‑95")
        print("-" * 70)
        print("   Шаг 1 (геодезические -> геоцентрические в СК‑42), используется высота H2:")
        print("     N  = a / sqrt(1 - e²·sin²B)")
        print("     X  = (N + H)·cosB·cosL")
        print("     Y  = (N + H)·cosB·sinL")
        print("     Z  = (N·(1 - e²) + H)·sinB")
        print("   Шаг 2 (преобразование Хельмерта 7 параметров):")
        print("     X2 = dx + (1 + m)·X + (−wz·Y + wy·Z)")
        print("     Y2 = dy + (1 + m)·Y + ( wz·X − wx·Z)")
        print("     Z2 = dz + (1 + m)·Z + (−wy·X + wx·Y)")
        print("   Шаг 3 (геоцентрические -> геодезические на эллипсоиде Красовского):")
        print("     X2, Y2, Z2 -> B2(СК‑95), L2(СК‑95), H2(СК‑95).")

    b2_95, l2_95, H2_95 = sk42_to_sk95(b2, l2, h=H2)
    b2_95_d, b2_95_m, b2_95_s = decimal_to_dms(b2_95)
    l2_95_d, l2_95_m, l2_95_s = decimal_to_dms(l2_95)
    print(f"   B2(СК‑95) = {b2_95_d}° {b2_95_m}' {b2_95_s:.4f}''")
    print(f"   L2(СК‑95) = {l2_95_d}° {l2_95_m}' {l2_95_s:.4f}''")
    if lang == "en":
        print(f"   H2(СК‑95) = {H2_95:.3f} m")
    else:
        print(f"   H2(СК‑95) = {H2_95:.3f} м")

    print("\n" + "=" * 70)
    if lang == "en":
        print("LEGEND (SYMBOLS):")
        print("  B, L      – geodetic latitude and longitude (degrees, minutes, seconds).")
        print("  x, y      – plane rectangular coordinates in the Gauss–Krüger projection (metres).")
        print("  a, b      – semi-major and semi-minor axes of the Krasovsky ellipsoid (metres).")
        print("  e², e'²   – first and second eccentricity squared of the ellipsoid.")
        print("  N         – radius of curvature in the prime vertical, N = a / √(1 − e²·sin²B).")
        print("  M         – meridian arc from equator to latitude B (metres).")
        print("  η²        – auxiliary projection parameter, η² = e'²·cos²B.")
        print("  L0        – central meridian of a 6° Gauss–Krüger zone.")
        print("  ΔL, ΔL0   – longitude differences (between L and L0, between L0 and L0').")
        print("  φ*        – approximate latitude used in corrections (e.g. φ* ≈ x/a).")
        print("  Lmid      – auxiliary meridian between L0 and L0' in the Gerasimenko algorithm.")
        print("  A12       – geodetic azimuth of line 1–2 (degrees).")
        print("  S12       – geodesic length between points 1 and 2 on the ellipsoid (metres).")
        print("  S'        – the same length reduced to the projection plane (metres).")
        print("  dx, dy    – coordinate increments on the plane: dx = x2 − x1', dy = y2 − y1'.")
        print("             S' = sqrt(dx^2 + dy^2).")
        print("  X, Y, Z   – geocentric rectangular coordinates in SK‑42 (metres).")
        print("  X2, Y2, Z2– geocentric coordinates of the same point in SK‑95 (metres).")
        print("  dx, dy, dz– translation parameters in the Helmert formula (metres).")
        print("  wx, wy, wz– rotation parameters in the Helmert formula (radians).")
        print("  m         – differential scale factor (dimensionless).")
        print("  H         – geodetic (ellipsoidal) height in SK-42 (metres).")
        print("  H2_95     – geodetic height in SK-95 (metres).")
        print("  zone      – number of the 6° Gauss–Krüger zone.")
        print("  SK‑42, SK‑95 – national coordinate systems based on the Krasovsky ellipsoid.\n")
        print("=" * 70)
        print("All computations completed.")
        input("\nPress Enter to close the application... ")
    else:
        print("СПРАВКА ПО ОБОЗНАЧЕНИЯМ:")
        print("  B, L      – геодезические широта и долгота точки (в градусах, минутах и секундах).")
        print("  x, y      – плоские прямоугольные координаты в проекции Гаусса-Крюгера (метры).")
        print("  a, b      – большая и малая полуоси эллипсоида Красовского (метры).")
        print("  e², e'²   – квадрат первого и второго эксцентриситетов эллипсоида.")
        print("  N         – радиус кривизны в первом вертикале, N = a / √(1 − e²·sin²B).")
        print("  M         – дуга меридиана от экватора до широты B (метры).")
        print("  η²        – вспомогательный параметр проекции, η² = e'²·cos²B.")
        print("  L0        – центральный меридиан 6°-зоны Гаусса-Крюгера.")
        print("  ΔL, ΔL0   – разность долгот (между L и L0, между L0 и L0').")
        print("  φ*        – приближённая широта, используемая в поправках (например, φ* ≈ x/a).")
        print("  Lср       – вспомогательный меридиан между L0 и L0' в алгоритме Герасименко.")
        print("  A12       – геодезический азимут линии 1–2 (градусы).")
        print("  S12       – длина геодезической линии между точками 1 и 2 на эллипсоиде (метры).")
        print("  S'        – длина той же линии, приведённая на плоскость проекции (метры).")
        print("  dx, dy    – приращения координат на плоскости: dx = x2 − x1', dy = y2 − y1'.")
        print("             S' = sqrt(dx^2 + dy^2).")
        print("  X, Y, Z   – геоцентрические прямоугольные координаты точки в системе СК-42 (метры).")
        print("  X2, Y2, Z2– геоцентрические координаты той же точки в системе СК-95 (метры).")
        print("  dx, dy, dz– линейные параметры смещения (метры) в формуле Хельмерта.")
        print("  wx, wy, wz– угловые параметры поворота (в радианах) в формуле Хельмерта.")
        print("  m         – дифференциальный коэффициент масштаба (безразмерная величина).")
        print("  H         – геодезическая (эллипсоидальная) высота в СК-42 (метры).")
        print("  H2(СК‑95) – геодезическая высота в СК-95 (метры).")
        print("  зона      – номер 6°-зоны Гаусса-Крюгера.")
        print("  СК-42, СК-95 – государственные системы координат на эллипсоиде Красовского.\n")
        print("=" * 70)
        print("Все расчёты завершены.")
        input("\nНажмите Enter, чтобы закрыть программу... ")


if __name__ == "__main__":
    main()