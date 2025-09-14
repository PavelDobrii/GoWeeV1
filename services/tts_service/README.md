# TTS Service

Stub service for text-to-speech generation.

## Endpoints

- `POST /tts/request` – request audio generation for a story.

The service also listens to `tts.requested` Kafka topic and produces
`tts.completed` events after creating a placeholder audio file.
