# Integración de la colección Weather Forecast

Se integran las peticiones de Azure Maps Weather **CurrentConditions** y **AirQuality** como dos dispositivos API externos: API-WEATHER y API-AIR. No se incluyen las peticiones de vehículos ni tráfico, ajenas al escenario. La petición Forecast5mins de la colección no tiene URL; no permite reproducir una consulta de pronóstico. Las proyecciones de humedad del asistente son extrapolaciones locales y no un pronóstico meteorológico de Azure.

## Configurar desde Visual Studio Code

En la ventana SSH del servidor, Ctrl+P → `/home/nicolas/invernadero-iot/invernadero-iot/.env` → Enter. Añadir y guardar con Ctrl+S:

```dotenv
AZURE_MAPS_KEY=REEMPLAZA_POR_TU_CLAVE_PRIVADA
WEATHER_LAT=7.11703
WEATHER_LON=-73.10534
```

Las coordenadas provienen del ejemplo de clase; no son una ubicación inferida del usuario. El adaptador revisa el archivo cada 30 segundos. En el despliegue Docker, recrear app después de editar las variables: `docker compose up -d app`. No publicar `.env`, claves, capturas del archivo ni la colección original con credenciales. Las coordenadas y el estado del proveedor se muestran en el panel, pero la clave no sale del backend.

## Arquitectura

Azure Maps (HTTPS GET, clave en header subscription-key) → weather_adapter.py (consulta cada 900 s, timeout 15 s) → tabla external_weather (SQLite en vista previa / PostgreSQL en Compose) → GET /api/weather e historial /api/weather/history → módulo Clima exterior y contexto del Asistente IA.

API-WEATHER devuelve temperatura exterior en °C, humedad relativa %, presencia de precipitación, descripción y viento en km/h. API-AIR devuelve índices del proveedor, categoría, contaminante dominante y concentraciones con unidades. El índice global se conserva en la escala de Azure; no se interpreta como otro AQI.

El navegador consulta únicamente el backend. Abrir el panel o pulsar Actualizar no vuelve a facturar una petición al proveedor; la captura periódica está en el servidor. Dos llamadas cada 15 minutos equivalen a 192 llamadas por día, sujetas a la tarifa y cuota de la cuenta Azure. La frecuencia está fijada en esta versión.

Las capturas válidas se conservan con hora UTC de consulta y de observación. El exportador entrega hasta los últimos cinco días registrados. No hay backfill ficticio: se debe mantener el servicio activo cinco días para acreditar una toma de datos de cinco días de esta fuente. Las diez fuentes simuladas originales siguen identificadas como tales.

Sin clave se muestra Pendiente de clave; una respuesta 401/403 indica revisar clave y permisos; 429 puede indicar cuota. Los errores se muestran sin URLs con secretos ni contenido bruto del proveedor. Tras un fallo se conserva la última captura y se marca error. El asistente usa clima sólo si la consulta fue reciente y la observación tiene menos de dos horas. La lluvia exterior no ejecuta riego ni demuestra que haya llegado agua al sustrato interior.

## Documentación primaria

- https://learn.microsoft.com/en-us/rest/api/maps/weather/get-current-conditions
- https://learn.microsoft.com/en-us/rest/api/maps/weather/get-current-air-quality

API version 1.1 para ambas consultas, según documentación consultada el 6 de noviembre de 2026. La llamada CurrentConditions del archivo de clase usaba 1.0; el adaptador usa la versión documentada 1.1.
