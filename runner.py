import os
import sys
import subprocess
import argparse
import re

# Global Epsilon for floating-point comparisons
EPSILON = 1e-5

def setup_directories():
    os.makedirs('logs/build', exist_ok=True)
    os.makedirs('logs/run', exist_ok=True)

def find_tests(tests_dir='tests'):
    if not os.path.exists(tests_dir):
        return []

    test_cases = []
    for item in os.listdir(tests_dir):
        test_path = os.path.join(tests_dir, item)
        if os.path.isdir(test_path):
            test_cases.append(test_path)
    return test_cases

def extract_numbers(text):
    # Extracts all integers and floating-point numbers from a string
    return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', text)]

def compare_golden(output_text, golden_text):
    output_nums = extract_numbers(output_text)
    golden_nums = extract_numbers(golden_text)

    if len(output_nums) != len(golden_nums):
        return False, f"Count mismatch: Expected {len(golden_nums)} numbers, got {len(output_nums)}."

    for i, (out_val, gold_val) in enumerate(zip(output_nums, golden_nums)):
        if abs(out_val - gold_val) > EPSILON:
            return False, f"Mismatch at index {i}: Expected {gold_val}, got {out_val} (diff: {abs(out_val - gold_val)})"

    return True, ""

def validate_test_structure(test_dir):
    files = os.listdir(test_dir)
    cpp_files = [f for f in files if f.endswith('.cpp')]
    cl_files = [f for f in files if f.endswith('.cl')]

    if len(cpp_files) == 0:
        return False, [], False, "No .cpp files found in test directory."

    if len(cpp_files) > 1 and 'main.cpp' not in cpp_files:
        return False, [], False, "Multiple .cpp files found, but 'main.cpp' is missing."

    if len(cl_files) == 0:
        return False, [], False, "No .cl kernel file found in test directory."

    if len(cl_files) > 1:
        return False, [], False, f"Multiple .cl files found: {cl_files}. Exactly one .cl file is allowed."

    has_golden = 'expected.txt' in files

    return True, cpp_files, has_golden, ""

def build_test(test_dir, test_name, cpp_files):
    # Auto-build is disabled as we now use CMake.
    # We just check if the test_bin executable was built manually.
    output_bin = os.path.join(test_dir, 'test_bin')

    if not os.path.exists(output_bin):
        return False, output_bin, "Executable 'test_bin' not found. Please build using CMake before running."

    return True, output_bin, ""

def run_test(test_dir, test_name, output_bin, has_golden):
    run_log_path = os.path.join('logs', 'run', f'{test_name}_run.log')

    try:
        # Run binary in the test directory so it can find local kernels
        result = subprocess.run([f"./{os.path.basename(output_bin)}"],
                                cwd=test_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)

        with open(run_log_path, 'w') as f:
            f.write("--- STDOUT ---\n")
            f.write(result.stdout)
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)

        # Check for OpenCL compilation errors logged by the C++ host
        if "[KERNEL_BUILD_ERROR]" in result.stderr:
            return False, f"OpenCL Kernel Build Error. See {run_log_path}"

        # Check execution success
        if result.returncode != 0:
            return False, f"Execution failed (exit code {result.returncode}). See {run_log_path}"

        if has_golden:
            # Verify Golden
            golden_path = os.path.join(test_dir, 'expected.txt')
            with open(golden_path, 'r') as f:
                golden_text = f.read()

            match, msg = compare_golden(result.stdout, golden_text)
            if not match:
                return False, f"Verification failed (Golden mismatch): {msg}"
        else:
            # Host-Verified Mode
            # Check for specific failure keywords in the output
            output_lower = result.stdout.lower() + result.stderr.lower()
            if "fail" in output_lower or "mismatch" in output_lower:
                return False, f"Verification failed (Host reported failure). See {run_log_path}"

            if "pass" not in output_lower:
                return False, f"Verification failed (Host did not report 'PASS'). See {run_log_path}"

        return True, ""

    except Exception as e:
        return False, f"Failed to execute binary: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="OpenCL Test Suite Runner")
    parser.add_argument("--keep-binaries", action="store_true", help="Do not delete compiled binaries after testing")
    args = parser.parse_args()

    setup_directories()

    test_cases = find_tests()
    if not test_cases:
        print("No test cases found in tests/ directory.")
        return

    print(f"Found {len(test_cases)} test case(s).")
    print("=" * 40)

    passed_count = 0

    for test_dir in test_cases:
        test_name = os.path.basename(test_dir)
        display_name = test_name

        # 1. Validate Structure
        valid, cpp_files, has_golden, err_msg = validate_test_structure(test_dir)
        if not valid:
            print(f"Test '{display_name}': [FAIL] - {err_msg}")
            continue

        # 2. Build
        build_ok, output_bin, build_err = build_test(test_dir, test_name, cpp_files)
        if not build_ok:
            print(f"Test '{display_name}': [FAIL] - {build_err}")
            continue

        # 3. Run & Verify
        run_ok, run_err = run_test(test_dir, test_name, output_bin, has_golden)

        # 4. Cleanup
        # Note: We now keep binaries by default since they are managed by CMake.
        # if not args.keep_binaries and os.path.exists(output_bin):
        #     os.remove(output_bin)

        # 5. Report
        if run_ok:
            print(f"Test '{display_name}': [PASS]")
            passed_count += 1
        else:
            print(f"Test '{display_name}': [FAIL] - {run_err}")

    print("=" * 40)
    print(f"Summary: {passed_count}/{len(test_cases)} tests passed.")

    if passed_count != len(test_cases):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
