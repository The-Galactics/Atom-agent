# Impediment Management [Atom]:

To maintain an orderly workflow, this document was created to record the stoppers and blockers encountered during the development of the AI assistant named Atom.

## Documentation and Tracking:

To maintain an organized record of stoppers and blockers for each sprint, a specific order is suggested for managing and registering them. They are identified by an ID (e.g., Imp-01), a date for exact tracking, the type of impediment (either a stopper or blocker), a brief description, how it impacts development, the person responsible, and the current status of the task, with the aim of resolving it at the root and being aware of points for improvement. This allows for feedback during our retrospective at the end of the sprint.

### Impediment Status:
Status levels allow us to track exactly whether a problem is being solved or not; these are divided into three categories and colors:

- **🔴 Pending:** When a stopper or blocker is newly detected, and the corresponding person responsible for the task is being sought.
- **🟡 In Progress:** When the stopper or blocker has been assigned to the responsible person and is being worked on.
- **🟢 Completed:** When the impediment has been resolved at the root.

### Impediment Impact:
The impact of the impediment is determined by the priority and difficulty of the process for the App, categorized from High to Low, followed by the functional requirement affected by the impediment.

- **High:** When it is a very important and priority functionality for the App's development and would eventually generate performance loss in the workflow.
- **Medium:** When it is something important but would not greatly affect development and has a more manageable solution.
- **Low:** When the impediment does not directly affect the App's functioning but should still be taken into account.

### Impediment Detail and Solutions:

Each impediment must follow a specific structure to identify the root cause, the actions performed to solve the impediment, and finally the resolution, where it is determined if the impediment is finished or needs validation from the PO or Scrum Master to proceed.

### Workflow and Resolution Example:

|ID|Date|Type|Description|Impact|Responsible|Status|
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
|Imp-01|05-09-2026|Stopper|Compatibility error between the floating bubble and Android 14.|High (Blocks RF-04)|Scrum Master / Dev Team|🔴 Pending|

---
#### [IMP-01] Android 14 Compatibility
- **Root Cause:** "Display over other apps" permissions changed in the latest API.
- **Action:** Investigate new Google security requirements.
- **Resolution:** *Pending validation.*

---

# Impediments - Sprint 1:
