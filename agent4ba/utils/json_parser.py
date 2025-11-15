"""Utilities for robust JSON parsing from LLM responses.

This module provides tools to extract and parse JSON from potentially "polluted"
responses that may contain markdown code blocks, extra text, or other artifacts.
"""

import json
import re
from typing import Any, Dict, List, Union


class JSONParsingError(ValueError):
    """Exception raised when JSON extraction or parsing fails.

    This exception is raised when the input text doesn't contain valid JSON
    or when the JSON structure is malformed.
    """

    pass


def extract_and_parse_json(response_text: str) -> Union[Dict[str, Any], List[Any]]:
    """Extract and parse JSON from a potentially polluted text response.

    This function handles various formats of LLM responses:
    - Pure JSON: {"key": "value"}
    - Markdown code blocks: ```json\\n{"key": "value"}\\n```
    - Generic code blocks: ```\\n{"key": "value"}\\n```
    - Text with embedded JSON: "Here is the result: {"key": "value"}"

    The function uses multiple strategies to extract JSON:
    1. Try to find markdown code blocks (```json or ```)
    2. Try to find JSON objects/arrays by locating { } or [ ]
    3. Try to parse the entire text as-is

    Args:
        response_text: The raw text response from an LLM that should contain JSON

    Returns:
        The parsed JSON structure (dict or list)

    Raises:
        JSONParsingError: If no valid JSON could be extracted or parsed

    Examples:
        >>> extract_and_parse_json('{"key": "value"}')
        {'key': 'value'}

        >>> extract_and_parse_json('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}

        >>> extract_and_parse_json('Here is: {"key": "value"}')
        {'key': 'value'}
    """
    if not response_text or not response_text.strip():
        raise JSONParsingError("Empty or whitespace-only response text")

    # Strategy 1: Try to extract from markdown code blocks
    # Pattern matches: ```json\n...\n``` or ```\n...\n```
    code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    code_block_match = re.search(code_block_pattern, response_text, re.DOTALL)

    if code_block_match:
        json_text = code_block_match.group(1).strip()
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise JSONParsingError(
                f"Found markdown code block but JSON parsing failed: {e}. "
                f"Extracted text: {json_text[:200]}..."
            )

    # Strategy 2: Try to extract JSON object or array by finding delimiters
    # Look for outermost { } or [ ]
    # IMPORTANT: Check which delimiter appears first to handle arrays correctly
    json_text = None

    # Determine which delimiter comes first (array or object)
    first_bracket = response_text.find("[")
    first_brace = response_text.find("{")

    # If array delimiter appears before object delimiter (or object delimiter not found)
    if first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
        try:
            start_index = first_bracket
            end_index = response_text.rindex("]") + 1
            json_text = response_text[start_index:end_index]
        except ValueError:
            pass  # Mismatched brackets

    # Otherwise, try to find JSON object (starts with {)
    if not json_text and first_brace != -1:
        try:
            start_index = first_brace
            end_index = response_text.rindex("}") + 1
            json_text = response_text[start_index:end_index]
        except ValueError:
            pass  # Mismatched braces

    if json_text:
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise JSONParsingError(
                f"Found JSON-like structure but parsing failed: {e}. "
                f"Extracted text: {json_text[:200]}..."
            )

    # Strategy 3: Try to parse the entire text as-is (last resort)
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        # All strategies failed
        raise JSONParsingError(
            f"Could not extract valid JSON from response. "
            f"JSON decode error: {e}. "
            f"Response preview: {response_text[:200]}..."
        )
