# Guía de uso del piloto

## Qué hace hoy el software

La aplicación lee los productos desde la hoja de Drive configurada, permite escoger un SKU base y genera una planilla de Walmart con una fila por cada talla o variante del producto.

Para `Vestuario`, completa automáticamente los SKU, nombre, marca, precio, medidas, peso, país de origen, fabricante, cantidad, unidad, modelo, grupo de variantes y tallas. Conserva las hojas internas, validaciones, encabezados e instrucciones de Walmart.

## Antes de comenzar

- Usa siempre una copia oficial y vigente descargada desde Walmart.
- Guarda la plantilla original sin modificar.
- No subas planillas reales al repositorio de GitHub.
- Durante este piloto la aplicación es local: las planillas generadas en un computador no aparecen en el computador de otro compañero. La vista compartida llegará cuando se despliegue el sistema.

## Preparar L-569-14

1. Inicia la aplicación y abre `http://127.0.0.1:8000`.
2. Busca `L-569-14` y pulsa `Preparar planilla`.
3. Confirma que aparezcan las cinco variantes: XS, S, M, L y XL.
4. Si todavía no hay una plantilla cargada, adjunta la plantilla oficial vigente de `Vestuario`, por ejemplo `RIP-2451.xlsx`.
5. Abre el Colab de EAN. Cambia `number_of_codes` a `5`, ejecútalo y pega los cinco códigos en el mismo orden de las variantes.
6. En WordPress, busca el SKU base. Copia la imagen 1 como principal, la imagen 2 como secundaria y la imagen 3 como secundaria 1.
7. Completa descripción larga, descripción corta, material, características, palabras clave y los dos textos de garantía que corresponden a este producto.
8. Revisa género y color. El color se propone desde la descripción de Drive, por lo que debe confirmarse antes de generar.
9. Pulsa `Generar planilla Walmart` y descarga el resultado.
10. Abre el archivo descargado y revísalo antes de subirlo a Drive.

## Qué no se debe modificar

- No borres ni renombres hojas.
- No cambies las filas 1 a 9 de `Vestuario`; contienen instrucciones y encabezados de Walmart.
- No hagas visible, edites ni elimines `Hidden_clothing_other`.
- No reemplaces la plantilla original por la copia de trabajo.

## Datos que requieren revisión humana

- Los EAN se generan en el Colab aprobado por el equipo. Nunca se inventan ni se reutilizan.
- Las URLs deben venir de las imágenes correctas de WordPress.
- Los textos deben describir el producto concreto. No reutilices una garantía o material de otro producto.
- La primera variante se marca como `Sí` y las demás como `No` en `Variante principal`.

## Cuando aparezca una nueva plantilla de Walmart

Las plantillas pueden variar por categoría. Antes de automatizar una nueva, sube una plantilla vacía oficial y un ejemplo correcto ya completado. El equipo técnico comparará sus campos y agregará una configuración específica para esa categoría.

## Próximas etapas

1. Registrar automáticamente en la hoja de Drive que la planilla está lista.
2. Consultar WordPress para proponer las imágenes del SKU.
3. Guardar el resultado en Google Drive y actualizar estados.
4. Agregar generación asistida de textos con revisión humana.
5. Cargar en los perfiles Abizi, Ofertas y Crazy y registrar errores de Walmart.
