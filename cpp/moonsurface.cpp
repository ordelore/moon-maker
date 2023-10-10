#include <iostream>
#include <fstream>
#include <tiffio.h>
#include <cxxopts.hpp>
#include <pthread.h>
#include "moonsurface.h"
#include "dem.h"
void *work_thread(void *state) {
    BagOfState *bag = (BagOfState *) state;
    DEMManager demManager = DEMManager(bag->options->dem_paths);

    float center_elevation = demManager.sample(bag->options->latlon[0], bag->options->latlon[1]);
    for (int coord_idx = bag->thread_idx; coord_idx < bag->vertices_height * bag->vertices_width; coord_idx += bag->thread_count) {
        int lat_idx = coord_idx / bag->vertices_width;
        int lon_idx = coord_idx % bag->vertices_width;
        std::vector<float> vertex;
        float lat = bag->options->min_latlon[0] + lat_idx / bag->options->verts_per_degree;
        float lon = bag->options->min_latlon[1] + lon_idx / bag->options->verts_per_degree;
        if (bag->options->rotate_flat) {
            vertex = demManager.getCartesian(lat, lon, bag->options->latlon[0], bag->options->latlon[1], center_elevation);
        } else {
            vertex = demManager.getCartesian(lat, lon);
        }
        int vert_idx = lat_idx * bag->vertices_width + lon_idx;
        (*bag->vertices)[vert_idx] = vertex;
        if (lat_idx < bag->vertices_height - 1) {
            int edge_idx = lat_idx * bag->vertices_width + lon_idx;
            (*bag->edges)[edge_idx] = {vert_idx, vert_idx + bag->vertices_width};
        }
        if (lon_idx < bag->vertices_width - 1) {
            int edge_idx = (bag->vertices_height -1 ) * bag->vertices_width + lat_idx * (bag->vertices_width - 1) + lon_idx;
            (*bag->edges)[edge_idx] = {vert_idx, vert_idx + 1};
        }
        if (lat_idx < bag->vertices_height - 1 && lon_idx < bag->vertices_width - 1) {
            int face_idx = lat_idx * (bag->vertices_width - 1) + lon_idx;
            (*bag->faces)[face_idx] = {vert_idx, vert_idx + bag->vertices_width, vert_idx + bag->vertices_width + 1, vert_idx + 1};
        }
    }

    demManager.close();
    
    return NULL;
}
int create_mesh(MoonSurfaceOptions meshOptions) {
    DEMManager demManager = DEMManager(meshOptions.dem_paths);
    // prepare file
    std::ofstream meshFile;
    meshFile.open(meshOptions.output + ".mesh");
    // write the dimensions of the faces in the file
    int vertices_height = floor(meshOptions.latlon_extent[0] * meshOptions.verts_per_degree) + 1;
    int vertices_width = floor(meshOptions.latlon_extent[1] * meshOptions.verts_per_degree) + 1;

    meshFile << vertices_width << " " << vertices_height << std::endl;

    std::cout << "Generating mesh" << std::endl;
    std::vector<std::vector<float>> vertices(vertices_width * vertices_height);
    std::vector<std::vector<int>> edges(vertices_width * (vertices_height - 1) + (vertices_width - 1) * vertices_height);
    std::vector<std::vector<int>> faces((vertices_height - 1) * (vertices_width - 1));

    pthread_t threads[meshOptions.threads];
    BagOfState bags[meshOptions.threads];
    for (int thread_idx = 0; thread_idx < meshOptions.threads; thread_idx++) {
        bags[thread_idx].thread_idx = thread_idx;
        bags[thread_idx].thread_count = meshOptions.threads;
        bags[thread_idx].vertices_width = vertices_width;
        bags[thread_idx].vertices_height = vertices_height;
        bags[thread_idx].options = &meshOptions;
        bags[thread_idx].vertices = &vertices;
        bags[thread_idx].edges = &edges;
        bags[thread_idx].faces = &faces;
        pthread_create(&threads[thread_idx], NULL, work_thread, &bags[thread_idx]);
    }
    // wait for each thread to finish
    for (int thread_idx = 0; thread_idx < meshOptions.threads; thread_idx++) {
        pthread_join(threads[thread_idx], NULL);
    }
    std::cout << "Writing vertices" << std::endl;
    for (std::vector<float> vertex : vertices) {
        meshFile << vertex[0] * meshOptions.scale << " " << vertex[1] * meshOptions.scale << " " << vertex[2] * meshOptions.scale << std::endl;
    }

    std::cout << "Writing edges" << std::endl;
    for (std::vector<int> edge : edges) {
        // std::cout << edge[0] << " " << edge[1] << std::endl;
        meshFile << edge[0] << " " << edge[1] << std::endl;
    }
    
    std::cout << "Writing faces" << std::endl;
    for (std::vector<int> face : faces) {
        meshFile << face[0] << " " << face[1] << " " << face[2] << " " << face[3] << std::endl;
    }
    
    std::cout << "Done" << std::endl;
    meshFile.close();
    return 0;
}

int argument_exists(std::string flag, cxxopts::Options options, cxxopts::ParseResult result) {
    if (result.count(flag) == 0) {
        std::cout << "Missing argument: " << flag << std::endl;
        std::cout << options.help() << std::endl;
        return 0;
    }
    return 1;
}

int main(int argc, char *argv[]) {
    cxxopts::Options options("MoonSurface", "A program to generate a moon surface");
    options.add_options()
        ("centerlat", "Center Latitude", cxxopts::value<double>())
        ("centerlon", "Center Longitude", cxxopts::value<double>())
        ("latextent", "Latitude Width", cxxopts::value<double>())
        ("lonextent", "Longitude Height", cxxopts::value<double>())
        ("verts-per-degree", "Vertices Per Degree", cxxopts::value<double>())
        ("scale", "Scale", cxxopts::value<double>()->default_value("1.0"))
        ("threads", "Number of threads", cxxopts::value<int>()->default_value("1"))
        ("rotate-flat", "Transform mesh so the center latlon is facing z-up", cxxopts::value<bool>()->default_value("false"))
        ("dem-path", "Path to DEM file. Can be used multiple times to load multiple DEM files.", cxxopts::value<std::vector<std::string>>())
        ("output", "Output file title", cxxopts::value<std::string>()->default_value("moonmesh"))
        ("h,help", "Print help")
        ;
    cxxopts::ParseResult result = options.parse(argc, argv);
    if (result.count("help")) {
        std::cout << options.help() << std::endl;
        return 0;
    }

    MoonSurfaceOptions meshOptions;
    if (!argument_exists("centerlat", options, result)) return 1;
    meshOptions.latlon[0] = result["centerlat"].as<double>();

    if (!argument_exists("centerlon", options, result)) return 1;
    meshOptions.latlon[1] = result["centerlon"].as<double>();

    if (!argument_exists("latextent", options, result)) return 1;
    meshOptions.latlon_extent[0] = result["latextent"].as<double>();

    if (!argument_exists("lonextent", options, result)) return 1;
    meshOptions.latlon_extent[1] = result["lonextent"].as<double>();

    meshOptions.min_latlon[0] = meshOptions.latlon[0] - meshOptions.latlon_extent[0] / 2.0;
    meshOptions.min_latlon[1] = meshOptions.latlon[1] - meshOptions.latlon_extent[1] / 2.0;
    if (!argument_exists("verts-per-degree", options, result)) return 1;
    meshOptions.verts_per_degree = result["verts-per-degree"].as<double>();

    meshOptions.scale = result["scale"].as<double>();
    meshOptions.threads = result["threads"].as<int>();
    meshOptions.rotate_flat = result["rotate-flat"].as<bool>();

    if (!argument_exists("dem-path", options, result)) return 1;
    meshOptions.dem_paths = result["dem-path"].as<std::vector<std::string>>();
    meshOptions.output = result["output"].as<std::string>();

    return create_mesh(meshOptions);
}