import math

def lat_lon_to_uv(lat, lon):
    return (lon / 360 + 0.5, 0.5 + lat / 180)

def process_pixel(lat, lon, img, center_lat_lon, base_radius, scale, offset):
    # sanitize latitude and longitude
    if lat > 90:
        lat = 180 - lat
        lon += 180
    elif lat < -90:
        lat = -180 - lat
        lon += 180
    lon = (lon + 180) % 360 - 180
    # convert the lat lon to uv coordinates
    uvs = lat_lon_to_uv(lat, lon)
    dem_x = (img.size[0] * uvs[0]) % img.size[0]
    dem_y = (img.size[1] - img.size[1] * uvs[1]) % img.size[1]
    
    dem_pixel = (img.getpixel((dem_x, dem_y)) + base_radius) * scale
    x = dem_pixel * math.cos(math.radians(lat)) * math.cos(math.radians(lon))
    y = dem_pixel * math.cos(math.radians(lat)) * math.sin(math.radians(lon))
    z = dem_pixel * math.sin(math.radians(lat))
    if not offset:
        return (x,y,z)
    if offset != 0:
        # rotate the point by -center lon degrees around the z axis
        rot = math.radians(center_lat_lon[1])
        rotated_x = x * math.cos(rot) + y * math.sin(rot)
        rotated_y = -x * math.sin(rot) + y * math.cos(rot)
        rotated_z = z
        # rotate the point by -(90 - center lat) degrees around the y axis
        rot = math.radians(-(90 - center_lat_lon[0]))
        global_x = rotated_x * math.cos(rot) + rotated_z * math.sin(rot)
        global_y = rotated_y
        global_z = -rotated_x * math.sin(rot) + rotated_z * math.cos(rot)
        
        return (global_x, global_y, global_z - (offset + base_radius) * scale)

def create_mesh_file(center_lat_lon, angular_extents, pixels_per_degree, dem_path, base_sphere_radius, scale, img_path, outfile, threads, use_offset, skip_texture):
    import multiprocessing as mp
    import PIL.Image as Image
    import pickle
    Image.MAX_IMAGE_PIXELS = None
    image_pixel_height = angular_extents[0] * pixels_per_degree
    image_pixel_width = angular_extents[1] * pixels_per_degree
    min_lat = center_lat_lon[0] - angular_extents[0] / 2
    lat_range = [min_lat + pxl_idx / pixels_per_degree for pxl_idx in range(image_pixel_height)]
    min_lon = center_lat_lon[1] - angular_extents[1] / 2
    lon_range = [min_lon + pxl_idx / pixels_per_degree for pxl_idx in range(image_pixel_width)]
    
    print("Generating vertices")
    # get the value of the dem pixel at the center lat lon
    with mp.Pool(threads) as pool:
        with Image.open(dem_path) as img:
            center_value = 0
            if use_offset:
                center_latlon_uv = lat_lon_to_uv(center_lat_lon[0], center_lat_lon[1])
                center_x = (img.size[0] * center_latlon_uv[0]) % img.size[0]
                center_y = (img.size[1] - img.size[1] * center_latlon_uv[1]) % img.size[1]
                center_value = img.getpixel((center_x, center_y))
            verts = pool.starmap(process_pixel, [(lat, lon, img, center_lat_lon, base_sphere_radius, scale, center_value) for lat in lat_range for lon in lon_range])
    # connect the edges
    edges = []
    # latitude edges
    for lat_idx in range(image_pixel_height - 1):
        row_offset = lat_idx * image_pixel_width
        edges.extend([(lon_idx + row_offset, lon_idx + row_offset + 1) for lon_idx in range(image_pixel_width - 1)])
    # longitude edges
    for lon_idx in range(image_pixel_width - 1):
        edges.extend([(lon_idx + image_pixel_width * lat_idx, lon_idx + image_pixel_width * (lat_idx+1)) for lat_idx in range(image_pixel_height - 1)])
    # faces
    faces = []
    for lat_idx in range(image_pixel_height - 1):
        row_offset = lat_idx * image_pixel_width
        faces.extend([(lon_idx + row_offset, lon_idx + row_offset + 1, lon_idx + row_offset + 1 + image_pixel_width, lon_idx + row_offset + image_pixel_width) for lon_idx in range(image_pixel_width-1)])
    with open(f"{outfile}.pkl", "wb") as f:
        pickle.dump({"verts": verts, "edges": edges, "faces": faces, "faces_width": image_pixel_width - 1, "faces_height": image_pixel_height - 1}, f)
    del verts
    del edges
    del faces
    if not skip_texture:
        print("Generating texture")
        # lower left uv
        base_uv = lat_lon_to_uv(min_lat, min_lon)
        # upper right uv
        extent_uv = lat_lon_to_uv(min_lat + angular_extents[0], min_lon + angular_extents[1])
        # cut out the region defined by the uvs in the img_path
        with Image.open(img_path) as img:
            # create a 3x3 grid of the image with the top and bottom rows flipped form the original image
            with Image.new("RGB", (img.size[0] * 3, img.size[1] * 3)) as img_mosaic:
                img_mosaic.paste(img.transpose(Image.FLIP_TOP_BOTTOM), (img.size[0] // 2, 0))
                img_mosaic.paste(img.transpose(Image.FLIP_TOP_BOTTOM), (3 * img.size[0] // 2, 0))
                img_mosaic.paste(img, (0, img.size[1]))
                img_mosaic.paste(img, (img.size[0], img.size[1]))
                img_mosaic.paste(img, (2*img.size[0], img.size[1]))
                img_mosaic.paste(img.transpose(Image.FLIP_TOP_BOTTOM), (img.size[0] // 2, 2 * img.size[1]))
                img_mosaic.paste(img.transpose(Image.FLIP_TOP_BOTTOM), (3 * img.size[0] // 2, 2 * img.size[1]))

                # crop the image to the region defined by the uvs while correcting for the new image mosaic
                base_uv = (base_uv[0] + 1, base_uv[1] + 1)
                extent_uv = (extent_uv[0] + 1, extent_uv[1] + 1)

                left = img.size[0] * base_uv[0]
                right = img.size[0] * extent_uv[0]
                top = img_mosaic.size[1] - img.size[1] * extent_uv[1]
                bottom = img_mosaic.size[1] - img.size[1] * base_uv[1]
                img_crop = img_mosaic.crop((left, top, right, bottom))
                img_crop.save(f"{outfile}.TIF")


def create_moon(meshfile="moon_mesh"):
    import bpy
    import pickle
    import os

    if "MoonMesh" in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes["MoonMesh"])
    if "MoonObject" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["MoonObject"])
    with open(os.path.join(os.path.dirname(__file__), f"{meshfile}.pkl"), "rb") as f:
        mesh = pickle.load(f)
    print(f"Mesh contains {len(mesh['verts'])} vertices")
    
    moon_mesh = bpy.data.meshes.new("MoonMesh")
    moon_mesh.from_pydata(mesh["verts"], mesh["edges"], mesh["faces"])

    moon_object = bpy.data.objects.new("MoonObject", moon_mesh)
    bpy.context.collection.objects.link(moon_object)
    if f"{meshfile}.TIF" in bpy.data.images:
        bpy.data.images[f"{meshfile}.TIF"].reload()
    else:
        bpy.data.images.load(os.path.join(os.path.dirname(__file__), f"{meshfile}.TIF"))
    # assign MoonMaterial to object
    if "MoonMaterial" in bpy.data.materials:
        moon_object.active_material = bpy.data.materials["MoonMaterial"]
    else:
        moon_object.active_material = bpy.data.materials.new(name="MoonMaterial")
        # assign MoonTexture to material
        moon_object.active_material.use_nodes = True
        moon_object.active_material.node_tree.nodes.clear()
        moon_object.active_material.node_tree.nodes.new("ShaderNodeTexImage")
        moon_object.active_material.node_tree.nodes["Image Texture"].image = bpy.data.images[f"{meshfile}.TIF"]
        moon_object.active_material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        moon_object.active_material.node_tree.nodes.new("ShaderNodeOutputMaterial")
        moon_object.active_material.node_tree.links.new(moon_object.active_material.node_tree.nodes["Image Texture"].outputs["Color"], moon_object.active_material.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        moon_object.active_material.node_tree.links.new(moon_object.active_material.node_tree.nodes["Principled BSDF"].outputs["BSDF"], moon_object.active_material.node_tree.nodes["Material Output"].inputs["Surface"])
        # set specular and roughness to 0
        moon_object.active_material.node_tree.nodes["Principled BSDF"].inputs["Specular"].default_value = 0
        moon_object.active_material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0
    
    # if the material already exists, check if the texture needs to be updated
    if moon_object.active_material.node_tree.nodes["Image Texture"].image != bpy.data.images[f"{meshfile}.TIF"]:
        moon_object.active_material.node_tree.nodes["Image Texture"].image = bpy.data.images[f"{meshfile}.TIF"]
    # Loops per face
    moon_uv = moon_mesh.uv_layers.new(name="UVMap")
    # the lower left corner of the uv map for the whole mesh
    base_uv = (0,0)
    # the upper right corner of the uv map for the whole mesh
    extent_uv = (1,1)
    # the number of faces in the width of the mesh
    faces_width = mesh["faces_width"]
    # the number of faces in the height of the mesh
    faces_height = mesh["faces_height"]
    # for each face, calculate the uv coordinates
    for face in moon_mesh.polygons:
        # the face index
        face_idx = face.index
        # the face's width index
        face_width_idx = face_idx % faces_width
        # the face's height index
        face_height_idx = face_idx // faces_width
        # the lower left corner of the face's uv map
        face_base_uv = (base_uv[0] + face_width_idx / (faces_width + 1) * (extent_uv[0] - base_uv[0]), base_uv[1] + face_height_idx / (faces_height + 1) * (extent_uv[1] - base_uv[1]))
        # the upper right corner of the face's uv map
        face_extent_uv = (base_uv[0] + (face_width_idx + 1) / (faces_width + 1) * (extent_uv[0] - base_uv[0]), base_uv[1] + (face_height_idx + 1) / (faces_height + 1) * (extent_uv[1] - base_uv[1]))
        # the face's uv coordinates
        face_uv = [face_base_uv, (face_extent_uv[0], face_base_uv[1]), face_extent_uv, (face_base_uv[0], face_extent_uv[1])]
        
        # assign the uv coordinates to the face
        for loop_idx, loop in enumerate(face.loop_indices):
            moon_uv.data[loop].uv = face_uv[loop_idx]
    

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create a mesh from a DEM')
    parser.add_argument('--latlon', type=int, nargs=2, required=True, help="The latitude and longitude of the center of the mesh")
    parser.add_argument('--angular-extents', type=int, nargs=2, required=True, help="The angular extents of the mesh in degrees")
    parser.add_argument('--pixels-per-degree', type=int, required=True, help="The number of pixels per degree in the DEM")
    parser.add_argument('--dem-path', type=str, required=True, help="The path to the DEM")
    parser.add_argument('--img-path', type=str, required=True, help="The path to the diffuse texture image")
    parser.add_argument('--base-sphere-radius', type=float, required=True, help="The radius of the base sphere")
    parser.add_argument('--scale', type=float, default=1, help="The scale of the mesh. Defaults to 1")
    parser.add_argument('--output', type=str, default="moon_mesh", help="The base of output filenames. The mesh will be saved as <output>.pkl and the texture will be saved as <output>.TIF. Defaults to moon_mesh")
    parser.add_argument('--threads', type=int, default=1, help="The number of threads to use. Defaults to 1")
    parser.add_argument('--use-offset', action='store_true', default=False, help="Places mesh's center at (0,0,0) and rotates the mesh so it is roughly parallel to the xy plane. Defaults to False")
    parser.add_argument('--skip-texture', action='store_true', default=False, help="Skips the texture generation step. Defaults to False")

    args = parser.parse_args()
    create_mesh_file(args.latlon, args.angular_extents, args.pixels_per_degree, args.dem_path, args.base_sphere_radius, args.scale, args.img_path, args.output, args.threads, args.use_offset, args.skip_texture)