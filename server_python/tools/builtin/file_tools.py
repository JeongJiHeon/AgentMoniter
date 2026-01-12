"""
File operation tools.
Provides read, write, glob, grep, and edit capabilities.
"""

import os
import re
import fnmatch
import aiofiles
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..base_tool import BaseTool, ToolValidationError, ToolExecutionError
from ..tool_schemas import (
    ToolResult,
    ToolParameter,
    ParameterType,
    ToolCategory,
)


class ReadFileTool(BaseTool):
    """Read the contents of a file."""

    name = "read_file"
    description = """Reads a file from the filesystem.
    Returns file contents with line numbers.
    Can read up to a specified number of lines with optional offset."""
    category = ToolCategory.FILE
    version = "1.0.0"

    parameters = [
        ToolParameter(
            name="file_path",
            type=ParameterType.STRING,
            description="The absolute path to the file to read",
            required=True,
        ),
        ToolParameter(
            name="offset",
            type=ParameterType.INTEGER,
            description="Line number to start reading from (1-indexed)",
            required=False,
            default=1,
            min_value=1,
        ),
        ToolParameter(
            name="limit",
            type=ParameterType.INTEGER,
            description="Maximum number of lines to read",
            required=False,
            default=2000,
            min_value=1,
            max_value=10000,
        ),
    ]

    async def execute(
        self,
        file_path: str,
        offset: int = 1,
        limit: int = 2000,
    ) -> ToolResult:
        """Execute the read file operation."""
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult.error_result(
                    f"File not found: {file_path}",
                    "FileNotFoundError"
                )

            if not path.is_file():
                return ToolResult.error_result(
                    f"Not a file: {file_path}",
                    "NotAFileError"
                )

            async with aiofiles.open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = await f.readlines()

            # Apply offset and limit
            start_idx = max(0, offset - 1)
            end_idx = start_idx + limit
            selected_lines = lines[start_idx:end_idx]

            # Format with line numbers
            result_lines = []
            for i, line in enumerate(selected_lines, start=offset):
                # Truncate long lines
                truncated = line.rstrip()[:2000]
                result_lines.append(f"{i:6}→{truncated}")

            content = "\n".join(result_lines)
            total_lines = len(lines)

            return ToolResult.success_result(
                content,
                total_lines=total_lines,
                shown_lines=len(selected_lines),
                file_path=file_path,
            )

        except PermissionError:
            return ToolResult.error_result(
                f"Permission denied: {file_path}",
                "PermissionError"
            )
        except UnicodeDecodeError:
            return ToolResult.error_result(
                f"Unable to decode file as text: {file_path}",
                "UnicodeDecodeError"
            )
        except Exception as e:
            return ToolResult.error_result(str(e), type(e).__name__)


class WriteFileTool(BaseTool):
    """Write content to a file."""

    name = "write_file"
    description = """Writes content to a file, creating it if necessary.
    Will overwrite existing files. Use with caution."""
    category = ToolCategory.FILE
    version = "1.0.0"
    requires_approval = True  # Writing files requires approval

    parameters = [
        ToolParameter(
            name="file_path",
            type=ParameterType.STRING,
            description="The absolute path to the file to write",
            required=True,
        ),
        ToolParameter(
            name="content",
            type=ParameterType.STRING,
            description="The content to write to the file",
            required=True,
        ),
        ToolParameter(
            name="create_dirs",
            type=ParameterType.BOOLEAN,
            description="Create parent directories if they don't exist",
            required=False,
            default=False,
        ),
    ]

    async def execute(
        self,
        file_path: str,
        content: str,
        create_dirs: bool = False,
    ) -> ToolResult:
        """Execute the write file operation."""
        try:
            path = Path(file_path)

            # Create parent directories if requested
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            elif not path.parent.exists():
                return ToolResult.error_result(
                    f"Parent directory does not exist: {path.parent}",
                    "DirectoryNotFoundError"
                )

            async with aiofiles.open(path, 'w', encoding='utf-8') as f:
                await f.write(content)

            return ToolResult.success_result(
                f"Successfully wrote {len(content)} characters to {file_path}",
                file_path=file_path,
                bytes_written=len(content.encode('utf-8')),
            )

        except PermissionError:
            return ToolResult.error_result(
                f"Permission denied: {file_path}",
                "PermissionError"
            )
        except Exception as e:
            return ToolResult.error_result(str(e), type(e).__name__)


class GlobTool(BaseTool):
    """Find files matching a glob pattern."""

    name = "glob"
    description = """Fast file pattern matching tool.
    Supports glob patterns like "**/*.py" or "src/**/*.ts".
    Returns matching file paths sorted by modification time."""
    category = ToolCategory.SEARCH
    version = "1.0.0"

    parameters = [
        ToolParameter(
            name="pattern",
            type=ParameterType.STRING,
            description="The glob pattern to match files against",
            required=True,
        ),
        ToolParameter(
            name="path",
            type=ParameterType.STRING,
            description="The directory to search in",
            required=False,
            default=".",
        ),
        ToolParameter(
            name="limit",
            type=ParameterType.INTEGER,
            description="Maximum number of results to return",
            required=False,
            default=100,
            max_value=1000,
        ),
    ]

    async def execute(
        self,
        pattern: str,
        path: str = ".",
        limit: int = 100,
    ) -> ToolResult:
        """Execute the glob operation."""
        try:
            base_path = Path(path).resolve()

            if not base_path.exists():
                return ToolResult.error_result(
                    f"Directory not found: {path}",
                    "DirectoryNotFoundError"
                )

            # Use pathlib's glob (run in executor for large dirs)
            loop = asyncio.get_event_loop()
            matches = await loop.run_in_executor(
                None,
                lambda: list(base_path.glob(pattern))
            )

            # Sort by modification time (newest first)
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Apply limit
            matches = matches[:limit]

            # Format results
            results = [str(p) for p in matches]

            return ToolResult.success_result(
                "\n".join(results) if results else "No matches found",
                total_matches=len(results),
                pattern=pattern,
                base_path=str(base_path),
            )

        except Exception as e:
            return ToolResult.error_result(str(e), type(e).__name__)


class GrepTool(BaseTool):
    """Search for patterns in files."""

    name = "grep"
    description = """Search tool for finding patterns in file contents.
    Supports regex patterns and file type filtering.
    Returns matching lines with context."""
    category = ToolCategory.SEARCH
    version = "1.0.0"

    parameters = [
        ToolParameter(
            name="pattern",
            type=ParameterType.STRING,
            description="The regex pattern to search for",
            required=True,
        ),
        ToolParameter(
            name="path",
            type=ParameterType.STRING,
            description="File or directory to search in",
            required=False,
            default=".",
        ),
        ToolParameter(
            name="glob_pattern",
            type=ParameterType.STRING,
            description="Glob pattern to filter files (e.g., '*.py')",
            required=False,
            default="**/*",
        ),
        ToolParameter(
            name="context_lines",
            type=ParameterType.INTEGER,
            description="Number of context lines before and after match",
            required=False,
            default=0,
            max_value=10,
        ),
        ToolParameter(
            name="case_insensitive",
            type=ParameterType.BOOLEAN,
            description="Case insensitive search",
            required=False,
            default=False,
        ),
        ToolParameter(
            name="limit",
            type=ParameterType.INTEGER,
            description="Maximum number of matches to return",
            required=False,
            default=100,
            max_value=500,
        ),
    ]

    async def execute(
        self,
        pattern: str,
        path: str = ".",
        glob_pattern: str = "**/*",
        context_lines: int = 0,
        case_insensitive: bool = False,
        limit: int = 100,
    ) -> ToolResult:
        """Execute the grep operation."""
        try:
            # Compile regex
            flags = re.IGNORECASE if case_insensitive else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult.error_result(
                    f"Invalid regex pattern: {e}",
                    "RegexError"
                )

            base_path = Path(path).resolve()

            if not base_path.exists():
                return ToolResult.error_result(
                    f"Path not found: {path}",
                    "PathNotFoundError"
                )

            # Find files to search
            if base_path.is_file():
                files = [base_path]
            else:
                loop = asyncio.get_event_loop()
                files = await loop.run_in_executor(
                    None,
                    lambda: [f for f in base_path.glob(glob_pattern) if f.is_file()]
                )

            matches = []
            match_count = 0

            for file_path in files:
                if match_count >= limit:
                    break

                try:
                    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = await f.readlines()

                    for i, line in enumerate(lines):
                        if regex.search(line):
                            # Get context
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)

                            context = []
                            for j in range(start, end):
                                prefix = ">" if j == i else " "
                                context.append(f"{j + 1:4}{prefix}{lines[j].rstrip()}")

                            matches.append({
                                "file": str(file_path),
                                "line": i + 1,
                                "content": "\n".join(context),
                            })

                            match_count += 1
                            if match_count >= limit:
                                break

                except (PermissionError, UnicodeDecodeError):
                    continue

            # Format output
            if not matches:
                return ToolResult.success_result(
                    "No matches found",
                    total_matches=0,
                    pattern=pattern,
                )

            output_lines = []
            for match in matches:
                output_lines.append(f"--- {match['file']}:{match['line']} ---")
                output_lines.append(match['content'])
                output_lines.append("")

            return ToolResult.success_result(
                "\n".join(output_lines),
                total_matches=len(matches),
                pattern=pattern,
                files_searched=len(files),
            )

        except Exception as e:
            return ToolResult.error_result(str(e), type(e).__name__)


class EditFileTool(BaseTool):
    """Edit a file by replacing text."""

    name = "edit_file"
    description = """Performs exact string replacements in files.
    Replaces old_string with new_string in the specified file.
    Can optionally replace all occurrences."""
    category = ToolCategory.FILE
    version = "1.0.0"
    requires_approval = True

    parameters = [
        ToolParameter(
            name="file_path",
            type=ParameterType.STRING,
            description="The absolute path to the file to modify",
            required=True,
        ),
        ToolParameter(
            name="old_string",
            type=ParameterType.STRING,
            description="The text to replace",
            required=True,
        ),
        ToolParameter(
            name="new_string",
            type=ParameterType.STRING,
            description="The replacement text",
            required=True,
        ),
        ToolParameter(
            name="replace_all",
            type=ParameterType.BOOLEAN,
            description="Replace all occurrences (default: first only)",
            required=False,
            default=False,
        ),
    ]

    async def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> ToolResult:
        """Execute the edit operation."""
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult.error_result(
                    f"File not found: {file_path}",
                    "FileNotFoundError"
                )

            # Read current content
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                content = await f.read()

            # Check if old_string exists
            if old_string not in content:
                return ToolResult.error_result(
                    f"String not found in file: {old_string[:50]}...",
                    "StringNotFoundError"
                )

            # Check uniqueness if not replace_all
            if not replace_all and content.count(old_string) > 1:
                return ToolResult.error_result(
                    f"String occurs {content.count(old_string)} times. "
                    "Use replace_all=True or provide more context.",
                    "AmbiguousMatchError"
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Write back
            async with aiofiles.open(path, 'w', encoding='utf-8') as f:
                await f.write(new_content)

            return ToolResult.success_result(
                f"Successfully replaced {replacements} occurrence(s)",
                file_path=file_path,
                replacements=replacements,
            )

        except PermissionError:
            return ToolResult.error_result(
                f"Permission denied: {file_path}",
                "PermissionError"
            )
        except Exception as e:
            return ToolResult.error_result(str(e), type(e).__name__)
