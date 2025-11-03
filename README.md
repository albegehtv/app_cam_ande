# Guía para resolver el error 403 al hacer push

La captura `image.png` corresponde a un intento de subir cambios a un repositorio
privado de Azure DevOps que devuelve **Error 403**. Este código indica que el
servidor rechazó la autenticación o que la cuenta utilizada no tiene permisos
para escribir en el proyecto. A continuación se describen los pasos más
habituales para solucionarlo.

## 1. Verificar la URL del remoto

```bash
git remote -v
```

- Asegúrate de que la URL apunte a `https://dev.azure.com/<organización>/<proyecto>/_git/<repo>`.
- Si la URL muestra el protocolo `ssh://` y no tienes las llaves registradas en Azure DevOps, cambia a HTTPS:

```bash
git remote set-url origin https://dev.azure.com/<organización>/<proyecto>/_git/<repo>
```

## 2. Regenerar un PAT y usarlo como contraseña

Azure DevOps deja de aceptar contraseñas de cuenta y requiere un **Personal
Access Token (PAT)**.

1. Ingresa a `https://dev.azure.com/` y abre **User settings → Personal Access Tokens**.
2. Crea un PAT con los scopes `Code (Read & Write)` y anota el token porque solo se muestra una vez.
3. Ejecuta un push; cuando Git pida credenciales, usa tu correo como usuario y el PAT como contraseña.

Si ya se guardaron credenciales incorrectas, elimínalas:

```bash
# En Windows
git credential-manager reject https://dev.azure.com
# En macOS
printf 'protocol=https\nhost=dev.azure.com\n\n' | git credential-osxkeychain erase
# En Linux
printf 'protocol=https\nhost=dev.azure.com\n\n' | git credential-cache exit
```

## 3. Confirmar permisos en el proyecto

- Pide al administrador que verifique que tu usuario pertenece al grupo **Contributors** del proyecto.
- Si utilizas una cuenta de servicio, comprueba que no haya caducado o que no esté bloqueada por políticas de la organización.

## 4. Validar desde la línea de comandos

Después de aplicar los pasos anteriores ejecuta:

```bash
git ls-remote origin
```

Si el comando lista las ramas remotas sin error, vuelve a intentar el push.

```bash
git push origin <tu-rama>
```

## 5. Mensajes comunes relacionados

- `fatal: Authentication failed`: credenciales incorrectas o PAT expirado.
- `remote: TF401019: The Git repository ... does not exist`: la URL del remoto es incorrecta.
- `remote: You do not have permission to create a pull request`: el usuario no tiene permisos suficientes.

Siguiendo estos pasos podrás resolver la causa del error 403 mostrado en la captura y completar el envío de tus cambios.
