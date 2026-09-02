# Script Documentation

Document each callable that Codex creates or materially changes in a tool or
script. Do not add documentation work for untouched legacy callables.

Use the normal language form:

- Python: Google-style docstrings.
- JavaScript and TypeScript: JSDoc or TSDoc.
- Java: Javadoc.
- C, C++, and compatible languages: Doxygen-compatible comments.
- Go: documentation comments that start with the declared name.
- Rust: rustdoc comments.
- Perl: POD.
- PowerShell: comment-based help.

State purpose, inputs, outputs, raised errors or failure conditions, and
important side effects when they apply. Keep the documentation proportional to
the callable.
