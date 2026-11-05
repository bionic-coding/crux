A fixture test root for the tier mechanism. Its manifest is named `test-tiers.example.json` so no
committed file other than a real root manifest is called `test-tiers.json`. A test copies this
directory to a temporary directory and renames the manifest before it runs the reader.
