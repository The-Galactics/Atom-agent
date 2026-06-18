# Historias de Usuario e Issues — Atom AI Assistant
**Versión:** 1.0.0 
**Estructura:** GitHub Issues organized by Feature and Developer
**Proyecto:** Atom — Asistente de IA para Dispositivos Móviles

---

> **Convención de IDs:**
> - Historia de Usuario: `HU-ATOM-[NNN]`
> - Issue: `ISSUE-[NNN]`
> - Feature: `FEAT-[MÓDULO]`
> - Requisito Técnico: `RT-[NNN]`
> - Caso de Prueba: `CP-ATOM-[NNN]`

---

## Distribución del Equipo

| Developer | Alias sugerido | Módulos asignados |
|-----------|----------------|-------------------|
| Developer 1 | `@dev1` | Frontend (Landing Page), Infraestructura Base |
| Developer 2 | `@dev2` | Mobile UI (Android), Integración UI |
| Developer 3 | `@dev3` | Core AI (Python), NLP, Procesamiento de Audio |
| Developer 4 | `@dev4` | Backend (Java Core), Persistencia, Seguridad |

---

# FEATURE: FEAT-LANDING — Landing Page (TypeScript)

## ISSUE-001 — Maquetado y Diseño Identidad Visual Atom
**Asignado a:** `@dev1` 
**Tipo:** Historia de Usuario (HU-01)
**Prioridad:** Alta 
**Labels:** `frontend`, `typescript`, `hexagonal`
**Casos de prueba:** `CP-ATOM-001`, `CP-ATOM-002`

### Descripción
Como usuario, quiero ver una página de aterrizaje profesional con la identidad visual de Atom para conocer el producto y sus beneficios.

### Criterios de Aceptación
- [ ] Landing operativa con estilos Geist Serif (títulos) y Lora (cuerpo).
- [ ] Diseño responsivo (Mobile-first) con fondo Pure Black (#0A0A0C).
- [ ] Implementación siguiendo arquitectura hexagonal en TypeScript.
- [ ] Uso de animaciones sutiles para transiciones de texto.

### Requisitos Técnicos
```
RT-001: Next.js / Vite con TypeScript
RT-002: Vanilla CSS / CSS Modules
RT-003: Arquitectura Hexagonal (Domain, Application, Infrastructure)
```

---

## ISSUE-002 — Botón de Descarga Funcional
**Asignado a:** `@dev1` 
**Tipo:** Historia de Usuario (HU-02)
**Prioridad:** Alta 
**Labels:** `frontend`, `feature`
**Casos de prueba:** `CP-ATOM-003`

### Descripción
Como usuario interesado, quiero un botón de descarga directo para obtener la aplicación móvil rápidamente.

### Criterios de Aceptación
- [ ] Botón en color Lavanda (#B794F4) con efecto hover.
- [ ] Redirección correcta al archivo APK o ejecutable.
- [ ] El botón debe ser el elemento de acción principal (CTA).

---

# FEATURE: FEAT-MOBILE — Interfaz Android y Experiencia de Usuario

## ISSUE-003 — Interfaz Minimalista Android
**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario (HU-03)
**Prioridad:** Alta 
**Labels:** `mobile`, `android`, `ui`
**Casos de prueba:** `CP-ATOM-004`, `CP-ATOM-005`

### Descripción
Como usuario, quiero una interfaz móvil con baja carga cognitiva para interactuar con la IA de forma sencilla.

### Criterios de Aceptación
- [ ] Pantalla principal limpia con máximo 3 elementos accionables.
- [ ] Implementación de temas oscuros optimizados para OLED.
- [ ] Navegación intuitiva sin menús complejos.

---

## ISSUE-004 — Disparador de Burbuja Flotante
**Asignado a:** `@dev2` 
**Tipo:** Historia de Usuario (HU-04)
**Prioridad:** Media 
**Labels:** `mobile`, `android`, `overlay`
**Casos de prueba:** `CP-ATOM-006`

### Descripción
Como usuario, quiero un disparador tipo burbuja que flote sobre otras aplicaciones para activar a Atom en cualquier momento.

### Criterios de Aceptación
- [ ] Burbuja persistente y movible por toda la pantalla.
- [ ] Al presionar, abre el modo de escucha de Atom.
- [ ] No interfiere con el uso normal de otras apps (transparencia/tamaño).

---

# FEATURE: FEAT-AI — Cerebro y Procesamiento NLP (Python)

## ISSUE-005 — Módulo STT (Speech-to-Text) y Audio
**Asignado a:** `@dev3` 
**Tipo:** Historia de Usuario (HU-07)
**Prioridad:** Alta 
**Labels:** `python`, `ai`, `stt`
**Casos de prueba:** `CP-ATOM-007`, `CP-ATOM-008`

### Descripción
Como usuario, quiero que mi voz se convierta en texto para que la IA pueda procesar mis órdenes verbales.

### Criterios de Aceptación
- [ ] Transcripción precisa con latencia menor a 500ms.
- [ ] Manejo de ruidos de fondo básicos.
- [ ] Feedback visual en la app durante el estado de escucha.

---

## ISSUE-006 — Interpretación de Lenguaje Natural con Gemma 4.0
**Asignado a:** `@dev3` 
**Tipo:** Historia de Usuario (HU-08)
**Prioridad:** Alta 
**Labels:** `python`, `ai`, `nlp`
**Casos de prueba:** `CP-ATOM-009`, `CP-ATOM-010`

### Descripción
Como sistema, necesito interpretar el lenguaje natural para extraer la intención (intent) y los parámetros de la acción.

### Criterios de Aceptación
- [ ] Identificación correcta de verbos de acción.
- [ ] Extracción de entidades (nombres, fechas, apps).
- [ ] Precisión del 90% en la clasificación de intención.

---

# FEATURE: FEAT-CORE — Arquitectura Hexagonal Java

## ISSUE-007 — Entidades de Dominio y Puertos
**Asignado a:** `@dev4` 
**Tipo:** Requisito Técnico (HU-10/11)
**Prioridad:** Crítica 
**Labels:** `java`, `core`, `hexagonal`

### Descripción
Definir los modelos de "Usuario" e "Intención" y las interfaces de entrada/salida (Puertos) siguiendo arquitectura hexagonal.

### Criterios de Aceptación
- [ ] Entidades puras en Java sin dependencias de infraestructura.
- [ ] Interfaces de puertos definidas para repositorios y servicios externos.
- [ ] Capa de aplicación (Use Cases) desacoplada de los adaptadores.

---

## ISSUE-008 — Persistencia y Seguridad (AES-256)
**Asignado a:** `@dev4` 
**Tipo:** Requisito Técnico (HU-12/13)
**Prioridad:** Alta 
**Labels:** `java`, `security`, `sql`
**Casos de prueba:** `CP-ATOM-011`

### Descripción
Implementar adaptador de persistencia SQL y lógica de cifrado AES-256 para proteger datos sensibles de perfiles.

### Criterios de Aceptación
- [ ] Registro de usuarios funcional con cifrado de campos sensibles.
- [ ] Optimización de consultas para respuestas < 100ms.
- [ ] Gestión de perfiles (Nombre, Apodo, Personalidad).