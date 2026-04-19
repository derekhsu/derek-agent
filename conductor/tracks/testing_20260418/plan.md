# Track Plan

## Phase 1: Establish test baseline and target high-risk modules
- [ ] Task: Inventory current startup-critical modules and define the initial regression surface
  - [ ] Sub-task: Review current tests and identify missing coverage in `src/core/` and `src/interface/`
  - [ ] Sub-task: Document the first batch of target modules and failure modes
- [ ] Task: Add focused tests for configuration or runtime initialization paths
  - [ ] Sub-task: Write failing tests for configuration loading or agent bootstrap behavior
  - [ ] Sub-task: Implement minimal fixes or test scaffolding until tests pass
- [ ] Task: Conductor - User Manual Verification 'Establish test baseline and target high-risk modules' (Protocol in workflow.md)

## Phase 2: Add interface startup coverage and verify repeatable execution
- [ ] Task: Add non-networked tests for TUI startup or main screen composition
  - [ ] Sub-task: Write failing tests that exercise the app or screen initialization path
  - [ ] Sub-task: Implement minimal code or mocks needed to make the tests pass
- [ ] Task: Record and verify repeatable local test commands for contributors
  - [ ] Sub-task: Run `pytest` and coverage commands in non-interactive mode
  - [ ] Sub-task: Update docs or plan details if the real commands differ from assumptions
- [ ] Task: Conductor - User Manual Verification 'Add interface startup coverage and verify repeatable execution' (Protocol in workflow.md)
