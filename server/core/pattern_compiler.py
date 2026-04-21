"""
Convert log4j2 layout patterns to Python regex patterns.

Supported directives:
  %d / %d{...}              → timestamp
  %p / %5p / %-5p           → level
  %c / %c{n}                → logger (full name)
  %C                        → class name (mapped to logger)
  %t / %T                   → thread / thread-id
  %m                        → message
  %ex / %n                  → skipped (stack traces handled by parser)
  %X{correlationId}         → correlation_id  (also Correlation-ID)
  %X{tenantDomain}          → tenant_domain
  %X{apiName}               → app_name
  %X{ip} / %X{host}         → skipped (no LogEntry field)
  [%tenantId]               → tid  (WSO2 custom)
  [%appName]                → app_name  (WSO2 custom)

Literal characters are escaped; whitespace sequences become \\s*.
"""
import re
from typing import Optional

# Match %[modifier]name[{option}]
_DIRECTIVE_RE = re.compile(r'%(-?\d+(?:\.\d+)?)?([a-zA-Z]+)(?:\{([^}]*)\})?')

# directive name (lowercased) → (LogEntry field, inner regex)
_FIELD_MAP: dict[str, tuple[str, str]] = {
    # timestamp
    'd':        ('timestamp',       r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[,\.]\d+'),
    'date':     ('timestamp',       r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[,\.]\d+'),
    # level
    'p':        ('level',           r'\w+'),
    'level':    ('level',           r'\w+'),
    'le':       ('level',           r'\w+'),
    # logger (full or short)
    'c':        ('logger',          r'[^\s\{\}\[\]]+'),
    'logger':   ('logger',          r'[^\s\{\}\[\]]+'),
    'lo':       ('logger',          r'[^\s\{\}\[\]]+'),
    'c':        ('logger',          r'[^\s\{\}\[\]]+'),
    # class name → treated as logger
    'class':    ('logger',          r'[^\s\{\}\[\]]+'),
    # thread / thread-id (%T is numeric thread ID, treated same as thread name)
    't':        ('thread',          r'[^\s\[\]|]+'),
    'thread':   ('thread',          r'[^\s\[\]|]+'),
    'tn':       ('thread',          r'[^\s\[\]|]+'),
    # message (greedy, dotall applied at compile time)
    'm':        ('message',         r'.*'),
    'msg':      ('message',         r'.*'),
    'message':  ('message',         r'.*'),
    # WSO2 custom context props
    'tenantid': ('tid',             r'[^\]]*'),
    'appname':  ('app_name',        r'[^\]]*'),
}

# MDC keys → LogEntry field  (keys are lowercased before lookup)
_MDC_FIELD_MAP: dict[str, str] = {
    'correlationid':   'correlation_id',
    'correlation_id':  'correlation_id',
    'correlation-id':  'correlation_id',   # APIM correlation.log header
    'tenantdomain':    'tenant_domain',
    'tenant_domain':   'tenant_domain',
    'tenant.domain':   'tenant_domain',
    'apiname':         'app_name',          # APIM api.log %X{apiName}
}

# MDC keys that have no LogEntry field — matched but discarded
_MDC_SKIP = {'ip', 'host'}

# Directives to silently skip (stack trace / newline)
_SKIP = {'ex', 'exception', 'throwable', 'xex', 'n', 'newline', 'rEx', 'xEx'.lower()}


def compile_pattern(pattern: str) -> tuple[Optional[re.Pattern], dict[str, str]]:
    """
    Convert a log4j2 layout pattern to a compiled regex.

    Returns:
        (compiled_pattern, field_map)
        field_map: {named_group → LogEntry field name}
        On error: (None, {})
    """
    regex_parts: list[str] = []
    field_map: dict[str, str] = {}
    used_fields: set[str] = set()
    i = 0

    while i < len(pattern):
        ch = pattern[i]

        if ch == '%':
            m = _DIRECTIVE_RE.match(pattern, i)
            if not m:
                regex_parts.append(re.escape('%'))
                i += 1
                continue

            name_raw = m.group(2)
            name = name_raw.lower()
            option = (m.group(3) or '').strip()
            i = m.end()

            if name in _SKIP:
                continue

            if name == 'x':
                # MDC: %X{key}
                key = option.lower()
                if key in _MDC_SKIP:
                    regex_parts.append(r'(?:[^\s|,}]*)')
                    continue
                entry_field = _MDC_FIELD_MAP.get(key)
                if entry_field and entry_field not in used_fields:
                    group = entry_field.replace('.', '_').replace('-', '_')
                    regex_parts.append(f'(?P<{group}>[^\\s|,}}]*)')
                    field_map[group] = entry_field
                    used_fields.add(entry_field)
                else:
                    regex_parts.append(r'(?:[^\s|,}]*)')
                continue

            mapping = _FIELD_MAP.get(name)
            if mapping is None:
                # Unknown directive: consume non-space token
                regex_parts.append(r'(?:[^\s]*)')
                continue

            field, pat = mapping
            if field in used_fields:
                regex_parts.append(f'(?:{pat})')
            else:
                regex_parts.append(f'(?P<{field}>{pat})')
                field_map[field] = field
                used_fields.add(field)

        elif ch in ' \t':
            # Collapse whitespace runs → flexible match
            while i < len(pattern) and pattern[i] in ' \t':
                i += 1
            regex_parts.append(r'\s*')
        else:
            regex_parts.append(re.escape(ch))
            i += 1

    regex_str = '^' + ''.join(regex_parts)
    try:
        return re.compile(regex_str, re.DOTALL), field_map
    except re.error:
        return None, {}


def test_pattern(pattern: str, line: str) -> dict:
    """
    Test a log4j2 pattern against a single log line.

    Returns:
        {
            "matched": bool,
            "fields": {field_name: value, ...},
            "regex": str,
            "error": str | None,
        }
    """
    compiled, field_map = compile_pattern(pattern)
    if compiled is None:
        return {"matched": False, "fields": {}, "regex": None, "error": "Invalid pattern: could not compile regex"}

    m = compiled.match(line.rstrip('\n'))
    if not m:
        return {"matched": False, "fields": {}, "regex": compiled.pattern, "error": None}

    fields: dict[str, str] = {}
    for group_name, entry_field in field_map.items():
        try:
            val = m.group(group_name)
            if val is not None:
                fields[entry_field] = val.strip()
        except IndexError:
            pass

    return {"matched": True, "fields": fields, "regex": compiled.pattern, "error": None}
