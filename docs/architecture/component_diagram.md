# Component Diagram

This document outlines the high-level components of the Narratix system.

```mermaid
graph TD
    CLI[Command Line Interface] --> Core
    WebApp[Web Application (Future)] --> API
    API[API Service] --> Core
    Core[Core Logic Engine] --> Infrastructure
    Core --> Services
    Services[External Services (e.g., TTS)]
    Infrastructure[Data Stores/File System]

    subgraph Narratix System
        CLI
        WebApp
        API
        Core
        Infrastructure
    end

    Narratix System --> Services
```

**Description:**

*   **CLI:** Provides command-line access for text processing and generation.
*   **API Service:** Exposes core functionality via a RESTful API (potential future development for WebApp).
*   **Core Logic Engine:** Contains the main domain logic, text parsing, character handling, voice mapping, and narrative generation.
*   **Infrastructure:** Handles data persistence (e.g., saving/loading projects, configurations) and interactions with the file system.
*   **External Services:** Interfaces with third-party services, primarily Text-to-Speech (TTS) engines.
*   **WebApp (Future):** Potential future graphical user interface for easier interaction. 