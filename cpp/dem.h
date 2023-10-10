#pragma once
#include <string>
#include <gdal_priv.h>

class SingleDEM {
    // constructor that takes a filename
    // function that samples a point from the DEM
    private:
        GDALDataset *dem;
        GDALRasterBand *band;
        OGRCoordinateTransformationH latLonToGeoTransformation;
        double geoSpaceToImageSpace[6];
        double sphereRadius;
    public: 
        double pixelSize;
        SingleDEM(std::string filename);
        int sample(float *outVal, float lat, float lon);
        void close();
};

class DEMManager {
    // constructor that takes a list of filenames
    // function that samples a point from the DEM
    private:
        std::vector<SingleDEM> dems;
    public: 
        DEMManager(std::vector<std::string> filenames);
        float sample(float lat, float lon);
        std::vector<float> getCartesian(float lat, float lon);
        std::vector<float> getCartesian(float lat, float lon, float center_lat, float center_lon, float center_elevation);
        void close();
};
