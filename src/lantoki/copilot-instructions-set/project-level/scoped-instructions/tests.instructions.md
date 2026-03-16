---
applyTo: "**/tests/**/*.py"
description: Rules for writing unit tests using Pytest.
---
# Python Testing Best Practices

## I. Organization and File Structure
* **Rule 1: Standardize file location and naming.** Name all test files following the `test_*.py` pattern. Place them inside a `tests` directory located at the exact same level as the source code being tested.
* **Rule 2: Organize shared setups logically.** Place global fixtures, hooks, and setups applicable to all tests in a `conftest.py` file at the root of the `tests` directory. If you have utilities or fixtures specific to a certain group of tests, isolate them within a `helpers/` directory.

---

## II. Anatomy and Naming Conventions
* **Rule 3: Enforce Given-When-Then in function names.** Encode the testing scenario directly into the test function's name using the Given-When-Then pattern (e.g., `def test_given_active_user_when_deleting_then_status_is_removed():`).
* **Rule 4: Separate logical stages visually.** Inside the test body, absolutely do not use the words "Given", "When", or "Then". Instead, separate the setup (given), execution (when), and assertion (then) phases strictly by using blank lines.
* **Rule 5: Strictly no comments.** Your code must be completely self-explanatory. Rely exclusively on clear, descriptive naming for variables, functions, and classes. If a test's logic is non-obvious, you must refactor the code for readability rather than adding a comment to explain it.

---

## III. Test Design and Execution
* **Rule 6: Test only the public interface.** Never call private methods or functions directly. Validate all internal logic, edge cases, and setups exclusively through the module's public API. This maintains encapsulation and prevents your tests from becoming tightly coupled to implementation details.
* **Rule 7: Guarantee isolation and determinism.** Tests must be independent, fast, and repeatable. They must never share state, assume the presence of resources created by other tests, or rely on external timing factors that could introduce flakiness. 
* **Rule 8: Maximize coverage through parameterization.** Explicitly design tests to validate expected behavior and catch bugs across all positive, negative, and edge-case scenarios. Use parameterization (like `@pytest.mark.parametrize`) to loop through variations, avoiding code duplication and improving readability.

---

## IV. Tools
* **Rule 9: Use Pytest.** Use Pytest as the testing framework for its powerful features, including fixtures, parameterization, and rich assertion introspection. Avoid using `unittest` or other testing frameworks to maintain consistency across the codebase.