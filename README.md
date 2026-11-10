# Invernadero IoT - entrega reproducible

Prototipo académico: 10 dispositivos lógicos multivariable, 5 días sintéticos, tablero propio, control bidireccional HTTP/MQTT y configuración de Homelab con Grafana. El panel está iniciado como vista previa en el servidor del equipo; el despliegue completo de contenedores y la URL pública requieren validación adicional. No hay sensores físicos conectados ni respuestas de API reales en los datos entregados.

## Panel de vidrio personalizable

La interfaz usa un fondo propio, vidrio translúcido y acentos cálidos. Personalizar permite reorganizar los ocho paneles mediante arrastre o flechas del teclado. Terminar conserva el orden en el navegador; Restaurar recupera el diseño inicial. Incluye ampliación del control en escritorio. Ver ASSETS.md para el fondo, su prompt y las pruebas de la interfaz. Los archivos glass.css, warm-glass.css, layout.js y greenhouse.jpg deben acompañar a dashboard.html.

## Inicio local (sin dependencias)

El menú izquierdo incluye Asistente IA (reglas y tendencia local, con riego simulado confirmado) y Clima exterior (Azure Maps). Consultar AZURE_MAPS.md para configurar la clave privada, los endpoints y el historial. El 6 de noviembre de 2026 se validaron respuestas reales de Azure para API-WEATHER y API-AIR y su visualización en el servidor. La clave fue configurada de forma privada por el usuario; no se usa la credencial incluida en la colección de clase. Los cinco días iniciales siguen siendo sintéticos; el historial meteorológico real comienza con la primera captura válida.

Con Python 3.11 o posterior, desde esta carpeta:

```sh
python app.py --seed
python app.py --live
```

Abrir http://localhost:8080. Token local: `local-demo-cambiar`. Para cambiarlo definir `ADMIN_TOKEN` antes de iniciar. El histórico abarca desde 2026-10-26 00:00 UTC hasta 2026-10-30 23:55 UTC. No cambiar al rango de hoy para ver ese histórico. Para ver datos nuevos, seleccionar la fecha actual y el día siguiente. Ejecutar sin `--live` deja habilitada sólo la recepción externa y el control.

El CSV incluye 57 600 valores: 10 dispositivos × 1 440 instantes × 4 variables. API fixture significa emulación de una fuente API, no una descarga. Dataset es sintético, no una fuente externa. D01/D02 están reservados para futura sustitución por hardware; hoy son gemelos.

## Homelab Linux + Docker Compose

1. Copiar el proyecto al servidor. Instalar Docker Engine y Compose siguiendo su documentación oficial. Dimensionamiento inicial propuesto: 2 CPU, 4 GB RAM y 20 GB de disco; medir el consumo real. No es un benchmark.
2. Tener dos subdominios propios con registros A hacia la IP pública. Abrir TCP 80 y 443 y reenviarlos al servidor. Con CGNAT, resolver conectividad con el ISP o un túnel autorizado antes de continuar. Este paquete no configura túneles ni DNS.
3. `cp .env.example .env`. Sustituir dominios y todos los secretos; usar valores hexadecimales aleatorios diferentes (por ejemplo `python -c "import secrets; print(secrets.token_hex(32))"`). No subir `.env`.
4. Crear el archivo de contraseñas de Mosquitto. Ejecutar desde esta carpeta; introducir las claves cuando se soliciten:

```sh
docker run --rm -it -v "$PWD/mosquitto:/config" eclipse-mosquitto:2 mosquitto_passwd -c /config/passwords service
docker run --rm -it -v "$PWD/mosquitto:/config" eclipse-mosquitto:2 mosquitto_passwd /config/passwords operator
chmod 644 mosquitto/passwords
docker compose config --quiet
docker compose up -d --build
docker compose exec app python app.py --seed
docker compose ps
docker compose logs --tail=80 app mosquitto caddy
```

La contraseña de `service` debe coincidir con MQTT_PASSWORD. Proteger la carpeta en el host; el contenedor necesita poder leer el archivo. El usuario operator tiene contraseña independiente. El primer comando crea un archivo nuevo: no repetir `-c` cuando ya tenga usuarios. El histórico se genera explícitamente y es idempotente. La simulación en vivo comienza con el contenedor.

5. Abrir `https://<APP_DOMAIN>/health` y el tablero. Abrir `https://<GRAFANA_DOMAIN>`; usuario `admin`, contraseña GRAFANA_PASSWORD. Dashboard provisionado: Invernadero. Caddy solicita certificados; requiere DNS y conectividad correctos.
6. En Grafana seleccionar 26 a 31 de octubre de 2026 UTC. El selector aplica a todos los paneles. Ver mínimo, máximo y promedio en la leyenda.
7. Para MQTT desde el servidor, usar `docker compose exec mosquitto mosquitto_pub` y `mosquitto_sub`. No publicar 1883 a Internet. Para sensores externos utilizar VPN o configurar un listener TLS y certificados antes de exponerlo. El Compose base sólo permite MQTT interno; no promete conectividad física externa.

## Protocolo y contrato

MQTT 3.1.1 sobre TCP, QoS 1. Topics: `greenhouse/D01/telemetry`, `greenhouse/D01/command`, `greenhouse/D01/ack`. No retener comandos. QoS 1 puede duplicar: lecturas se deduplican por dispositivo/instante/variable; comandos por ID. El ACK MQTT confirma aplicación al gemelo, no un actuador físico. El PUBACK del bróker sólo confirma entrega MQTT.

Telemetría (las cuatro variables son obligatorias):

```json
{"ts":"2026-10-26T12:00:00Z","values":{"temperature":27.2,"humidity":65,"soil":52,"light":32000}}
```

Comando MQTT: generar `issued_at` como Unix epoch actual y un UUID nuevo; caduca a los 60 segundos.

```json
{"id":"uuid-unico","issued_at":0,"settings":{"enabled":false}}
```

El valor 0 es ilustrativo y será rechazado por expiración. Suscribirse al ACK antes de publicar el comando con usuario operator. Ejecutar el comando `date +%s` para obtener la hora actual en Linux. No hay actuadores físicos ni firmware ESP32 en esta versión. El servicio consume comandos y aplica el estado de los gemelos; al integrar hardware, reservar un topic distinto y esperar su ACK real antes de reportar éxito.

HTTP: `GET /api/devices`, `GET /api/data?device=D01&variable=temperature&start=2026-10-26&end=2026-10-31`, `POST /api/command` y `POST /api/telemetry`. POST requiere `Authorization: Bearer <ADMIN_TOKEN>`.

```json
{"device":"D01","settings":{"enabled":true,"offset":1.2,"interval_s":30}}
```

El control web usa HTTPS y aplica directamente al gemelo; no atraviesa MQTT. El receptor MQTT proporciona una segunda ruta independiente de control. La simulación local inserta datos directamente: sus gráficas no prueban tráfico MQTT. Apagar detiene sólo el publicador simulado; no bloquea telemetría externa entrante. Calibrar modifica la temperatura futura y no reescribe históricos. Fuentes API/dataset futuras permiten controlar el adaptador local, no el proveedor remoto.

## Reglas y datos

Temperatura >32 °C y suelo <40 % producen conteos visuales por muestra en el intervalo consultado. No hay envío de correos, motor de incidentes ni actuación automática. Para incidentes reales añadir persistencia de alarma, permanencia de 15 minutos e histéresis al bajar de 30 °C o subir de 45 %; esas mejoras no están implementadas. La app calcula media/mínimo/máximo sobre valores crudos. Grafana agrega medias por intervalo y muestra min/max/media de esa serie agregada; pueden diferir al ampliar la ventana.

## Pruebas

```sh
python -m unittest -v test_project.py
```

También ejecutar la demostración HTTP descrita en SUSTENTACION.md. El Compose y Grafana requieren validación real en el servidor; no se probaron con Docker en el entorno de autoría.

## Publicar en GitHub

Crear en GitHub un repositorio vacío llamado `invernadero-iot`, sin añadir README remoto. Desde esta carpeta:

```sh
git init
git add .
git commit -m "Proyecto IoT de invernadero reproducible"
git branch -M main
git remote add origin https://github.com/USUARIO/invernadero-iot.git
git push -u origin main
```

Sustituir USUARIO. La autenticación se realiza con tu cuenta; no pegar claves en el repositorio. Registrar la URL efectiva en ENTREGA.md y en el informe final. No se creó ningún repositorio desde esta sesión.

## Operación

Persistencia PostgreSQL, Grafana y Caddy en volúmenes. Respaldo: `docker compose exec -T postgres pg_dump -U iot iot > backup.sql`. Conservar cifrado fuera del servidor y probar restauración antes de depender del respaldo. `docker compose down` conserva volúmenes; evitar `down -v` porque elimina los datos. Guardar revisiones de configuración y fijar los digests de las imágenes después de la validación del servidor. El prototipo no incluye alta disponibilidad, control de usuarios por dispositivo en HTTP ni pruebas de carga.

## Cierre de requisitos

Implementado y comprobado localmente: datos sintéticos de 5 días, 10 dispositivos lógicos × 4 variables, gráficos en PDF, API, control de gemelos y pruebas automatizadas. Preparado pero pendiente de ejecución: Mosquitto/Grafana/PostgreSQL/Caddy en Homelab. Pendiente del usuario: dominio, despliegue, repositorio público/privado accesible al docente y evidencia real de MQTT. Si el docente exige las cuatro categorías Real/Digital Twin/API/DataSet, esta versión no cumple aún la categoría Real ni API conectada: integrar dispositivos físicos y una API auténtica antes de presentar como entrega definitiva.
