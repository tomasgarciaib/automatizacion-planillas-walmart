# Configuración de GitHub para el equipo

## 1. Mantener el repositorio privado

El código puede ser compartido, pero las planillas, datos de productos y credenciales no deben ser públicos. Confirma en `Settings > General > Danger Zone` que la visibilidad permanezca en `Private`.

## 2. Invitar a los compañeros

Como el repositorio pertenece a una cuenta personal, los colaboradores tienen acceso de escritura una vez que aceptan la invitación. Pide primero el usuario de GitHub de cada persona y luego entra a `Settings > Collaborators > Add people`.

Invita solo a quienes participen de la práctica. Cuando alguien deje el proyecto, elimínalo desde la misma pantalla.

## 3. Flujo obligatorio del equipo

Hasta que se pueda activar protección técnica para `main`, el equipo debe seguir este acuerdo:

1. No hacer `git push origin main`.
2. Crear una rama por cambio.
3. Abrir un pull request hacia `main`.
4. Esperar la revisión de otra persona antes de combinarlo.
5. Comprobar que el flujo `Pruebas` esté correcto.

Las instrucciones y prefijos de ramas están en [CONTRIBUTING.md](../CONTRIBUTING.md).

## 4. Protección técnica de `main`

GitHub limita las reglas de protección y CODEOWNERS en repositorios privados de cuentas gratuitas. Los colaboradores de una cuenta personal también tienen el mismo nivel de escritura; no existen roles finos por persona. Por eso, si en tu repositorio no aparece `Rules` o `Branches > Add branch protection rule`, no es un error de configuración.

Si más adelante cuentan con GitHub Pro, Team o Enterprise, crea una regla para la rama `main` con estas opciones:

- Requerir pull request antes de combinar.
- Requerir 1 aprobación.
- Descartar aprobaciones antiguas cuando haya nuevos commits.
- Requerir que pasen los checks de estado. Selecciona el check `Pruebas / test` después de que haya corrido al menos una vez.
- Requerir resolver conversaciones.
- Bloquear force pushes y borrado de la rama.
- Requerir revisión de CODEOWNERS si esa opción está disponible.

El archivo `.github/CODEOWNERS` ya designa al responsable inicial. GitHub solo puede exigir esa revisión cuando la función esté disponible en el plan y se active en la regla.

## 5. Cuándo considerar una organización

Si el proyecto continúa después de la práctica o necesita más de una persona administradora, transfieran el repositorio a una organización de la empresa. Una organización facilita usar equipos, separar responsables y conservar el proyecto aunque una persona deje de participar. No transfieran el repositorio sin acordarlo con el jefe y sin verificar que los permisos y el plan contratado permitan las reglas necesarias.

## Fuentes oficiales

- [Invitar colaboradores a un repositorio personal](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)
- [Permisos de repositorios personales](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)
- [Reglas de protección de ramas](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
- [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
