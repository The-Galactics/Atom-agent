# Casos de Prueba Gherkin — Proyecto Atom AI
**Versión:** 1.0.0 
**Formato:** BDD (Behavior Driven Development)
**Proyecto:** Atom — Mobile AI Assistant

---

## Módulo: Landing Page (FEAT-LANDING)

### CP-ATOM-001 — Identidad Visual y Tipografía
**Asociado a:** ISSUE-001 | HU-01
```gherkin
Feature: Identidad Visual de la Landing Page
  Como usuario, quiero que el sitio refleje la elegancia y simplicidad de Atom

  Scenario: Verificación de fuentes y colores base
    Given que el usuario accede a la URL de la landing page
    Then el fondo del sitio debe ser "Pure Black" (#0A0A0C)
    And los títulos principales deben usar la fuente "Geist Serif"
    And los textos descriptivos deben usar la fuente "Lora"
    And el contraste de texto debe permitir una lectura clara sin fatiga visual
```

### CP-ATOM-002 — Responsividad y Mobile-First
**Asociado a:** ISSUE-001 | HU-01
```gherkin
Feature: Diseño Responsivo
  Scenario: Adaptación a dispositivos móviles pequeños
    Given que el usuario abre la landing en un dispositivo con ancho 375px
    When visualiza la sección Hero
    Then el contenido debe apilarse verticalmente
    And no debe existir scroll horizontal
    And el botón de descarga debe ser fácilmente accionable con el pulgar
```

### CP-ATOM-003 — Descarga del Aplicativo
**Asociado a:** ISSUE-002 | HU-02
```gherkin
Feature: Botón de Descarga Funcional
  Scenario: Descarga exitosa del APK desde Android
    Given que el usuario navega desde un dispositivo Android
    When presiona el botón "Descargar Atom" (Lavanda #B794F4)
    Then el navegador debe iniciar la descarga de un archivo con extensión ".apk"
    And se debe mostrar un mensaje breve con los pasos de instalación manual
```

---

## Módulo: Interfaz Mobile (FEAT-MOBILE)

### CP-ATOM-004 — Simplicidad Extrema en UI
**Asociado a:** ISSUE-003 | HU-03
```gherkin
Feature: Simplicidad y Carga Cognitiva
  Scenario: Límite de elementos accionables en pantalla principal
    Given que la aplicación Atom está abierta en la pantalla principal
    Then el número de botones o campos de entrada visibles no debe exceder de 3
    And el espacio negativo (negro) debe predominar sobre los elementos visuales
```

### CP-ATOM-005 — Feedback de Escucha (Animación)
**Asociado a:** ISSUE-003 | HU-05
```gherkin
Feature: Indicador Visual de Escucha
  Scenario: Activación de animación durante entrada de audio
    Given que el usuario ha activado el modo de voz
    When el micrófono detecta entrada de audio
    Then la interfaz debe mostrar una animación circular pulsante
    And el color de la animación debe ser Lavanda (#B794F4)
    And la animación debe detenerse inmediatamente al terminar de hablar
```

### CP-ATOM-006 — Disparador de Burbuja Flotante
**Asociado a:** ISSUE-004 | HU-04
```gherkin
Feature: Burbuja de Acceso Rápido
  Scenario: Persistencia sobre otras aplicaciones
    Given que la opción "Burbuja de Atom" está activada
    When el usuario abre otra aplicación (ej. WhatsApp)
    Then el ícono circular de Atom debe permanecer visible en un lateral de la pantalla
    And al arrastrar el ícono, este debe seguir el movimiento del dedo
    And al soltar el ícono, este debe ajustarse al borde más cercano
```

---

## Módulo: Cerebro AI & NLP (FEAT-AI)

### CP-ATOM-007 — Precisión STT (Speech-to-Text)
**Asociado a:** ISSUE-005 | HU-07
```gherkin
Feature: Transcripción de Voz a Texto
  Scenario: Transcripción correcta de comando simple
    Given que el sistema está en modo de escucha
    When el usuario dice claramente "Abre el calendario"
    Then el módulo STT debe generar el string de texto exacto "Abre el calendario"
    And la latencia de transcripción debe ser menor a 500ms
```

### CP-ATOM-008 — Manejo de Silencio o Audio Inválido
**Asociado a:** ISSUE-005 | HU-07
```gherkin
Feature: Robusteza del Módulo de Audio
  Scenario: Intento de comando sin hablar
    Given que el modo de escucha está activo
    When transcurren 3 segundos de silencio total
    Then el sistema debe cerrar el modo de escucha automáticamente
    And mostrar un mensaje sutil: "No te escuché, ¿puedes repetir?"
```

### CP-ATOM-009 — Clasificación de Intención (Gemma 4.0)
**Asociado a:** ISSUE-006 | HU-08
```gherkin
Feature: Interpretación de Intenciones NLP
  Scenario: Identificación de intención de envío de correo
    Given que el usuario ingresa el texto "Manda un mail a Juan diciendo que llego tarde"
    When el modelo Gemma 4.0 procesa la petición
    Then la intención detectada debe ser "SEND_EMAIL"
    And los parámetros extraídos deben incluir:
      | destinatario | Juan |
      | mensaje      | llego tarde |
    And la confianza (confidence) del resultado debe ser superior al 0.90
```

### CP-ATOM-010 — Aprendizaje de Acciones (Vector DB)
**Asociado a:** ISSUE-006 | HU-08
```gherkin
Feature: Optimización por Aprendizaje
  Scenario: Respuesta rápida a comando repetido
    Given que el usuario ha ejecutado "Abre Spotify" 5 veces previamente
    When el usuario dice "Pon música"
    Then el sistema debe encontrar la relación en la base vectorial (ChromaDB)
    And ejecutar la acción sin necesidad de un análisis NLP profundo
    And la respuesta debe ser instantánea (latencia < 100ms)
```

---

## Módulo: Core & Seguridad (FEAT-CORE)

### CP-ATOM-011 — Cifrado de Datos AES-256
**Asociado a:** ISSUE-008 | HU-13
```gherkin
Feature: Protección de Datos Sensibles
  Scenario: Persistencia de perfil cifrada
    Given que el usuario configura su apodo como "Tony Stark"
    When el sistema guarda el perfil en la base de datos
    Then el valor almacenado físicamente en el campo "apodo" no debe ser legible en texto plano
    And el algoritmo utilizado para el cifrado debe ser AES-256
    And al recuperar el perfil, el apodo debe mostrarse correctamente como "Tony Stark"
```
