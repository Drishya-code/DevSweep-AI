#!/usr/bin/env python3
"""
Generate realistic demo project with actual files of real sizes.
This script is run locally to create demo data - NOT committed to git.
"""

import os
import random
import shutil
from pathlib import Path

DEMO_ROOT = Path(__file__).parent / "demo-project"

def generate_demo():
    """Generate realistic demo project with actual file sizes."""
    # Clean existing demo dirs
    dirs_to_clean = ["node_modules", "dist", ".vite", "logs", "cache", "coverage", ".nyc_output"]
    for d in dirs_to_clean:
        path = DEMO_ROOT / d
        if path.exists():
            shutil.rmtree(path)
    
    # Create directories
    for d in dirs_to_clean:
        (DEMO_ROOT / d).mkdir(parents=True, exist_ok=True)
    
    # 1. node_modules - simulate with many small files (typical npm install)
    print("Generating node_modules...")
    node_modules = DEMO_ROOT / "node_modules"
    for i in range(500):  # 500 packages
        pkg_dir = node_modules / f"pkg-{i}"
        pkg_dir.mkdir()
        # Each package has a few files
        for j in range(random.randint(2, 10)):
            file_path = pkg_dir / f"file{j}.js"
            size = random.randint(1000, 50000)  # 1KB - 50KB per file
            file_path.write_bytes(os.urandom(size))
    
    # 2. dist - build output
    print("Generating dist...")
    dist = DEMO_ROOT / "dist"
    for i in range(50):  # 50 build files
        file_path = dist / f"bundle.{i}.js"
        size = random.randint(10000, 500000)  # 10KB - 500KB
        file_path.write_bytes(os.urandom(size))
    # Add some .map and .css files
    for i in range(10):
        file_path = dist / f"style.{i}.css"
        size = random.randint(5000, 100000)
        file_path.write_bytes(os.urandom(size))
        file_path = dist / f"bundle.{i}.js.map"
        size = random.randint(50000, 300000)
        file_path.write_bytes(os.urandom(size))
    
    # 3. .vite - cache
    print("Generating .vite...")
    vite = DEMO_ROOT / ".vite"
    for i in range(100):
        file_path = vite / f"cache.{i}.data"
        size = random.randint(1000, 20000)
        file_path.write_bytes(os.urandom(size))
    
    # 4. logs - log files (larger to trigger CAUTION > 10MB)
    print("Generating logs...")
    logs = DEMO_ROOT / "logs"
    for i in range(50):
        file_path = logs / f"app-{i}.log"
        size = random.randint(200000, 500000)  # 200KB - 500KB
        file_path.write_bytes(os.urandom(size))
    
    # 5. cache - general cache (larger to trigger CAUTION > 10MB)
    print("Generating cache...")
    cache = DEMO_ROOT / "cache"
    for i in range(50):
        file_path = cache / f"cache-{i}.bin"
        size = random.randint(200000, 500000)  # 200KB - 500KB
        file_path.write_bytes(os.urandom(size))
    
    # 6. coverage - test coverage reports
    print("Generating coverage...")
    coverage = DEMO_ROOT / "coverage"
    for i in range(30):
        file_path = coverage / f"coverage-{i}.json"
        size = random.randint(10000, 200000)
        file_path.write_bytes(os.urandom(size))
    
    # 7. .nyc_output - nyc intermediate files
    print("Generating .nyc_output...")
    nyc = DEMO_ROOT / ".nyc_output"
    for i in range(20):
        file_path = nyc / f"out-{i}.json"
        size = random.randint(5000, 100000)
        file_path.write_bytes(os.urandom(size))
    
    print("\nDemo generation complete!")
    
    # Report actual sizes
    print("\nActual sizes:")
    for d in dirs_to_clean:
        path = DEMO_ROOT / d
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        print(f"  {d}: {total / (1024*1024):.2f} MB ({total:,} bytes)")
    
    total_all = sum(
        sum(f.stat().st_size for f in (DEMO_ROOT / d).rglob("*") if f.is_file())
        for d in dirs_to_clean
    )
    print(f"\nTotal recoverable: {total_all / (1024*1024):.2f} MB ({total_all:,} bytes)")

if __name__ == "__main__":
    generate_demo()