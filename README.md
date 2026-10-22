# Automatización de planillas Walmart

Aplicación web interna para preparar, validar y organizar planillas de productos antes de cargarlas en Walmart.

## Objetivo de la primera versión

La primera versión no utiliza IA ni realiza cargas a Walmart. Permitirá al equipo:

- Crear campañas por marca y descuento.
- Cargar la planilla fuente y la plantilla oficial de Walmart.
- Mantener un registro centralizado de los archivos y sus estados.
- Dejar la base lista para implementar la generación de planillas, Google Drive, WordPress y, posteriormente, IA.

## Tecnología

- **Backend y web:** Python + FastAPI.
- **Datos de desarrollo:** SQLite.
- **Planillas:** OpenPyXL.
- **Despliegue futuro:** Docker + Google Cloud Run.

## Ejecutar localmente

Requiere Python 3.12 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Luego abre `http://127.0.0.1:8000`.

## Pruebas

```powershell
pytest
```

## Seguridad

- No subir contraseñas, claves de API, archivos de cuentas de servicio ni planillas reales con información sensible.
- Usar `.env` solamente en desarrollo.
- Cuando se publique, las credenciales se guardarán en Google Secret Manager.

## Próximos pasos

1. Definir el mapeo exacto para la primera marca piloto.
2. Implementar generación y validación de la plantilla Walmart.
3. Conectar Drive y el estado de las campañas.
4. Incorporar WordPress e IA como integraciones opcionales.
