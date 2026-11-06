# MediCore Project Constitution

**Project:** MediCore — Hospital Management System
**Document Type:** Project Constitution
**Version:** 1.0.0
**Status:** Ratified — 2026-11-07

## 1. Core Principles

### I. Requirements-First Development

- Every significant feature MUST have an approved specification before implementation.
- Requirements MUST describe the feature's purpose, actors, expected behavior, acceptance criteria, and constraints.
- Ambiguous requirements MUST be clarified before architectural planning.
- Implementation MUST follow the approved specification and plan.
- Changes to approved requirements MUST be documented and reviewed.

### II. Maintainable and Modular Architecture

- The system MUST follow a modular architecture with clear separation of responsibilities.
- Frontend, backend, business logic, API interfaces, and data persistence MUST have clearly defined boundaries.
- Backend functionality MUST be organized into cohesive Django applications.
- Frontend functionality MUST use reusable, appropriately scoped components and modules.
- Business rules MUST NOT be duplicated across unrelated modules.
- Dependencies between modules MUST remain explicit and manageable.
- Architectural changes MUST be documented and justified.

### III. Security and Privacy by Design

- Authentication MUST be required for protected system functionality.
- Authorization MUST follow Role-Based Access Control (RBAC).
- Users MUST only access functionality and information permitted by their assigned roles.
- Authorization MUST be enforced on the backend; frontend restrictions alone are insufficient.
- Sensitive information MUST be protected during transmission and storage using appropriate security controls.
- Passwords MUST never be stored in plaintext.
- Secrets, credentials, tokens, and private configuration MUST NOT be committed to version control.
- Development and testing MUST use synthetic patient information rather than real patient records.
- Sensitive information MUST NOT be unnecessarily exposed through logs, error messages, or API responses.

### IV. Data Integrity and Reliability

- PostgreSQL MUST serve as the primary relational database.
- Data relationships and constraints MUST be explicitly designed.
- Database migrations MUST be version-controlled and reproducible.
- Operations involving multiple dependent database changes MUST use appropriate transactions.
- Input validation MUST be enforced on the backend.
- Critical records and financial transactions MUST maintain consistency and traceability.
- Important operations MUST handle failures without leaving inconsistent data.
- Destructive changes to persistent data MUST be controlled and justified.

### V. Quality Assurance and Test-First Development

- Critical business logic MUST have automated tests.
- Authentication and authorization rules MUST be tested.
- Critical patient registration, appointment, clinical record, laboratory, and billing workflows MUST have appropriate automated coverage when included in the approved scope.
- API validation, error handling, and database integrity MUST be tested.
- Integration tests MUST verify interactions between dependent modules.
- End-to-end tests MUST cover important user journeys.
- Tests MUST be executed after relevant changes.
- Existing tests MUST NOT be weakened or removed merely to make an implementation pass.
- Known critical defects MUST be resolved before a feature is considered complete.

### VI. Consistent and Accessible User Experience

- The interface MUST be consistent across the application.
- The application MUST support the needs of its intended hospital staff.
- Forms MUST provide meaningful validation and error feedback.
- Important actions MUST provide clear success, failure, or confirmation feedback.
- Interfaces MUST be responsive and usable across supported screen sizes.
- Accessibility and usability MUST be considered during interface design.
- Destructive or sensitive actions MUST include appropriate safeguards.

### VII. Documentation and Traceability

- Requirements, specifications, architecture decisions, and implementation plans MUST be maintained in the repository.
- Significant architectural decisions MUST have documented rationale.
- API contracts MUST be documented and kept consistent with implementation.
- Database design documentation MUST reflect the implemented schema.
- Features MUST be traceable from approved requirements through tasks, implementation, and tests.
- Documentation MUST be updated when relevant behavior or architecture changes.
- Git commits MUST communicate the purpose of their changes.

### VIII. Simplicity and Scope Discipline

- Implementation MUST solve approved requirements without unnecessary complexity.
- New dependencies MUST have a clear technical justification.
- Features outside the approved project scope MUST NOT be implemented without project-owner approval.
- Reusable abstractions SHOULD be introduced when they provide genuine value.
- Premature optimization and unnecessary architectural patterns SHOULD be avoided.
- Maintainability and clarity MUST take priority over clever or unnecessarily complicated solutions.

## 2. Project Scope and Technical Constraints

### 2.1 Hospital Scope

- MediCore MUST initially support one hospital organization.
- The architecture SHOULD remain modular enough to accommodate future expansion if formally approved.
- Multi-hospital tenancy and cross-hospital data isolation are not part of the initial scope.

### 2.2 Technology Standards

The proposed technology stack is:

- Frontend: React with TypeScript.
- Frontend tooling: Vite.
- UI styling: Tailwind CSS and shadcn/ui.
- Backend: Python with Django and Django REST Framework.
- Database: PostgreSQL.
- Version control: Git and GitHub.
- Specification workflow: GitHub Spec Kit.

Final technology selections MUST be confirmed through the approved architecture plan.

### 2.3 Access Control

- MediCore MUST implement Role-Based Access Control.
- Roles and their permissions MUST be explicitly defined.
- Access MUST follow the principle of least privilege.
- Administrative privileges MUST be restricted to authorized users.
- Sensitive operations MUST be protected by backend authorization checks.
- Access-control changes MUST be documented and tested.

### 2.4 Healthcare Data

- Development environments MUST use synthetic data.
- Patient records MUST be accessible only to appropriately authorized users.
- Medical and financial records MUST preserve appropriate data integrity and auditability.
- Data collection MUST be limited to information required by approved workflows.
- Applicable privacy and data-protection requirements MUST be identified during requirements discovery.

### 2.5 Quality Standards

- Critical workflows MUST be covered by automated tests.
- The backend MUST validate incoming data.
- The frontend MUST handle API errors gracefully.
- Code MUST follow consistent formatting and naming conventions.
- Changes MUST NOT introduce avoidable regressions.
- A feature MUST satisfy its acceptance criteria before completion.

## 3. Development Workflow

MediCore MUST follow the Spec-Driven Development workflow:

1. Constitution — establish governing engineering principles.
2. Specify — document feature requirements and acceptance criteria.
3. Clarify — resolve ambiguities and missing decisions.
4. Plan — define architecture and implementation approach.
5. Checklist — validate specification quality where appropriate.
6. Tasks — create actionable implementation tasks.
7. Analyze — identify inconsistencies across project artifacts.
8. Implement — execute approved tasks.
9. Converge — verify implementation against requirements and identify remaining work.

Not every optional workflow step is mandatory for every feature, but requirements, planning, implementation, and verification MUST remain traceable.

Both Antigravity and Qoder MUST follow the same constitution, approved specifications, and architectural decisions.

Neither AI agent may independently:

- Change the approved technology stack.
- Modify the project constitution.
- Expand the approved project scope.
- Introduce major architectural changes.
- Bypass security or testing requirements.

Such changes require explicit project-owner approval.

## 4. Governance

- This constitution is the highest-level source of engineering principles for MediCore.
- All project specifications, plans, tasks, code, and reviews MUST comply with it.
- Amendments MUST be reviewed and explicitly approved by the project owner.
- Every amendment MUST include a documented rationale.
- Constitution changes MUST follow semantic versioning:
  - MAJOR: Removal or fundamental redefinition of an existing principle.
  - MINOR: Addition of a new principle or significant expansion of existing requirements.
  - PATCH: Clarification, wording improvements, or non-substantive corrections.
- Agents MUST identify conflicts between requested work and this constitution rather than silently ignoring the governing rules.
- Temporary exceptions MUST be explicitly approved and documented.

**Version**: 1.0.0 | **Ratified**: 2026-11-07 | **Last Amended**: 2026-11-07
