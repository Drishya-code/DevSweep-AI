# Demo Project for DevSweep AI
# This is a lightweight fixture that simulates a large project with 2+ GB recoverable

# Project Structure:
# node_modules/ - 1.8 GB (regenerable from package-lock.json)
# dist/ - 420 MB (build output)
# .vite/ - 86 MB (Vite cache)
# logs/ - 12 MB (log files)
# cache/ - 45 MB (cache)
# coverage/ - 25 MB (test coverage)
# .nyc_output/ - 8 MB (NYC coverage)

# Source files (PROTECTED - never deleted):
# src/ - ~4 MB (actual source code)
# public/ - ~1 MB (static assets)
# package.json, package-lock.json, tsconfig.json, etc.