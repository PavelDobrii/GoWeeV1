# Документация API

В каталоге `docs/` хранятся спецификации OpenAPI и AsyncAPI для сервисов
платформы. Ниже приведены варианты их просмотра локально.

## Просмотр OpenAPI

### Redocly CLI
```bash
npm install -g @redocly/cli
redocly preview-docs contracts/openapi/auth_profile.yaml
```
Замените `auth_profile.yaml` на нужный OpenAPI-файл.

### Swagger UI (Docker)
```bash
docker run --rm -p 8080:8080 \
  -e SWAGGER_JSON=/foo/auth_profile.yaml \
  -v $(pwd)/contracts/openapi/auth_profile.yaml:/foo/auth_profile.yaml \
  swaggerapi/swagger-ui
```

## Просмотр AsyncAPI

### AsyncAPI CLI
```bash
npm install -g @asyncapi/cli
asyncapi preview contracts/asyncapi/cityguide-events.yaml
```
