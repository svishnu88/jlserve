# Issue #15: Add `jlserve build` Command for Containerized Deployments

We are working on this issue. https://github.com/svishnu88/jlserve/issues/15

## High-Level Task List

### Phase 1: Environment Variable Support ✅
- [x] Add environment variable validation utilities
  - [x] `JLSERVE_CACHE_DIR` validator (required for both build and dev)
  - [x] `UV_CACHE_DIR` - decided not needed (UV handles internally)
- [x] Create configuration module for cache directory management
- [x] Add tests for environment variable validation

**Implementation:**
- Created `jlserve/config.py` with `get_jlserve_cache_dir()` function
- Added `CacheConfigError` exception to `jlserve/exceptions.py`
- Created comprehensive tests in `jlserve/config_test.py`
- All tests passing (4/4 config tests, 105/105 total tests)

### Phase 2: Download Weights Lifecycle Method ✅
- [x] Update decorator/validator to recognize `download_weights()` method
  - [x] Add validation that method exists on app class
  - [x] Add validation that method has correct signature (no params, no return)
  - [x] Make it required for all apps (not just build)
- [x] Document `download_weights()` pattern in docstrings
- [x] Add tests for method presence/signature validation

**Implementation:**
- Created shared `_validate_lifecycle_method()` helper in `jlserve/validator.py`
- Added `validate_setup_method()` and `validate_download_weights_method()` validators
- Both methods now required for all apps (enforced by `validate_app()`)
- Added 24 comprehensive tests covering all validation scenarios
- Updated all existing test apps (38 apps) to include both lifecycle methods
- Validators ensure: method exists, is callable, only accepts 'self', returns None
- All tests passing (129/129 total tests)

### Phase 3: Build Command Implementation ✅
- [x] Create `jlserve build` CLI command in cli.py
  - [x] Add Typer command definition
  - [x] Accept file path argument
  - [x] Validate JLSERVE_CACHE_DIR environment variable
- [x] Implement build workflow:
  - [x] Extract requirements from Python file (scan imports/app)
  - [x] Install dependencies using `uv pip install`
  - [x] Load app class and call `download_weights()`
  - [x] ~~Optionally validate by calling `setup()`~~ (deferred - not needed for Phase 3)
- [x] Add proper error handling and user feedback
- [x] Add tests for build command

**Implementation:**
- Created `jlserve/cli_utils.py` with extracted helper functions:
  - `validate_python_file()` - File validation
  - `install_requirements()` - Dependency installation
  - `load_app_class()` - App loading and registration
- Refactored `dev` command to use shared utilities
- Implemented `build` command with:
  - Cache directory validation via `get_jlserve_cache_dir()`
  - Requirements installation (reuses existing logic)
  - App validation via `validate_app()`
  - App instantiation and `download_weights()` call
  - Clear user feedback with ✓ checkmarks
- Added 7 comprehensive tests in `TestBuildCommand` class:
  - test_build_success - Happy path
  - test_build_file_not_found - File validation
  - test_build_file_must_be_python - File type validation
  - test_build_cache_dir_not_set - Cache directory requirement
  - test_build_download_weights_fails - Error handling
  - test_build_installs_requirements - Requirements installation
  - test_build_validates_app_structure - App validation
- All tests passing (124/124 total tests)

### Phase 4: Update Dev Command ✅
- [x] Modify `jlserve dev` to check JLSERVE_CACHE_DIR and marker file
  - [x] Check JLSERVE_CACHE_DIR is set (hard error if missing)
  - [x] Check for `.jlserve-build-complete` marker file (hard error if missing)
  - [x] Provide clear error messages guiding user to run `jlserve build` first
- [x] Update `jlserve build` to create marker file after successful build
  - [x] Create `.jlserve-build-complete` marker in cache directory
  - [x] Only create marker after `download_weights()` succeeds
- [x] Add tests for marker file validation
  - [x] test_dev_fails_when_cache_dir_not_set
  - [x] test_dev_fails_when_marker_file_missing
  - [x] test_dev_succeeds_when_marker_file_exists
  - [x] test_build_creates_marker_file
- [x] Fix existing tests to work with marker file requirement
  - [x] Updated all dev command tests to set up cache with marker
  - [x] Updated all build command tests to use real temp directories

**Implementation:**
- Modified `jlserve/cli.py` dev command (lines 37-64):
  - Added cache directory validation with helpful error messages
  - Added marker file check with guidance to run `jlserve build`
  - Exits with code 1 if either check fails
- Modified `jlserve/cli.py` build command (lines 148-151):
  - Creates `.jlserve-build-complete` marker after successful `download_weights()`
  - Marker indicates build completed successfully
- Added comprehensive tests in `jlserve/cli_test.py`:
  - New test class `TestDevCommandMarkerValidation` with 3 marker validation tests
  - New test `test_build_creates_marker_file` in `TestBuildCommand`
  - Fixed 10 existing tests to set up cache with marker file
- All tests passing (128/128 total tests)

**Design Decision: Marker File Approach** ✅ DECIDED
- Uses `.jlserve-build-complete` marker file in cache directory
- Performance impact: ~1 microsecond (negligible)
- Clear separation: build creates marker, dev checks marker
- Simple and reliable validation mechanism

### Phase 5: Documentation
- [ ] Update README with `jlserve build` usage
- [ ] Document environment variables (JLSERVE_CACHE_DIR)


## Key Design Decisions to Validate

1. **Should `download_weights()` be required for all apps or only when using `build`?** ✅ DECIDED
   - Decision: Required for all apps (enforced by validator)
   - Rationale: Simplifies the pattern and makes it consistent

2. **Should `setup()` validation be mandatory or optional in build?**
   - Proposal: Optional with --validate flag

3. **Error handling for missing cache directory** ✅ DECIDED
   - Both Build and Dev: Hard error (required)
   - Rationale: Simpler, more predictable behavior. Cache dir should always be set.

## Success Criteria

- [ ] `jlserve build app.py` successfully downloads dependencies and weights to cache
- [ ] `jlserve dev app.py` reuses cached weights without re-downloading
- [ ] Validation catches missing `download_weights()` method when using build
- [ ] Documentation clearly explains the containerized deployment pattern
- [ ] All tests pass including integration tests
