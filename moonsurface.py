import math

def lat_lon_to_uv(lat, lon):
    return (lon / 360 + 0.5, 0.5 + lat / 180)

def cutout_img_lat_lon(min_latlon, max_latlon, img_path):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    base_uv = lat_lon_to_uv(min_latlon[0], min_latlon[1])
    # upper right uv
    extent_uv = lat_lon_to_uv(max_latlon[0], max_latlon[1])
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
            return img_mosaic.crop((left, top, right, bottom))

def process_pixel(lat_lon, min_lat_lon, angular_extents, img, center_lat_lon, base_radius, scale, offset):
    dlat = (lat_lon[0] - min_lat_lon[0]) / angular_extents[0]
    dlon = (lat_lon[1] - min_lat_lon[1]) / angular_extents[1]
    
    # convert the lat lon to uv coordinates
    dem_x = (img.size[0] * dlon) % img.size[0]
    dem_y = (img.size[1] - img.size[1] * dlat) % img.size[1]
    dem_pixel = (img.getpixel((dem_x, dem_y)) + base_radius) * scale
    x = dem_pixel * math.cos(math.radians(lat_lon[0])) * math.cos(math.radians(lat_lon[1]))
    y = dem_pixel * math.cos(math.radians(lat_lon[0])) * math.sin(math.radians(lat_lon[1]))
    z = dem_pixel * math.sin(math.radians(lat_lon[0]))
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

def create_mesh_file(center_lat_lon, angular_extents, img_path, outfile, use_offset, date, time, ephemeris_path):
    import PIL.Image as Image
    import pickle
    from jplephem.spk import SPK
    import datetime
    import jdcal

    Image.MAX_IMAGE_PIXELS = None
    min_lat = center_lat_lon[0] - angular_extents[0] / 2
    min_lon = center_lat_lon[1] - angular_extents[1] / 2
    
    # calculate the sun angle
    sun_rot = (45,45,0)
    if date is not None and time is not None and ephemeris_path is not None:
        print("Calculating sun angle")
        dt = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
        jt = jdcal.gcal2jd(dt.year, dt.month, dt.day)
        jul = jt[0] + jt[1] + ((dt.hour + 12) % 24) / 24 + dt.minute / (24 * 60) + dt.second / (24 * 60 * 60)
        with SPK.open(ephemeris_path) as ephemeris:
            # position of the sun relative to the moon
            sun_to_earth = ephemeris[0, 3].compute(jul)
            earth_to_moon = ephemeris[3, 301].compute(jul)
            moon_to_sun = [earth_to_moon[i] + sun_to_earth[i] for i in range(3)]
            # find the angle of the sun relative to the direction the mesh is oriented
            if use_offset:
                # rotate the moon_to_sun vector by -center lon degrees around the z axis
                rot = math.radians(center_lat_lon[1])
                rotated_x = moon_to_sun[0] * math.cos(rot) + moon_to_sun[1] * math.sin(rot)
                rotated_y = -moon_to_sun[0] * math.sin(rot) + moon_to_sun[1] * math.cos(rot)
                rotated_z = moon_to_sun[2]
                
                # rotate the moon_to_sun vector by -(90 - center lat) degrees around the y axis
                rot = math.radians(-(90 - center_lat_lon[0]))
                moon_to_sun[0] = rotated_x * math.cos(rot) + rotated_z * math.sin(rot)
                moon_to_sun[1] = rotated_y
                moon_to_sun[2] = -rotated_x * math.sin(rot) + rotated_z * math.cos(rot)
            # calculate the angle of the sun
            sun_rot_x = math.atan2(moon_to_sun[1], moon_to_sun[2])
            sun_rot_y = math.atan2(moon_to_sun[0], moon_to_sun[2])
            sun_rot_z = 0
            sun_rot = (sun_rot_x, sun_rot_y, sun_rot_z)

    # generate the texture
    print("Generating texture")
    # lower left uv
    img_crop = cutout_img_lat_lon((min_lat, min_lon), (min_lat + angular_extents[0], min_lon + angular_extents[1]), img_path)
    img_crop.save(f"{outfile}.png")
    
    print("Saving to file")
    with open(f"{outfile}.pkl", "wb") as f:
        pickle.dump({"sun_rot": sun_rot}, f)


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
    
    moon_mesh = bpy.data.meshes.new("MoonMesh")
    with open(os.path.join(os.path.dirname(__file__), f"{meshfile}.mesh")) as cpp_output:
        meshlines = cpp_output.read().splitlines()
        vertices_width, vertices_height = [int(x) for x in meshlines[0].split(" ")]
        faces_width = vertices_width - 1
        faces_height = vertices_height - 1
        number_of_vertices = vertices_width * vertices_height
        number_of_edges = (vertices_width) * (vertices_height - 1) + (vertices_width - 1) * (vertices_height)
        vertex_lines = meshlines[1:number_of_vertices + 1]
        edges_lines = meshlines[number_of_vertices + 1:number_of_vertices + 1 + number_of_edges]
        faces_lines = meshlines[number_of_vertices + 1 + number_of_edges:]
        vertices = [[float(x) for x in line.split(" ")] for line in vertex_lines]
        edges = [[int(x) for x in line.split(" ")] for line in edges_lines]
        faces = [[int(x) for x in line.split(" ")] for line in faces_lines]
        print(f"Mesh contains {len(vertices)} vertices")
        moon_mesh.from_pydata(vertices, edges, faces)
            
    moon_object = bpy.data.objects.new("MoonObject", moon_mesh)
    bpy.context.collection.objects.link(moon_object)
    moonmesh_texture_filename = f"{meshfile}.png"
    if moonmesh_texture_filename in bpy.data.images:
        bpy.data.images[moonmesh_texture_filename].reload()
    else:
        bpy.data.images.load(os.path.join(os.path.dirname(__file__), moonmesh_texture_filename))
    # assign MoonMaterial to object
    if "MoonMaterial" in bpy.data.materials:
        moon_object.active_material = bpy.data.materials["MoonMaterial"]
    else:
        moon_object.active_material = bpy.data.materials.new(name="MoonMaterial")
        # assign MoonTexture to material
        moon_object.active_material.use_nodes = True
        moon_object.active_material.node_tree.nodes.clear()
        moon_object.active_material.node_tree.nodes.new("ShaderNodeTexImage")
        moon_object.active_material.node_tree.nodes["Image Texture"].image = bpy.data.images[moonmesh_texture_filename]
        moon_object.active_material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        moon_object.active_material.node_tree.nodes.new("ShaderNodeOutputMaterial")
        moon_object.active_material.node_tree.links.new(moon_object.active_material.node_tree.nodes["Image Texture"].outputs["Color"], moon_object.active_material.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        moon_object.active_material.node_tree.links.new(moon_object.active_material.node_tree.nodes["Principled BSDF"].outputs["BSDF"], moon_object.active_material.node_tree.nodes["Material Output"].inputs["Surface"])
        # set specular and roughness to 0
        moon_object.active_material.node_tree.nodes["Principled BSDF"].inputs["Specular"].default_value = 0
        moon_object.active_material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0
    
    # if the material already exists, check if the texture needs to be updated
    if moon_object.active_material.node_tree.nodes["Image Texture"].image != bpy.data.images[moonmesh_texture_filename]:
        moon_object.active_material.node_tree.nodes["Image Texture"].image = bpy.data.images[moonmesh_texture_filename]
    # Loops per face
    moon_uv = moon_mesh.uv_layers.new(name="UVMap")
    # the lower left corner of the uv map for the whole mesh
    base_uv = (0,0)
    # the upper right corner of the uv map for the whole mesh
    extent_uv = (1,1)

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
    
    # set the angle of the sun
    if "Sun" in bpy.data.objects:
        bpy.data.objects["Sun"].rotation_euler = mesh["sun_rot"][0], mesh["sun_rot"][1], mesh["sun_rot"][2]
    else:
        sunlight = bpy.data.lights.new(name="Sun", type="SUN")
        sunobject = bpy.data.objects.new(name="Sun", object_data=sunlight)
        bpy.context.collection.objects.link(sunobject)
        sunobject.rotation_euler = mesh["sun_rot"][0], mesh["sun_rot"][1], mesh["sun_rot"][2]
        sunobject.location = (0,0,0)
        sunobject.data.energy = 1360
        sunobject.data.angle = math.radians(0.526)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create a mesh from a DEM')
    parser.add_argument('--latlon', type=float, nargs=2, required=True, help="The latitude and longitude of the center of the mesh")
    parser.add_argument('--angular-extents', type=float, nargs=2, required=True, help="The angular extents of the mesh in degrees")
    parser.add_argument('--img-path', type=str, required=True, help="The path to the diffuse texture image")
    parser.add_argument('--output', type=str, default="moon_mesh", help="The base of output filenames. The mesh will be saved as <output>.pkl and the texture will be saved as <output>.TIF. Defaults to moon_mesh")
    parser.add_argument('--rotate-flat', action='store_true', default=False, help="Places mesh's center at the origin and rotates the mesh so the center points in the positive z direction. Defaults to False")
    parser.add_argument('--date', type=str, default=None, help="The UTC date to use for the sun angle. Must be YYYY-MM-DD")
    parser.add_argument('--time', type=str, default=None, help="The UTC time to use for the sun angle. Must be HH:MM:SS")
    parser.add_argument('--ephemeris-path', type=str, default=None, help="The path to the ephemeris file.")

    args = parser.parse_args()
    create_mesh_file(args.latlon, args.angular_extents, args.img_path, args.output, args.rotate_flat, args.date, args.time, args.ephemeris_path)