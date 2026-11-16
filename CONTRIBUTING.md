# Contributing to Realtime Voice Assistant Local 🎙️

Thank you for your interest in improving the project! We welcome contributions from the community: new voice blend recipes, custom tools, foreign language translations, or performance optimizations for local inference.

---

## 🛠️ How to Contribute

### 1. Adding a Custom Modular Tool (`custom_tools/`)
The easiest way to contribute is by adding a new modular tool:
1. Create a Python file inside `custom_tools/` (e.g. `custom_tools/weather_local.py`).
2. Define the tool metadata and execution function:
   ```python
   TOOL_NAME = "my_tool"
   AUTHOR = "Your Name"
   DESCRIPTION = "Brief summary of what this tool does."
   TRIGGERS = ["trigger phrase 1", "trigger phrase 2"]

   def execute(user_text: str, lang: str = "en") -> str:
       # Return the spoken response string
       return "Result to be spoken aloud by Kokoro."
   ```
3. Test your tool locally. The engine will automatically discover and load it without modifying server code!

### 2. Adding a Persona (`personas/`)
To add a new character profile:
1. Create a JSON file in `personas/` (e.g. `personas/socrates.json`).
2. Provide `name`, `emoji`, `voice_name`, `speech_speed`, and `system_prompt`.

### 3. Reporting Bugs & Feature Requests
- Use the official [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md).
- Use the [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md).

---

## 🧪 Running Tests Before Submitting PR
Ensure all unit and end-to-end tests pass before opening a Pull Request:
```bash
python tests/run_all_tests.py
```
A green test suite is required by GitHub Actions CI for all PRs.
