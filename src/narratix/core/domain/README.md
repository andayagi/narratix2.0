# Domain Layer

The domain layer represents the core business logic and data structures of the Narratix application.

## Purpose

This layer contains:

1. **Entities**: Core business objects with attributes and methods that model the problem domain
2. **Value Objects**: Immutable objects that represent concepts in the domain
3. **Services**: Classes that handle complex operations involving multiple entities
4. **Repositories**: Interfaces for data access (implementations are in the infrastructure layer)

## Design Principles

The domain layer follows these key principles:

- **Isolation**: Domain logic should be isolated from infrastructure and application concerns
- **Rich Domain Models**: Entities have both data and behavior
- **Ubiquitous Language**: Names and concepts match the business terminology
- **Domain-Driven Design**: Focus on the core domain and domain logic

## Structure

- **entities/**: Core business objects (TextContent, Character, Voice, NarrativeElement)
- **services/**: Domain services for operations that don't naturally fit into entities
- **repositories/**: Interfaces defining data access contracts
- **value_objects/**: Immutable objects representing domain concepts

## Usage Guidelines

When working with the domain layer:

1. Keep external dependencies minimal
2. Don't import infrastructure concerns (e.g., database code) into the domain
3. Focus on business rules and domain logic
4. Use value objects for immutable concepts
5. Define clear interfaces for repositories to enable different implementations 