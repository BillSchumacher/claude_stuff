---
name: nestjs
description: "Applies when building or reviewing NestJS applications. Covers modules, DI, pipes/guards/interceptors, DTOs, exception filters, and testing."
---

# NestJS

## Architecture

1. **One module per feature domain.** Each module encapsulates controllers, providers, and DTOs. Import only what's needed.
2. **Use dependency injection for everything.** Never `new Service()` manually. Register in module `providers`, inject via constructor.
3. **Controllers handle HTTP, services handle business logic.** Never put DB queries or business rules in controllers.

## Validation and DTOs

4. **Use class-validator DTOs with `ValidationPipe`.** Apply globally: `app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }))`. `whitelist` strips unknown properties.
5. **DTOs for every request body.** Separate CreateDto, UpdateDto (with PartialType). Never pass raw request bodies to services.

## Guards, pipes, interceptors

6. **Guards for auth/authorization.** Return boolean. Apply with `@UseGuards()`. `AuthGuard` checks JWT, `RolesGuard` checks permissions.
7. **Interceptors for cross-cutting concerns.** Logging, caching, response transformation, timeout. Use `@UseInterceptors()` or register globally.
8. **Exception filters for error formatting.** Custom filter to return RFC 9457 ProblemDetails or consistent error shape.

## Database and config

9. **Use `@nestjs/config` with ConfigService.** Validate env vars with Joi or class-validator. Never access `process.env` directly in services.
10. **TypeORM or Prisma — not both.** Use `@nestjs/typeorm` with repository pattern or Prisma with a custom provider.

## Testing

11. **Use `Test.createTestingModule` for unit tests.** Override providers with mocks.
12. **Use `supertest` with `app.getHttpServer()` for e2e tests.** Spin up the full NestJS app.

## Microservices

13. **Transport layer abstraction.** TCP, Redis, NATS, MQTT, gRPC, Kafka. Switch without changing business logic.
14. **Use `@MessagePattern` for request-response, `@EventPattern` for events.**
