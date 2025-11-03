# Sistema de gestión de detección de vehículos

Esta aplicación ofrece un flujo completo para vigilar una cámara, identificar vehículos o personas de interés y accionar alarmas sonoras, visuales y un relay programable cuando se produce una coincidencia.

## Características principales

- **Panel web** para registrar vehículos/personas con fotografía de referencia y metadatos.
- **Motor de detección** basado en [YOLOv8](https://github.com/ultralytics/ultralytics) (o un modo degradado sin IA si el modelo no está disponible).
- **Comparación por características**: se calculan histogramas de color, color dominante y densidad de bordes para mejorar la coincidencia frente a la lista de vigilancia.
- **Registro de eventos** en base de datos SQLite con historial accesible desde el panel.
- **Alarmas** sonoras, visuales y activación opcional de un relay para detener maquinaria.

## Requisitos

1. Python 3.11+
2. Dependencias (ver `pyproject.toml` o instale directamente):
   ```bash
   pip install -r requirements.txt
   ```
3. Modelo YOLO compatible (`yolov8n.pt` por defecto). Puede descargarse automáticamente con `pip install ultralytics`.
4. Para alarmas físicas:
   - Archivo WAV si desea sonido.
   - Librería `gpiozero` (opcional) y acceso a los pines GPIO donde se conecte el relay.

## Configuración rápida

1. **Instale dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Inicie la API y panel web**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. Acceda a `http://localhost:8000/panel` para cargar fotos de referencia y consultar eventos.

## Ejecución del motor de detección

En otra terminal ejecute:

```bash
python -m app.detector_runner --source 0 --model yolov8n.pt
```

- Cambie `--source` por la ruta RTSP o archivo de vídeo según corresponda.
- Use `--sound /ruta/a/alarma.wav` si desea un tono personalizado.
- Ajuste `--frame-skip` para equilibrar rendimiento y precisión.

Cuando el motor detecta una coincidencia:

1. Guarda la captura en la carpeta `detections/`.
2. Registra un evento en la base de datos.
3. Dispara la alarma sonora y visual.
4. Activa el relay durante los segundos configurados (`settings.alarm.relay_active_seconds`).

## Estructura del proyecto

```
app/
├── api/            # Endpoints REST
├── services/       # Lógica de negocio: detección, alarmas, eventos
├── web/            # Panel web con Jinja2 y recursos estáticos
├── detector_runner.py  # Script CLI para monitorear la cámara
├── main.py         # Aplicación FastAPI
└── ...
```

Los ajustes básicos se encuentran en `app/config.py`. Se pueden sobreescribir mediante variables de entorno:

- `APP_WATCHLIST_DIR`
- `APP_DETECTIONS_DIR`
- `APP_STATE_DIR`

## Nota sobre el modo degradado

Si `ultralytics` no está disponible o no puede cargarse el modelo YOLO, el sistema seguirá funcionando en modo degradado: se analizará una región central del cuadro y se comparará contra la lista de vigilancia utilizando únicamente las características visuales básicas. Este modo está pensado para facilitar pruebas sin aceleración de IA.

## Seguridad y despliegue

- Coloque el servicio detrás de HTTPS y gestione autenticación según su entorno (no implementado por simplicidad).
- Configure copias de seguridad de la base de datos `app.db`.
- Ajuste permisos de escritura de las carpetas `watchlist/` y `detections/` según corresponda.

## Pruebas básicas

Con dependencias instaladas, puede ejecutar una verificación rápida de importaciones:

```bash
python -m compileall app
```

Esto garantiza que los módulos no tienen errores de sintaxis.

---

> **Importante:** Para evitar errores de binarios incompatibles, todas las dependencias se gestionan vía `pip` y no se incluyen archivos compilados en el repositorio.
