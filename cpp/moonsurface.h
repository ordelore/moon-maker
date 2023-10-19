#pragma once
#include <string>
#include "dem.h"
struct MoonSurfaceOptions {
    float latlon[2];
    float min_latlon[2];
    float latlon_extent[2];
    float verts_per_degree;
    float scale;
    int threads;
    bool rotate_flat;
    std::vector<std::string> dem_paths;
    std::string output;
};

struct BagOfState {
    int thread_idx;
    int thread_count;
    int vertices_width;
    int vertices_height;
    MoonSurfaceOptions *options;
    std::vector<std::array<float, 3>> *vertices;
};
