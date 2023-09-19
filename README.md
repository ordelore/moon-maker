# Moon Mesh Maker

## Installation

After cloning this repo into a folder, run the following commands to install the dependencies:

```bash
pip3 install -r requirements.txt
```

## Source Data

For my videos, I started with the DEM and diffuse data from NASA's Goddard Space Flight Center's Scientific Visualization Studio's CGI Moon kit at <https://svs.gsfc.nasa.gov/4720>.

Later, I stitched DTM data from the LROC accessible at <https://wms.lroc.asu.edu/lroc/view_rdr/WAC_GLD100>.

Due to large file sizes, none of the source data is included in this repo. You will need to download the data yourself.

## Limitations

The source textures must be cylindrical projections centered at (0,0). The output meshes also assume the Moon is a sphere. If you try to use data from non-spherical bodies, the mesh will not be accurate.

## Usage

First, run the following command to generate a `.pkl` file containing the mesh data

```bash
usage: python3 moonsurface.py [-h] --latlon LAT LON --angular-extents LAT_EXTENT LON_EXTENT --pixels-per-degree PIXELS_PER_DEGREE --dem-path DEM_PATH --img-path IMG_PATH --base-sphere-radius BASE_SPHERE_RADIUS [--scale SCALE] [--output OUTPUT] [--threads THREADS] [--use-offset]

Create a mesh from a DEM

options:
  -h, --help            show this help message and exit
  --latlon LATLON LATLON
                        The latitude and longitude of the center of the mesh
  --angular-extents ANGULAR_EXTENTS ANGULAR_EXTENTS
                        The angular extents of the mesh in degrees
  --pixels-per-degree PIXELS_PER_DEGREE
                        The number of pixels per degree in the DEM
  --dem-path DEM_PATH   The path to the DEM
  --img-path IMG_PATH   The path to the diffuse texture image
  --base-sphere-radius BASE_SPHERE_RADIUS
                        The radius of the base sphere
  --scale SCALE         The scale of the mesh. Defaults to 1
  --output OUTPUT       The base of output filenames. The mesh will be saved as <output>.pkl and the texture will be saved as <output>.TIF. Defaults to moon_mesh
  --threads THREADS     The number of threads to use. Defaults to 1
  --use-offset          Places mesh's center at (0,0,0) and rotates the mesh so it is roughly parallel to the xy plane. Defaults to False
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
