# ReAct 3D Model Generator

An AI-powered system that generates 3D models in Blender from natural language descriptions using ReAct (Reasoning + Acting) architecture.

## Features

- **Natural Language to 3D**: Convert text descriptions into working Blender models
- **ReAct Architecture**: AI reasons through modeling approach before generating code
- **Multi-LLM Pipeline**: Uses Gemini 2.5 Pro for complex reasoning and Flash for validation
- **Code Validation**: Automatic syntax and logic checking before execution
- **Error Recovery**: Intelligent retry mechanism for failed generations

## Architecture

```
User Input → Prompt Preprocessing → ReAct Planner → Code Generation → Validation → 3D Model
                                        ↑                                ↓
                                   Error Feedback ←─────────────── Failed Validation
```

The system uses a multi-stage pipeline:

1. **Preprocessing**: Converts natural language to technical specifications
2. **ReAct Planning**: AI reasons through modeling steps before acting
3. **Code Generation**: Gemini 2.5 Pro generates Blender Python code
4. **Validation**: Gemini 2.5 Flash checks for errors and logical issues
5. **Execution**: Clean code runs in Blender to create 3D models

## Tech Stack

- **AI Models**: Google Gemini 2.5 Pro & Flash
- **3D Software**: Blender (Python API)
- **Architecture**: ReAct (Reasoning + Acting)
- **Language**: Python
- **APIs**: Blender Python API (bpy)

## Prerequisites

- Python 3.8+
- Blender 3.0+
- Google AI API key
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/react-3d-generator.git
cd react-3d-generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Google AI API key:
```bash
export GOOGLE_AI_API_KEY="your-api-key-here"
```

4. Configure Blender path in `config.py`

## Usage

### Basic Usage

```python
from react_3d_generator import ModelGenerator

generator = ModelGenerator()
result = generator.generate("Create a medieval sword")

if result.success:
    print(f"Model generated successfully: {result.model_path}")
else:
    print(f"Generation failed: {result.error}")
```

### Command Line Interface

```bash
python generate.py "Create a medieval sword with ornate handle"
```

### Example Prompts

- "Create a medieval sword"
- "Generate a simple chair"
- "Make a coffee mug with handle"
- "Create a basic house structure"

## Project Structure

```
react-3d-generator/
├── src/
│   ├── react_planner.py      # ReAct reasoning logic
│   ├── code_generator.py     # Gemini Pro integration
│   ├── validator.py          # Gemini Flash validation
│   ├── blender_interface.py  # Blender API wrapper
│   └── preprocessor.py       # Input processing
├── examples/                 # Example generated models
├── tests/                   # Unit tests
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## How It Works

### ReAct Process Example

**Input**: "Create a medieval sword"

**Reasoning Phase** (Gemini 2.5 Pro):
```
Thought: To create a medieval sword, I need:
1. A blade - long cylinder, scaled and positioned
2. A handle - smaller cylinder below the blade
3. A crossguard - thin rectangular piece perpendicular to blade
4. A pommel - small sphere at the end of handle

Action: Generate Blender Python code for these components
```

**Code Generation**:
```python
import bpy

# Create blade
bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=1.5, location=(0, 0, 0.75))
blade = bpy.context.active_object
blade.name = "Sword_Blade"

# Create handle
bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.3, location=(0, 0, -0.15))
handle = bpy.context.active_object
handle.name = "Sword_Handle"
# ... additional code
```

**Validation Phase** (Gemini 2.5 Flash):
- Checks syntax errors
- Validates bpy API usage
- Ensures logical object placement
- Verifies naming conventions

## Configuration

Create a `config.py` file:

```python
GOOGLE_API_KEY="YOUR_API_KEY"
LANGCHAIN_API_KEY="YOUR_API_KEY"
LANGCHAIN_PROJECT="YOUR_API_KEY"
LANGCHAIN_TRACING_V2="YOUR_API_KEY"
LANGSMITH_TRACING="YOUR_API_KEY"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
```

## Current Limitations

- Basic geometric shapes only
- Limited material support
- Single-object generation (no assemblies)
- Local execution only
- Manual Blender setup required

## Future Improvements

- [ ] Web-based interface
- [ ] Real-time preview
- [ ] Advanced material generation
- [ ] Multi-part assemblies
- [ ] Asset library integration
- [ ] Texture generation
- [ ] Cloud deployment

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Google AI for Gemini models
- Blender Foundation for the amazing 3D software
- ReAct paper authors for the reasoning framework

## Contact

Your Name - your.email@example.com

Project Link: [https://github.com/yourusername/react-3d-generator](https://github.com/yourusername/react-3d-generator)
