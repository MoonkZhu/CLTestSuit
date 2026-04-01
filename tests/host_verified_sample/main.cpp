#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <cmath>

#ifdef __APPLE__
#include <OpenCL/opencl.h>
#else
#include <CL/cl.h>
#endif

void checkError(cl_int err, const char* operation) {
    if (err != CL_SUCCESS) {
        std::cerr << "Error during operation '" << operation << "': " << err << std::endl;
        exit(1);
    }
}

int main() {
    // 1. Setup OpenCL Platform & Device
    cl_uint num_platforms;
    cl_int err = clGetPlatformIDs(0, nullptr, &num_platforms);
    checkError(err, "clGetPlatformIDs count");

    if (num_platforms == 0) {
        std::cerr << "No OpenCL platforms found." << std::endl;
        return 1;
    }

    std::vector<cl_platform_id> platforms(num_platforms);
    err = clGetPlatformIDs(num_platforms, platforms.data(), nullptr);

    cl_platform_id platform = platforms[0];

    cl_uint num_devices;
    err = clGetDeviceIDs(platform, CL_DEVICE_TYPE_ALL, 0, nullptr, &num_devices);
    checkError(err, "clGetDeviceIDs count");

    if (num_devices == 0) {
        std::cerr << "No OpenCL devices found." << std::endl;
        return 1;
    }

    std::vector<cl_device_id> devices(num_devices);
    err = clGetDeviceIDs(platform, CL_DEVICE_TYPE_ALL, num_devices, devices.data(), nullptr);

    cl_device_id device = devices[0];

    // 2. Create Context & Command Queue
    cl_context context = clCreateContext(nullptr, 1, &device, nullptr, nullptr, &err);
    cl_command_queue queue = clCreateCommandQueue(context, device, 0, &err);

    // 3. Load & Build Kernel
    std::ifstream kernelFile("kernel.cl");
    if (!kernelFile.is_open()) {
        std::cerr << "Failed to open kernel.cl" << std::endl;
        return 1;
    }

    std::stringstream buffer;
    buffer << kernelFile.rdbuf();
    std::string kernelSource = buffer.str();
    const char* sourcePtr = kernelSource.c_str();
    size_t sourceSize = kernelSource.length();

    cl_program program = clCreateProgramWithSource(context, 1, &sourcePtr, &sourceSize, &err);
    err = clBuildProgram(program, 1, &device, nullptr, nullptr, nullptr);
    if (err != CL_SUCCESS) {
        size_t log_size;
        clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, 0, nullptr, &log_size);
        std::vector<char> build_log(log_size);
        clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, log_size, build_log.data(), nullptr);

        std::cerr << "[KERNEL_BUILD_ERROR]\n" << build_log.data() << std::endl;
        return 1;
    }

    cl_kernel kernel = clCreateKernel(program, "multiply_by_two", &err);

    // 4. Setup Data
    const int num_elements = 5;
    std::vector<float> A = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    std::vector<float> B(num_elements, 0.0f);

    size_t buffer_size = sizeof(float) * num_elements;

    cl_mem d_A = clCreateBuffer(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, buffer_size, A.data(), &err);
    cl_mem d_B = clCreateBuffer(context, CL_MEM_WRITE_ONLY, buffer_size, nullptr, &err);

    // 5. Run Kernel
    err = clSetKernelArg(kernel, 0, sizeof(cl_mem), &d_A);
    err |= clSetKernelArg(kernel, 1, sizeof(cl_mem), &d_B);
    int num_elements_arg = num_elements;
    err |= clSetKernelArg(kernel, 2, sizeof(int), &num_elements_arg);

    size_t global_work_size = num_elements;
    err = clEnqueueNDRangeKernel(queue, kernel, 1, nullptr, &global_work_size, nullptr, 0, nullptr, nullptr);

    // 6. Read Results
    err = clEnqueueReadBuffer(queue, d_B, CL_TRUE, 0, buffer_size, B.data(), 0, nullptr, nullptr);

    // 7. Verify Results in Host Code
    bool passed = true;
    for (int i = 0; i < num_elements; ++i) {
        float expected = A[i] * 2.0f;
        if (std::abs(B[i] - expected) > 1e-5) {
            std::cerr << "mismatch at index " << i << ": expected " << expected << " but got " << B[i] << std::endl;
            passed = false;
        }
    }

    if (passed) {
        std::cout << "PASS" << std::endl;
    } else {
        std::cout << "FAIL" << std::endl;
    }

    // 8. Cleanup
    clReleaseMemObject(d_A);
    clReleaseMemObject(d_B);
    clReleaseKernel(kernel);
    clReleaseProgram(program);
    clReleaseCommandQueue(queue);
    clReleaseContext(context);

    return passed ? 0 : 1;
}