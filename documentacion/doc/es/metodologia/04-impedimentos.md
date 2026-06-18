# Gestión de Impedimentos [Atom]:

Para llevar un flujo de trabajo ordenado, se creó este documento con la finalidad de llevar registro de los stopers y blockers que se presentaron en medio del desarrollo de el asistente de AI llamado Atom.

## Documentación y Seguimiento:

Para llevar un registro organizado de los stopers y blockers de cada sprint, se suguiere tener un orden para gestionar y registrarlos, siendo identificados por un id (ej. Imp-01), una fecha para llevar un seguimiento exacto, el tipo de impedimento, ya sea un stopper o blocker, una breve descripción, como impacta esto en el desarrollo, la persona que se va a ser responsable de estos y el estado en el que se encuentra la tarea, con el fin de terminarla de raiz y ser concientes de los puntos a mejorar. Permitiendo asi, tener una retroalimentación para nuestra retrospective al final del sprint.

### Estados del impedimento:
Los estados nos permiten llevar un seguimiento exacto de si este problema se esta solucionando o no; estos se dividiran en tres categorias y colores.

- **🔴 Pendiente:** Cuando apenas se detecta el stopper o blocker, y se esta buscando al responsable correspondiente de la tarea para solucionarla.
- **🟡 En proceso:** Cuando ya se le asigno el stoper o blocker al responsable de su solución y se esta trabajando en ello.
- **🟢 Finalizado:** Cuando se solucionó el impedimento de raiz.

### Impacto del impedimento:
El impacto del impedimento se determina por la prioridad y dificultad del proceso para la App, siendo categorizadas desde Alto hasta bajo, seguido del requisito funcional afectado por el impedimento.

- **Alto:** Cuando es una funcionalidad muy importante y prioritaria para el desarrollo de la App y a la larga generaria perdida de rendimiento en el flujo de trabajo.
- **Medio:** Cuando es algo importante pero que no afectaria en gran medida al desarrollo y puede tener una solución más llevadera.
- **Bajo:** Cuando el impedimento directamente no afecta al funcionamiento de la App pero debería ser tomado en cuenta.

### Detalle de Impedimentos y Soluciones:

Para cada impedimento debe de haber una estructura a seguir para saber cual fue el problema de raiz, que acciones se realizaron para solucionar el impedimento y por ultimo la resolución del problema, donde se determina si el impedimento se terminó o se necesita validación del PO o Scrum Master para proceder.

### Ejemplo del flujo de trabajo y resolución de impedimentos:

|ID|Fecha|Tipo|Descripción|Impacto|Responsable|Estado|
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
|Imp-01|09-05-2026|Stopper|Error de compatibilidad entre la burbuja flotante y Android 14.|Alto (Bloquea RF-04)|Scrum Master / Dev Team|🔴 Pendiente|

---
#### [IMP-01] Compatibilidad Android 14
- **Causa raíz:** Los permisos de "Mostrar sobre otras aplicaciones" cambiaron en la última API.
- **Acción:** Investigar los nuevos requerimientos de seguridad de Google.
- **Resolución:** *Pendiente de validación.*

---

# Impedimentos-Sprint 1:
