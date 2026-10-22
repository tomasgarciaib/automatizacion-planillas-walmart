# Guía de uso del piloto

## Qué hace hoy el software

La aplicación organiza una campaña y permite preparar una plantilla limpia de Walmart. Esta es la primera etapa antes de automatizar el llenado con la planilla fuente, las imágenes y Google Drive.

La copia limpia conserva el archivo oficial, sus hojas internas, validaciones, encabezados e instrucciones. Solo borra los datos de producto de la hoja `Vestuario` desde la fila 10.

## Antes de comenzar

- Usa siempre una copia oficial y vigente descargada desde Walmart.
- Guarda la plantilla original sin modificar.
- No subas planillas reales al repositorio de GitHub.
- Durante este piloto la aplicación es local: las campañas de un computador no aparecen en el computador de otro compañero. La vista compartida llegará cuando se despliegue el sistema y se conecte a Drive.

## Crear una plantilla limpia con RIP-2451

1. Inicia la aplicación y abre `http://127.0.0.1:8000`.
2. Pulsa `Nueva campaña` e ingresa un nombre claro, por ejemplo `Ripholia 15% - prueba`.
3. Indica la marca y el descuento.
4. En `Archivos de trabajo`, selecciona `Plantilla Walmart`.
5. Adjunta `RIP-2451.xlsx` y pulsa `Adjuntar archivo`.
6. Cuando aparezca en la lista, pulsa `Crear plantilla limpia`.
7. Descarga el documento de tipo `Plantilla limpia`.
8. Abre solo la copia descargada y verifica que la hoja `Vestuario` conserve los encabezados y que las filas de producto estén vacías.

## Qué no se debe modificar

- No borres ni renombres hojas.
- No cambies las filas 1 a 9 de `Vestuario`; contienen instrucciones y encabezados de Walmart.
- No hagas visible, edites ni elimines `Hidden_clothing_other`.
- No reemplaces la plantilla original por la copia de trabajo.

## Cuando aparezca una nueva plantilla de Walmart

Las plantillas pueden variar por categoría. Antes de automatizar una nueva, sube una plantilla vacía oficial y un ejemplo correcto ya completado. El equipo técnico comparará sus campos y agregará una configuración específica para esa categoría.

## Próximas etapas

1. Leer datos desde una planilla fuente por marca y descuento.
2. Validar SKU, medidas, precios y campos obligatorios.
3. Crear la planilla final con los datos del producto.
4. Guardar el resultado en Google Drive y actualizar estados.
5. Agregar WordPress, generación asistida de textos y carga en Walmart.
