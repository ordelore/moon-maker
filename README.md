# Moon Mesh Maker

## Installation

After cloning this repo into a folder, run the following command to install the Python dependencies:

```bash
pip3 install -r requirements.txt
```

To compile the C++ components, ensure that the `gdal`, `cxxopts`, and `libtiff` libraries are installed. Then go into the `cpp` directory and run the following commands:

```bash
mkdir build
cd build
cmake ..
make
```

## Source Data

For my videos, I started with the DEM and diffuse data from NASA's Goddard Space Flight Center's Scientific Visualization Studio's CGI Moon kit at <https://svs.gsfc.nasa.gov/4720>.

Later, I stitched DTM data from the LROC accessible at <https://wms.lroc.asu.edu/lroc/view_rdr/WAC_GLD100>.

I use JOL's planetary ephemeris from <https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/>.

Due to large file sizes, none of the source data is included in this repo. You will need to download the data yourself.

## Limitations

The source textures must be cylindrical projections centered at (0,0). The output meshes also assume the Moon is a sphere. If you try to use data from non-spherical bodies, the mesh will not be accurate.

## Usage

First, you will need to generate a mesh from the DEM. To do this, run `./cpp/build/MoonSurface` with the following arguments:

```text
A program to generate a moon surface
Usage:
  MoonSurface [OPTION...]

      --centerlat arg         Center Latitude
      --centerlon arg         Center Longitude
      --latextent arg         Latitude Width
      --lonextent arg         Longitude Height
      --verts-per-degree arg  Vertices Per Degree
      --scale arg             Scale (default: 1.0)
      --threads arg           Number of threads (default: 1)
      --rotate-flat           Transform mesh so the center latlon is facing 
                              z-up
      --dem-path arg          Path to DEM file. Can be used multiple times 
                              to load multiple DEM files.
      --output arg            Output file title (default: moonmesh)
  -h, --help                  Print help
```

Next, run `python moonsurface.py` with the following arguments to generate a `.pkl` file containing the sun position and image texture

```text
usage: moonsurface.py [-h] --latlon LATLON LATLON --angular-extents ANGULAR_EXTENTS ANGULAR_EXTENTS --img-path IMG_PATH [--output OUTPUT] [--rotate-flat] [--date DATE]
                      [--time TIME] [--ephemeris-path EPHEMERIS_PATH]

Create a mesh from a DEM

options:
  -h, --help            show this help message and exit
  --latlon LATLON LATLON
                        The latitude and longitude of the center of the mesh
  --angular-extents ANGULAR_EXTENTS ANGULAR_EXTENTS
                        The angular extents of the mesh in degrees
  --img-path IMG_PATH   The path to the diffuse texture image
  --output OUTPUT       The base of output filenames. The mesh will be saved as <output>.pkl and the texture will be saved as <output>.TIF. Defaults to moon_mesh
  --rotate-flat         Places mesh's center at the origin and rotates the mesh so the center points in the positive z direction. Defaults to False
  --date DATE           The UTC date to use for the sun angle. Must be YYYY-MM-DD
  --time TIME           The UTC time to use for the sun angle. Must be HH:MM:SS
  --ephemeris-path EPHEMERIS_PATH
                        The path to the ephemeris file.
```

After creating the file, create a Blender file and save it in the same directory as the repo. In the `Scripting` tab, open the `load_moon.py` script. If you used a different output name, change the `MESH_NAME` variable so it is the same as the one you used. Then, you can run the script to load the generated mesh into Blender.

## License

This project is licensed under the MIT License. See the license file for details.

## Credits

### CGI Moon Kit

NASA's Scientific Visualization Studio

- Visualizer: Ernie Wright (USRA) [Lead]
- Scientist: Noah Petro (NASA/GSFC)

### LROC Raw DTMs

Scholten, F., Oberst, J., Matz, K. D., Roatsch, T., Wählisch, M., Speyerer,
    E. J., & Robinson, M. S. (2012). GLD100: The near-global lunar 100 m raster
    DTM from LROC WAC stereo image data. Journal of Geophysical Research:
    Planets, 117(E12).
    <https://dx.doi.org/10.1029/2011JE003926>

Smith, D. E., Zuber, M. T., Neumann, G. A., Lemoine, F. G., Mazarico, E.,
    Torrence, M. H., McGarrey, J. F., Rowlands, D. D., Head, J. W., Duxbury,
    T. H., Aharonson, O., Lucey, P. G., Robinson, M. S., Barnouin, O. S.,
    Cavanaugh, J. F., Sun, X., Liiva, P., Mao, D., Smith, J.C., & Bartels, A. E.
    (2010). Initial observations from the lunar orbiter laser altimeter (LOLA).
    Geophysical Research Letters, 37(18).
    <https://dx.doi.org/10.1029/2010GL043751>
