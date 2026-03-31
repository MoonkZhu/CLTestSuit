# OpenCL Test Suite Rules

Adding a new test case to this framework is designed to be extremely simple. Just follow these rules:

## 1. Directory Structure
Every test case must live in its own subdirectory inside the `tests/` folder.
Example: `tests/my_new_test/`

## 2. Required Files
Each test directory must contain at least three things:
1. **`manifest.json`**: A configuration file defining the test metadata.
2. **C++ Host Source Code**: Usually `main.cpp`.
3. **Golden Reference File**: A text file containing the expected numerical output.

*Optional*: If your test uses an external OpenCL kernel, include your `.cl` file in the directory.

## 3. The `manifest.json` Format
The manifest tells the Python runner how to build and verify your test.
```json
{
  "name": "My New Test",
  "host_sources": ["main.cpp"],
  "kernel_files": ["kernel.cl"],
  "compiler_flags": ["-std=c++11", "-lOpenCL"],
  "golden_file": "expected.txt"
}
```

## 4. Writing the C++ Host Code
- **Success/Failure**: Your C++ program MUST return `0` on success and a non-zero exit code on failure. The Python runner uses this to determine if the process crashed or completed.
- **Output Format**: Simply print your numerical results to `stdout` (e.g., `std::cout << result << std::endl;`). The Python runner will automatically extract numbers from your output and compare them against the golden reference file using a global floating-point tolerance (epsilon = `1e-5`).
- **OpenCL Build Errors**: If your `clBuildProgram` fails at runtime, you MUST catch it and print the OpenCL build log to `stderr` with the prefix `[KERNEL_BUILD_ERROR]`. The Python runner will look for this prefix to identify compilation failures vs. execution failures.
  Example:
  ```cpp
  std::cerr << "[KERNEL_BUILD_ERROR]\n" << build_log << std::endl;
  return 1;
  ```

## 5. Running the Tests
From the root directory, simply run:
```bash
python runner.py
```
To keep the compiled binaries around for debugging in CI, use:
```bash
python runner.py --keep-binaries
```

The runner will automatically:
1. Discover your test in the `tests/` folder.
2. Compile your C++ code.
3. Run the binary.
4. Compare the numerical output against your golden file.
5. Provide a clean `[PASS]` or `[FAIL]` summary in the terminal.
6. Save build and run logs to `logs/build/` and `logs/run/`.