# Sustentación individual - 8 minutos

1. Contexto (1 min): invernadero con dos zonas, diez nodos, cuatro variables. Aclarar datos sintéticos y qué quedó desplegado realmente.
2. Arquitectura (1 min): seguir sensor/adaptador → MQTT → ingestión → PostgreSQL → Grafana. Explicar que el simulador local usa inserción directa; HTTP es otro camino.
3. Datos (1 min): mostrar 26-30 octubre, cambiar dispositivo y rango; explicar resolución de 5 min y 57 600 valores.
4. Gráficas (1 min): D03 tiene un aumento térmico inyectado el día 28 entre 12:00 y 14:55 UTC. La humedad del suelo desciende y se reinicia cada 12 horas. No afirmar causalidad experimental.
5. Retorno (2 min): elegir fecha actual, cambiar intervalo a 5 s, confirmar ACK. Guardar último timestamp. Apagar y esperar al menos dos intervalos; el timestamp debe permanecer estable. Encender y esperar datos nuevos. Aplicar offset +2 °C y comparar con la lectura previa, explicando la variación aleatoria. Mostrar registro en la tabla commands.
6. Protocolos (1 min): MQTT QoS 1 vs ACK de aplicación; comandos sin retain; autenticación y ACL. Mostrar PUB/SUB real en el servidor, no sólo el tablero.
7. Evidencia y límites (1 min): URLs efectivas, commit, servicios activos y captura HTTPS. Cada integrante debe poder repetir el control y explicar promedio/mínimo/máximo.

Preguntas frecuentes: ¿por qué UTC? Evita ambigüedades. ¿Por qué calibración ±5 °C? Límite del prototipo, no certificado metrológico. ¿Por qué no apagar la API externa? Sólo puede pausarse nuestro adaptador. ¿Los datos demuestran ahorro de agua? No; se requeriría experimento con comparación y medición de caudal.
