# Google JavaScript Style Guide Summary

This document summarizes key rules and best practices from the Google JavaScript Style Guide.

## 1. Source File Basics
- **File Naming:** All lowercase, with underscores (`_`) or dashes (`-`). Extension must be `.js`.
- **File Encoding:** UTF-8.
- **Whitespace:** Use only ASCII horizontal spaces (0x20). Tabs are forbidden for indentation.

## 2. Source File Structure
- New files should be ES modules (`import`/`export`).
- **Exports:** Use named exports. **Do not use default exports.**
- **Imports:** Do not use line-wrapped imports. The `.js` extension in import paths is mandatory.

## 3. Formatting
- **Braces:** Required for all control structures.
- **Indentation:** +2 spaces for each new block.
- **Semicolons:** Every statement must be terminated with a semicolon.
- **Column Limit:** 80 characters.

## 4. Language Features
- **Variable Declarations:** Use `const` by default, `let` if reassignment is needed. **`var` is forbidden.**
- **Equality Checks:** Always use identity operators (`===` / `!==`).

## 5. JSDoc
- JSDoc is used on all classes, fields, and methods.

*Source: [Google JavaScript Style Guide](https://google.github.io/styleguide/jsguide.html)*
