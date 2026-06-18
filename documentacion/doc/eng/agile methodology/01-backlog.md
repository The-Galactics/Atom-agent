# User Story Backlog [Atom]:

This document aims to present our user story repository and how story points will be classified to motivate developers every day.

Story points will be assigned to each US using a measurement based on the Fibonacci sequence (1, 2, 3, 5, 8), where 1 is a very simple task and 8 is a task with significantly higher complexity.

## **Sprint 1: Foundation and Connectivity:**

**Objective:** Establish the base infrastructure, the Java-Python bridge, and initial voice/text capture.

| ID | Component | User Story (US) | Story Points (SP) |
| :--- | :--- | :--- | :---: |
| **US-01** | FRONTEND | Landing Page layout with Atom's visual identity. | 3 |
| **US-02** | FRONTEND | Functional download button for the mobile App. | 1 |
| **US-03** | MOBILE | Minimalist Android interface (low cognitive load). | 3 |
| **US-04** | MOBILE | Floating bubble implementation as a trigger. | 5 |
| **US-05** | MOBILE | Visual feedback (animation) during listening state. | 3 |
| **US-06** | AI-PYTHON | Output Adapter configuration for Nvidia APIs. | 2 |
| **US-07** | AI-PYTHON | STT Module (Speech-to-Text) for audio transcription. | 5 |
| **US-08** | AI-PYTHON | TTS Module (Text-to-Speech) for voice responses. | 5 |
| **US-09** | AI-PYTHON | NLP Processor for natural language interpretation. | 5 |
| **US-10** | INFRA | Python-Java Bridge (gRPC/REST) for service communication. | 8 |
| **US-11** | JAVA-CORE | Definition of Domain Entities (User, Intent). | 3 |
| **US-12** | JAVA-CORE | Implementation of Input/Output Ports (Interfaces). | 1 |
| **US-13** | JAVA-INFRA | SQL Persistence Adapter (User repository). | 3 |
| **US-14** | SECURITY | AES-256 encryption logic for sensitive data. | 5 |
| **US-15** | JAVA-CORE | Profile management (Name, Nickname, Personality). | 5 |
| **US-16** | QA | Domain Unit Testing setup and execution. | 8 |

## **Sprint 2: Action, Vision, and Learning:**

**Objective:** Provide Atom with interface vision capabilities and autonomous task execution.

| ID | Component | User Story (US) | Story Points (SP) |
| :--- | :--- | :--- | :---: |
| **US-17** | AI-PYTHON | Intent Classification at 90%. | 8 |
| **US-18** | AI-VISION | Interface Analysis Module (Screen vision). | 8 |
| **US-19** | MOBILE | Touch event injection (Gestures, autonomous clicks). | 8 |
| **US-20** | JAVA-CORE | "Orchestrator" Logic: Agent coordination. | 5 |
| **US-21** | JAVA-CORE | "Developer" Logic: Recording new flows. | 8 |
| **US-22** | SECURITY | Automatic blocking in banking/sensitive apps. | 5 |
| **US-23** | AI-PYTHON | Response optimization (Inference < 4 seconds). | 8 |
| **US-24** | MOBILE | Initial multi-layer support (OneUI adjustments). | 3 |
| **US-25** | MOBILE | Initial multi-layer support (HyperOS adjustments). | 3 |
| **US-26** | DATABASE | Vector Database implementation for flows. | 8 |
| **US-27** | JAVA-INFRA | Adapter for saving step sequences (Workflows). | 8 |
| **US-28** | QA | Stress testing: 5 base tasks with 70% success. | 5 |
| **US-29** | QA | Validation of physical interaction reduction (65%). | 3 |
| **US-30** | MOBILE | Post-autonomous task Notification/Feedback system. | 5 |
| **US-31** | SECURITY | Accessibility permissions management and alerts (RF-08). | 5 |
| **US-32** | DOCS | Update of Technical Guides and AI Methods. | 8 |
