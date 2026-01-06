#!/usr/bin/env python3
"""
🔍 HOMES-Engine System Benchmark Tool
Verifica se o ambiente (Termux/Linux) aguenta o tranco do render.
"""

import os
import time
import platform
import subprocess
import shutil
import sys
from pathlib import Path

def print_header(title):
    print(f"\n\033[1;36m{title}\033[0m")
    print("=" * 40)

def check_cpu():
    print_header("1. 🧠 CPU & SYSTEM INFO")
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    print(f"Python: {sys.version.split()[0]}")
    
    try:
        # Tenta pegar info de cores no Android/Linux
        cpu_count = os.cpu_count()
        print(f"Logical Cores: {cpu_count}")
    except:
        print("Cores: Unknown")

def check_ffmpeg():
    print_header("2. 🎬 FFMPEG CAPABILITIES")
    try:
        res = subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT).decode()
        line = res.split('\n')[0]
        print(f"Version: {line}")
        
        # Check HW accel (Android often supports mediacodec)
        print("\nChecking Encoders:")
        encoders = subprocess.check_output(["ffmpeg", "-encoders"], stderr=subprocess.STDOUT).decode()
        for codec in ["libx264", "h264_mediacodec", "aac"]:
            status = "✅ Found" if codec in encoders else "❌ Missing"
            print(f"  - {codec}: {status}")
            
    except FileNotFoundError:
        print("❌ FFmpeg not found!")

def benchmark_disk_io():
    print_header("3. 💾 DISK I/O SPEED (Write Test)")
    test_file = "benchmark_test.tmp"
    size_mb = 100
    chunk_size = 1024 * 1024 # 1MB
    
    print(f"Writing {size_mb}MB file...")
    start = time.time()
    with open(test_file, "wb") as f:
        for _ in range(size_mb):
            f.write(os.urandom(chunk_size))
    end = time.time()
    
    duration = end - start
    speed = size_mb / duration
    print(f"Time: {duration:.2f}s")
    print(f"Speed: \033[1;32m{speed:.2f} MB/s\033[0m")
    
    os.remove(test_file)

def check_internet_latency():
    print_header("4. 🌐 API LATENCY (Google DNS)")
    try:
        # Ping google (cross-platform ping is tricky, using simple request logic via subprocess)
        cmd = ["ping", "-c", "3", "8.8.8.8"]
        subprocess.run(cmd)
    except Exception as e:
        print(f"Ping failed: {e}")

def main():
    print("\033[1;33m🚀 HOMES-ENGINE BENCHMARK TOOL\033[0m")
    check_cpu()
    check_ffmpeg()
    benchmark_disk_io()
    check_internet_latency()
    
    print_header("🏁 RESULTADO")
    print("Seu ambiente parece pronto para 'Absolute Cinema'.")

if __name__ == "__main__":
    main()
