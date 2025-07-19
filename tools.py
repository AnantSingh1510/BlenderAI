import os
import re
import subprocess
import platform
import shutil
from datetime import datetime
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage

script_generation_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.1,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

script_validation_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

async def validate_blender_script(code: str) -> tuple[bool, str]:
    prompt = (
        "You are a Blender Python script validator for Blender 4.x. Check the script for errors.\n\n"
        "VALIDATION RULES:\n"
        "1. If script is valid, respond with exactly 'VALID'\n"
        "2. If errors found, return ONLY the corrected Python code\n"
        "3. Ensure all bpy operations have proper error handling\n"
        "4. Use correct Blender 4.x syntax and node names\n"
        "5. For materials, use: 'Base Color', 'Metallic', 'Roughness', 'Alpha'\n"
        "6. Always check if objects exist before operating on them\n"
        "7. Use try-except blocks for risky operations\n"
        "8. CRITICAL: Verify all location and rotation values are reasonable\n"
        "9. Check that object positioning makes logical sense\n"
        "10. Ensure rotations use proper Euler angles or mathutils.Euler\n\n"
        f"Script to validate:\n```python\n{code}\n```"
    )

    try:
        response = await script_validation_llm.ainvoke([HumanMessage(content=prompt)])
        validation_result = response.content.strip()

        if validation_result == "VALID":
            return True, code
        else:
            cleaned_code = clean_code_output(validation_result)
            return False, cleaned_code
    except Exception as e:
        print(f"Validation error: {e}")
        return True, code


def clean_code_output(code: str) -> str:
    if "```python" in code:
        code = code.split("```python", 1)[1]
    if "```" in code:
        code = code.split("```")[0]

    lines = code.strip().split('\n')
    cleaned_lines = []
    for line in lines:
        if not line.strip().startswith(('Here', 'The corrected', 'Fixed')):
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines).strip()


async def generate_blender_script(description: str) -> str:
    """Generates and validates a Blender Python script from a description."""
    max_retries = 3

    for attempt in range(max_retries):
        prompt = create_generation_prompt(description, attempt)

        try:
            response = await script_generation_llm.ainvoke([HumanMessage(content=prompt)])
            generated_code = clean_code_output(response.content)

            print(f"--- Generation Attempt {attempt + 1} ---")
            print(f"Generated code length: {len(generated_code)} characters")

            if not generated_code or len(generated_code) < 50:
                print("Generated code too short, retrying...")
                continue

            if "import bpy" not in generated_code:
                generated_code = "import bpy\n" + generated_code

            is_valid, validated_code = await validate_blender_script(generated_code)

            if is_valid:
                print("Script validated successfully.")
                return validated_code
            else:
                print(f"Validation suggested improvements, using corrected version.")
                return validated_code

        except Exception as e:
            print(f"Generation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                return create_fallback_script(description)

    return create_fallback_script(description)


def create_generation_prompt(description: str, attempt: int) -> str:
    """Create the prompt for script generation with improved positioning guidance."""
    base_prompt = f"""You are an expert Blender Python script generator. Create a robust Python script for Blender 4.x with PRECISE positioning and rotation.

COORDINATE SYSTEM RULES (CRITICAL):
- Blender uses Z-up coordinate system (Z is vertical)
- Origin (0,0,0) is the world center
- Positive X = right, Positive Y = forward/depth, Positive Z = up
- Ground plane is typically Z=0
- Place objects thoughtfully - don't just use random positions
- Use mathutils.Euler() for rotations: Euler((x_rot, y_rot, z_rot), 'XYZ')

POSITIONING BEST PRACTICES:
- For ground objects: Z position should be >= 0 (objects sit ON ground, not in it)
- For hanging objects: use positive Z values appropriately
- For multiple objects: space them logically (2-5 units apart typically)
- Consider object size when positioning - don't overlap accidentally
- Think about the relationship between objects before placing them

ROTATION GUIDELINES:
- Use mathutils.Euler for precise rotations
- Common rotations: (0,0,0) = default, (π/2,0,0) = 90° around X-axis
- Import math for π: import math; then use math.pi or math.radians()
- For random rotations, use reasonable ranges: random.uniform(-math.pi/6, math.pi/6)

CRITICAL REQUIREMENTS:
1. Output ONLY raw Python code, no explanations or markdown
2. Always start with required imports: bpy, random, mathutils, math
3. Clean scene at start: delete existing mesh objects
4. Use try-except blocks for all risky operations
5. Create simple RGB materials using random colors
6. Add basic modifiers for detail (subdivision surface, bevel)
7. DO NOT include render commands or filepath settings
8. DO NOT add cameras or lights
9. Use proper object naming and selection
10. Always check if objects/materials exist before using them
11. MOST IMPORTANT: Think about positioning logically before placing objects

REQUIRED SCRIPT STRUCTURE:
```
import bpy
import random
import math
from mathutils import Vector, Euler

# Clean scene
try:
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()
except:
    pass

# Plan your scene layout first - think about where objects should be
# Example good positioning:
# - Table at (0, 0, 0) - on ground
# - Object on table at (0, 0, table_height + object_size/2)
# - Objects around table at (2, 0, 0), (-2, 0, 0), etc.

# Create objects with thoughtful positioning
# ... your creation code here with specific coordinates ...

# Apply rotations using mathutils.Euler if needed
# obj.rotation_euler = Euler((math.radians(angle_x), math.radians(angle_y), math.radians(angle_z)), 'XYZ')

# Apply materials with error handling
# ... material code here ...
```

POSITIONING EXAMPLES:
- Floor tile: location=(x, y, 0.1) - slightly above ground
- Wall: location=(0, -5, 2.5) - back wall, halfway up
- Ceiling light: location=(0, 0, 5) - above scene
- Table: location=(0, 0, 0.4) - table height from ground
- Chair: location=(0, -1.5, 0.45) - in front of table
- Decoration on table: location=(0, 0, 0.8 + decoration_height/2)

Generate a detailed script for: {description}

Focus on creating a logical, well-positioned scene with proper spatial relationships."""

    if attempt > 0:
        base_prompt += f"""

ATTEMPT {attempt + 1} FOCUS:
- Double-check all location coordinates make sense
- Ensure Z-coordinates respect gravity (things don't float randomly)
- Verify object relationships are spatially logical
- Add more precise positioning calculations
- Consider object dimensions when placing them"""

    return base_prompt


def create_fallback_script(description: str) -> str:
    """Create a simple fallback script with proper positioning."""
    return '''import bpy
import random
import math
from mathutils import Vector, Euler

# Clean scene
try:
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()
except:
    pass

# Create properly positioned objects
try:
    # Create a ground plane
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    ground = bpy.context.active_object
    if ground:
        ground.name = "Ground"

    # Create main object positioned logically above ground
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 1.5))
    main_obj = bpy.context.active_object
    if main_obj:
        main_obj.name = "Generated_Object"

        # Apply a slight random rotation using proper Euler angles
        main_obj.rotation_euler = Euler((
            math.radians(random.uniform(-15, 15)),
            math.radians(random.uniform(-15, 15)), 
            math.radians(random.uniform(0, 360))
        ), 'XYZ')

        # Add subdivision with proper error handling
        try:
            subsurf = main_obj.modifiers.new(name='Subdivision', type='SUBSURF')
            subsurf.levels = 2
        except:
            pass

        # Create and assign material
        try:
            mat = bpy.data.materials.new(name='Generated_Material')
            mat.use_nodes = True

            # Get principled BSDF
            bsdf = None
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    bsdf = node
                    break

            if bsdf and 'Base Color' in bsdf.inputs:
                bsdf.inputs['Base Color'].default_value = (
                    random.random(), 
                    random.random(), 
                    random.random(), 
                    1.0
                )

            # Assign material
            if len(main_obj.data.materials) == 0:
                main_obj.data.materials.append(mat)
            else:
                main_obj.data.materials[0] = mat

        except Exception as e:
            print(f"Material creation error: {e}")

    # Add a couple more objects with logical positioning
    try:
        # Object to the side
        bpy.ops.mesh.primitive_cube_add(size=0.8, location=(3, 0, 0.4))
        side_obj = bpy.context.active_object
        if side_obj:
            side_obj.name = "Side_Object"

        # Object in back
        bpy.ops.mesh.primitive_cylinder_add(radius=0.6, depth=1.5, location=(0, -3, 0.75))
        back_obj = bpy.context.active_object
        if back_obj:
            back_obj.name = "Back_Object"

    except Exception as e:
        print(f"Additional object creation error: {e}")

except Exception as e:
    print(f"Object creation error: {e}")
'''


async def run_blender_script_tool(tool_input: dict) -> str:
    """Generates and executes a Blender Python script and renders the output."""
    try:
        description = tool_input.get("description")
        open_blender = tool_input.get("open_blender", True)  # Option to keep Blender open

        if not description:
            return "Error: Missing 'description' in tool_input."

        print(f"Updated prompt: {description}")
        user_code = await generate_blender_script(description)

        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.abspath(os.path.join(output_dir, f"render_{timestamp}.png"))

        user_script_path = f"user_script_{timestamp}.py"
        with open(user_script_path, "w", encoding="utf-8") as f:
            f.write(user_code)

        complete_script = create_complete_script_with_import(user_script_path, output_path, open_blender)

        script_path = "blender_script.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(complete_script)

        blender_exe = find_blender_executable()
        if not blender_exe:
            return "Error: Blender executable not found. Please install Blender and add it to PATH."

        env = os.environ.copy()
        env["TBB_MALLOC_DISABLE_REPLACEMENT"] = "1"
        env["BLENDER_USER_CONFIG"] = ""

        print(f"Executing Blender: {blender_exe}")

        blender_args = [blender_exe]
        if not open_blender:
            blender_args.append("--background")
        blender_args.extend(["--python", script_path, "--enable-autoexec"])

        if open_blender:
            subprocess.Popen(blender_args, env=env)
            return f"SUCCESS: Blender opened with your model! You can view it and render manually.\nGenerated script: {script_path}\nUser script: {user_script_path}"
        else:
            proc = subprocess.run(
                blender_args,
                capture_output=True,
                text=True,
                env=env,
                timeout=300
            )

            try:
                os.remove(script_path)
                os.remove(user_script_path)
            except:
                pass

            if proc.returncode != 0:
                error_msg = proc.stderr.strip() if proc.stderr else "Unknown error"
                stdout_msg = proc.stdout.strip() if proc.stdout else ""
                return f"Blender execution failed (code {proc.returncode}):\nSTDERR: {error_msg}\nSTDOUT: {stdout_msg}"

            if not os.path.exists(output_path):
                return f"Render completed but no output file found at: {output_path}\nBlender output: {proc.stdout}"

            try:
                open_rendered_file(output_path)
                open_msg = " File opened in default viewer."
            except:
                open_msg = " Could not open file automatically."

            return f"SUCCESS: 3D model rendered successfully!{open_msg}\nOutput: {output_path}"

    except subprocess.TimeoutExpired:
        return "Error: Blender execution timed out (300 seconds). The script might be too complex."
    except Exception as e:
        return f"Error: {str(e)}"


def create_complete_script_with_import(user_script_path: str, output_path: str, open_blender: bool = False) -> str:
    """Create the complete Blender script that imports the user script."""
    return f'''#!/usr/bin/env python3

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
    scene.render.filepath = "{output_path.replace(os.sep, '/')}"

    print("Render settings configured.")

    # Execute user script by importing it
    print("Executing user-generated code...")

    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Import the user script (this will execute it)
    user_module_name = "{os.path.splitext(user_script_path)[0]}"
    try:
        __import__(user_module_name)
        print("User code executed successfully.")
    except Exception as e:
        print(f"Error executing user code: {{e}}")
        import traceback
        traceback.print_exc()
        if not {str(open_blender).lower() == 'true'}:
            sys.exit(1)

    # Get all mesh objects for camera positioning
    mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH']
    print(f"Found {{len(mesh_objects)}} mesh objects.")

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

    print(f"Scene center: {{center}}, Camera distance: {{camera_distance}}")

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
    if not {str(open_blender).lower() == 'true'}:
        print("Starting render...")
        bpy.ops.render.render(write_still=True)
        print(f"Render completed successfully: {{scene.render.filepath}}")
    else:
        print("Blender opened in GUI mode - you can view and render manually.")
        print("To render: Press F12 or go to Render > Render Image")

except Exception as e:
    print(f"Script execution error: {{str(e)}}")
    import traceback
    traceback.print_exc()
    if not {str(open_blender).lower() == 'true'}:
        sys.exit(1)

print("Script completed successfully.")
'''


def find_blender_executable():
    """Find Blender executable across platforms."""
    # Check PATH first
    blender_cmd = shutil.which("blender")
    if blender_cmd:
        return blender_cmd

    # Platform-specific paths
    system = platform.system()

    if system == "Windows":
        # Windows paths
        possible_paths = []
        for version in ["4.2", "4.1", "4.0", "3.6", "3.5"]:
            possible_paths.extend([
                f"C:\\Program Files\\Blender Foundation\\Blender {version}\\blender.exe",
                f"C:\\Program Files (x86)\\Blender Foundation\\Blender {version}\\blender.exe",
            ])
        possible_paths.extend([
            "C:\\Blender\\blender.exe",
            os.path.expanduser("~/AppData/Local/Programs/Blender/blender.exe")
        ])

    elif system == "Darwin":  # macOS
        possible_paths = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender.app/Contents/MacOS/blender",
            "/usr/local/bin/blender",
            "/opt/homebrew/bin/blender"
        ]

    else:  # Linux and others
        possible_paths = [
            "/usr/bin/blender",
            "/usr/local/bin/blender",
            "/snap/bin/blender",
            "/opt/blender/blender",
            os.path.expanduser("~/Applications/blender")
        ]

    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            return path

    return None


def open_rendered_file(filepath):
    """Open rendered file with default application."""
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(filepath)
        elif system == "Darwin":
            subprocess.run(["open", filepath], check=False)
        else:  # Linux
            subprocess.run(["xdg-open", filepath], check=False)
    except Exception as e:
        print(f"Could not open file: {e}")


TOOL_REGISTRY = {
    "RunBlenderScript": run_blender_script_tool,
}