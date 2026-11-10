# Groq en el Asistente IA

Abrir en el servidor:

```sh
nano /home/nicolas/invernadero-iot/invernadero-iot/.env
```

Añadir sin reemplazar las líneas existentes:

```dotenv
GROQ_API_KEY=REEMPLAZAR_POR_TU_CLAVE
GROQ_MODEL=openai/gpt-oss-120b
```

Guardar con Ctrl+O, Enter y salir con Ctrl+X. El backend lee esta configuración al solicitar el análisis; no hace falta reiniciar la vista previa. Con Docker, recrear app para actualizar las variables de entorno. Nunca pegar la clave en el chat ni en el navegador. El archivo .env no se incluye en Git ni en el ZIP.

En Asistente IA, escribir una pregunta y pulsar Analizar con Groq. Las consultas no requieren token; el token de administración se reserva para los comandos de dispositivos y el riego. La clave Groq sólo se usa en el servidor como header Authorization. Los secretos se introducen por el propietario; la interfaz no los imprime.

## Flujo

Dashboard → POST /api/ai/groq sin token → lecturas actuales y fuentes → HTTPS POST https://api.groq.com/openai/v1/chat/completions → respuesta de texto → dashboard.

Se comparten con Groq IDs lógicos, zonas Norte/Sur, últimas lecturas y sus fechas, riegos simulados registrados, extrapolaciones locales y valores de clima/AQI de Azure. No se envían coordenadas, contraseñas ni claves. La pregunta admite hasta 500 caracteres. Hay un límite global de una llamada por minuto y timeout de 35 segundos. El consumo depende de la cuenta Groq; no se programa generación automática.

La respuesta se muestra como texto, sin ejecutar HTML ni comandos. Groq no dispone de herramientas para activar riego. El botón de riego conserva la confirmación, límites y bitácora existentes. La extrapolación numérica procede de reglas/regresión local; el modelo explica el contexto y sus límites. Toda recomendación requiere revisión humana.

Sin clave, sin permisos de modelo o sin cuota, se muestra el error sin exponer credenciales y permanece disponible el análisis local. El modelo es configurable; usar un identificador disponible para la cuenta en https://console.groq.com/docs/models.

Documentación: https://console.groq.com/docs/text-chat y https://console.groq.com/docs/api-reference.

Pruebas: respuesta mediante transporte simulado, ausencia de herramientas ejecutables, separación de la clave del cuerpo de la petición, límite temporal y configuración obligatoria. El 6 de noviembre de 2026 se validó una respuesta real con openai/gpt-oss-120b, después de la autorización explícita del propietario para enviar las lecturas, fechas, riegos simulados y valores de Azure. No se enviaron coordenadas ni claves en el contenido.
