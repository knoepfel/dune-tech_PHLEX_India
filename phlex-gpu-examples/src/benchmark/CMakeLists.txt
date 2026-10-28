cmake_minimum_required(VERSION 3.31)

# Compile for the GPU(s) on this machine unless told otherwise, for example
#   cmake -DCMAKE_CUDA_ARCHITECTURES="80;90" ...
# 'native' needs a GPU visible when you run cmake. Must be set before project().
if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
  set(CMAKE_CUDA_ARCHITECTURES native)
endif()

project(phlex_gpu_benchmark VERSION 0.0.1 LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 23) # the Phlex plugins
set(CMAKE_CUDA_STANDARD 17) # the .cu file; nvcc never sees a Phlex header

# A benchmark should be optimized even if nobody asked for a build type
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(Boost REQUIRED json)
find_package(TBB REQUIRED)
find_package(spdlog REQUIRED)
find_package(phlex REQUIRED)
find_package(CUDAToolkit REQUIRED)

# The same strict warnings as phlex-examples, for C++ only: nvcc rejects -Wpedantic and the
# -Wno-* flags, so every option is wrapped in a COMPILE_LANGUAGE:CXX generator expression.
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  if(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "14.1")
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "15")
      add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wno-stringop-overflow>)
    endif()
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "16")
      add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wno-array-bounds>)
    endif()
  endif()
endif()
add_compile_options("$<$<COMPILE_LANGUAGE:CXX>:-Wall;-Wpedantic;-Werror>")

# Framework-agnostic experiment library, written in CUDA
# N.B. The library type should be SHARED.
add_library(my_saxpy_bench SHARED my_saxpy_bench.cu)
# Link the shared CUDA runtime, and record where it is (RUNPATH): CMake counts the CUDA library
# directory as one of nvcc's own, so it would leave it out, and neither the linker nor phlex
# could then find libcudart.so when a program or plugin uses this library.
set_target_properties(my_saxpy_bench PROPERTIES CUDA_RUNTIME_LIBRARY Shared BUILD_RPATH "${CUDAToolkit_LIBRARY_DIR}")
target_link_libraries(my_saxpy_bench PRIVATE CUDA::cudart)

# The same library without Phlex: a plain program
add_executable(bench_standalone bench_standalone.cpp)
target_link_libraries(bench_standalone PRIVATE my_saxpy_bench)

# Phlex plugins (MODULE libraries, loaded by phlex at run time)
add_library(problem_size_source MODULE problem_size_source.cpp)
target_link_libraries(problem_size_source PRIVATE phlex::module)

add_library(saxpy_bench_and_record MODULE saxpy_bench_and_record.cpp)
target_link_libraries(saxpy_bench_and_record PRIVATE phlex::module my_saxpy_bench)
# Keep assert() active in a Release build: the observer checks the GPU answer with assert
target_compile_options(saxpy_bench_and_record PRIVATE -UNDEBUG)
