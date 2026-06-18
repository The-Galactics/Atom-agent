# Backlog historias de usuario [Atom]:

En este documente se busca dar a conocer el repositorio de nuestras historias de usuario y como se clasificaran los story points para motivar a los desarrolladores cada día.

Los story points seran otorgados a cada HU por medio de una medición basada en la secuencia de Fibonacci (1, 2, 3, 5, 8), siendo el número 1 una tarea más sencilla y el número 8 una tarea con muchisima más complejidad.

## **Sprint 1: Cimentación y Conectividad:**

**Objetivo:** Establecer la infraestructura base, el bridge Java-Python y la captura inicial de voz/texto.

| ID | Componente | Historia de Usuario (HU) | Story Points (SP) |
| :--- | :--- | :--- | :---: |
| **HU-01** | FRONTEND | Maquetado de Landing Page con identidad visual de Atom. | 3 |
| **HU-02** | FRONTEND | Botón de descarga funcional para la App móvil. | 1 |
| **HU-03** | MOBILE | Interfaz minimalista Android (baja carga cognitiva). | 3 |
| **HU-04** | MOBILE | Implementación de burbuja flotante como disparador. | 5 |
| **HU-05** | MOBILE | Feedback visual (animación) durante estado de escucha. | 3 |
| **HU-06** | IA-PYTHON | Configuración del Adaptador de Salida para APIs de Nvidia. | 2 |
| **HU-07** | IA-PYTHON | Módulo STT (Speech-to-Text) para transcripción de audio. | 5 |
| **HU-08** | IA-PYTHON | Módulo TTS (Text-to-Speech) para respuestas de voz. | 5 |
| **HU-09** | IA-PYTHON | Procesador NLP para interpretación de lenguaje natural. | 5 |
| **HU-10** | INFRA | Bridge Python-Java (gRPC/REST) para comunicación entre servicios. | 8 |
| **HU-11** | JAVA-CORE | Definición de Entidades de Dominio (Usuario, Intención). | 3 |
| **HU-12** | JAVA-CORE | Implementación de Puertos (Interfaces) de entrada/salida. | 1 |
| **HU-13** | JAVA-INFRA | Adaptador de Persistencia SQL (Repositorio de usuarios). | 3 |
| **HU-14** | SEGURIDAD | Lógica de cifrado AES-256 para datos sensibles. | 5 |
| **HU-15** | JAVA-CORE | Gestión de perfiles (Nombre, Apodo, Personalidad). | 5 |
| **HU-16** | QA | Setup y ejecución de Pruebas Unitarias de Dominio. | 8 |

## **Sprint 2: Acción, Visión y Aprendizaje:**

**Objetivo:** Dotar a Atom de capacidades de visión de interfaz y ejecución de tareas autónomas.

| ID | Componente | Historia de Usuario (HU) | Story Points (SP) |
| :--- | :--- | :--- | :---: |
| **HU-17** | IA-PYTHON | Clasificación de Intenciones (Intent Classification) al 90%. | 8 |
| **HU-18** | IA-VISION | Módulo de Análisis de Interfaz (Visión de pantalla). | 8 |
| **HU-19** | MOBILE | Inyección de eventos táctiles (Gestos, Clics autónomos). | 8 |
| **HU-20** | JAVA-CORE | Lógica de "Orquestadora": Coordinación de agentes. |5 |
| **HU-21** | JAVA-CORE | Lógica de "Desarrolladora": Grabación de nuevos flujos. | 8 |
| **HU-22** | SEGURIDAD | Bloqueo automático en aplicaciones bancarias/sensibles. | 5 |
| **HU-23** | IA-PYTHON | Optimización de respuesta (Inferencias < 4 segundos). | 8 |
| **HU-24** | MOBILE | Soporte multi-capa inicial (Ajustes en OneUI). | 3 |
| **HU-25** | MOBILE | Soporte multi-capa inicial (Ajustes en HyperOS). | 3 |
| **HU-26** | DATABASE | Implementación de Base de Datos Vectorial para flujos. | 8 |
| **HU-27** | JAVA-INFRA | Adaptador para guardado de secuencias de pasos (Workflows). | 8 |
| **HU-28** | QA | Pruebas de estrés: 5 tareas base con 70% de éxito. | 5 |
| **HU-29** | QA | Validación de reducción de interacciones físicas (65%). | 3 |
| **HU-30** | MOBILE | Sistema de Notificaciones/Feedback post-tarea autónoma. | 5 |
| **HU-31** | SEGURIDAD | Gestión y aviso de permisos de accesibilidad (RF-08). | 5 |
| **HU-32** | DOCS | Actualización de Guías Técnicas y Métodos de la IA. | 8 |
