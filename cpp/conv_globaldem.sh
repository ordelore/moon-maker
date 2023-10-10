#!/bin/sh
src_dem=$1
# pixel limits
W=`gdalinfo $1 | grep "Size is" | sed "s/Size is //" | sed "s/,.*//"`
H=`gdalinfo $1 | grep "Size is" | sed "s/Size is //" | sed "s/.*, //"`
echo $W $H
HW=$(($W / 2))
# geo limits of the output
srsinfo=`gdalsrsinfo -o proj4 $src_dem`
topLeft=`echo -180 90 | proj $srsinfo`
topCenter=`echo 0 90 | proj $srsinfo`
bottomCenter=`echo 0 -90 | proj $srsinfo`
bottomRight=`echo 180 -90 | proj $srsinfo`

gdal_translate -srcwin 0 0 $HW $H -a_ullr $topCenter $bottomRight $src_dem dem_right.vrt
gdal_translate -srcwin $HW 0 $HW $H -a_ullr $topLeft $bottomCenter $src_dem dem_left.vrt
gdalbuildvrt dem.vrt dem_left.vrt dem_right.vrt
gdal_translate dem.vrt dem.IMG
rm dem.vrt dem_left.vrt dem_right.vrt