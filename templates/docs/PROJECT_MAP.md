# Project Map

## Project Identity

- repository type:
- primary language(s):
- main runtime/platform:
- build system or IDE:

## Startup Chain

Document the actual runtime path from entrypoint to business logic.

Example:

1. process entry
2. framework/bootstrap
3. scheduler/task creation
4. business loop

## Active Communication Chains

For each important chain, capture:

- where it starts
- who parses inputs
- who updates state
- who emits outputs

Common examples:

- HTTP/TCP/API
- CAN/UART/SPI/I2C
- filesystem/persistence
- UI event flow

## Core Business Objects

List the important shared state structs, classes, or modules and what they represent.

## Currently Enabled vs Present In Tree

Separate:

- active runtime modules
- modules that exist but are not currently initialized or called

## Known Suspicious Areas

Keep a short list of architecture-level doubts or mismatches that future chats should verify.
