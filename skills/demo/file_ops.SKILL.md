# File Operations Skill

This skill handles reading from and writing to the file system.

## Steps
1. Determine the file path and operation type (read/write/append).
2. Check if the file exists and if the user has appropriate permissions.
3. For read operations: open the file, read contents, close the file.
4. For write operations: create or overwrite the file with provided content.
5. Confirm the operation succeeded to the user.

## Constraints
- Never access files outside the user's designated working directory.
- Do not write sensitive information (passwords, keys) to files without explicit user consent.
- Ensure proper file encoding (UTF-8) when reading or writing text files.

## Dependencies
- Requires file system access permissions.

## Examples
- Example 1: {"input": "Read the contents of /docs/notes.txt", "output": "The full text content of notes.txt"}
- Example 2: {"input": "Write 'Hello World' to /tmp/output.txt", "output": "File written successfully to /tmp/output.txt"}
