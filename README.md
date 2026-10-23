# oscope-mock

A mock Tektronix TDS5000B oscilloscope that speaks SCPI over a raw TCP socket. It stands in
for the instrument when developing and testing the
[oscope](https://github.com/judebattista/oscope_recon) client. It implements the
`FILESystem` command group against a Windows-style virtual filesystem, plus the IEEE 488.2
status commands a client needs to detect errors. It identifies itself as a TDS5054B.

The TDS5000B programming manual is the specification. The design is described in
[docs/superpowers/specs/2026-05-22-tds5000b-mock-iteration1-design.md](docs/superpowers/specs/2026-05-22-tds5000b-mock-iteration1-design.md).

## Running

Requires Python 3.12+. The server uses only the standard library, so there is nothing to
install to run it.

```bash
python server.py                        # fresh temporary fs-root, printed at startup
python server.py --fs-root ./scope-fs   # keep files between runs
python server.py --host 0.0.0.0         # accept clients from other machines
```

| Option      | Default                   | Meaning                                         |
|-------------|---------------------------|-------------------------------------------------|
| `--host`    | `127.0.0.1`               | Address to listen on                            |
| `--port`    | `4000`                    | TCP port (the TekVISA socket server default)    |
| `--fs-root` | a new temporary directory | Host directory that holds the virtual drives    |

A temporary fs-root is not deleted when the server exits. Every received message is logged
to stderr. All connections share one instrument state, as they would on the real scope.

## Virtual filesystem

Windows paths map to directories under the fs-root, one per drive letter:
`C:\TekScope\Waveforms\a.wfm` is stored at `<fs-root>/C/TekScope/Waveforms/a.wfm`.

On startup the server creates `C:\TekScope` with `Waveforms`, `Images` and `Settings`
subdirectories, and the working directory starts at `C:\TekScope`. Other drives exist only
if you create their directory on the host, e.g. `<fs-root>/D` for `D:`.

Relative paths resolve against the working directory, `..` stops at the drive root, a path
starting with `\` stays on the current drive, and `/` is accepted as a separator.

## Supported commands

Mnemonics accept their long or short form in any case (`FILESystem`, `FILE`, `file`), and
`;` separates commands within a message.

| Group       | Commands                                                                              |
|-------------|---------------------------------------------------------------------------------------|
| FILESystem  | `CWD`, `CWD?`, `DIR?`, `FILESystem?` (same as `DIR?`), `MKDir`, `RMDir`, `DELEte`, `REName`, `COPy`, `READFile`, `PRInt` (same as `READFile`), `WRITEFile` |
| Status      | `*ESR?`, `EVMsg?`, `*STB?`, `*CLS`, `*RST`, `*OPC`, `*OPC?`, `*IDN?`                  |
| Responses   | `HEADer` / `HDR`, `HEADer?` / `HDR?`, `VERBose`, `VERBose?`                           |

Behaviour a client needs to handle:

- **Headers are on by default**, so query responses are prefixed with the command, e.g.
  `:FILESYSTEM:CWD "C:\TekScope"`. Send `HEADer 0` for bare responses.
- **Errors produce no response.** They set bits in the Standard Event Status Register and
  queue an event. Read `*ESR?`, then `EVMsg?` until it returns `0`. Command errors (1xx) set
  CME; execution errors (2xx) set EXE. The manual's table of 2xx codes is missing, so the
  mock assumes the SCPI-99 numbers, e.g. 256 "File name not found".
- **`READFile` and `PRInt` need the port argument `GPIb`** (`FILESystem:READFile "a.wfm",GPIb`)
  and send the file's raw bytes with no terminator. The connection stays open, so a client
  has to detect the end of the data by silence.
- **`WRITEFile` takes IEEE 488.2 block data**, definite (`#15hello`) or indefinite (`#0...`).
- **`DIR?` lists `"."` and `".."`** along with the directory's entries.
- **If the working directory is deleted**, it resets to `C:\TekScope` on the next filesystem
  command.

## Differences from the real instrument

- Only the commands above exist; anything else reports event 110 "Command header error".
- Paths are case-sensitive when the host filesystem is (Linux), unlike on the instrument.
- A header with a leading colon (`:FILESystem:CWD?`) is not recognised.
- A command after `;` must give its full path; `FILESystem:MKDir "a";RMDir "a"` does not
  resolve `RMDir` within `FILESystem`.
- `REName` overwrites an existing destination on Linux and macOS hosts.
- File names that Windows rejects, such as `bad|name`, are accepted on Linux and macOS hosts.
- `*OPC` sets the OPC bit without queueing event 402 "Operation complete".

## Using it with the oscope client

```bash
python server.py &
oscope -H 127.0.0.1 ls
```

The client's integration tests run against the mock the same way; see the client's README.

## Development

```bash
uv venv
uv pip install --group dev   # or: pip install --group dev (pip 25.1+)
pre-commit install           # once: runs ruff and mypy on every commit
pytest
ruff check .
mypy                         # checks scpi, server.py and tests
```
