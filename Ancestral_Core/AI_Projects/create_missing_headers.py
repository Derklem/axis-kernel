import os

# Define the missing header files and their paths
missing_files = {
    "include/missing_vld1_neon.h": "// Placeholder for missing_vld1_neon.h\n#pragma once",
    "include/missing_vst1_neon.h": "// Placeholder for missing_vst1_neon.h\n#pragma once",
    "include/Exceptions.h": "// Placeholder for Exceptions.h\n#pragma once",
    "include/CUDAException.h": "// Placeholder for CUDAException.h\n#pragma once",
    "include/Exception.h": "// Placeholder for Exception.h\n#pragma once",
    "include/XPUException.h": "// Placeholder for XPUException.h\n#pragma once",
}

# Create directories and files
for file_path, content in missing_files.items():
    dir_path = os.path.dirname(file_path)
    
    # Ensure the directory exists
    os.makedirs(dir_path, exist_ok=True)
    
    # Create the file if it doesn't exist
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Created: {file_path}")
    else:
        print(f"Already exists: {file_path}")

print("\nAll missing header files have been created or verified.")
