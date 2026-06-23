---
name: postman_to_frontend_models
description: Reads a Postman collection, calls the APIs to retrieve real response data, and generates TypeScript frontend data models/interfaces based on the JSON responses.
---

# Postman to Frontend Models Generator

When the user triggers this skill, you must automate the extraction of frontend data models (TypeScript interfaces) directly from a working API backend by using a Postman Collection as a reference.

## 1. Locate and Read the Postman Collection
- Ask the user for the path to the Postman Collection JSON and Environment JSON (if not provided).
- Read the Postman Collection and Environment files using the `view_file` tool.
- Parse the environment variables (like `base_url`, `auth_token`, etc.).

## 2. Identify the Endpoints
- Iterate through the requests defined in the Postman collection.
- For each request, identify the HTTP Method, URL, required Headers, and Request Body.
- Substitute any `{{variable}}` placeholders in the URL and headers with the actual values from the Postman Environment file.

## 3. Call the APIs to get Real Data
- Use the `run_command` tool to execute `curl` (via PowerShell `Invoke-RestMethod`) or write a short Python/NodeJS script to actually call the API endpoints.
- Ensure the backend services are running locally before calling.
- **Tip**: For authenticated routes, you must first call the Login/Auth endpoint to retrieve a valid token, use it to update the token variable in memory, and then call the protected routes.

## 4. Generate TypeScript Data Models
- Once you receive a successful JSON response (e.g., `200 OK`) from an endpoint, analyze the JSON object structure.
- Generate standard TypeScript interfaces or types that strongly type the response payload.
- Also generate Request payload interfaces for the JSON body of any `POST/PUT/PATCH` requests.
- Use best practices for TypeScript: `PascalCase` for interface names, ensure property names match the API exact casing (usually `snake_case`), and use appropriate scalar types (`string`, `number`, `boolean`, `Date`).

## 5. Output the Models
- Write the generated TypeScript interfaces to the frontend project directory (e.g., `snaprise-frontend/src/types/api/`) using the `write_to_file` tool.
- Group the types into domain-specific files (e.g., `auth.types.ts`, `otp.types.ts`, `board.types.ts`).
- Present a final summary of the generated models to the user, highlighting any endpoints that failed or required manual intervention.
