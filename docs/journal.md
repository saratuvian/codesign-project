# CoDesign – Project Journal

## 2026-01-22 (Bi-weekly update)

### Goals for this period

- Establish a working backend foundation for the project.
- Prove integration feasibility with Autodesk Platform Services (APS) for file storage and retrieval.
- Validate an end-to-end visualization pipeline for CAD files (DWG → Viewer).
- Prepare the project for continuous development (GitHub + documentation).

### Work completed

- Created a Python backend using Flask (local API server).
- Set up environment isolation using `venv`.
- Added configuration management using `.env` (APS credentials and settings).
- Implemented APS OAuth 2.0 (2-legged) token retrieval.
- Implemented OSS (Object Storage Service) flow:
  - Create/verify bucket (`/api/oss/setup`).
  - Upload a DWG sample file (`/api/oss/upload-sample`).
  - Generate signed download URL and verify retrieval (`/api/oss/download-sample`).
- Implemented APS Model Derivative pipeline for visualization:
  - Generated URN for uploaded DWG files.
  - Submitted translation jobs to APS Model Derivative service (SVF2, 2D/3D).
  - Implemented translation status tracking via manifest retrieval.
- Integrated APS Viewer in a web-based frontend:
  - Rendered translated DWG models directly in the browser.
  - Verified visualization without requiring local AutoCAD installation.
- Refactored the repository structure:
  - Introduced `backend/` folder for server code.
  - Introduced `docs/` folder for documentation.
  - Adjusted imports after refactor and verified the server runs from `backend/`.
- Connected the project to GitHub repository:
  - https://github.com/saratuvian/codesign-project

### Issues encountered and resolutions

- APS legacy endpoints caused errors due to deprecation.
  Resolved by updating the implementation to supported APS endpoints.
- After refactoring folders, encountered import/module path issues (`ModuleNotFoundError`).
  Resolved by updating imports and execution paths.
- Viewer initially rendered an empty scene due to incorrect environment configuration.
  Resolved by explicitly configuring the viewer to use the `AutodeskProduction` environment
  and `derivativeV2` API.

### Key engineering decisions

- Separated code concerns:
  - `app.py` handles HTTP routes (API layer).
  - `aps_service.py` encapsulates APS integration logic (service layer).
- Used `.env` and `.gitignore` to prevent credential leakage and keep the repository clean.
- Chose to validate the full visualization flow (upload → translate → render) before
  implementing model modification or AI-driven features.
- Adopted a layered architecture separating read-only visualization from future
  write-capable model modification.
  The current implementation provides a model mediation layer designed to be extended
  with an MCP/Automation-based modification layer in later stages.

### Evidence / current endpoints

- Token retrieval: `GET /api/token`
- Bucket setup: `POST /api/oss/setup`
- Upload sample DWG: `POST /api/oss/upload-sample`
- Signed download URL: `GET /api/oss/download-sample`
- Generate URN: `GET /api/oss/sample-urn`
- Submit translation job: `POST /api/viewer/translate-sample`
- Translation status (manifest): `GET /api/viewer/manifest-sample`
- Viewer UI: `/viewer`

### Plan for next 2 weeks (based on supervisor guidance)

- Extend the system from read-only visualization to model modification:
  - Evaluate AutoCAD MCP / APS Design Automation as a write-capable model mediation layer.
  - Implement a minimal CAD modification proof-of-concept (e.g., inserting a door or annotation).
- Define a structured assistant command schema:
  - Natural language request → structured modification parameters.
- Add initial database support for managing projects and model versions.
- Maintain continuous updates:
  - Git commits after each milestone.
  - Journal update every two weeks with progress, issues, and next steps.
