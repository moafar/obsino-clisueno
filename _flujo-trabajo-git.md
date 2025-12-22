# Flujo de trabajo con ramas en Git

Guía resumida para trabajar con ramas y mantener sincronizado tu repositorio local y remoto.

---

## 🧩 1. Crear y trabajar en una nueva rama
```bash
git checkout -b nombre_rama
# (editar, agregar archivos, commits, etc.)
git add .
git commit -m "Descripción del cambio"
```

## 🔄 2. Mantenerla actualizada con `main`
Antes de subir tu trabajo, sincroniza con la rama principal:
```bash
git fetch origin
git merge origin/main
# o si prefieres un historial lineal:
# git rebase origin/main
```

## ☁️ 3. Subir la rama al remoto
```bash
git push -u origin nombre_rama
```

## 🔀 4. Crear el Pull Request
1. En GitHub, haz clic en **"Compare & pull request"**
2. Base: `main` ← Compare: `nombre_rama`
3. Revisa y crea el PR.

## ✅ 5. Hacer el merge en GitHub
1. Clic en **"Merge pull request"**
2. Confirmar (**"Confirm merge"**)  
   - GitHub mostrará el estado como **"Merged"** cuando se complete.

## 🔽 6. Actualizar tu `main` local
```bash
git checkout main
git pull origin main
```

## 🧹 7. Limpiar ramas
```bash
git branch -d nombre_rama
git push origin --delete nombre_rama
```

---

# Checklist de publicación de versiones (Extractor PSG)

## En local (desarrollo)

- [ ] Ejecutar `git status`  
  Confirmar que el working tree está **clean**.

- [ ] Ejecutar `git push origin main`  
  **Solo si** hay commits nuevos desde la última versión.

- [ ] Crear el tag de versión  
  ```bash
  git tag vX.Y.Z
  ```

- [ ] Subir el tag al remoto  
  ```bash
  git push origin vX.Y.Z
  ```

---

## En el servidor (ejecución)

- [ ] Traer los tags del remoto  
  ```bash
  git fetch --tags
  ```

- [ ] Cambiar a la versión deseada  
  ```bash
  git checkout vX.Y.Z
  ```

- [ ] Verificar la versión activa  
  ```bash
  git describe --tags
  ```

---

## Reglas de oro

- [ ] El servidor **nunca** ejecuta desde `main`.
- [ ] El servidor **nunca** recibe commits.
- [ ] Cada ejecución productiva se hace desde un **tag**.
- [ ] Rollback inmediato:  
  ```bash
  git checkout vVERSIÓN_ANTERIOR
  ```
