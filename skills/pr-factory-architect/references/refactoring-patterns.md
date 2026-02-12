# Refactoring Patterns for Small Architectural Improvements

Safe refactoring patterns that fit in small PRs (<200 LOC).

## Pattern 1: Extract Duplicate Code

### When to Use
- Same code/logic in 3+ places
- Copy-paste detected
- Similar functions with different names

### How to Refactor

**Before:**
```typescript
// file1.ts
function validateUserEmail(email: string): boolean {
  const regex = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i;
  return regex.test(email);
}

// file2.ts
function checkEmail(email: string): boolean {
  const pattern = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i;
  return pattern.test(email);
}

// file3.ts
const emailRegex = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i;
function isValidEmail(e: string) {
  return emailRegex.test(e);
}
```

**After:**
```typescript
// constants/validation.ts
export const EMAIL_REGEX = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i;

// file1.ts
import { EMAIL_REGEX } from '../constants/validation';
function validateUserEmail(email: string): boolean {
  return EMAIL_REGEX.test(email);
}

// file2.ts
import { EMAIL_REGEX } from '../constants/validation';
function checkEmail(email: string): boolean {
  return EMAIL_REGEX.test(email);
}

// file3.ts
import { EMAIL_REGEX } from '../constants/validation';
function isValidEmail(e: string) {
  return EMAIL_REGEX.test(e);
}
```

**Benefits:**
- Single source of truth
- Easier to update (1 place instead of 3)
- Consistent behavior

**Size:** ~20-30 LOC

**Verification:**
```bash
npm test  # All existing tests should pass
grep -r 'EMAIL_REGEX' src/  # Should find only 1 definition
```

## Pattern 2: Isolate Side-Effect

### When to Use
- Business logic directly calls I/O (file, network, DB)
- Hard to test (need real external resources)
- Tight coupling to infrastructure

### How to Refactor

**Before:**
```typescript
// business-logic.ts
import * as fs from 'fs';

export function processConfig() {
  const config = JSON.parse(fs.readFileSync('./config.json', 'utf-8'));
  // ... business logic using config
  return result;
}
```

**After:**
```typescript
// interfaces.ts
export interface FileReader {
  readFile(path: string): string;
}

// adapters/fs-file-reader.ts
import * as fs from 'fs';
import { FileReader } from '../interfaces';

export class FsFileReader implements FileReader {
  readFile(path: string): string {
    return fs.readFileSync(path, 'utf-8');
  }
}

// business-logic.ts
import { FileReader } from './interfaces';

export function processConfig(fileReader: FileReader) {
  const configText = fileReader.readFile('./config.json');
  const config = JSON.parse(configText);
  // ... business logic using config
  return result;
}

// main.ts
import { processConfig } from './business-logic';
import { FsFileReader } from './adapters/fs-file-reader';

const result = processConfig(new FsFileReader());
```

**Benefits:**
- Business logic testable without file system
- Can inject mock FileReader in tests
- Clear separation: core vs adapter

**Size:** ~50-80 LOC

**Verification:**
```typescript
// test
const mockReader: FileReader = {
  readFile: (path) => '{"key": "value"}'
};
const result = processConfig(mockReader);
expect(result).toBe(expected);
```

## Pattern 3: Reduce Circular Imports

### When to Use
- Module A imports B, B imports A
- Build warnings about circular dependencies
- Hard to understand module dependencies

### How to Refactor

**Before:**
```typescript
// user.ts
import { hashPassword } from './auth';

export interface User {
  id: string;
  email: string;
}

export function createUser(email: string, password: string) {
  return {
    id: generateId(),
    email,
    passwordHash: hashPassword(password)
  };
}

// auth.ts
import { User } from './user';  // CIRCULAR!

export function hashPassword(password: string): string {
  // ...
}

export function authenticate(user: User, password: string): boolean {
  // ...
}
```

**After:**
```typescript
// user-types.ts (new file)
export interface User {
  id: string;
  email: string;
  passwordHash?: string;
}

// user.ts
import { User } from './user-types';
import { hashPassword } from './auth';

export function createUser(email: string, password: string): User {
  return {
    id: generateId(),
    email,
    passwordHash: hashPassword(password)
  };
}

// auth.ts
import { User } from './user-types';

export function hashPassword(password: string): string {
  // ...
}

export function authenticate(user: User, password: string): boolean {
  // ...
}
```

**Benefits:**
- No circular dependency
- Clear dependency direction: user → auth → user-types
- Easier to understand and test

**Size:** ~30-50 LOC

**Verification:**
```bash
npm run build  # Should not warn about circular deps
npm test  # All tests pass
```

## Pattern 4: Clarify Boundaries (Hexagonal/Onion)

### When to Use
- Business logic mixed with CLI/API handlers
- Core logic hard to reuse (tied to HTTP/CLI)
- Tests require setting up HTTP/CLI

### How to Refactor

**Before:**
```typescript
// cli.ts
import * as fs from 'fs';
import { parseArgs } from './args';

export function runCLI() {
  const args = parseArgs(process.argv);

  // Business logic mixed with CLI
  const config = JSON.parse(fs.readFileSync(args.config, 'utf-8'));
  const result = processData(config.data);

  console.log(result);
}
```

**After:**
```typescript
// core/processor.ts
export interface ProcessorConfig {
  data: any;
}

export function processData(config: ProcessorConfig) {
  // Pure business logic
  return result;
}

// adapters/file-config-loader.ts
import * as fs from 'fs';

export function loadConfig(path: string): ProcessorConfig {
  const raw = fs.readFileSync(path, 'utf-8');
  return JSON.parse(raw);
}

// cli.ts
import { parseArgs } from './args';
import { processData } from './core/processor';
import { loadConfig } from './adapters/file-config-loader';

export function runCLI() {
  const args = parseArgs(process.argv);
  const config = loadConfig(args.config);
  const result = processData(config);
  console.log(result);
}
```

**Benefits:**
- Core logic testable without CLI
- Core reusable in API/web/mobile
- Clear layers: CLI → Core ← Adapters

**Size:** ~60-100 LOC

**Verification:**
```typescript
// test core in isolation
import { processData } from './core/processor';

test('processData', () => {
  const config = { data: testData };
  const result = processData(config);
  expect(result).toBe(expected);
});
```

## Pattern 5: Introduce Error Type

### When to Use
- Errors thrown inconsistently (string, Error, custom)
- Hard to handle errors (don't know type)
- No error context (stack trace, code, etc.)

### How to Refactor

**Before:**
```typescript
// various files
function parseURL(url: string) {
  if (!url) throw "URL is required";  // string
  if (!isValid(url)) throw new Error("Invalid URL");  // Error
  // ...
}

function validateEmail(email: string) {
  if (!email) throw { message: "Email required" };  // object
  // ...
}
```

**After:**
```typescript
// errors.ts
export class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public context?: any
  ) {
    super(message);
    this.name = 'AppError';
  }
}

export class ValidationError extends AppError {
  constructor(message: string, context?: any) {
    super(message, 'VALIDATION_ERROR', context);
    this.name = 'ValidationError';
  }
}

// usage
import { ValidationError } from './errors';

function parseURL(url: string) {
  if (!url) throw new ValidationError("URL is required");
  if (!isValid(url)) throw new ValidationError("Invalid URL", { url });
  // ...
}

function validateEmail(email: string) {
  if (!email) throw new ValidationError("Email required");
  // ...
}

// error handling
try {
  parseURL(input);
} catch (error) {
  if (error instanceof ValidationError) {
    console.log(`Validation error: ${error.message}`, error.context);
  }
}
```

**Benefits:**
- Consistent error types
- Better error context
- Type-safe error handling

**Size:** ~40-80 LOC

**Verification:**
```typescript
test('throws ValidationError on invalid input', () => {
  expect(() => parseURL('')).toThrow(ValidationError);
});
```

## Size Guidelines by Pattern

| Pattern | Typical LOC | Files Changed | Risk |
|---------|------------|---------------|------|
| Extract constant | 10-30 | 3-5 | Low |
| Extract function | 20-50 | 3-8 | Low |
| Isolate side-effect | 50-100 | 5-10 | Medium |
| Reduce circular imports | 30-60 | 3-6 | Low |
| Clarify boundaries | 80-150 | 8-15 | Medium |
| Introduce error type | 40-100 | 5-12 | Medium |

**Rule:** If approaching 200 LOC, split into multiple PRs.

## Verification Strategies

### Strategy 1: All Tests Pass
```bash
npm test
# If all tests pass, behavior is preserved
```

**When to use:** Low-risk refactors with good test coverage

### Strategy 2: Before/After Behavior Test
```typescript
// Before refactor, capture behavior
const testCases = [
  { input: 'test@example.com', expected: true },
  { input: 'invalid', expected: false }
];

// After refactor, verify same behavior
testCases.forEach(({ input, expected }) => {
  expect(validateEmail(input)).toBe(expected);
});
```

**When to use:** Medium-risk refactors

### Strategy 3: Manual Verification
```bash
# Before refactor
npm run build && node dist/cli.js --config test.json
# Capture output

# After refactor
npm run build && node dist/cli.js --config test.json
# Verify output unchanged
```

**When to use:** No tests, high-risk refactors

### Strategy 4: Static Analysis
```bash
# Check for circular dependencies
npm run build 2>&1 | grep -i "circular"

# Check for unused imports
npx eslint . --ext .ts

# Type check
npx tsc --noEmit
```

**When to use:** All refactors (as safety net)

## Language-Specific Patterns

### TypeScript/JavaScript

**Common improvements:**
- Extract magic strings/numbers to constants
- Extract type definitions to shared file
- Introduce interface for dependency injection
- Use const enum for string unions

**Example:**
```typescript
// Before
function getStatus(code: number) {
  if (code === 200) return 'success';
  if (code === 404) return 'not found';
}

// After
enum StatusCode {
  Success = 200,
  NotFound = 404
}

const STATUS_MESSAGES = {
  [StatusCode.Success]: 'success',
  [StatusCode.NotFound]: 'not found'
} as const;

function getStatus(code: StatusCode) {
  return STATUS_MESSAGES[code];
}
```

### Python

**Common improvements:**
- Extract duplicate code to function
- Introduce dataclass for structured data
- Use Protocol for interface
- Extract constants to module

**Example:**
```python
# Before
def process_user(name, email, age):
    if not name:
        raise ValueError("Name required")
    if not email:
        raise ValueError("Email required")
    # ...

def process_admin(name, email, age, role):
    if not name:
        raise ValueError("Name required")
    if not email:
        raise ValueError("Email required")
    # ...

# After
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    email: str
    age: int

    def validate(self):
        if not self.name:
            raise ValueError("Name required")
        if not self.email:
            raise ValueError("Email required")

def process_user(person: Person):
    person.validate()
    # ...

def process_admin(person: Person, role: str):
    person.validate()
    # ...
```

### Go

**Common improvements:**
- Extract interface for dependency
- Introduce error type
- Extract duplicate error handling
- Use struct for configuration

**Example:**
```go
// Before
func ReadFile(path string) ([]byte, error) {
    data, err := ioutil.ReadFile(path)
    if err != nil {
        log.Printf("Error reading file: %v", err)
        return nil, err
    }
    return data, nil
}

func WriteFile(path string, data []byte) error {
    err := ioutil.WriteFile(path, data, 0644)
    if err != nil {
        log.Printf("Error writing file: %v", err)
        return err
    }
    return nil
}

// After
type FileReader interface {
    ReadFile(path string) ([]byte, error)
}

type FileWriter interface {
    WriteFile(path string, data []byte) error
}

type FileSystem struct{}

func (fs *FileSystem) ReadFile(path string) ([]byte, error) {
    return ioutil.ReadFile(path)
}

func (fs *FileSystem) WriteFile(path string, data []byte) error {
    return ioutil.WriteFile(path, data, 0644)
}
```

### Rust

**Common improvements:**
- Extract error type
- Use trait for interface
- Extract duplicate pattern matching
- Introduce newtype for strong typing

**Example:**
```rust
// Before
fn parse_url(s: &str) -> Result<Url, String> {
    if s.is_empty() {
        return Err("URL is empty".to_string());
    }
    // ...
}

fn parse_email(s: &str) -> Result<Email, String> {
    if s.is_empty() {
        return Err("Email is empty".to_string());
    }
    // ...
}

// After
#[derive(Debug)]
enum ValidationError {
    Empty,
    Invalid(String),
}

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            ValidationError::Empty => write!(f, "Input is empty"),
            ValidationError::Invalid(msg) => write!(f, "Invalid: {}", msg),
        }
    }
}

fn parse_url(s: &str) -> Result<Url, ValidationError> {
    if s.is_empty() {
        return Err(ValidationError::Empty);
    }
    // ...
}

fn parse_email(s: &str) -> Result<Email, ValidationError> {
    if s.is_empty() {
        return Err(ValidationError::Empty);
    }
    // ...
}
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Premature Abstraction

❌ **Bad:**
```typescript
// Extract function used only once
function validateEmailFormat(email: string) {
  return EMAIL_REGEX.test(email);
}

// Used in only 1 place
function validateEmail(email: string) {
  if (!validateEmailFormat(email)) {
    throw new Error("Invalid email");
  }
}
```

✅ **Good:**
```typescript
// Inline if used only once
function validateEmail(email: string) {
  if (!EMAIL_REGEX.test(email)) {
    throw new Error("Invalid email");
  }
}
```

**Rule:** Extract only if used 2+ times.

### Anti-Pattern 2: Over-Engineering

❌ **Bad:**
```typescript
// Introduce factory + strategy + builder for simple config
class ConfigFactory {
  create(type: string): IConfig { /* ... */ }
}
class ConfigBuilder {
  build(): IConfig { /* ... */ }
}
// 200 LOC for what should be 20 LOC
```

✅ **Good:**
```typescript
// Simple object for simple case
const config = {
  api: process.env.API_URL,
  timeout: 5000
};
```

**Rule:** Use simplest solution that works.

### Anti-Pattern 3: Refactoring Without Tests

❌ **Bad:**
```
1. Refactor 100 LOC
2. Hope it works
3. Push to prod
```

✅ **Good:**
```
1. Write tests (if none)
2. Verify tests pass
3. Refactor
4. Verify tests still pass
```

**Rule:** Never refactor without tests.

## Summary Checklist

Before proposing architectural improvement:

- [ ] Scope: <200 LOC, <10 files
- [ ] Benefit: Reduces duplication/coupling/complexity
- [ ] Risk: Low-medium (not high)
- [ ] Tests: Existing tests cover behavior
- [ ] Verification: Clear commands to verify
- [ ] API: No public API changes (unless internal)
- [ ] Dependencies: No new dependencies (unless necessary)
- [ ] Single improvement: Not "improve architecture" (too vague)
