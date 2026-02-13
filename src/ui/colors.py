"""
BB84 Quantum Chat - Color Palette
Rich style definitions for the terminal UI.
"""

from rich.theme import Theme

# Color palette
COLORS = {
    'alice':        'bold cyan',
    'bob':          'bold green',
    'system':       'bold yellow',
    'error':        'bold red',
    'warning':      'bold bright_yellow',
    'success':      'bold green',
    'encrypted':    'dim white',
    'key':          'bold magenta',
    'header':       'bold white on blue',
    'secure':       'bold green',
    'compromised':  'bold red',
    'eve':          'bold red',
    'info':         'cyan',
    'dim':          'dim',
    'highlight':    'bold bright_white',
    'phase':        'bold bright_cyan',
    'photon':       'bright_magenta',
    'basis_match':  'green',
    'basis_miss':   'red',
    'bit':          'bright_white',
    'angle':        'bright_yellow',
    'progress':     'bright_green',
}

CHAT_THEME = Theme({
    'alice': COLORS['alice'],
    'bob': COLORS['bob'],
    'system': COLORS['system'],
    'error': COLORS['error'],
    'warning': COLORS['warning'],
    'success': COLORS['success'],
    'encrypted': COLORS['encrypted'],
    'key': COLORS['key'],
    'secure': COLORS['secure'],
    'compromised': COLORS['compromised'],
    'eve': COLORS['eve'],
    'info': COLORS['info'],
    'dim': COLORS['dim'],
    'highlight': COLORS['highlight'],
    'phase': COLORS['phase'],
    'photon': COLORS['photon'],
})

# Emoji / symbols
SYMBOLS = {
    'secure':       '🟢',
    'warning':      '⚠️ ',
    'compromised':  '🔴',
    'lock':         '🔒',
    'unlock':       '🔓',
    'key':          '🔑',
    'send':         '~~~>',
    'receive':      '<~~~',
    'check':        '✓',
    'cross':        '✗',
    'photon':       '◆',
    'antenna':      '📡',
    'shield':       '🛡️',
    'eye':          '👁️',
}
