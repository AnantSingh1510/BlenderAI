import os
import re
import subprocess
import platform
import shutil
from datetime import datetime


async def run_blender_script_tool(tool_input: dict) -> str:
    """Execute a Blender Python script and render output for ReAct agent."""
    try:
        user_code = tool_input.get("code") or tool_input.get("script")
        if not user_code:
            return "Error: Missing 'code' or 'script' in tool_input."

        # Create output directory
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        # Generate unique output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.abspath(os.path.join(output_dir, f"render_{timestamp}.png"))

        # Clean user code - remove any existing filepath and render calls
        user_code = re.sub(r"bpy\.context\.scene\.render\.filepath\s*=.*", "", user_code)
        user_code = re.sub(r"bpy\.ops\.render\.render\(.*\)", "", user_code)

        # Ensure bpy import exists
        if "import bpy" not in user_code:
            user_code = "import bpy\n" + user_code

        texture_code = ""
        if tool_input.get("texture"):
            texture_type = tool_input.get("texture")
            if texture_type == "checker":
                texture_code = """
# Apply checker texture to the last object
if bpy.context.object:
    obj = bpy.context.object
    mat = bpy.data.materials.new(name="CheckerMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    
    checker_tex = mat.node_tree.nodes.new("ShaderNodeTexChecker")
    checker_tex.inputs["Scale"].default_value = 20.0
    
    mat.node_tree.links.new(bsdf.inputs["Base Color"], checker_tex.outputs["Color"])
    
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
"""

        # Append render configuration
        render_config = f'''
import bpy
from mathutils import Vector
import bmesh

# Clear existing objects (but keep default camera and light references)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False, confirm=False)

# Configure render settings FIRST
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

# Set output path (using forward slashes for compatibility)
scene.render.filepath = "{output_path.replace(chr(92), '/')}"

print(f"Render output path set to: {{scene.render.filepath}}")

# Execute user code FIRST
{user_code}

{texture_code}

# After user code, check what we have and fix common issues
supported_types = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'VOLUME', 'GPENCIL'}
geom_objects = [obj for obj in scene.objects if obj.type in supported_types and hasattr(obj, 'bound_box')]
print(f"Found {{len(geom_objects)}} geometric objects in scene")

# Calculate bounding box of all geometric objects
if geom_objects:
    # Get world coordinates of all vertices
    all_coords = []
    for obj in geom_objects:
        for vertex in obj.bound_box:
            world_coord = obj.matrix_world @ Vector(vertex)
            all_coords.append(world_coord)

    if all_coords:
        min_x = min(coord.x for coord in all_coords)
        max_x = max(coord.x for coord in all_coords)
        min_y = min(coord.y for coord in all_coords)
        max_y = max(coord.y for coord in all_coords)
        min_z = min(coord.z for coord in all_coords)
        max_z = max(coord.z for coord in all_coords)

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2

        # Calculate distance needed to fit objects in view
        size_x = max_x - min_x
        size_y = max_y - min_y
        size_z = max_z - min_z
        max_size = max(size_x, size_y, size_z)

        camera_distance = max_size * 2.5  # Distance multiplier

        print(f"Object bounds: x=[{{min_x:.2f}}, {{max_x:.2f}}], y=[{{min_y:.2f}}, {{max_y:.2f}}], z=[{{min_z:.2f}}, {{max_z:.2f}}]")
        print(f"Center: ({{center_x:.2f}}, {{center_y:.2f}}, {{center_z:.2f}})")
        print(f"Camera distance: {{camera_distance:.2f}}")
    else:
        # Fallback values
        center_x, center_y, center_z = 0, 0, 0
        camera_distance = 7

# Setup camera
camera_found = False
for obj in scene.objects:
    if obj.type == 'CAMERA':
        camera = obj
        camera_found = True
        break

if not camera_found:
    print("No camera found, creating default camera")
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    scene.camera = camera

# Position camera to look at the objects
camera.location = (
    center_x + camera_distance * 0.7,
    center_y - camera_distance * 0.7,
    center_z + camera_distance * 0.5
)

# Point camera at center of objects
direction = Vector((center_x, center_y, center_z)) - camera.location
camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

print(f"Camera positioned at: {{camera.location}}")
print(f"Camera rotation: {{camera.rotation_euler}}")

# Setup lighting
light_found = False
for obj in scene.objects:
    if obj.type == 'LIGHT':
        light_found = True
        break

if not light_found:
    print("No light found, creating default lighting")
    # Add sun light
    bpy.ops.object.light_add(type='SUN', location=(center_x + 5, center_y + 5, center_z + 10))
    sun_light = bpy.context.object
    sun_light.data.energy = 5
    sun_light.rotation_euler = (0.5, 0, 0.5)

    # Add fill light
    bpy.ops.object.light_add(type='POINT', location=(center_x - 3, center_y - 3, center_z + 5))
    point_light = bpy.context.object
    point_light.data.energy = 100
else:
    print("Light found in scene")

# Enable ambient occlusion for better depth
scene.eevee.use_gtao = True
scene.eevee.gtao_distance = 0.2

# Set world background to light gray instead of black
world = scene.world
if world.use_nodes:
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.2, 0.2, 0.2, 1.0)  # Light gray
        bg_node.inputs[1].default_value = 1.0  # Strength

# Final render call
print("Starting render...")
try:
    bpy.ops.render.render(write_still=True)
    print(f"Render completed successfully: {{scene.render.filepath}}")
except Exception as e:
    print(f"Render failed: {{e}}")
    import traceback
    traceback.print_exc()
'''

        # Write script to file
        script_path = "agent_script.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(render_config)

        # Find Blender executable
        blender_exe = find_blender_executable()
        if not blender_exe:
            return "Error: Blender executable not found. Please install Blender."

        # Set environment
        env = os.environ.copy()
        env["TBB_MALLOC_DISABLE_REPLACEMENT"] = "1"

        # Execute Blender
        proc = subprocess.run(
            [blender_exe, "--python", script_path],
            capture_output=True,
            text=True,
            env=env,
            timeout=180
        )

        # Clean up script file
        try:
            os.remove(script_path)
        except:
            pass

        # Check execution result
        if proc.returncode != 0:
            error_msg = proc.stderr.strip() if proc.stderr else "Unknown error"
            stdout_msg = proc.stdout.strip() if proc.stdout else "No output"
            return f"Blender execution failed (code {proc.returncode}): {error_msg}\nOutput: {stdout_msg}"

        # Print stdout for debugging
        if proc.stdout:
            print("Blender stdout:", proc.stdout.strip())

        # Verify output file exists
        if not os.path.exists(output_path):
            stdout_msg = proc.stdout.strip() if proc.stdout else "No output"
            return f"Blender ran but no output file created at: {output_path}\nBlender output: {stdout_msg}"

        # Try to open the file (optional, don't fail if this doesn't work)
        try:
            open_rendered_file(output_path)
            open_msg = " (opened in default viewer)"
        except:
            open_msg = ""

        return f"SUCCESS: Blender render completed{open_msg}. Output saved to: {output_path}"

    except subprocess.TimeoutExpired:
        return "Error: Blender script execution timed out (90 seconds exceeded)."
    except Exception as e:
        return f"Error executing Blender script: {str(e)}"


def find_blender_executable():
    """Find Blender executable across different platforms."""
    # Check if blender is in PATH first
    if shutil.which("blender"):
        return shutil.which("blender")

    # Platform-specific paths
    if platform.system() == "Windows":
        possible_paths = [
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.4\blender.exe",
        ]
    elif platform.system() == "Darwin":  # macOS
        possible_paths = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
        ]
    else:  # Linux
        possible_paths = [
            "/usr/bin/blender",
            "/usr/local/bin/blender",
            "/snap/bin/blender",
        ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def open_rendered_file(filepath):
    """Try to open the rendered file with default application."""
    if platform.system() == "Windows":
        os.startfile(filepath)
    elif platform.system() == "Darwin":
        subprocess.run(["open", filepath], check=True)
    else:
        subprocess.run(["xdg-open", filepath], check=True)



# Updated tool registry
TOOL_REGISTRY = {
    "RunBlenderScript": run_blender_script_tool,
}
