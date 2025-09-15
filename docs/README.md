# API Contracts

This directory contains OpenAPI and AsyncAPI specifications for the services.

## Viewing OpenAPI specs

### Redocly CLI

```bash
npm install -g @redocly/cli
redocly preview-docs contracts/openapi/auth_profile.yaml
```

### Swagger UI (Docker)

```bash
docker run --rm -p 8080:8080 -e SWAGGER_JSON=/foo/auth_profile.yaml -v $(pwd)/contracts/openapi/auth_profile.yaml:/foo/auth_profile.yaml swaggerapi/swagger-ui
```

Replace `auth_profile.yaml` with any other OpenAPI file to view it.

## Viewing AsyncAPI specs

### AsyncAPI CLI

```bash
npm install -g @asyncapi/cli
asyncapi preview contracts/asyncapi/cityguide-events.yaml
```
