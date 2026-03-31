# OpenCL Test Suite Rules

Adding a new test case to this framework is designed to be extremely simple. Just follow these rules:

## 1. Directory Structure
Every test case must live in its own subdirectory inside the `tests/` folder. The name of the directory will automatically be used as the name of the test.
Example: `tests/my_new_test/`

## 2. Required Files
The Python runner automatically discovers your test files based on the following conventions. Each test directory must contain exactly:
1. **C++ Host Source Code (`.cpp` files)**: You must have at least one `.cpp` file. If your test requires multiple `.cpp` files, one of them *must* be named `main.cpp`.
2. **OpenCL Kernel File (`.cl` file)**: You must provide exactly *one* `.cl` file. The runner will throw an error if multiple kernel files are found in a single test directory.
3. **Golden Reference File (`expected.txt`)**: A text file containing the expected numerical output.

*Note: The runner automatically compiles your `.cpp` files with the flags `-std=c++11 -lOpenCL`.*

## 3. Writing the C++ Host Code
- **Success/Failure**: Your C++ program MUST return `0` on success and a non-zero exit code on failure. The Python runner uses this to determine if the process crashed or completed.
- **Output Format**: Simply print your numerical results to `stdout` (e.g., `std::cout << result << std::endl;`). The Python runner will automatically extract numbers from your output and compare them against `expected.txt` using a global floating-point tolerance (epsilon = `1e-5`).
- **OpenCL Build Errors**: If your `clBuildProgram` fails at runtime, you MUST catch it and print the OpenCL build log to `stderr` with the prefix `[KERNEL_BUILD_ERROR]`. The Python runner will look for this prefix to identify compilation failures vs. execution failures.
  Example:
  ```cpp
  std::cerr << "[KERNEL_BUILD_ERROR]\n" << build_log << std::endl;
  return 1;
  ```

## 4. Running the Tests
From the root directory, simply run:
```bash
python runner.py
```
To keep the compiled binaries around for debugging in CI, use:
```bash
python runner.py --keep-binaries
```

The runner will automatically:
1. Discover your test in the `tests/` folder and name it based on the directory.
2. Validate the directory structure (e.g. exactly one `.cl` file, presence of `expected.txt`).
3. Compile your C++ code.
4. Run the binary.
5. Compare the numerical output against `expected.txt`.
6. Provide a clean `[PASS]` or `[FAIL]` summary in the terminal.
7. Save build and run logs to `logs/build/` and `logs/run/`.