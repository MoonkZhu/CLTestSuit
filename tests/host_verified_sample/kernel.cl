__kernel void multiply_by_two(__global const float *A, __global float *B, int num_elements) {
    int i = get_global_id(0);
    if (i < num_elements) {
        B[i] = A[i] * 2.0f;
    }
}