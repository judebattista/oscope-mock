# TDS5000B Mock Oscilloscope — Iteration 1 Design

**Date:** 2026-05-22
**Scope:** SCPI-over-TCP server responding to all FILESystem commands with a Windows-style virtual filesystem.

---

## Overview

Mock of a Tektronix TDS5000B Series Digital Phosphor Oscilloscope. Accepts SCPI commands over a raw TCP connection (TekVISA-style virtual GPIB). Iteration 1 implements the full FILESystem command group plus minimal IEEE 488.2 instrument commands. Future iterations will add command groups (ACQuire, CHannel, TRIGger, etc.).

---

## File Layout

```
oscope-mock/
├── server.py              # entry point, asyncio TCP listener, --port / --fs-root flags
├── scpi/
│   ├── __init__.py
│   ├── parser.py          # SCPI tokenizer: mnemonic resolution, compound cmds, block data
│   ├── dispatcher.py      # routes canonical command keys to registered handlers
│   ├── filesystem.py      # all 11 FILESystem handlers + FileSystemState
│   └── instrument.py      # *IDN?, *RST, *CLS, *ESR?, *STB?, *OPC, HDR/HEADer
└── pyproject.toml         # stdlib-only runtime; dev tools in the `dev` dependency group
```

---

## TCP Transport

- Raw TCP, default port **4000** (TekVISA virtual GPIB default), configurable via `--port`
- One asyncio coroutine per client connection
- Commands delimited by `\n` or `\r\n`
- Multiple commands on one line separated by `;`
- Responses terminated by `\n`
- Block data (e.g. `WRITEFile`) may span multiple reads; server buffers until block complete before dispatching

---

## SCPI Parser (`scpi/parser.py`)

SCPI mnemonics have a long form and a short form. The short form is the ALL-CAPS prefix of the mnemonic (e.g. `FILESystem` → long `FILESYSTEM`, short `FILE`). Both are valid; matching is case-insensitive.

**Pipeline:**
1. Split input on `;` → list of raw command strings
2. For each: split on first whitespace → `(header, args_string)`
3. Split header on `:` → node list; strip trailing `?` → query flag
4. Resolve each node against known long/short forms → canonical uppercase key
5. Parse `args_string`: strip surrounding quotes, handle IEEE 488.2 block data

**Block data formats (WRITEFile):**
- Definite length: `#NDD...` where N = digits in length, D...D = byte count
- Indefinite length: `#0<data>\n<EOI>` (newline terminates)

**Canonical key examples:**
```
"filesystem:cwd?"       → key=FILESYSTEM:CWD, query=True
"FILE:COP "a","b""      → key=FILESYSTEM:COPY, query=False
"FILESYSTEM:WRITEFILE"  → key=FILESYSTEM:WRITEFILE, query=False
```

---

## Dispatcher (`scpi/dispatcher.py`)

- Dict of `canonical_key → handler_function`
- Handler signature: `handler(args: list[str], state: InstrumentState) -> str | bytes | None`
- Returns `None` for no-response commands; returns response string (or raw bytes for file contents) for queries
- Unknown command → push error code 110 ("Command header error") onto event queue

---

## Shared State (`scpi/instrument.py`)

All handlers receive a single `InstrumentState` object:

```python
@dataclass
class InstrumentState:
    headers: bool = True  # HDR/HEADer setting
    esr: int = 0  # Event Status Register
    stb: int = 0  # Status Byte Register
    event_queue: list = field(default_factory=list)
    filesystem: FileSystemState = field(default_factory=FileSystemState)
```

`FileSystemState` is defined in `filesystem.py`; `InstrumentState` imports and composes it.

## Instrument Commands (`scpi/instrument.py`)

Minimal IEEE 488.2 required commands:

| Command | Response | Notes |
|---|---|---|
| `*IDN?` | `TEKTRONIX,TDS5054B,0,CF:91.1CT FV:v2.00 TDS5054B` | Fixed identity string |
| `*RST` | none | Reset CWD to `C:\TekScope`, clear error queue |
| `*CLS` | none | Clear status registers + error queue |
| `*ESR?` | ESR byte (0–255) | Returns and clears Event Status Register |
| `*STB?` | Status byte | Returns Status Byte Register |
| `*OPC` | none | Set OPC bit in ESR |
| `*OPC?` | `1` | Synchronization query |
| `HDR {ON\|OFF\|NR1}` | none | Toggle response header prefix (default ON) |
| `HEADer {ON\|OFF\|NR1}` | none | Alias for HDR |
| `HEADer?` / `HDR?` | `1` or `0` | Query header state |

**Response headers:** When ON (default), query responses are prefixed with the canonical command path:
- `FILESystem:CWD?` → `:FILESYSTEM:CWD "C:\TekScope"`
- When OFF → `"C:\TekScope"`

---

## FILESystem Handlers (`scpi/filesystem.py`)

### FileSystemState

```python
@dataclass
class FileSystemState:
    cwd: str = r"C:\TekScope"  # Windows-style virtual CWD
    root: str = ""  # real host root dir (set from --fs-root or tempdir)
```

### Path Mapping

Virtual Windows paths map to real host paths under `{root}`:

```
C:\TekScope\Waveforms  →  {root}/C/TekScope/Waveforms/
D:\Data\file.txt       →  {root}/D/Data/file.txt
.\newfile.txt          →  resolved against CWD → {root}/C/TekScope/newfile.txt
```

Rules:
- Absolute paths: extract drive letter, map `{drive}:\...` → `{root}/{drive}/...`
- Relative paths: join against CWD, then apply absolute mapping
- Path separator: accept both `\` and `/`

### Initial Directory Structure (created at startup)

```
C:\TekScope\
C:\TekScope\Waveforms\
C:\TekScope\Images\
C:\TekScope\Settings\
```

### Command Reference

| Command | Args | Behavior | Response |
|---|---|---|---|
| `FILESystem:COPy` | `"<src>","<dst>"` | `shutil.copy2(src, dst)` | none |
| `FILESystem:CWD` | `"<path>"` | update `state.cwd` | none |
| `FILESystem:CWD?` | — | return CWD string | `:FILESYSTEM:CWD "C:\TekScope"` |
| `FILESystem:DELEte` | `"<path>"` | `os.remove(path)` | none |
| `FILESystem:DIR?` | — | list entries in CWD | `:FILESYSTEM:DIR ".","..","wfm1.wfm"` |
| `FILESystem:MKDir` | `"<path>"` | `os.makedirs(path, exist_ok=True)` | none |
| `FILESystem:PRInt` | `"<path>",GPIb` | read file bytes, send raw on TCP channel; `GPIb` arg accepted but ignored (TCP-only mock) | file contents |
| `FILESystem:READFile` | `"<path>",GPIb` | identical to PRInt | file contents |
| `FILESystem:RENAme` | `"<old>","<new>"` | `os.rename(old, new)` | none |
| `FILESystem:RMDir` | `"<path>"` | `os.rmdir(path)` (fails if non-empty) | none |
| `FILESystem:WRITEFile` | `"<path>",<block>` | parse IEEE 488.2 block, write to file | none |
| `FILESystem?` | — | alias for `FILESystem:DIR?` | same as DIR? |

### Error Handling

Errors push an event code onto the instrument event queue and set ESR bit 3 (Device-Specific Error):

| Condition | Event Code |
|---|---|
| File not found | 2002 |
| Directory not empty (RMDir) | 2003 |
| Path already exists (MKDir) | 2004 |
| Missing / malformed arguments | 110 |
| Unknown command header | 110 |

---

## Startup

```bash
python server.py [--port 4000] [--fs-root /tmp/tds5000b_mock]
```

- If `--fs-root` omitted: create a `tempfile.mkdtemp()` directory and print the path to stdout
- Pre-create initial directory structure under root
- Log each connection and each command received to stdout

---

## Out of Scope (Iteration 1)

- All other command groups (ACQuire, CHannel, TRIGger, MEASurement, WAVEform, etc.)
- GPIB bus simulation
- VXI-11 / HiSLIP protocol framing (raw TCP only)
- Authentication / TekSecure
- Persistent state across restarts (beyond what's on disk)
