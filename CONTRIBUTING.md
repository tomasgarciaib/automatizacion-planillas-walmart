# Cómo colaborar

Este repositorio contiene código de una herramienta interna. El objetivo es que cada cambio sea pequeño, revisable y fácil de revertir.

## Regla principal

No se trabaja directamente en `main`. Cada cambio se hace en una rama y entra mediante un pull request.

## Crear una rama

Actualiza tu copia antes de comenzar y usa uno de estos prefijos:

```powershell
git switch main
git pull
git switch -c feat/nombre-corto
```

- `feat/`: nueva función.
- `fix/`: corrección de un error.
- `docs/`: documentación.
- `chore/`: mantenimiento sin cambios funcionales.

Ejemplo: `feat/validar-precio-walmart`.

## Antes de abrir un pull request

1. Ejecuta `pytest`.
2. Revisa `git status` y confirma que no haya planillas, secretos ni archivos personales.
3. Escribe un commit breve y descriptivo, por ejemplo: `feat: validar campos obligatorios`.
4. Sube tu rama con `git push -u origin nombre-de-tu-rama`.
5. Abre un pull request hacia `main` y completa la plantilla.

## Revisión

- No apruebes ni combines tu propio pull request.
- Quien revise debe comprobar que las pruebas estén en verde y que el cambio responda al objetivo descrito.
- Si se modifica el procesamiento de una planilla Walmart, se debe probar con una copia y nunca con el único archivo original.

## Qué no se sube a GitHub

- Planillas de productos reales o archivos descargados de Walmart.
- Contraseñas, tokens, claves de API o archivos `.env`.
- Credenciales de Google, WordPress o Walmart.
- Archivos de las carpetas `data/`, `uploads/` y `outputs/`.

## Responsable inicial

El archivo `.github/CODEOWNERS` asigna temporalmente la revisión a `@tomasgarciaib`. Cuando el equipo defina otro responsable técnico, agreguen su usuario de GitHub allí mediante un pull request.
