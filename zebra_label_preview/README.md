# Zebra ZT411 Label Preview - 300 DPI

**Módulo Odoo 19.0 para generación y previsualización de etiquetas ZPL optimizadas para impresora Zebra ZT411**

## 📋 Descripción General

Este módulo proporciona:
- ✅ Generación automática de etiquetas ZPL en formato 4x6"
- ✅ Previsualización en tiempo real vía Labelary API
- ✅ Integración con movimientos de inventario (stock.move.line)
- ✅ Captura manual de datos técnicos (calibre, ancho, etc.)
- ✅ Generación de códigos de barras 1D y QR 2D
- ✅ Optimización completa para **300 DPI**

---

## 🎯 Especificaciones Técnicas

| Parámetro | Valor |
|-----------|-------|
| **Impresora** | Zebra ZT411 |
| **Formato** | 4×6 pulgadas |
| **Resolución** | 300 DPI (12 dpmm) |
| **Ancho Lienzo** | 1200 dots |
| **Alto Lienzo** | 1800 dots |
| **Odoo** | 19.0+ |
| **Dependencias** | stock, purchase |

---

## 📦 Estructura del Módulo

```
zebra_label_preview/
├── __init__.py                          # Inicialización
├── __manifest__.py                      # Metadatos del módulo
├── README.md                            # Este archivo
│
├── models/
│   ├── __init__.py
│   └── stock_move_line.py              # Modelo heredado + método acción
│
├── report/
│   └── zebra_label_report.xml          # Template ZPL (QWeb-Text)
│
├── wizard/
│   ├── __init__.py
│   ├── stock_label_preview_wizard.py   # Modelo transient
│   └── stock_label_preview_wizard_view.xml  # Formulario modal
│
├── views/
│   └── stock_move_line_views.xml       # Vistas personalizadas
│
├── security/
│   └── ir.model.access.csv             # Acceso a modelos
│
└── scripts/
    └── validate_zpl_params.py          # Script validación ZPL
```

---

## 🚀 Instalación

### 1. Copiar módulo
```bash
cp -r zebra_label_preview /path/to/odoo/addons/
```

### 2. Instalar en Odoo
```
Menú: Apps
Buscar: "Zebra ZT411"
Botón: Instalar
```

### 3. Validar parámetros (opcional)
```bash
python3 zebra_label_preview/scripts/validate_zpl_params.py \
  zebra_label_preview/report/zebra_label_report.xml
```

---

## 📖 Uso

### Flujo Principal

1. **Recibir mercancía en almacén**
   - Crear picking de entrada
   - Escanear productos

2. **Completar datos técnicos**
   - Calibre (mm)
   - Ancho (mm)
   - Factura proveedor
   - Rollo proveedor
   - Lote proveedor

3. **Generar vista previa**
   - Seleccionar línea de movimiento
   - Botón: "Vista Previa Etiqueta Zebra"

4. **Previsualizar etiqueta**
   - Ventana modal con PNG renderizado
   - Visualizar código ZPL generado

5. **Imprimir etiqueta**
   - Botón: "Imprimir Etiqueta Física"
   - Enviar a impresora Zebra ZT411

### Campos Capturados

| Campo | Descripción | Fuente |
|-------|-------------|--------|
| `x_calibre` | Grosor del material (mm) | Manual |
| `x_ancho` | Ancho del material (mm) | Manual |
| `x_factura_proveedor` | Número de factura | Manual |
| `x_rollo_proveedor` | ID del rollo del proveedor | Manual |
| `x_lote_proveedor` | Lote del proveedor | Manual |
| `x_qr_content` | Contenido QR | Computado |

### Contenido del QR

Estructura: `{Código}|{Lote}|{Cantidad}`

Ejemplo: `ABC001|LOTE-2024-001|500.00`

---

## 🎨 Diseño de Etiqueta

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│            EMPRESA XYZ S.A.S.                        │ (66pt)
│                                                      │
├──────────────────────────────────────────────────────┤
│ Articulo              Entrada de mercancia           │ (33pt)
│ ABC001                WH/IN/12345                    │ (48pt)
├──────────────────────────────────────────────────────┤
│ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ Barcode 1D (100px alto)          │
│                                                      │
│ MATERIAL: ACERO INOXIDABLE                           │ (48pt)
│ Calibre: 2.00mm        Ancho: 100.00mm              │ (36pt)
│                                                      │
│ Cantidad: 500 Kilos                                  │ (42pt)
│ ▄▄▄▄▄▄▄▄▄▄ Barcode (75px alto)                      │
│                                                      │
│ Factura: FAC-001                                     │ (36pt)
│ Recibe: Juan Pérez      ███████ QR ███████           │ (36pt)
│ Fecha: 15/08/2024 02:30 PM                           │ (36pt)
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 🔧 Configuración

### API Labelary

**URL Base (Preconfigured):**
```
http://api.labelary.com/v1/printers/12dpmm/labels/4x6/0/
```

- `12dpmm`: 300 DPI (Zebra ZT411 estándar)
- `4x6`: Formato de etiqueta
- `0`: Índice de impresora

### Parámetros ZPL

Los siguientes parámetros están optimizados para 300 DPI:

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `^PW` | 1200 | Print Width (ancho) |
| `^LL` | 1800 | Label Length (alto) |
| `^CI28` | - | Character Set (UTF-8) |
| `^LR` | - | Left-Right orientation |

---

## 📊 Parámetros ZPL Detallados

### Configuración de Página
```zpl
^XA              ; Inicio de etiqueta
^CI28            ; Set de caracteres UTF-8
^PW1200          ; Ancho: 1200 dots (4" @ 300 DPI)
^LL1800          ; Alto: 1800 dots (6" @ 300 DPI)
^LR              ; Orientación: Left-Right
```

### Elementos de Texto
```zpl
^FO{x},{y}       ; Field Origin - Posición X,Y
^A0N,{h},{w}     ; Font - Altura, Ancho
^FD{text}        ; Field Data - Contenido
^FS              ; Field Separator - Fin de campo
```

### Códigos de Barras
```zpl
^BCN,{h},N,N,N   ; Code128 1D - Altura en dots
^BVR,{h},N,N,N   ; Code128 Vertical - Altura
^BQN,{m},{a}     ; QR 2D - Module size, Aspect ratio
```

---

## 🔍 Validación

### Script de Validación

Verificar que todos los parámetros sean correctos:

```bash
python3 zebra_label_preview/scripts/validate_zpl_params.py \
  zebra_label_preview/report/zebra_label_report.xml
```

**Salida esperada:**
```
✅ ^PW correcto: 1200 dots
✅ ^LL correcto: 1800 dots
✅ Posiciones validadas
✅ Fuentes validadas
✅ Códigos de barras validados
```

### Pruebas Manuales

1. **Validar previsualización**
   - Generar etiqueta de prueba
   - Verificar que no hay pixelación
   - Confirmar legibilidad de todos los elementos

2. **Validar códigos**
   - Escanear barcode 1D con lector físico
   - Escanear QR con teléfono
   - Confirmar datos correctos

3. **Validar impresión**
   - Imprimir etiqueta física
   - Medir posiciones
   - Confirmar que no hay truncamiento

---

## 🎓 Documentación Adicional

En el repositorio encontrará:

| Documento | Contenido |
|-----------|-----------|
| **AJUSTES_300DPI.md** | Guía completa de cambios realizados |
| **TABLA_CONVERSION_DPI.md** | Tablas de referencia rápida de conversión |
| **COMPARACION_ZPL_VISUAL.md** | Visualización de antes/después |
| **RESUMEN_AJUSTES.md** | Overview ejecutivo con checklists |

---

## 🐛 Troubleshooting

### Previsualización no carga

**Problema:** Error conectando con Labelary API

**Solución:**
1. Verificar conexión a internet
2. Confirmar que URL es correcta en `stock_move_line.py`
3. Revisar logs de Odoo

### QR no se escanea

**Problema:** Código QR demasiado pequeño o con errores

**Solución:**
1. Verificar parámetro `^BQN,3,9` en template
2. Confirmar que contenido QR es correcto
3. Probar con lector industrial

### Texto truncado en etiqueta

**Problema:** Algunos campos no se muestran completos

**Solución:**
1. Revisar ancho de bloque (`^FB`)
2. Aumentar tamaño vertical del campo
3. Validar con script `validate_zpl_params.py`

### Barcode no se escanea

**Problema:** Lector no reconoce código de barras

**Solución:**
1. Verificar altura mínima (100 dots para 300 DPI)
2. Confirmar que datos son válidos
3. Probar con código manualmente ingresado

---

## 📋 Checklist Pre-Producción

### Instalación
- [ ] Módulo instalado correctamente
- [ ] Permisos de acceso configurados
- [ ] Dependencias (stock, purchase) instaladas

### Configuración
- [ ] URL Labelary verificada
- [ ] Parámetros ZPL validados
- [ ] Campos customizados creados

### Pruebas
- [ ] Vista previa genera PNG correcto
- [ ] Códigos 1D escaneables
- [ ] QR escaneable
- [ ] Texto legible en física

### Usuarios
- [ ] Personal capacitado
- [ ] Documentación distribuida
- [ ] Procedimiento conocido

---

## 🔐 Seguridad

### Acceso

El módulo utiliza el modelo transient `stock.label.preview.wizard`:
- ✅ Usuarios con permiso "stock.move.line" pueden acceder
- ✅ Datos no se persisten en BD
- ✅ Cada sesión genera wizards únicos

### Datos Sensibles

- ❌ NO se almacenan imágenes de etiquetas
- ❌ NO se guardan códigos ZPL
- ❌ Cada generación es efímera
- ✅ Auditaría: `write_uid`, `write_date`

---

## 📈 Performance

| Operación | Tiempo | Notas |
|-----------|--------|-------|
| Generar ZPL | < 100ms | Desde template QWeb |
| Llamada Labelary | 1-2 seg | Depende latencia red |
| Renderizar modal | < 500ms | Base64 decode + display |
| Imprimir físicamente | 10-15 seg | Depende impresora |

---

## 🔄 Actualización

### Mantener Compatibilidad

Si necesita modificar parámetros:

1. **Factor de escala:** Usar `1.477x` para ir de 203→300 DPI
2. **Validar:** Ejecutar script `validate_zpl_params.py`
3. **Probar:** Generar etiqueta de prueba
4. **Imprimir:** Confirmar en física

### Reversión a 203 DPI

Si necesita volver atrás:
```
- Usar factor: 0.677x
- Cambiar URL Labelary: 8dpmm
- Revertir ^PW a 812, ^LL a 1218
- Validar antes de usar
```

---

## 📞 Soporte

### Errores Comunes

Ver sección **🐛 Troubleshooting** arriba

### Documentación Técnica

- Zebra ZPL Manual: `https://www.zebra.com/en/us/products/printers/industrial.html`
- Labelary API: `http://labelary.com/service.html`
- Odoo 19.0 Docs: `https://www.odoo.com/documentation/19.0`

### Contacto

Para soporte técnico del módulo, contactar al equipo de desarrollo

---

## 📝 Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2024 | Migración a 300 DPI |
| 0.9 | 2024 | Versión inicial (203 DPI) |

---

## 📄 Licencia

LGPL-3

---

## 👥 Contribuyentes

- Odoo Consultant
- Team de Desarrollo

---

## 🎉 Características Principales

✨ **Razones para usar este módulo:**

1. **300 DPI Optimizado**
   - Máxima claridad y definición
   - Compatible con Zebra ZT411
   - Etiquetas profesionales

2. **QR Integrado**
   - Datos: Código | Lote | Cantidad
   - Fácil rastreo de inventario
   - Integración con móviles

3. **Previsualización**
   - Ver exactamente cómo se verá
   - Ajustar antes de imprimir
   - Ahorrar etiquetas

4. **Automático**
   - Campos editables en recepción
   - Generación instantánea
   - Sin entrada manual adicional

5. **Integrado**
   - Con stock.move.line
   - Con picking y compras
   - Con usuarios y auditoría

---

**Versión Actual:** 1.0 (300 DPI)  
**Estado:** ✅ Producción  
**Última Actualización:** 2024
