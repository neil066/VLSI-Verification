# Verilog Circuit Visualizer and Simulator

A comprehensive Python tool for visualizing and simulating Verilog circuits. This tool can handle both hierarchical and flat designs, mapped and unmapped circuits, with support for 18+ gate types and interactive simulation modes.

## 🚀 Features

- **Universal Verilog Support**: Works with any Verilog file (hierarchical or flat, mapped or unmapped)
- **Dual Visualization Modes**: 
  - Structure visualization (circuit topology without values)
  - Simulation visualization (circuit with logic values propagated)
- **High-Level Views**:
  - Highest-level structure view (single top-module block)
  - Higher-level simulation view (sub-modules as blocks with propagated values)
- **Two Simulation Modes**:
  - **Full Mode (`-f`)**: Run complete simulation showing all values at once
  - **Step Mode (`-s`)**: Run step-by-step simulation level by level
- **Interactive Input**: Automatically detects required inputs and prompts for values or accepts input files
- **PDF Visualization**: Generates clean, readable circuit diagrams with logic values
- **Assign/Expression Support**: Evaluates `assign` expressions (including ternary and bitwise operators) during simulation
- **Accurate Unknown Handling**: Unresolved signals remain as `X` and are reported after simulation
- **Comprehensive Gate Support**: Supports 18+ gate types including:
  - Basic gates: AND, OR, NOT, NAND, NOR, XOR, XNOR
  - Arithmetic: Full Adder (FA), Half Adder (HA), Full Subtractor (FS), Half Subtractor (HS)
  - Multiplexers: MUX2, MUX4
  - Custom hierarchical modules

## 📋 Requirements

- Python 3.7+
- Graphviz (system package, required for PDF generation)

## 🔧 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/neil066/New-VLSI-Code.git
   cd New-VLSI-Code
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Graphviz (required for PDF generation):**
   - **Windows**: Download and install from [https://graphviz.org/download/](https://graphviz.org/download/)
     - Make sure to add Graphviz to your system PATH
   - **Linux**: 
     ```bash
     sudo apt-get install graphviz
     ```
   - **macOS**: 
     ```bash
     brew install graphviz
     ```

## 💻 Usage

### Basic Usage

The tool requires you to specify a simulation mode (`-f` for full or `-s` for step-by-step):

```bash
# Full simulation mode (show all values at once)
python verilog_visualizer.py circuit.v -f

# Step-by-step simulation mode (level by level)
python verilog_visualizer.py circuit.v -s
```

### With Input File

When prompted for input file, provide the path to your input file:

```bash
python verilog_visualizer.py circuit.v -f
# When prompted: Enter path to input file (or press Enter to skip): Input Files/test_simple_gates.txt
```

### Multiple Verilog Files

You can process multiple Verilog files at once:

```bash
python verilog_visualizer.py *.v -f
python verilog_visualizer.py 4-bit-add-hier.v 4_mapped.v -s
```

## 📝 Input File Format

Create a text file with space-separated or comma-separated input values. The tool will automatically map them to the circuit inputs.

**Example (`test_simple_gates.txt`):**
```
101
```
This maps to: `a=1, b=0, c=1`

**Example (`test_4bit_adder.txt`):**
```
1010 1101 0
```
This maps to: `a[0]=1, a[1]=0, a[2]=1, a[3]=0, b[0]=1, b[1]=1, b[2]=0, b[3]=1, cin=0`

**Alternative format (comma-separated):**
```
a[0]=1, a[1]=0, a[2]=1, a[3]=0, b[0]=1, b[1]=1, b[2]=0, b[3]=1, cin=0
```

## 📤 Output Files

For each Verilog file processed, the tool generates:

- `{filename}_structure.dot` - Graphviz DOT file showing circuit structure (no values)
- `{filename}_structure.pdf` - PDF visualization of circuit structure
- `{filename}_simulation.dot` - Graphviz DOT file with simulation values
- `{filename}_simulation.pdf` - PDF visualization with logic values propagated
- `{filename}_highest_level.dot` - High-level top-module structure DOT (single-block view)
- `{filename}_highest_level.pdf` - High-level top-module structure PDF
- `{filename}_high_level_simulation.dot` - High-level simulation DOT
- `{filename}_high_level_simulation.pdf` - High-level simulation PDF (sub-module block view)

**Example:** For `simple_gates.v`, you'll get:
- `simple_gates_structure.dot` and `simple_gates_structure.pdf`
- `simple_gates_simulation.dot` and `simple_gates_simulation.pdf`
- `simple_gates_highest_level.dot` and `simple_gates_highest_level.pdf`
- `simple_gates_high_level_simulation.dot` and `simple_gates_high_level_simulation.pdf`

## 📁 Example Files

The repository includes several example Verilog files and test inputs:

### Verilog Files (`Verilog Files/` directory):
- `simple_gates.v` - Basic gate example (AND, OR, NOT)
- `test_all_gates.v` - Comprehensive gate type demonstration
- `4-bit-add-hier.v` - Hierarchical 4-bit adder with Full/Half Adders
- `4_mapped.v` - Mapped/flattened 4-bit adder
- `mult3mod7.v` - Multiplier modulo 7 with hierarchical modules
- `Rest-div-5-3-hier.v` - Restoring divider with hierarchical structure
- `debug_ha.v` - Half adder debugging example

### Input Files (`Input Files/` directory):
- `test_simple_gates.txt` - Input for simple_gates.v
- `test_all_gates.txt` - Input for test_all_gates.v
- `test_4bit_adder.txt` - Input for 4-bit adders
- `test_4mapped.txt` - Input for 4_mapped.v
- `test_mult3mod7.txt` - Input for mult3mod7.v
- `test_restdiv.txt` - Input for Rest-div-5-3-hier.v
- `test_debug_ha.txt` - Input for debug_ha.v

## 🎨 Circuit Visualization

The generated PDF visualizations show:

- **Gates**: Labeled boxes with gate types (AND, OR, NOT, FA, HA, MUX2, etc.)
- **Input Bubbles**: Green ellipses for primary inputs
- **Output Bubbles**: Red ellipses for final outputs
- **Wire Values**: Logic values (0, 1, X for unknown) displayed on connections
- **Left-to-Right Flow**: Logical signal flow from inputs to outputs
- **Hierarchical Modules**: Nested structures for hierarchical designs
- **Top-Level Summary Views**: Optional high-level diagrams for quick architecture and value-flow checks

## 🏗️ Architecture

The tool consists of several key components:

1. **VerilogParser**: Parses Verilog files using regex patterns and extracts circuit structure
2. **LogicSimulator**: Simulates combinational logic behavior with proper value propagation
3. **DOTGenerator**: Creates Graphviz DOT representations with styling and layout
4. **VerilogVisualizer**: Main coordinator class that orchestrates the entire workflow

### Workflow

```
Verilog File(s) → Parse → Structure Visualization → Input Collection → Simulation → Simulation Visualization → PDF Output
```

## ✅ Supported Verilog Constructs

- Module definitions and instantiations
- Port declarations (input/output/inout)
- Gate instantiations (and, or, not, nand, nor, xor, xnor)
- Arithmetic modules (Full Adder, Half Adder, Full Subtractor, Half Subtractor)
- Multiplexers (MUX2, MUX4)
- Continuous assignments (`assign`) with expressions (`&`, `|`, `^`, `!`, `~`, `?:`)
- Wire declarations
- Hierarchical module instantiation
- Multi-bit signals (buses)
- Port mapping (named and positional)

## 🧪 Testing

See `docs/TESTING_GUIDE.md` for comprehensive testing instructions and test results for all example files.

Quick test example:
```bash
# Test simple gates
python verilog_visualizer.py "Verilog Files/simple_gates.v" -f
# When prompted, enter: Input Files/test_simple_gates.txt
```

## 🐛 Troubleshooting

### Common Issues

1. **"graphviz not found" or "Executable not found"**
   - **Solution**: Install Graphviz system package and ensure it's in your PATH
   - Windows: Restart terminal after installation
   - Verify: Run `dot -V` in terminal

2. **"pyverilog not installed"**
   - **Solution**: Run `pip install -r requirements.txt`

3. **"pydot not installed"**
   - **Solution**: Run `pip install -r requirements.txt`

4. **Empty PDF or missing visualization**
   - **Solution**: Check Verilog syntax and gate connections
   - Examine the `.dot` file to verify circuit structure
   - Ensure all inputs are provided
   - Check console notes for unresolved (`X`) nets

5. **"You must specify a simulation mode"**
   - **Solution**: Use `-f` (full) or `-s` (step) flag when running the tool

6. **Missing inputs during simulation**
   - **Solution**: Provide input file when prompted or enter values interactively
   - Check input file format matches expected pattern

7. **Unexpected `X` values in output**
   - **Cause**: One or more required nets could not be resolved from available inputs/logic
   - **Solution**: Verify all primary inputs are present and that assign expressions reference valid signals

### Debug Mode

For debugging, examine the intermediate `.dot` files to verify the circuit structure before PDF generation. You can also open `.dot` files in a text editor to inspect the Graphviz representation.

## 🔧 Extending the Tool

The modular design makes it easy to add support for:

- Additional gate types (add patterns in `VerilogParser._parse_gate_instances`)
- Sequential logic (flip-flops, registers) - requires simulation engine updates
- Custom module libraries
- Different output formats (SVG, PNG, etc.)
- Advanced simulation features (timing, delays, etc.)

## 📚 Additional Resources

- `docs/TESTING_GUIDE.md` - Complete testing guide with examples
- `docs/explanations/` - Detailed documentation and explanations
- Graphviz documentation: [https://graphviz.org/documentation/](https://graphviz.org/documentation/)

## 📄 License

This project is open source. Feel free to use, modify, and distribute.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 👤 Author

**neil066**

- GitHub: [@neil066](https://github.com/neil066)

---

For detailed documentation and advanced usage, see the files in the `docs/explanations/` directory.
