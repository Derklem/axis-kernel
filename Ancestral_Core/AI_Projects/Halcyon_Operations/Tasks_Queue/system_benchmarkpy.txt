import time
import psutil  # To get system stats
import platform

def benchmark_system():
    print("Starting system performance benchmark...")
    
    # Get system info
    cpu_info = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory().percent
    disk_info = psutil.disk_usage('/').percent
    system_info = platform.uname()

    # Log system stats
    with open("system_benchmark_results.txt", "a") as file:
        file.write(f"System Benchmark - {time.ctime()}\n")
        file.write(f"System: {system_info.system} {system_info.release} {system_info.version}\n")
        file.write(f"CPU Usage: {cpu_info}%\n")
        file.write(f"Memory Usage: {memory_info}%\n")
        file.write(f"Disk Usage: {disk_info}%\n")
        file.write("-" * 50 + "\n")
    
    print("Benchmark completed.")

if __name__ == "__main__":
    benchmark_system()
