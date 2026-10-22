# Automatización de planillas Walmart

Aplicación web interna para preparar, validar y organizar planillas de productos antes de cargarlas en Walmart.

## Estado actual

La aplicación empieza desde la hoja compartida de productos de Drive. Cada integrante elige un SKU ML sin asignar; el sistema identifica su SKU Base y genera una planilla con una fila por cada SKU ML del grupo.

Para la categoría `Vestuario`, la aplicación completa automáticamente desde Drive los SKU, nombre, marca, precio, dimensiones, peso, tallas, modelo e identificadores de variantes. Conserva las hojas, encabezados, validaciones y formato de la plantilla oficial de Walmart.

Los EAN, URLs de WordPress y textos específicos del producto siguen siendo revisados e ingresados por la persona responsable. La aplicación no inventa esos datos ni permite crear una planilla final si faltan.

## Ejecutar localmente

Requiere Python 3.12 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Abre `http://127.0.0.1:8000` en el navegador.

## Prueba con L-569-14

1. Abre la página inicial y busca `L-RIP-569-14-XS`.
2. Pulsa **Crear planilla**. El sistema reunirá los cinco SKU ML del SKU Base `L-569-14`.
3. Si todavía no está configurada, un administrador carga una copia vigente de la plantilla oficial de Walmart para `Vestuario`, por ejemplo `RIP-2451.xlsx`. Esto se hace una vez y se reutiliza para todos los productos.
4. En el Colab de EAN, configura `number_of_codes` con `5` y pega los cinco códigos resultantes, uno por línea.
5. Copia desde WordPress las tres URLs de imágenes y completa los textos específicos del producto.
6. Revisa los datos obtenidos de Drive y pulsa **Generar planilla Walmart**.
7. Descarga el resultado y revísalo antes de subirlo a Drive.

La configuración de la hoja fuente puede cambiarse con `SOURCE_SHEET_CSV_URL` y `SOURCE_SHEET_WEB_URL` en `.env`.

Lee la guía completa en [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## Pruebas

```powershell
pytest
```

## Colaboración

Antes de modificar el proyecto, lee [CONTRIBUTING.md](CONTRIBUTING.md) y la configuración recomendada de GitHub en [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md).

## Seguridad

- No subir contraseñas, claves de API, archivos de cuentas de servicio ni planillas reales con información sensible.
- Usar `.env` solamente en desarrollo.
- No publicar planillas de productos en GitHub: los archivos cargados y generados se excluyen mediante `.gitignore`.
- Cuando se publique la aplicación, las credenciales se guardarán en Google Secret Manager.
