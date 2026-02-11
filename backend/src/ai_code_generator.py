"""
AI Code Generation Service - generates and executes Python code for dynamic rules.

Uses Azure OpenAI (primary) or OpenRouter (fallback) to generate Python code
based on natural language prompts, with safe execution in a sandboxed environment.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

import pandas as pd

from src.ai_service import AIProvider, AIService

logger = logging.getLogger(__name__)


class CodeGenerationStatus(str, Enum):
    """Status of code generation."""

    SUCCESS = "success"
    GENERATION_ERROR = "generation_error"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT_ERROR = "timeout_error"


@dataclass
class GeneratedCode:
    """Container for AI-generated code."""

    code: str
    prompt: str
    model: str
    provider: AIProvider
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    validation_passed: bool = False
    validation_errors: list[str] = field(default_factory=list)
    tokens_used: int = 0


@dataclass
class CodeExecutionResult:
    """Result of code execution."""

    success: bool
    result: Any
    status: CodeGenerationStatus
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    generated_code: Optional[GeneratedCode] = None


class SafeCodeValidator:
    """Validates generated code for safety before execution."""

    # Forbidden imports that could be dangerous
    FORBIDDEN_IMPORTS = {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
        "requests",
        "urllib",
        "http",
        "ftplib",
        "smtplib",
        "pickle",
        "marshal",
        "shelve",
        "dbm",
        "sqlite3",
        "builtins",
        "__builtins__",
        "importlib",
        "ctypes",
        "multiprocessing",
        "threading",
        "asyncio",
        "concurrent",
    }

    # Forbidden function calls
    FORBIDDEN_CALLS = {
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "__import__",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
    }

    # Forbidden AST node types
    FORBIDDEN_NODES = {
        ast.Import,
        ast.ImportFrom,
        ast.Global,
        ast.Nonlocal,
        ast.AsyncFunctionDef,
        ast.AsyncFor,
        ast.AsyncWith,
        ast.Await,
    }

    @classmethod
    def validate(cls, code: str) -> tuple[bool, list[str]]:
        """Validate code for safety.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check for forbidden imports via string matching first
        for forbidden in cls.FORBIDDEN_IMPORTS:
            if re.search(rf"\bimport\s+{forbidden}\b", code):
                errors.append(f"Forbidden import: {forbidden}")
            if re.search(rf"\bfrom\s+{forbidden}\b", code):
                errors.append(f"Forbidden import from: {forbidden}")

        # Check for forbidden function calls
        for forbidden in cls.FORBIDDEN_CALLS:
            if re.search(rf"\b{forbidden}\s*\(", code):
                errors.append(f"Forbidden function call: {forbidden}")

        # Parse and validate AST
        try:
            tree = ast.parse(code)
            ast_errors = cls._validate_ast(tree)
            errors.extend(ast_errors)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")

        return len(errors) == 0, errors

    @classmethod
    def _validate_ast(cls, tree: ast.AST) -> list[str]:
        """Validate AST nodes.

        Args:
            tree: AST to validate

        Returns:
            List of error messages
        """
        errors = []

        for node in ast.walk(tree):
            # Check for forbidden node types
            if type(node) in cls.FORBIDDEN_NODES:
                errors.append(f"Forbidden construct: {type(node).__name__}")

            # Check for attribute access to forbidden modules
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    if node.value.id in cls.FORBIDDEN_IMPORTS:
                        errors.append(f"Access to forbidden module: {node.value.id}")

            # Check for forbidden function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.FORBIDDEN_CALLS:
                        errors.append(f"Forbidden function call: {node.func.id}")

        return errors


class SafeExecutionEnvironment:
    """Provides a sandboxed environment for code execution."""

    # Safe built-in functions
    SAFE_BUILTINS = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "pow": pow,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
        "True": True,
        "False": False,
        "None": None,
    }

    @classmethod
    def create_safe_globals(
        cls, row: pd.Series, df: Optional[pd.DataFrame] = None
    ) -> dict[str, Any]:
        """Create safe globals for code execution.

        Args:
            row: Current row being evaluated
            df: Full dataframe (optional, for aggregate operations)

        Returns:
            Dictionary of safe globals
        """
        safe_globals = {
            "__builtins__": cls.SAFE_BUILTINS,
            "row": row,
            "pd": pd,  # Allow pandas for data operations
        }

        if df is not None:
            safe_globals["df"] = df

        # Add math functions
        import math

        safe_math = {
            "sqrt": math.sqrt,
            "ceil": math.ceil,
            "floor": math.floor,
            "log": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
        }
        safe_globals.update(safe_math)

        # Add datetime for date operations
        from datetime import datetime, timedelta

        safe_globals["datetime"] = datetime
        safe_globals["timedelta"] = timedelta

        return safe_globals

    @classmethod
    def execute(
        cls,
        code: str,
        row: pd.Series,
        df: Optional[pd.DataFrame] = None,
        timeout_seconds: float = 5.0,
    ) -> tuple[bool, Any, Optional[str]]:
        """Execute code in a safe environment.

        Args:
            code: Python code to execute
            row: Current row being evaluated
            df: Full dataframe (optional)
            timeout_seconds: Execution timeout

        Returns:
            Tuple of (success, result, error_message)
        """
        import signal
        import time

        start_time = time.time()

        # Create safe execution environment
        safe_globals = cls.create_safe_globals(row, df)
        safe_locals: dict[str, Any] = {}

        try:
            # Compile the code
            compiled = compile(code, "<ai_generated>", "exec")

            # Execute with timeout (Unix only)
            def timeout_handler(signum, frame):
                raise TimeoutError("Code execution timed out")

            # Set timeout if on Unix
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout_seconds))
            except (AttributeError, ValueError):
                # Windows or signal not available
                old_handler = None

            try:
                exec(compiled, safe_globals, safe_locals)
            finally:
                if old_handler is not None:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)

            # Get the result (expect a 'result' variable to be set)
            result = safe_locals.get("result", None)

            execution_time = (time.time() - start_time) * 1000

            return True, result, None

        except TimeoutError as e:
            return False, None, f"Execution timeout: {e}"
        except Exception as e:
            return False, None, f"Execution error: {type(e).__name__}: {e}"


class AICodeGenerator:
    """Generates and executes Python code using AI services."""

    CODE_GENERATION_PROMPT = """You are a Python code generator for a maintenance work categorization system.
Generate a small Python function body that evaluates a row of maintenance data.

## Context
You have access to:
- `row`: A pandas Series containing the current data row
- `df`: The full pandas DataFrame (optional, for aggregate operations)
- Standard Python math functions (sqrt, ceil, floor, log, etc.)
- datetime and timedelta for date operations
- pandas (pd) for data operations

## Task
{task_description}

## Data Columns Available
{column_info}

## Requirements
1. Write ONLY the function body (no imports, no function definition)
2. Set a variable called `result` to True if the condition is met, False otherwise
3. Handle missing/null values gracefully using pd.isna() or pd.notna()
4. Keep the code simple and under 20 lines
5. Do NOT use: eval, exec, open, import, os, sys, subprocess, or any file/network operations

## Example Output Format
```python
# Check if priority is high and cost is within budget
priority = row.get('Priority', '')
cost = row.get('Cost Estimate', 0)
budget = 10000

result = (priority == 'High' and cost <= budget)
```

## Your Code
Generate code for the following task:
{task_description}

Respond with ONLY the Python code, no explanations:"""

    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        provider: AIProvider = AIProvider.AZURE_OPENAI,
    ):
        """Initialize the code generator.

        Args:
            ai_service: Existing AI service instance
            provider: AI provider to use if creating new service
        """
        if ai_service:
            self._ai_service = ai_service
        else:
            self._ai_service = AIService(provider=provider)

        self._validator = SafeCodeValidator()
        self._execution_env = SafeExecutionEnvironment()

        # Cache for generated code
        self._code_cache: dict[str, GeneratedCode] = {}

    def generate_code(
        self,
        prompt: str,
        column_info: Optional[dict[str, str]] = None,
        use_cache: bool = True,
    ) -> GeneratedCode:
        """Generate Python code from a natural language prompt.

        Args:
            prompt: Natural language description of the rule
            column_info: Dictionary mapping column names to descriptions
            use_cache: Whether to use cached code for identical prompts

        Returns:
            GeneratedCode instance
        """
        # Check cache
        cache_key = prompt
        if use_cache and cache_key in self._code_cache:
            return self._code_cache[cache_key]

        # Format column info
        if column_info:
            col_info_str = "\n".join(
                f"- {name}: {desc}" for name, desc in column_info.items()
            )
        else:
            col_info_str = "Column information not provided. Use row.get('column_name', default) to access values safely."

        # Build the full prompt
        full_prompt = self.CODE_GENERATION_PROMPT.format(
            task_description=prompt,
            column_info=col_info_str,
        )

        # Call AI service
        self._ai_service._init_client()

        try:
            if self._ai_service.provider == AIProvider.AZURE_OPENAI:
                response = self._ai_service._client.chat.completions.create(
                    model=self._ai_service._get_azure_deployment(),
                    max_tokens=500,
                    temperature=0.2,  # Low temperature for more deterministic code
                    messages=[{"role": "user", "content": full_prompt}],
                )
            else:
                response = self._ai_service._client.chat.completions.create(
                    model=self._ai_service._get_model(),
                    max_tokens=500,
                    temperature=0.2,
                    messages=[{"role": "user", "content": full_prompt}],
                    extra_headers={
                        "HTTP-Referer": "https://mwcs.local",
                        "X-Title": "MWCS",
                    },
                )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Extract code from response (handle markdown code blocks)
            code = self._extract_code(content)

            # Validate the code
            is_valid, validation_errors = self._validator.validate(code)

            generated = GeneratedCode(
                code=code,
                prompt=prompt,
                model=self._ai_service._get_model(),
                provider=self._ai_service.provider,
                validation_passed=is_valid,
                validation_errors=validation_errors,
                tokens_used=tokens_used,
            )

            # Cache if valid
            if is_valid and use_cache:
                self._code_cache[cache_key] = generated

            return generated

        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return GeneratedCode(
                code="",
                prompt=prompt,
                model=self._ai_service._get_model(),
                provider=self._ai_service.provider,
                validation_passed=False,
                validation_errors=[f"Generation error: {e}"],
            )

    def _extract_code(self, content: str) -> str:
        """Extract Python code from AI response.

        Args:
            content: Raw AI response

        Returns:
            Extracted Python code
        """
        # Try to extract from markdown code block
        code_block_match = re.search(r"```(?:python)?\s*(.*?)```", content, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()

        # Otherwise return the content as-is (stripped)
        return content.strip()

    def execute_generated_code(
        self,
        generated_code: GeneratedCode,
        row: pd.Series,
        df: Optional[pd.DataFrame] = None,
    ) -> CodeExecutionResult:
        """Execute previously generated code.

        Args:
            generated_code: GeneratedCode instance
            row: Current row to evaluate
            df: Full dataframe (optional)

        Returns:
            CodeExecutionResult
        """
        import time

        start_time = time.time()

        # Check if code is valid
        if not generated_code.validation_passed:
            return CodeExecutionResult(
                success=False,
                result=None,
                status=CodeGenerationStatus.VALIDATION_ERROR,
                error_message="; ".join(generated_code.validation_errors),
                generated_code=generated_code,
            )

        # Execute the code
        success, result, error = self._execution_env.execute(
            generated_code.code, row, df
        )

        execution_time = (time.time() - start_time) * 1000

        if success:
            return CodeExecutionResult(
                success=True,
                result=result,
                status=CodeGenerationStatus.SUCCESS,
                execution_time_ms=execution_time,
                generated_code=generated_code,
            )
        else:
            return CodeExecutionResult(
                success=False,
                result=None,
                status=CodeGenerationStatus.EXECUTION_ERROR,
                error_message=error,
                execution_time_ms=execution_time,
                generated_code=generated_code,
            )

    def generate_and_execute(
        self,
        prompt: str,
        row: pd.Series,
        df: Optional[pd.DataFrame] = None,
        column_info: Optional[dict[str, str]] = None,
    ) -> CodeExecutionResult:
        """Generate and execute code in one step.

        Args:
            prompt: Natural language description
            row: Current row to evaluate
            df: Full dataframe (optional)
            column_info: Column descriptions

        Returns:
            CodeExecutionResult
        """
        generated = self.generate_code(prompt, column_info)

        if not generated.validation_passed:
            return CodeExecutionResult(
                success=False,
                result=None,
                status=CodeGenerationStatus.VALIDATION_ERROR,
                error_message="; ".join(generated.validation_errors),
                generated_code=generated,
            )

        return self.execute_generated_code(generated, row, df)

    def clear_cache(self) -> None:
        """Clear the code cache."""
        self._code_cache.clear()

    def get_cached_code(self, prompt: str) -> Optional[GeneratedCode]:
        """Get cached code for a prompt.

        Args:
            prompt: The original prompt

        Returns:
            Cached GeneratedCode or None
        """
        return self._code_cache.get(prompt)

    def validate_code(self, code: str) -> tuple[bool, list[str]]:
        """Validate code without executing it.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, list of errors)
        """
        return self._validator.validate(code)


# Factory function for creating code generator with proper AI service
def create_code_generator(
    provider: AIProvider = AIProvider.AZURE_OPENAI,
    fallback_provider: Optional[AIProvider] = AIProvider.OPENROUTER,
) -> AICodeGenerator:
    """Create an AICodeGenerator with optional fallback.

    Args:
        provider: Primary AI provider
        fallback_provider: Fallback provider if primary fails

    Returns:
        Configured AICodeGenerator
    """
    try:
        ai_service = AIService(provider=provider)
        ai_service.test_connection()
        return AICodeGenerator(ai_service=ai_service)
    except Exception as e:
        logger.warning(f"Primary provider {provider} failed: {e}")

        if fallback_provider:
            try:
                ai_service = AIService(provider=fallback_provider)
                ai_service.test_connection()
                logger.info(f"Using fallback provider: {fallback_provider}")
                return AICodeGenerator(ai_service=ai_service)
            except Exception as fallback_e:
                logger.error(f"Fallback provider also failed: {fallback_e}")

        # Return generator anyway, will fail on actual use
        return AICodeGenerator(provider=provider)
