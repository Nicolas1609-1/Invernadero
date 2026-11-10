# Fondo del dashboard

Archivo: `greenhouse.jpg`. Fondo propio generado con la herramienta integrada ImageGen y optimizado a JPEG. El archivo original generado se conserva fuera del paquete; el JPEG está incluido en este proyecto y se sirve desde `/greenhouse.jpg`.

Prompt final utilizado:

> Use case: photorealistic-natural. Asset type: full-screen photographic background for a glassmorphism greenhouse monitoring dashboard, landscape 16:9. Create only the photograph, NO interface, NO cards, NO text. Scene: a luxurious botanical glasshouse conservatory at blue-hour dusk, dark charcoal metal window mullions, lush large-leaf foliage at both edges, warm amber globe lamps and subtle orange light, a comfortable teal velvet lounge chair low in the left foreground, natural wood and stone. Center should be dark, softly defocused, unobtrusive negative space so translucent UI panels are readable. Warm cinematic interior photography, muted olive, smoky brown and deep teal palette, realistic materials and fine detail. Wide architectural view, calm premium atmosphere. Avoid people, text, logos, watermarks, interface elements, exaggerated saturated colors.

La imagen de referencia proporcionada por el usuario se utilizó para interpretar la dirección visual; no se publica dentro del proyecto. El diseño funcional se implementa en HTML/CSS/JavaScript, no dentro de la imagen.

## Personalización de paneles

1. Pulsar Personalizar.
2. Arrastrar el asa Mover hacia otro panel y soltar; también admite toque o flechas del teclado al enfocar el asa.
3. Ampliar control alterna entre dos anchos en escritorio.
4. Pulsar Terminar para salir del modo de edición.
5. Restaurar recupera orden y tamaño iniciales.

La distribución se guarda con localStorage, por navegador y origen. Abrir el dominio HTTPS o usar otro dispositivo crea una distribución independiente; no hay sincronización por cuenta. Los controles de sensores mantienen su autenticación y son independientes de la organización de paneles.

Verificación realizada: arrastre con puntero, reordenamiento por teclado, persistencia tras recarga, ampliación de control, restauración y revisión de escritorio/móvil. No se observaron errores de JavaScript en el navegador.
