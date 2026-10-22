# Arquitectura

## Primera versión

La aplicación registra campañas y recibe dos documentos por campaña:

1. Planilla fuente de productos y precios.
2. Plantilla oficial de Walmart.

La base de datos SQLite y los archivos locales se usan solo durante el desarrollo. No se debe publicar esta configuración tal cual para el equipo remoto.

## Producción

| Componente | Servicio propuesto | Propósito |
| --- | --- | --- |
| Aplicación | Google Cloud Run | Ejecutar la aplicación web sin administrar servidores. |
| Identidad | Firebase Authentication | Permitir acceso con cuentas Google personales autorizadas. |
| Estado | Firestore | Guardar campañas, trabajos y estados de carga. |
| Archivos | Google Drive | Mantener fuentes, plantillas y resultados. |
| Secretos | Google Secret Manager | Proteger claves de integraciones. |

## Principios de seguridad

- El repositorio es privado y no almacena datos de producción.
- Las claves solo existirán como secretos de la nube.
- La aplicación usará una lista administrable de correos autorizados.
- La generación de archivos conservará la plantilla original y creará un resultado nuevo; nunca sobrescribirá el archivo fuente.

## Fases

1. Fundaciones: campañas, archivos, configuración por marca y pruebas.
2. Generador Excel: mapeo, validaciones y archivo Walmart final.
3. Drive y WordPress: lectura/escritura autorizada y URLs de imágenes.
4. IA opcional: generación revisable de textos por producto.
5. Walmart: envío por perfil y recuperación de errores.
