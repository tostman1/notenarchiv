# Shared runtime and Windows distribution

## Runtime recommendation

Package an application directory with a private Python interpreter, pinned
packages, collected static files, migrations, PDFium, fonts and OCR binaries
and trained data. A native launcher should start the same WSGI application and
one worker, expose the UI in a managed WebView and bind exclusively to loopback.
This preserves template rendering, authentication, CSRF and the existing service
APIs. A user-installed Python would conflict with the distribution requirement.
A single-file self-extracting executable adds extraction cost and complicates
native library discovery and child interpreter invocation. Validate the directory
bundle first. An installer and WebView/runtime redistribution rights, offline
installation and update/rollback tests are later desktop deliverables.

PyInstaller is a packaging alternative that needs a dedicated child-process
dispatcher because its frozen executable is a bootloader. The current PDF and
resource-limit children expect a Python interpreter. A private interpreter
directory avoids that specific change and preserves module subprocesses.
This recommendation follows the documented runtime semantics and still needs
an installed-runtime prototype. See [PyInstaller runtime information](https://pyinstaller.org/en/stable/runtime-information.html)
and [bundle modes](https://pyinstaller.org/en/stable/operating-mode.html).

## Existing boundaries and work before desktop delivery

* Services and ORM models already implement catalog, resolution, snapshots and
  job ownership. Reuse them through the existing UI. Keep Gunicorn, Compose,
  mount validation and private TLS at the server entry point.
* A desktop shortcut can start in an arbitrary directory. Database readiness
  now invokes the installed management script. PDF subprocesses start in the
  installed code tree and continue to stage data only in their private scratch
  directory. Keep installed code read-only.
* The local profile creates synthetic roots and supports development login.
  Implement desktop settings separately from that profile. Validate configured
  roots for identity, nesting, permissions and reparse points before any writes.
  Keep database, logs, secret, settings and scratch in private writable storage.
  Store only validated selections and change them while the worker is quiescent.
* SQLite migrations and short transactions are shared. Require local database
  storage, exclusive maintenance and isolated recovery. The launcher must hold
  the application lifecycle lock, migrate before serving and supervise shutdown.
  Verify crash recovery, single-instance startup and database backup/restore on
  NTFS with synthetic data before enabling desktop use.
* `core.files.Root` depends on descriptor-relative POSIX operations.
  Inventory, publication, STATUS replacement, download staging, export cleanup
  and backup also use directory descriptors directly. Windows archive access
  requires handle-relative traversal, reparse rejection, independent RAW write
  denial, file identity checks, no-clobber publication and tested crash durability.
  Keep operations unavailable until the backend and its consumers pass equivalent
  race, collision, withdrawal and recovery tests. Ordinary path normalization
  alone cannot meet this contract.
  Inventory traversal now consumes the root's directory metadata interface.
  The backend owns no-follow enumeration and directory mutation detection.
  Cycle detection, relative references and entry budgets stay in inventory
  policy and can be tested independently on both platforms.
* core/processes.py already binds descendants to a Windows Job or Linux process
  group. Preserve bounded CPU, memory, time, input and output for PDF and OCR.
  Windows output writers must enforce byte bounds explicitly. WP-24 should use
  an explicit trusted Tesseract installation and bundled language data, with
  matching evidence and error behavior on each platform.
* Printing is currently unavailable. Future adapters must expose platform
  capabilities and retain uncertain-submission semantics. Spooler and physical
  acceptance remain separate.

## Verification boundary

The foreign-working-directory PDF regression exercises inspection, extraction
and native rendering with synthetic inputs. The migration regression checks the
selected script path. Neither exercises an installed desktop launcher. Desktop
release requires offline clean-machine installation, per-user data ACLs, shared
business workflow tests, managed shutdown and uninstall with user data preserved.
The server retains full Foundation and Container checks and separate NAS acceptance.

The Windows CI job runs configuration, native PDF, process-tree/resource-limit
and startup tests with pinned Python and locked dependencies. Foundation repeats
these contracts on Linux. Windows archive publication and installed desktop
lifecycle remain explicit future acceptance gates.
