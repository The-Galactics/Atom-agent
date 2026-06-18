# Guía De Identidad Visual:

## Tipografia:

La selección de la tipografía, busca ser la más adecuada para cumplir con nuestros estándares de calidad minimalistas y poco sofocante para la interacción entre el usuario y la aplicación.

 1. **Titulos y encabezados:**

 - **Fuente:** Geist Serif.
 - **Especificación:** Utilizada para títulos de secciones, nombres de funciones y encabezados de la Landing Page.
 - **Atributo:** Aporta elegancia técnica y claridad, permitiendo una jerarquía visual inmediata sin sobrecargar el diseño.

 2. **Cuerpo de textos y Encabezados:**

 - **Fuente:** Lora.
 -  **Especificación:** Utilizada para todas las respuestas del asistente, descripciones largas y guías de usuario.
    
-  **Atributo:** Su diseño optimizado para lectura prolongada asegura que el usuario pueda interactuar con la IA de manera cómoda y amigable.

---

## Paleta de Colores y Contraste

El sistema de color está diseñado para maximizar el enfoque en el contenido y asegurar la accesibilidad para personas con dificultades visuales.

---
|Color | Nombre | Hexadecimal | Uso |
|--|--|--|--|
|![](https://img.shields.io/static/v1?label=&message=%20%20%20%20&color=0A0A0C&style=for-the-badge)	|Pure Black|#0A0A0C| Fondo optimizado para pantallas móviles OLED, eliminando distracciones y ahorrando energía.|
|![](https://img.shields.io/static/v1?label=&message=%20%20%20%20&color=FFFFFF&style=for-the-badge)	|White| #FFFFFF| Texto principal, Proporciona el máximo ratio de contraste posible (21:1) para una lectura sin esfuerzo.|
|![](https://img.shields.io/static/v1?label=&message=%20%20%20%20&color=A1A1A1&style=for-the-badge)	|Steel Gray|#A1A1A1|Utilizado para metadatos o información menos crítica para jerarquizar la lectura.
|![](https://img.shields.io/static/v1?label=&message=%20%20%20%20&color=B794F4&style=for-the-badge)	|Lavanda|#B794F4| Utilizado exclusivamente para botones de interacción inmediata|

---

# Principios de diseño:

-   **Simplicidad Extrema:** No deben existir más de 3 elementos accionables por vista.
    
-   **Espaciado Negativo:** Se prioriza el espacio en blanco (o negro, en este caso) para que los textos en **Lora** respiren y la información no se sienta aglomerada.

# Estructura Hexagonal para Java y Python

domain
    models

application

    port
        in
        out

    usecase

infrastructure
    adapter
        in
        out
    entity
    mapper