cmake_minimum_required(VERSION 3.19)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)
project(MoonSurface)
include_directories(/opt/homebrew/include)
add_executable(MoonSurface moonsurface.cpp dem.cpp dem.h)

find_package(cxxopts REQUIRED)
target_link_libraries(MoonSurface cxxopts::cxxopts)

find_package(GDAL CONFIG REQUIRED)
target_link_libraries(MoonSurface GDAL::GDAL)
