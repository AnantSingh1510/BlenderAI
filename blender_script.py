#!/usr/bin/env python3

import bpy
import bmesh
import random
import math
from mathutils import Vector, Euler
import sys
import os

print("Starting Blender script execution...")

try:
    # Configure render settings
    scene = bpy.context.scene

    # Try newer EEVEE first, fall back to regular EEVEE
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except:
        scene.render.engine = 'BLENDER_EEVEE'

    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = "C:/Users/anant/Documents/Anant's workspace/testAiAgent/outputs/render_20250719_151646.png"

    print("Render settings configured.")

    # Execute user script by importing it
    print("Executing user-generated code...")

    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Import the user script (this will execute it)
    user_module_name = "user_script_20250719_151646"
    try:
        __import__(user_module_name)
        print("User code executed successfully.")
    except Exception as e:
        print(f"Error executing user code: {e}")
        import traceback
        traceback.print_exc()
        if not True:
            sys.exit(1)

    # Get all mesh objects for camera positioning
    mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH']
    print(f"Found {len(mesh_objects)} mesh objects.")

    if mesh_objects:
        # Calculate scene bounds more carefully
        all_coords = []
        for obj in mesh_objects:
            try:
                # Skip very large ground planes from camera calculations
                if (hasattr(obj, 'name') and 'ground' in obj.name.lower() and 
                    any(dim > 8 for dim in obj.dimensions)):
                    continue

                for vertex in obj.bound_box:
                    world_coord = obj.matrix_world @ Vector(vertex)
                    all_coords.append(world_coord)
            except:
                continue

        if all_coords:
            min_coord = Vector((min(c.x for c in all_coords), min(c.y for c in all_coords), min(c.z for c in all_coords)))
            max_coord = Vector((max(c.x for c in all_coords), max(c.y for c in all_coords), max(c.z for c in all_coords)))
            center = (min_coord + max_coord) / 2
            size = max_coord - min_coord
            max_size = max(size.x, size.y, size.z)
            camera_distance = max(max_size * 2.5, 8)  # Better camera distance calculation

            # Ensure camera height is reasonable
            camera_height = max(center.z + max_size * 0.5, 3)
        else:
            center = Vector((0, 0, 1))  # Slightly above ground
            camera_distance = 10
            camera_height = 3
    else:
        center = Vector((0, 0, 1))
        camera_distance = 10
        camera_height = 3

    print(f"Scene center: {center}, Camera distance: {camera_distance}")

    # Setup or find camera with better positioning
    camera = scene.camera
    if not camera:
        for obj in scene.objects:
            if obj.type == 'CAMERA':
                camera = obj
                scene.camera = camera
                break

    if not camera:
        bpy.ops.object.camera_add()
        camera = bpy.context.object
        scene.camera = camera

    # Position camera at a better angle
    camera.location = (
        center.x + camera_distance * 0.7,  # Slightly closer
        center.y - camera_distance * 0.7,
        camera_height
    )

    # Point camera at center
    direction = center - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    print("Camera positioned.")

    # Setup lighting
    light_objects = [obj for obj in scene.objects if obj.type == 'LIGHT']
    if not light_objects:
        # Add key light (sun)
        bpy.ops.object.light_add(type='SUN', location=(center.x + 10, center.y + 10, center.z + 15))
        sun_light = bpy.context.object
        sun_light.data.energy = 3
        sun_light.data.angle = 0.1

        # Add fill light
        bpy.ops.object.light_add(type='POINT', location=(center.x - 5, center.y - 5, center.z + 8))
        point_light = bpy.context.object
        point_light.data.energy = 50

        print("Lighting setup complete.")

    # Configure world background
    if scene.world:
        if not scene.world.use_nodes:
            scene.world.use_nodes = True

        world_nodes = scene.world.node_tree.nodes
        bg_node = world_nodes.get("Background")
        if bg_node:
            bg_node.inputs[0].default_value = (0.15, 0.15, 0.15, 1.0)  # Dark gray background

    # Enable better rendering features if available
    if hasattr(scene, 'eevee'):
        try:
            scene.eevee.use_gtao = True  # Ambient occlusion
            scene.eevee.use_bloom = True  # Bloom effect
            scene.eevee.gtao_distance = 0.2
        except:
            pass  # Some versions might not have these properties

    # Only render if in background mode
    if not True:
        print("Starting render...")
        bpy.ops.render.render(write_still=True)
        print(f"Render completed successfully: {scene.render.filepath}")
    else:
        print("Blender opened in GUI mode - you can view and render manually.")
        print("To render: Press F12 or go to Render > Render Image")

except Exception as e:
    print(f"Script execution error: {str(e)}")
    import traceback
    traceback.print_exc()
    if not True:
        sys.exit(1)

print("Script completed successfully.")
