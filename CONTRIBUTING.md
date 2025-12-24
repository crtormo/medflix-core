# Contribuir a MedFlix Core

¡Gracias por tu interés en contribuir a MedFlix Core! 🎉

Este documento proporciona pautas y pasos para contribuir al proyecto. Siguiéndolas, ayudarás a mantener el código limpio, funcional y fácil de mantener.

## ¿Cómo puedo contribuir?

### 1. Reportar Bugs
Si encuentras un error, por favor crea un *Issue* en GitHub incluyendo:
- Pasos para reproducir el error.
- Comportamiento esperado vs real.
- Screenshots o logs si es posible.

### 2. Sugerir Mejoras
¿Tienes una idea para una nueva funcionalidad? Abre un *Issue* con la etiqueta `enhancement` y describe tu propuesta detalladamente.

### 3. Pull Requests (PRs)
1. **Fork** el repositorio.
2. Crea una **rama** para tu feature o fix (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza tus **cambios** siguiendo el estilo de código existente.
4. **Prueba** tus cambios localmente.
5. Haz **commit** de tus cambios (`git commit -m 'feat: añade nueva funcionalidad'`).
6. Haz **push** a tu rama (`git push origin feature/nueva-funcionalidad`).
7. Abre un **Pull Request** hacia la rama `master` del repositorio original.

## Estilo de Código

- Seguimos **PEP 8** para Python.
- Usa **Type Hints** en las funciones siempre que sea posible.
- Documenta las funciones y clases con **Docstrings**.

## Configuración de Desarrollo

Asegúrate de tener un entorno virtual configurado y todas las dependencias instaladas:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

¡Esperamos tus contribuciones! 🚀
