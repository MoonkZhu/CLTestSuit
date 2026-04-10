import os
import sys
import subprocess
import time
import csv
import re

# Global Epsilon for floating-point comparisons
EPSILON = 1e-5

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

def run_test(test_dir, test_name):
    output_bin = os.path.join(test_dir, 'test_bin')
    has_golden = os.path.exists(os.path.join(test_dir, 'expected.txt'))

    if not os.path.exists(output_bin):
        return False, 0.0, f"Executable 'test_bin' not found in {test_dir}."

    start_time = time.time()

    try:
        # Run binary in the test directory
        result = subprocess.run(["./test_bin"],
                                cwd=test_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)

        exec_time = time.time() - start_time

        # Check for OpenCL compilation errors logged by the C++ host
        if "[KERNEL_BUILD_ERROR]" in result.stderr:
            return False, exec_time, "OpenCL Kernel Build Error."

        # Check execution success (exit code)
        if result.returncode != 0:
            return False, exec_time, f"Execution failed (exit code {result.returncode})."

        if has_golden:
            # Verify Golden
            golden_path = os.path.join(test_dir, 'expected.txt')
            with open(golden_path, 'r') as f:
                golden_text = f.read()

            match, msg = compare_golden(result.stdout, golden_text)
            if not match:
                return False, exec_time, f"Verification failed: {msg}"
        else:
            # Host-Verified Mode
            output_lower = result.stdout.lower() + result.stderr.lower()
            if "fail" in output_lower or "mismatch" in output_lower:
                return False, exec_time, "Verification failed (Host reported failure)."

            if "pass" not in output_lower:
                return False, exec_time, "Verification failed (Host did not report 'PASS')."

        return True, exec_time, ""

    except Exception as e:
        return False, time.time() - start_time, f"Failed to execute binary: {str(e)}"

def main():
    build_tests_dir = os.path.join('build', 'tests')

    if not os.path.exists(build_tests_dir):
        print(f"Directory {build_tests_dir} does not exist. Please build the tests using CMake first.")
        sys.exit(1)

    test_cases = []
    for item in os.listdir(build_tests_dir):
        test_path = os.path.join(build_tests_dir, item)
        if os.path.isdir(test_path):
            test_cases.append((item, test_path))

    if not test_cases:
        print(f"No test cases found in {build_tests_dir}.")
        sys.exit(0)

    print(f"Found {len(test_cases)} test case(s) in {build_tests_dir}.")
    print("=" * 60)

    results = []
    passed_count = 0

    for test_name, test_dir in test_cases:
        success, exec_time, err_msg = run_test(test_dir, test_name)

        status = "PASS" if success else "FAIL"
        results.append({
            "Test Name": test_name,
            "Execution Time (s)": f"{exec_time:.4f}",
            "Result": status
        })

        if success:
            print(f"Test '{test_name}': [{status}] in {exec_time:.4f}s")
            passed_count += 1
        else:
            print(f"Test '{test_name}': [{status}] in {exec_time:.4f}s - {err_msg}")

    print("=" * 60)
    print(f"Summary: {passed_count}/{len(test_cases)} tests passed.")

    # Write to CSV
    csv_file = 'results.csv'
    with open(csv_file, 'w', newline='') as csvfile:
        fieldnames = ['Test Name', 'Execution Time (s)', 'Result']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"Results saved to {csv_file}")

    if passed_count != len(test_cases):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()