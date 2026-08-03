#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de validación de parámetros ZPL para Zebra ZT411 - 300 DPI

Verifica que todos los parámetros del módulo sean consistentes con:
- Resolución: 300 DPI
- Formato: 4x6 pulgadas
- Impresora: Zebra ZT411
"""

import re
import sys

# Constantes de validación
DPI = 300
WIDTH_INCHES = 4
HEIGHT_INCHES = 6
DPI_EXPECTED = 12  # dpmm en Labelary (12dpmm ≈ 300 DPI)
WIDTH_DOTS = 1200   # 4" × 300 DPI
HEIGHT_DOTS = 1800  # 6" × 300 DPI
SCALE_FACTOR = WIDTH_DOTS / 812  # Factor de escala desde 203 DPI

# Márgenes permitidos (en dots)
MARGIN_MIN = 40
MARGIN_MAX = 150

# Rangos válidos
FONT_HEIGHT_RANGES = {
    'titulo': (50, 80),        # Header/Título principal
    'grande': (40, 65),        # Campos importantes
    'media': (30, 45),         # Campos normales
    'pequeña': (20, 35),       # Campos secundarios
}

BARCODE_HEIGHT_RANGES = {
    '1d_grande': (90, 120),    # Código de barras principal
    '1d_media': (60, 90),      # Código de barras secundario
    '2d': (3, 10),             # Magnitud de QR
}


def validate_url(url):
    """Valida que la URL de Labelary sea correcta"""
    print("\n[URL LABELARY]")
    
    expected_url = f'http://api.labelary.com/v1/printers/{DPI_EXPECTED}dpmm/labels/4x6/0/'
    
    if url == expected_url:
        print(f"✅ URL correcta: {url}")
        return True
    else:
        print(f"❌ URL incorrecta")
        print(f"   Esperada: {expected_url}")
        print(f"   Encontrada: {url}")
        return False


def validate_zpl_dimensions(pw, ll):
    """Valida que las dimensiones ZPL sean correctas"""
    print("\n[DIMENSIONES ZPL]")
    
    errors = []
    
    if pw != WIDTH_DOTS:
        errors.append(f"^PW incorrecto: {pw} (esperado {WIDTH_DOTS})")
    else:
        print(f"✅ ^PW correcto: {pw} dots (4 pulgadas × 300 DPI)")
    
    if ll != HEIGHT_DOTS:
        errors.append(f"^LL incorrecto: {ll} (esperado {HEIGHT_DOTS})")
    else:
        print(f"✅ ^LL correcto: {ll} dots (6 pulgadas × 300 DPI)")
    
    if errors:
        for error in errors:
            print(f"❌ {error}")
        return False
    return True


def validate_field_position(name, x, y, x_expected_range=None, y_expected_range=None):
    """Valida que una posición de campo esté dentro de rangos válidos"""
    errors = []
    
    # Verificar márgenes mínimos
    if x < MARGIN_MIN:
        errors.append(f"X={x} muy cerca del borde izquierdo (min {MARGIN_MIN})")
    if y < MARGIN_MIN:
        errors.append(f"Y={y} muy cerca del borde superior (min {MARGIN_MIN})")
    
    # Verificar límites máximos
    if x > WIDTH_DOTS - MARGIN_MIN:
        errors.append(f"X={x} muy cerca del borde derecho (max {WIDTH_DOTS - MARGIN_MIN})")
    if y > HEIGHT_DOTS - MARGIN_MIN:
        errors.append(f"Y={y} muy cerca del borde inferior (max {HEIGHT_DOTS - MARGIN_MIN})")
    
    # Verificar rangos específicos si se proporcionan
    if x_expected_range and (x < x_expected_range[0] or x > x_expected_range[1]):
        errors.append(f"X={x} fuera del rango esperado {x_expected_range}")
    if y_expected_range and (y < y_expected_range[0] or y > y_expected_range[1]):
        errors.append(f"Y={y} fuera del rango esperado {y_expected_range}")
    
    if errors:
        print(f"❌ {name}: ({x},{y})")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print(f"✅ {name}: ({x},{y})")
        return True


def validate_font_size(name, height, category='media'):
    """Valida que un tamaño de fuente sea razonable"""
    valid_range = FONT_HEIGHT_RANGES.get(category, (20, 80))
    
    if height < valid_range[0] or height > valid_range[1]:
        print(f"❌ {name}: {height}pt fuera de rango {valid_range}")
        return False
    else:
        print(f"✅ {name}: {height}pt")
        return True


def validate_barcode_height(name, height, barcode_type='1d_media'):
    """Valida que la altura de un código de barras sea válida"""
    valid_range = BARCODE_HEIGHT_RANGES.get(barcode_type, (20, 120))
    
    if height < valid_range[0] or height > valid_range[1]:
        print(f"❌ {name}: {height} fuera de rango {valid_range}")
        return False
    else:
        print(f"✅ {name}: {height}")
        return True


def validate_zpl_file(filepath):
    """Valida el archivo ZPL completo"""
    print("\n" + "=" * 60)
    print("VALIDACIÓN ZPL - ZEBRA ZT411 (300 DPI, 4x6\")")
    print("=" * 60)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {filepath}")
        return False
    
    all_valid = True
    
    # Extraer valores
    pw_match = re.search(r'\^PW(\d+)', content)
    ll_match = re.search(r'\^LL(\d+)', content)
    url_match = re.search(r'http://api\.labelary\.com/v1/printers/(\d+)dpmm', content)
    
    # Validar URL
    if url_match:
        dpmm = int(url_match.group(1))
        if dpmm == DPI_EXPECTED:
            print(f"✅ DPI Labelary correcto: {dpmm}dpmm (≈ 300 DPI)")
        else:
            print(f"❌ DPI Labelary incorrecto: {dpmm}dpmm (esperado {DPI_EXPECTED}dpmm)")
            all_valid = False
    
    # Validar dimensiones ZPL
    if pw_match and ll_match:
        pw = int(pw_match.group(1))
        ll = int(ll_match.group(1))
        if not validate_zpl_dimensions(pw, ll):
            all_valid = False
    
    # Extraer y validar campos de posición
    print("\n[POSICIONES DE CAMPOS (FO = Field Origin)]")
    fo_matches = re.findall(r'\^FO(\d+),(\d+)', content)
    
    field_count = 0
    for x, y in fo_matches[:15]:  # Validar primeros 15 campos
        x, y = int(x), int(y)
        field_count += 1
        
        # Validación básica de márgenes
        if x < MARGIN_MIN or y < MARGIN_MIN:
            print(f"⚠️  Campo {field_count}: ({x},{y}) - Muy cerca del borde")
        else:
            print(f"✅ Campo {field_count}: ({x},{y})")
    
    # Validar tamaños de fuente
    print("\n[TAMAÑOS DE FUENTE]")
    a0_matches = re.findall(r'\^A0N,(\d+),\d+', content)
    expected_sizes = [66, 33, 33, 54, 48, 48, 42, 33, 36, 36, 36, 36, 36, 30]
    
    for i, size in enumerate(a0_matches[:14]):
        size = int(size)
        if i < len(expected_sizes):
            if size == expected_sizes[i]:
                print(f"✅ Fuente {i+1}: {size}pt (esperado)")
            else:
                print(f"⚠️  Fuente {i+1}: {size}pt (esperado {expected_sizes[i]}pt)")
                all_valid = False
    
    # Validar alturas de códigos de barras
    print("\n[CÓDIGOS DE BARRAS]")
    bc_matches = re.findall(r'\^BCN,(\d+),', content)
    bq_matches = re.findall(r'\^BQN,(\d+),(\d+)', content)
    
    if bc_matches:
        print(f"✅ Códigos 1D encontrados: {len(bc_matches)}")
        for i, height in enumerate(bc_matches):
            height = int(height)
            if validate_barcode_height(f"BC{i+1}", height, '1d_grande' if height > 80 else '1d_media'):
                pass
            else:
                all_valid = False
    
    if bq_matches:
        print(f"✅ Códigos QR encontrados: {len(bq_matches)}")
        for i, (mod_size, aspect) in enumerate(bq_matches):
            mod_size, aspect = int(mod_size), int(aspect)
            print(f"   QR{i+1}: módulo={mod_size}, aspecto={aspect}")
    
    # Resumen
    print("\n" + "=" * 60)
    if all_valid:
        print("✅ VALIDACIÓN EXITOSA - Todos los parámetros son correctos")
    else:
        print("⚠️  VALIDACIÓN CON ADVERTENCIAS - Revisar los errores arriba")
    print("=" * 60)
    
    return all_valid


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # Ruta por defecto
        filepath = 'report/zebra_label_report.xml'
    
    validate_zpl_file(filepath)
