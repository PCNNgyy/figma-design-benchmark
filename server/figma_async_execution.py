"""Await a model's single async IIFE instead of silently discarding its promise."""
import re

START=re.compile(r'^\(\s*async\s*(?:(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>|function\b)')
END=re.compile(r'\)\s*\(\s*\)\s*;?\s*$')

def await_async_iife(code):
    source=str(code or '').strip()
    if not START.match(source) or not END.search(source):
        return str(code or '')
    # An expression wrapper fails at parse time if this is not a single
    # expression; it never guesses at or rewrites the contents of the function.
    return 'return await ('+source.rstrip(';').rstrip()+');'
