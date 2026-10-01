# Demo Project for DevSweep AI
# This is a lightweight fixture that simulates a project with ~128 MB recoverable

# Project Structure:
# node_modules/ - ~76 MB (regenerable from package-lock.json)
# dist/ - ~14 MB (build output)
# .vite/ - ~1 MB (Vite cache)
# logs/ - ~16 MB (log files, CAUTION threshold >10MB)
# cache/ - ~16 MB (cache, CAUTION threshold >10MB)
# coverage/ - ~3 MB (test coverage)
# .nyc_output/ - ~1 MB (NYC coverage)

# Source files (PROTECTED - never deleted):
# src/ - ~4 MB (actual source code)
# public/ - ~1 MB (static assets)
# package.json, package-lock.json, tsconfig.json, etc.