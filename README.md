# Automatización de planillas Walmart

Aplicación web interna para preparar, validar y organizar planillas de productos antes de cargarlas en Walmart.

## Estado actual

La primera función disponible permite adjuntar una plantilla oficial de Walmart y crear una copia limpia para comenzar una carga nueva. La copia conserva la estructura técnica del archivo y elimina únicamente los datos de productos desde la fila 10 de la hoja `Vestuario`.

Esta versión todavía no usa IA, no completa productos desde la planilla fuente, no se conecta con Google Drive, WordPress ni carga archivos en Walmart. Es una base de trabajo local para validar el flujo con el equipo.

## Ejecutar localmente

Requiere Python 3.12 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Abre `http://127.0.0.1:8000` en el navegador.

## Prueba con RIP-2451

1. Crea una campaña de prueba.
2. Adjunta `RIP-2451.xlsx` como **Plantilla Walmart**.
3. Pulsa **Crear plantilla limpia**.
4. Descarga el archivo generado desde la lista de documentos.
5. Completa la copia descargada. No modifiques las filas de instrucciones ni la hoja técnica oculta.

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
