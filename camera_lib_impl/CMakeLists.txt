cmake_minimum_required(VERSION 3.10)
project(global_shutter_rng CXX)  # Specify C++ language

find_package(PkgConfig REQUIRED)
pkg_check_modules(Libcamera REQUIRED libcamera)

add_executable(global_shutter_rng global_shutter_rng.cpp)  # Updated filename
target_include_directories(global_shutter_rng PRIVATE ${Libcamera_INCLUDE_DIRS})
target_link_libraries(global_shutter_rng ${Libcamera_LIBRARIES})
