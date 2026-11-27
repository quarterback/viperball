# Cookbook save recovery

A user reported a server error after selecting Save playbook. Ordinary saves and reopen requests succeeded in the cloud workspace. A test database that rejected the write reproduced a generic server error. The cause of the user’s original report remains unknown.

The Cookbook now logs a storage error and returns the editor with the draft intact. The write runs outside the request event loop. An existing book remains unchanged if its update fails, and the same draft can be submitted again.

All 26 focused tests passed. Chromium verified that a failed new save preserved the name, package, and preference and that a retry saved and reopened the book.
