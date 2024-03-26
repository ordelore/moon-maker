#include "dem.h"
#include <iostream>
#include <cmath>

SingleDEM::SingleDEM(std::string filename) {
    this->dem = GDALDataset::FromHandle(GDALOpen(filename.c_str(), GA_ReadOnly));
    this->band = this->dem->GetRasterBand(1);
    this->sphereRadius = this->dem->GetSpatialRef()->GetSemiMajor();

    OGRSpatialReferenceH ref = GDALGetSpatialRef(this->dem);
    OGRSpatialReferenceH latLonRef = OSRCloneGeogCS(ref);

    OSRSetAxisMappingStrategy(latLonRef, OAMS_TRADITIONAL_GIS_ORDER);
    OSRSetAngularUnits(latLonRef, SRS_UA_DEGREE, CPLAtof(SRS_UA_DEGREE_CONV));
    
    this->latLonToGeoTransformation = OCTNewCoordinateTransformation(latLonRef, ref);

    OGRCoordinateTransformationH geoToLatLonTransformation = OCTNewCoordinateTransformation(ref, latLonRef);

    double imageSpaceToGeoSpace[6];
    this->dem->GetGeoTransform(imageSpaceToGeoSpace);
    
    if (!GDALInvGeoTransform(imageSpaceToGeoSpace, this->geoSpaceToImageSpace)) {
        std::cout << "Failed to invert geotransform" << std::endl;
        this->geoSpaceToImageSpace[0] = 0.0;
        this->geoSpaceToImageSpace[1] = 1.0;
        this->geoSpaceToImageSpace[2] = 0.0;
        this->geoSpaceToImageSpace[3] = 0.0;
        this->geoSpaceToImageSpace[4] = 0.0;
        this->geoSpaceToImageSpace[5] = 1.0;
    }
    this->pixelSize = imageSpaceToGeoSpace[1] * imageSpaceToGeoSpace[5];

    this->circumnavigates = false;
    const char *projectionName = this->dem->GetSpatialRef()->GetAttrValue("projection");
    if (!strcmp(projectionName, SRS_PT_EQUIRECTANGULAR)) {
        // see if the dataset has a longitude extent of 360 degrees. If so, set this->circumnavigates to true
        double min_lon, max_lon;
        
        // calculate min_lon
        double x = 0;
        double y = 0;
        double image_row, image_column;
        image_column = imageSpaceToGeoSpace[0] + imageSpaceToGeoSpace[1] * x + imageSpaceToGeoSpace[2] * y;
        image_row = imageSpaceToGeoSpace[3] + imageSpaceToGeoSpace[4] * x + imageSpaceToGeoSpace[5] * y;
        (void)OCTTransform(geoToLatLonTransformation, 1, &image_column, &image_row, NULL);
        min_lon = image_column;

        x = this->dem->GetRasterXSize();
        y = this->dem->GetRasterYSize();
        image_column = imageSpaceToGeoSpace[0] + imageSpaceToGeoSpace[1] * x + imageSpaceToGeoSpace[2] * y;
        image_row = imageSpaceToGeoSpace[3] + imageSpaceToGeoSpace[4] * x + imageSpaceToGeoSpace[5] * y;
        (void)OCTTransform(geoToLatLonTransformation, 1, &image_column, &image_row, NULL);
        max_lon = image_column;
        // way of saying it's basically 0

        if (fabs(max_lon + min_lon) <= 1e-8) {
            this->circumnavigates = true;
        }
    }

}
// finds the value at the lat lon position in the DEM
// if the position is not in the DEM, return 1 and don't update outVal or valResolution
// if the resolution of the DEM is lower than the resolution of the output, don't update outVal
int SingleDEM::sample(float *outVal, float lat, float lon) {
    if (lat > 90) {
        lat = 180 - lat;
        lon += 180;
    }
    if (lat < -90) {
        lat = -180 - lat;
        lon += 180;
    }
    double x = lon;
    double y = lat;
    
    // convert lat lon to geo space
    if (!OCTTransform(this->latLonToGeoTransformation, 1, &x, &y, NULL)) {
        return 1;
    }
    
    // convert geo space to image space
    double image_row, image_column;
    image_column = this->geoSpaceToImageSpace[0] + this->geoSpaceToImageSpace[1] * x + this->geoSpaceToImageSpace[2] * y;
    image_row = this->geoSpaceToImageSpace[3] + this->geoSpaceToImageSpace[4] * x + this->geoSpaceToImageSpace[5] * y;
    
    int column_floor = (int)floor(image_column);
    int column_ceil = (int)ceil(image_column);
    int row_floor = (int)floor(image_row);
    int row_ceil = (int)ceil(image_row);
    // if the pixel is beyond beyonds, instantly return
    if (image_row < 0 || image_row >= this->dem->GetRasterYSize() || row_ceil >= this->dem->GetRasterYSize()) {
        return 1;
    }
    // if the DEM circumnavigates the globe, then the column will always be contained in its bounds.
    if (this->circumnavigates) {
        if (column_floor < 0) {
            column_floor += this->dem->GetRasterXSize();
        }
        if (column_ceil < 0) {
            column_ceil += this->dem->GetRasterXSize();
        }
        if (column_floor >= this->dem->GetRasterXSize()) {
            column_floor -= this->dem->GetRasterXSize();
        }
        if (column_ceil >= this->dem->GetRasterXSize()) {
            column_ceil -= this->dem->GetRasterXSize();
        }

    } else {
        if (image_column < 0 || image_column >= this->dem->GetRasterXSize() || column_ceil >= this->dem->GetRasterXSize()) {
            return 1;
        }
    }

    // get the value at the image space position by sampling the raster band at each corner
    // and interpolating the value. If any of the corners are not defined, return 1
    float val;
    // top left corner
    (void)this->band->RasterIO(GF_Read, column_floor, row_floor, 1, 1, &val, 1, 1, GDT_Float32, 0, 0);
    float val_tl = val;
    if (this->band->GetNoDataValue() == val_tl) {
        return 1;
    }
    // top right corner
    (void)this->band->RasterIO(GF_Read, column_ceil, row_floor, 1, 1, &val, 1, 1, GDT_Float32, 0, 0);
    float val_tr = val;
    if (this->band->GetNoDataValue() == val_tr) {
        return 1;
    }
    // bottom left corner
    (void)this->band->RasterIO(GF_Read, column_floor, row_ceil, 1, 1, &val, 1, 1, GDT_Float32, 0, 0);
    float val_bl = val;
    if (this->band->GetNoDataValue() == val_bl) {
        return 1;
    }
    // bottom right corner
    (void)this->band->RasterIO(GF_Read, column_ceil, row_ceil, 1, 1, &val, 1, 1, GDT_Float32, 0, 0);
    float val_br = val;
    if (this->band->GetNoDataValue() == val_br) {
        return 1;
    }

    // interpolate the value
    float x_frac = image_column - floor(image_column);
    float y_frac = image_row - floor(image_row);
    float val_t = val_tl + (val_tr - val_tl) * x_frac;
    float val_b = val_bl + (val_br - val_bl) * x_frac;
    float val_interp = val_t + (val_b - val_t) * y_frac;
        
    // the dem is just an elevation above the sphere radius, so add the sphere radius to get the distance from the center to the surface
    *outVal = val_interp + this->sphereRadius;

    return 0;
}

void SingleDEM::close() {
    GDALClose(this->dem);
}

DEMManager::DEMManager(std::vector<std::string> filenames) {
    for (std::string filename : filenames) {
        this->dems.push_back(SingleDEM(filename));
    }
}

float DEMManager::sample(float lat, float lon) {
    float val = -INFINITY;
    double demResolution = INFINITY;
    for (SingleDEM dem : this->dems) {
        float val2;
        if (!dem.sample(&val2, lat, lon)) {
            if (fabs(dem.pixelSize) < demResolution) {
                val = val2;
                demResolution = dem.pixelSize;
            }
        }
    }
    if (val == -INFINITY) {
        std::cout << "No DEMs contained the point " << lat << " " << lon << std::endl;
    }
    return val;
}

void DEMManager::getCartesian(std::array<float, 3> *outPoint, float lat, float lon) {
    float val = this->sample(lat, lon);
    float lat_radians = lat * M_PI / 180.0;
    float lon_radians = lon * M_PI / 180.0;
    (*outPoint)[0] = val * cos(lat_radians) * cos(lon_radians);
    (*outPoint)[1] = val * cos(lat_radians) * sin(lon_radians);
    (*outPoint)[2] = val * sin(lat_radians);
    return;
}

void DEMManager::getCartesian(std::array<float, 3> *outPoint, float lat, float lon, float scale) {
    this->getCartesian(outPoint, lat, lon);
    (*outPoint)[0] *= scale;
    (*outPoint)[1] *= scale;
    (*outPoint)[2] *= scale;
    return;
}

void DEMManager::getCartesian(std::array<float, 3> *outPoint, float lat, float lon, float center_lat, float center_lon, float center_elevation) {
    this->getCartesian(outPoint, lat, lon);
    
    // rotate the point by center lon degrees around the z axis
    float center_lon_radians = center_lon * M_PI / 180.0;
    float rotated_x = (*outPoint)[0] * cos(center_lon_radians) + (*outPoint)[1] * sin(center_lon_radians);
    float rotated_y = -(*outPoint)[0] * sin(center_lon_radians) + (*outPoint)[1] * cos(center_lon_radians);
    float rotated_z = (*outPoint)[2];

    // rotate the point by -(90 - center lat) degrees around the y axis
    float center_lat_radians = (-(90 - center_lat)) * M_PI / 180.0;
    float global_x = rotated_x * cos(center_lat_radians) + rotated_z * sin(center_lat_radians);
    float global_y = rotated_y;
    float global_z = -rotated_x * sin(center_lat_radians) + rotated_z * cos(center_lat_radians);

    // translate the point down by center elevation
    (*outPoint)[0] = global_x;
    (*outPoint)[1] = global_y;
    (*outPoint)[2] = global_z - center_elevation;
    return;
}

void DEMManager::getCartesian(std::array<float, 3> *outPoint, float lat, float lon, float center_lat, float center_lon, float center_elevation, float scale) {
    this->getCartesian(outPoint, lat, lon, center_lat, center_lon, center_elevation);
    (*outPoint)[0] *= scale;
    (*outPoint)[1] *= scale;
    (*outPoint)[2] *= scale;
    return;
}

void DEMManager::close() {
    for (SingleDEM dem : this->dems) {
        dem.close();
    }
}
