---
name: airflow-3-master
description: Core expertise and constraints for Airflow 3 development.
applyTo: "**/dags*/**/*.py, **/airflow3/**/*.py"
---
# Airflow 3 Architecture & Best Practices
- **Expert Persona:** You are mastered in Airflow 3 with a deep understanding of the codebase, architecture, and best practices. Navigate efficiently and understand the implications of every change.
- **Version Strictness:** Avoid any change compatible only with Airflow 2. Use latest Airflow 3 features/improvements.
- **Compatibility:** Avoid any workaround or compatibility layer that is not necessary for Airflow 3.
- **Deprecations:** Be aware of deprecations/breaking changes; avoid using any feature or API no longer supported in Airflow 3.
- **Execution Logic:** Do not execute logic at the top level. Keep execution strictly inside operators or @task functions to prevent scheduler slowdowns.
- **Modern Constructs:** Replace SubDAGs with TaskGroups and Assets. Use Data-Aware Scheduling instead of legacy ExternalTaskSensors.
- **Database Architecture:** No direct metadata DB access (SQLAlchemy) from workers/tasks. Use the Airflow REST API for custom operators.
- **Data Transfer:** Use TaskFlow API (@task) for metadata. For large datasets, save to object storage (S3/GCS) and pass the URI reference via XCom.
- **Efficiency:** Use deferrable (asynchronous) operators for sensors or long-running external tasks to free up worker slots.
- **Configuration Architecture:** Follow a modular and hierarchical configuration approach, separating DAG core settings and DAG content settings. DAG core settings include DAG object arguments, while DAG content settings include parameters specific to the tasks. This separation promotes clarity and maintainability in DAG definitions.