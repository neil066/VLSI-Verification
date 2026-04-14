#!/usr/bin/env python3
"""
Verilog Circuit Visualizer and Simulator

A comprehensive tool for visualizing and simulating Verilog circuits.
Supports hierarchical and flat designs, mapped and unmapped circuits.
"""

# Standard library imports for argument parsing, file operations, and data structures
import argparse  # For command-line argument parsing
import sys       # For system operations and exit codes
import os        # For file system operations
from typing import Dict, List, Tuple, Set, Optional, Any  # Type hints for better code documentation
from dataclasses import dataclass  # For creating structured data classes
from enum import Enum  # For creating enumerated constants
import re  # For regular expression pattern matching

# Try to import pyverilog - a Verilog parsing library
try:
    import pyverilog
    # Note: We'll use a simpler approach for parsing instead of the complex AST imports
    # The commented imports below are more advanced pyverilog features we could use later:
    # from pyverilog.vparser.parser import parse  # For parsing Verilog into AST
    # from pyverilog.ast_code_generator.codegen import ASTCodeGenerator  # For generating code from AST
    # from pyverilog.dataflow.dataflow import DFG  # For data flow graph analysis
    # from pyverilog.dataflow.modulevisitor import ModuleVisitor  # For visiting module nodes
    # from pyverilog.dataflow.optimizer import DFGOptimizer  # For optimizing data flow
except ImportError:
    print("Error: pyverilog not installed. Please run: pip install pyverilog")
    sys.exit(1)

# Try to import graph visualization libraries
try:
    import graphviz  # For creating and rendering Graphviz DOT files
    import pydot     # Alternative DOT file manipulation library
except ImportError:
    print("Error: graphviz or pydot not installed. Please run: pip install graphviz pydot")
    sys.exit(1)


class LogicValue(Enum):
    """
    Logic value enumeration for digital circuit simulation
    
    This enum defines the three possible logic states in digital circuits:
    - ZERO: Logic low (0V in hardware, false in boolean)
    - ONE: Logic high (VCC in hardware, true in boolean) 
    - X: Unknown/undefined state (used for uninitialized signals or don't-care conditions)
    """
    ZERO = "0"  # Logic low state
    ONE = "1"   # Logic high state
    X = "X"     # Unknown/undefined state


@dataclass
class Gate:
    """
    Represents a logic gate in the circuit
    
    This data class stores information about each logic gate including:
    - name: Unique identifier for the gate instance (e.g., "G1", "AND1", "FA0")
    - gate_type: Type of gate (e.g., "and", "or", "not", "fa", "ha", "mux2")
    - inputs: List of input net names connected to this gate
    - outputs: List of output net names driven by this gate
    - bit_width: Width of the gate (usually 1 for single-bit gates)
    
    The __post_init__ method ensures inputs and outputs are always lists, even if None
    """
    name: str           # Gate instance name (e.g., "G1", "AND1")
    gate_type: str      # Gate type (e.g., "and", "or", "fa", "mux2")
    inputs: List[str]   # Input net names
    outputs: List[str]  # Output net names
    bit_width: int = 1  # Bit width (default 1 for single-bit gates)
    port_map: Dict[str, str] = None # Mapping from port name to net name (for modules)
    expression: Optional[str] = None  # Original RHS expression for assign gates
    
    def __post_init__(self):
        """Initialize empty lists if inputs/outputs are None"""
        if not self.inputs:
            self.inputs = []
        if not self.outputs:
            self.outputs = []
        if self.port_map is None:
            self.port_map = {}


@dataclass
class Net:
    """
    Represents a wire/net in the circuit
    
    This data class stores information about each wire or net in the circuit:
    - name: Net name (e.g., "w1", "sum", "carry_out")
    - value: Current logic value during simulation (LogicValue enum)
    - bit_width: Width of the net (usually 1 for single-bit nets)
    - driver: Name of the gate that drives this net (source)
    - loads: List of gate names that use this net as input (sinks)
    
    The __post_init__ method ensures loads is always a list
    """
    name: str                           # Net name (e.g., "w1", "sum")
    value: LogicValue = LogicValue.X    # Current simulation value (default unknown)
    bit_width: int = 1                  # Bit width (default 1)
    driver: Optional[str] = None        # Gate that drives this net (source)
    loads: List[str] = None             # Gates that use this net as input (sinks)
    
    def __post_init__(self):
        """Initialize empty list if loads is None"""
        if self.loads is None:
            self.loads = []  # Ensure loads is always a list


@dataclass
class Module:
    """
    Represents a Verilog module
    
    This data class stores complete information about a Verilog module:
    - name: Module name (e.g., "full_adder", "adder_4bit")
    - ports: Dictionary mapping port names to their directions (input/output/inout)
    - gates: List of all Gate objects in this module
    - nets: Dictionary mapping net names to Net objects
    - submodules: List of sub-module instances (for hierarchical designs)
    
    The __post_init__ method ensures submodules is always a list
    """
    name: str                    # Module name
    ports: Dict[str, str]        # port_name -> direction (input/output/inout)
    gates: List[Gate]            # All gates in this module
    nets: Dict[str, Net]         # All nets in this module
    submodules: List['Module'] = None  # Sub-module instances (hierarchical)
    
    def __post_init__(self):
        """Initialize empty list if submodules is None"""
        if self.submodules is None:
            self.submodules = []  # Ensure submodules is always a list


class VerilogParser:
    """
    Parses Verilog files and extracts circuit structure
    
    This class handles the parsing of Verilog files to extract:
    - Module definitions and their ports
    - Gate instantiations (and, or, not, fa, ha, etc.)
    - Wire/net declarations
    - Module instantiations (hierarchical designs)
    - Assign statements
    
    The parser uses regex-based pattern matching for reliability and simplicity.
    """
    
    def __init__(self):
        """Initialize the parser with empty module list"""
        self.modules: List[Module] = []           # List of parsed modules
        self.current_module: Optional[Module] = None  # Currently being parsed module
        
    def parse_file(self, filename: str) -> List[Module]:
        """
        Parse a Verilog file and return list of modules
        
        Args:
            filename: Path to the Verilog file to parse
            
        Returns:
            List of Module objects extracted from the file
            
        This method:
        1. Reads the entire Verilog file into memory
        2. Calls _extract_modules_from_code to parse the content
        3. Returns the list of parsed modules
        4. Handles file I/O errors gracefully
        """
        try:
            # Read the entire Verilog file
            with open(filename, 'r') as f:
                verilog_code = f.read()
            
            # Use regex-based parsing for now (more reliable than complex AST parsing)
            # This approach is simpler and more predictable than using pyverilog's AST
            self._extract_modules_from_code(verilog_code)
            return self.modules
            
        except Exception as e:
            print(f"Error parsing {filename}: {e}")
            return []  # Return empty list on error
    
    def _extract_modules_from_code(self, verilog_code: str):
        """
        Extract module definitions from Verilog code using regex
        
        This method uses regex to find all module definitions in the Verilog code.
        The regex pattern looks for:
        - 'module' keyword
        - Module name (captured as group 1)
        - Port list in parentheses (captured as group 2)
        - Semicolon terminator
        
        Args:
            verilog_code: The complete Verilog source code as a string
        """
        # Regex pattern to match module definitions:
        # module\s+([^\s(]+)\s*\((.*?)\)\s*;
        # - module\s+: matches "module" followed by whitespace
        # - ([^\s(]+): captures module name (non-whitespace, non-parenthesis chars)
        # - \s*\(: matches optional whitespace and opening parenthesis
        # - (.*?): captures port list (non-greedy match)
        # - \)\s*;: matches closing parenthesis, optional whitespace, and semicolon
        module_pattern = r'module\s+([^\s(]+)\s*\((.*?)\)\s*;'
        modules = re.findall(module_pattern, verilog_code, re.DOTALL)  # re.DOTALL makes . match newlines
        
        # Process each found module
        for module_name, ports_str in modules:
            # Create Module object from the parsed string data
            module = self._create_module_from_string(module_name, ports_str, verilog_code)
            if module:  # Only add if module creation was successful
                self.modules.append(module)
    
    def _create_module_from_string(self, name: str, ports_str: str, code: str) -> Optional[Module]:
        """
        Create a Module object from parsed string data
        
        This method orchestrates the creation of a complete Module object by:
        1. Parsing port declarations from both the module header and body
        2. Extracting all gates and nets from the module body
        3. Creating and returning the Module object
        
        Args:
            name: Module name extracted from the module declaration
            ports_str: Port list string from the module header
            code: Complete Verilog code (needed to find module body)
            
        Returns:
            Module object if successful, None if parsing fails
        """
        try:
            # Parse ports from both the module header port list and module body declarations
            # Some Verilog styles declare ports in the header, others in the body
            ports = self._parse_ports(ports_str)  # Parse ports from header
            ports.update(self._parse_ports_from_body(code))  # Add ports found in module body
            
            # Extract all gates and nets from the module body
            gates, nets = self._extract_gates_and_nets(code, name)
            
            # Create and return the Module object
            return Module(
                name=name,    # Module name
                ports=ports,  # Port dictionary (name -> direction)
                gates=gates,  # List of gates in this module
                nets=nets     # Dictionary of nets (name -> Net object)
            )
            
        except Exception as e:
            print(f"Error creating module {name}: {e}")
            return None  # Return None if module creation fails
    
    def _parse_ports_from_body(self, code: str) -> Dict[str, str]:
        """
        Parse port declarations from module body
        
        This method extracts port declarations that appear inside the module body,
        such as:
        - input a, b, cin;
        - output [3:0] sum;
        - output cout;
        
        It handles both single ports and multiple ports on one line, as well as
        array notation like [3:0].
        
        Args:
            code: Complete Verilog code
            
        Returns:
            Dictionary mapping port names to their directions (input/output/inout)
        """
        ports = {}
        
        # Find the module body by locating the module keyword
        module_start = code.find('module')
        if module_start == -1:
            return ports  # No module found
        
        # Find the start of module body (after the port list and semicolon)
        body_start = code.find(';', module_start)
        if body_start == -1:
            return ports  # No semicolon found after module declaration
        
        # Find the end of the module (before endmodule)
        body_end = code.find('endmodule', body_start)
        if body_end == -1:
            body_end = len(code)  # Use end of file if no endmodule found
        
        # Extract the module body text
        module_body = code[body_start:body_end]
        
        # Look for input/output/inout declarations in module body
        # Pattern matches: direction keyword + whitespace + port list + semicolon
        # Examples: "input a, b;" or "output [3:0] sum;"
        port_pattern = r'(input|output|inout)\s+([^;]+);'
        matches = re.findall(port_pattern, module_body)
        
        # Process each port declaration
        for direction, port_list in matches:
            # Split comma-separated port list and clean up whitespace
            port_names = [port.strip() for port in port_list.split(',')]
            
            # Process each individual port name
            for port_name in port_names:
                # Handle array notation if present (e.g., "sum[3:0]")
                if '[' in port_name and ']' in port_name:
                    # Extract base name (e.g., "sum" from "sum[3:0]")
                    base_name = port_name.split('[')[0]
                    array_part = port_name.split('[')[1].split(']')[0]
                    
                    # Add both the full port name and base name to the ports dictionary
                    ports[port_name] = direction.strip()  # Full name with array bounds
                    ports[base_name] = direction.strip()  # Base name without bounds
                else:
                    # Simple port name without array notation
                    ports[port_name.strip()] = direction.strip()
        
        return ports
    
    def _parse_ports(self, ports_str: str) -> Dict[str, str]:
        """
        Parse module ports from the module header port list string
        
        This method parses port declarations that appear in the module header,
        such as: 
        - module adder(input a, input b, output cout);
        - module mult(input a2, a1, a0, b2, b1, b0, output z);
        
        It handles both single ports and comma-separated port lists.
        
        Args:
            ports_str: Port list string from module header
            
        Returns:
            Dictionary mapping port names to their directions
        """
        ports = {}
        
        # First, try to match direction keywords with their port lists
        # This pattern captures: direction + everything until next direction or end
        # Examples:
        # "input a, b, c" -> direction="input", port_list="a, b, c"
        # "output [3:0] sum" -> direction="output", port_list="[3:0] sum"
        
        # Split by direction keywords while keeping the keywords
        tokens = re.split(r'\b(input|output|inout)\b', ports_str)
        
        current_direction = None
        for token in tokens:
            token = token.strip()
            
            # Check if this token is a direction keyword
            if token in ['input', 'output', 'inout']:
                current_direction = token
            elif current_direction and token:
                # This token contains port names for the current direction
                # Remove any trailing commas and split by comma
                port_list = token.rstrip(',').strip()
                
                # Split by comma to get individual port declarations
                port_items = [p.strip() for p in port_list.split(',') if p.strip()]
                
                for port_item in port_items:
                    # Check for array notation [msb:lsb]
                    array_match = re.match(r'\[(\d+):(\d+)\]\s*(\w+)', port_item)
                    if array_match:
                        msb, lsb, port_name = array_match.groups()
                        # Expand array into individual ports
                        try:
                            msb_int = int(msb)
                            lsb_int = int(lsb)
                            for i in range(min(msb_int, lsb_int), max(msb_int, lsb_int) + 1):
                                ports[f"{port_name}[{i}]"] = current_direction
                            ports[port_name] = current_direction
                        except ValueError:
                            pass
                    else:
                        # Simple port name without array notation
                        # Extract just the identifier (handles cases like "a2", "b_in", etc.)
                        port_match = re.match(r'(\w+)', port_item)
                        if port_match:
                            port_name = port_match.group(1)
                            ports[port_name] = current_direction
        
        # Fallback: also try the old pattern for compatibility
        port_pattern = r'(input|output|inout)\s+(?:\[(\d+):(\d+)\])?\s*(\w+)'
        matches = re.findall(port_pattern, ports_str)
        
        # Process each matched port declaration
        for direction, msb, lsb, port_name in matches:
            # Handle array notation if present
            if msb and lsb:
                try:
                    # Convert string bounds to integers
                    msb_val = int(msb)  # Most Significant Bit (higher index)
                    lsb_val = int(lsb)  # Least Significant Bit (lower index)
                    
                    # Create individual port entries for each bit in the array
                    if msb_val >= lsb_val:
                        # Normal order: [3:0] means bits 3, 2, 1, 0
                        for i in range(lsb_val, msb_val + 1):
                            ports[f"{port_name}[{i}]"] = direction.strip()
                    else:
                        # Reverse order: [0:3] means bits 0, 1, 2, 3
                        for i in range(msb_val, lsb_val + 1):
                            ports[f"{port_name}[{i}]"] = direction.strip()
                    
                    # Also add the base port name (without array bounds)
                    ports[port_name] = direction.strip()
                    
                except ValueError:
                    # If bounds parsing fails, just add the base port name
                    ports[port_name] = direction.strip()
            else:
                # Simple port without array notation
                ports[port_name.strip()] = direction.strip()
        
        return ports
    
    def _extract_gates_and_nets(self, code: str, module_name: str) -> Tuple[List[Gate], Dict[str, Net]]:
        """
        Extract all gates and nets from a module's code
        
        This is the main method that orchestrates the extraction of circuit elements
        from the module body. It:
        1. Finds the module body boundaries
        2. Extracts gate instances (and, or, not, etc.)
        3. Extracts module instantiations (hierarchical components)
        4. Extracts assign statements (treated as gates)
        5. Extracts wire/net declarations
        
        Args:
            code: Complete Verilog code
            module_name: Name of the module to extract from
            
        Returns:
            Tuple of (gates_list, nets_dictionary)
        """
        gates = []           # List to store all Gate objects
        nets = {}            # Dictionary to store Net objects (name -> Net)
        seen_gates = set()   # Track gates to avoid duplicates across parsing methods
        
        # Find the specific module in the code
        module_start = code.find(f'module {module_name}')
        if module_start == -1:
            return gates, nets  # Module not found
        
        # Find the start of module body
        # Some modules use 'begin' keyword, others don't
        body_start = code.find('begin', module_start)
        if body_start == -1:
            # No 'begin' keyword, start after the semicolon following port list
            body_start = code.find(';', module_start) + 1
        
        # Find the end of the module
        body_end = code.find('endmodule', body_start)
        if body_end == -1:
            body_end = len(code)  # Use end of file if no endmodule found
        
        # Extract the module body text for parsing
        module_body = code[body_start:body_end]
        
        # Extract different types of gates and circuit elements
        gates.extend(self._parse_gate_instances(module_body, seen_gates))     # Basic gates (and, or, not, etc.)
        gates.extend(self._parse_module_instances(module_body, seen_gates))   # Module instantiations
        gates.extend(self._parse_assign_statements(module_body, seen_gates))  # Assign statements as gates
        
        # Extract wire/net declarations
        nets = self._parse_net_declarations(module_body)
        
        return gates, nets
    
    def _parse_gate_instances(self, module_body: str, seen_gates: set = None) -> List[Gate]:
        """
        Parse basic gate instances from module body
        
        This method extracts gate instantiations like:
        - and G1 (a, b, y);
        - or G2 (x, y, z);
        - not INV1 (a, y);
        - fa FA0 (a, b, cin, cout, sum);
        
        It handles both uppercase (mapped files) and lowercase (unmapped files) gate names.
        The method also handles multi-output gates like full adders and half adders.
        
        Args:
            module_body: The module body text to parse
            seen_gates: Set to track already parsed gates (prevents duplicates)
            
        Returns:
            List of Gate objects representing the parsed gates
        """
        gates = []
        if seen_gates is None:
            seen_gates = set()  # Track gates to avoid duplicates
        
        # Gate patterns in order of specificity (more specific patterns first)
        # Each pattern is a tuple of (regex_pattern, gate_type_name)
        # The regex captures: gate_name and connection_list
        # Examples: "and G1 (a, b, y);" -> gate_name="G1", connections="a, b, y"
        gate_patterns = [
            # \b ensures we match standalone gate keywords, not substrings
            # of longer names (e.g. 'or' must not match inside 'Subtractor')
            (r'\bXNOR\s+(\w+)\s*\((.*?)\)\s*;', 'xnor'),
            (r'\bXOR\s+(\w+)\s*\((.*?)\)\s*;', 'xor'),
            (r'\bNAND\s+(\w+)\s*\((.*?)\)\s*;', 'nand'),
            (r'\bNOR\s+(\w+)\s*\((.*?)\)\s*;', 'nor'),
            (r'\bAND\s+(\w+)\s*\((.*?)\)\s*;', 'and'),
            (r'\bOR\s+(\w+)\s*\((.*?)\)\s*;', 'or'),
            (r'\bNOT\s+(\w+)\s*\((.*?)\)\s*;', 'not'),
            (r'\bINV\s+(\w+)\s*\((.*?)\)\s*;', 'not'),
            (r'\bMUX4\s+(\w+)\s*\((.*?)\)\s*;', 'mux4'),
            (r'\bMUX2\s+(\w+)\s*\((.*?)\)\s*;', 'mux2'),
            (r'\bMUX\s+(\w+)\s*\((.*?)\)\s*;', 'mux'),
            (r'\bHA\s+(\w+)\s*\((.*?)\)\s*;', 'ha'),
            (r'\bFA\s+(\w+)\s*\((.*?)\)\s*;', 'fa'),
            (r'\bHS\s+(\w+)\s*\((.*?)\)\s*;', 'hs'),
            (r'\bFS\s+(\w+)\s*\((.*?)\)\s*;', 'fs'),
            (r'\bxnor\s+(\w+)\s*\((.*?)\)\s*;', 'xnor'),
            (r'\bxor\s+(\w+)\s*\((.*?)\)\s*;', 'xor'),
            (r'\bnand\s+(\w+)\s*\((.*?)\)\s*;', 'nand'),
            (r'\bnor\s+(\w+)\s*\((.*?)\)\s*;', 'nor'),
            (r'\band\s+(\w+)\s*\((.*?)\)\s*;', 'and'),
            (r'\bor\s+(\w+)\s*\((.*?)\)\s*;', 'or'),
            (r'\bnot\s+(\w+)\s*\((.*?)\)\s*;', 'not'),
            (r'\bha\s+(\w+)\s*\((.*?)\)\s*;', 'ha'),
            (r'\bfa\s+(\w+)\s*\((.*?)\)\s*;', 'fa'),
            (r'\bhs\s+(\w+)\s*\((.*?)\)\s*;', 'hs'),
            (r'\bfs\s+(\w+)\s*\((.*?)\)\s*;', 'fs'),
        ]
        
        # Apply each gate pattern to the module body
        for pattern, gate_type in gate_patterns:
            # Find all matches for this gate type pattern
            matches = re.findall(pattern, module_body, re.DOTALL)
            
            # Process each matched gate
            for match in matches:
                gate_name = match[0]      # First capture group: gate instance name
                connections = match[1]    # Second capture group: connection list
                
                # Skip if we've already seen this gate (avoid duplicates)
                if gate_name not in seen_gates:
                    inputs, outputs, port_map = self._parse_gate_connections(connections, gate_type)
                    
                    # Create Gate object with parsed information
                    gate = Gate(
                        name=gate_name,        # Instance name (e.g., "G1", "FA0")
                        gate_type=gate_type,   # Gate type (e.g., "and", "fa")
                        inputs=inputs,         # List of input net names
                        outputs=outputs,       # List of output net names
                        port_map=port_map      # Port mapping
                    )
                    gates.append(gate)
                    seen_gates.add(gate_name)  # Mark as seen to avoid duplicates
        
        return gates
    
    def _parse_module_instances(self, module_body: str, seen_gates: set = None) -> List[Gate]:
        """
        Parse module instantiations from module body
        
        This method extracts hierarchical module instantiations like:
        - full_adder FA0 (.a(a[0]), .b(b[0]), .cin(cin), .sum(sum[0]), .cout(c1));
        - half_adder HA0 (.a(a), .b(b), .sum(s), .cout(c));
        
        It handles named port connections (e.g., .a(input_signal)) and treats
        module instantiations as gates for visualization purposes.
        
        Args:
            module_body: The module body text to parse
            seen_gates: Set to track already parsed gates (prevents duplicates)
            
        Returns:
            List of Gate objects representing module instantiations
        """
        gates = []
        if seen_gates is None:
            seen_gates = set()
        
        # Pattern for module instantiations:
        # module_type instance_name (.port1(net1), .port2(net2), ...);
        # Examples:
        # - full_adder FA0 (.a(a[0]), .b(b[0]), .cin(cin), .sum(sum[0]), .cout(c1));
        # - half_adder HA0 (.a(a), .b(b), .sum(s), .cout(c));
        pattern = r'(\w+)\s+(\w+)\s*\((.*?)\)\s*;'
        matches = re.findall(pattern, module_body, re.DOTALL)
        
        # Process each module instantiation
        for module_type, instance_name, connections in matches:
            # Skip if already processed
            if instance_name not in seen_gates:
                # Skip basic gates (already handled by _parse_gate_instances)
                # This prevents double-parsing of gates that could be interpreted as modules
                skip_types = {
                    'and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor',
                    'AND', 'OR', 'NOT', 'NAND', 'NOR', 'XOR', 'XNOR',
                    'INV', 'FA', 'HA', 'FS', 'HS', 'MUX', 'MUX2', 'MUX4',
                    'fa', 'ha', 'fs', 'hs', 'mux', 'mux2', 'mux4',
                    'input', 'output', 'inout', 'wire', 'reg', 'assign',
                }
                if module_type in skip_types:
                    continue
                
                # Map module type names to simulator-recognized gate types
                gate_type_mapping = {
                    'full_adder': 'fa',
                    'FullAdder': 'fa',
                    'half_adder': 'ha',
                    'HalfAdder': 'ha',
                    'full_subtractor': 'fs',
                    'FullSubtractor': 'fs',
                    'half_subtractor': 'hs',
                    'HalfSubtractor': 'hs',
                    'mux2': 'mux2',
                    'Mux': 'mux2',
                    'mux4': 'mux4',
                }
                mapped_gate_type = gate_type_mapping.get(module_type, module_type)

                # Parse connections, passing mapped gate type for positional splitting
                inputs, outputs, port_map = self._parse_gate_connections(connections, mapped_gate_type)
                
                # Create Gate object representing the module instantiation
                gate = Gate(
                    name=instance_name,        # Instance name (e.g., "FA0", "HA0")
                    gate_type=mapped_gate_type,  # Mapped gate type for simulation
                    inputs=inputs,             # List of input net names
                    outputs=outputs,           # List of output net names
                    port_map=port_map          # Port mapping
                )
                gates.append(gate)
                seen_gates.add(instance_name)  # Mark as seen to avoid duplicates
        
        return gates
    
    def _parse_assign_statements(self, module_body: str, seen_gates: set = None) -> List[Gate]:
        """
        Parse assign statements as gates
        
        This method extracts continuous assignments like:
        - assign sum = a ^ b ^ cin;
        - assign carry = (a & b) | (b & cin) | (a & cin);
        - assign output = input1 & input2;
        
        It treats assign statements as gates for visualization purposes, parsing
        the right-hand side expression to determine gate type and inputs.
        
        Args:
            module_body: The module body text to parse
            seen_gates: Set to track already parsed gates (prevents duplicates)
            
        Returns:
            List of Gate objects representing assign statements
        """
        gates = []
        if seen_gates is None:
            seen_gates = set()
        
        # Pattern for assign statements:
        # assign output_variable = expression;
        # Examples:
        # - assign sum = a ^ b ^ cin;
        # - assign carry = (a & b) | (b & cin);
        # - assign Q[2] = !bout2[2];  (with array indexing and NOT)
        # Handle array notation like Q[2], bout2[2], etc.
        pattern = r'assign\s+(\w+(?:\[\d+\])?)\s*=\s*(.*?)\s*;'
        matches = re.findall(pattern, module_body, re.DOTALL)
        
        # Process each assign statement
        for output_var, expression in matches:
            # Skip if already processed
            if output_var not in seen_gates:
                # Parse the expression to determine gate type and extract input variables
                inputs, gate_type = self._parse_expression(expression)
                
                gate = Gate(
                    name=f"assign_{output_var}",
                    gate_type=gate_type,
                    inputs=inputs,
                    outputs=[output_var],
                    expression=expression.strip(),
                )
                gates.append(gate)
                seen_gates.add(output_var)  # Mark as seen to avoid duplicates
        
        return gates
    
    def _parse_expression(self, expression: str) -> Tuple[List[str], str]:
        """
        Parse a logical expression to extract inputs and gate type
        
        This method analyzes Verilog expressions like:
        - a ^ b ^ cin (XOR operation)
        - a & b (AND operation)
        - !bout2[2] (NOT operation with array indexing)
        - !PR2[2] & bout1[2] (NOT and AND operation)
        - (a & b) | (b & cin) | (a & cin) (complex expression)
        
        It determines the gate type based on operators and extracts input variables.
        
        Args:
            expression: The right-hand side of an assign statement
            
        Returns:
            Tuple of (input_variables_list, gate_type)
        """
        expression = expression.strip()
        original_expression = expression
        
        # Check for NOT operator first (handled separately)
        has_not = False
        if '!' in expression or '~' in expression:
            has_not = True
            # Remove NOT operators for variable extraction (but keep track)
            expression = re.sub(r'[!~]', '', expression)
        
        # Remove parentheses and clean up the expression
        # This simplifies parsing but may lose some structural information
        expression = re.sub(r'[()]', '', expression)
        
        # Determine gate type based on operators present in the expression
        # This is a simplified approach - complex expressions are treated as single gates
        if '^' in expression and ('&' in expression or '|' in expression):
            # Complex expression mixing XOR and AND/OR operations
            gate_type = 'complex'
        elif '&' in expression and '|' in expression:
            # Complex expression with both AND and OR
            gate_type = 'and'  # Default to AND for complex expressions
        elif '^' in expression:
            # XOR operation: a ^ b ^ cin
            # If NOT applies to whole expression, use XNOR; otherwise XOR
            if has_not and not ('&' in original_expression or '|' in original_expression):
                gate_type = 'xnor'
            else:
                gate_type = 'xor'
        elif '&' in expression:
            # AND operation: a & b or !PR2[2] & bout1[2]
            # If NOT applies to whole expression, use NAND; otherwise AND
            if has_not and expression.count('&') == 1 and '|' not in original_expression:
                # Check if NOT is applied to a single term or the whole expression
                # For simplicity, treat as AND (NOT will be handled by input value)
                gate_type = 'and'
            else:
                gate_type = 'and'
        elif '|' in expression:
            # OR operation: a | b
            # If NOT applies to whole expression, use NOR; otherwise OR
            if has_not and not ('&' in original_expression):
                gate_type = 'nor'
            else:
                gate_type = 'or'
        elif has_not:
            # Simple NOT operation: !a or ~a
            gate_type = 'not'
        else:
            # Simple wire assignment with no operators (e.g. assign sel = Q)
            gate_type = 'buf'
        
        # Extract variable names from the expression (handle array indexing)
        # Pattern matches: variable names with optional array indices like Q[2], bout2[2]
        # Examples: "Q[2]", "bout2[2]", "PR2[0]", "a", "b"
        variables = re.findall(r'\b[a-zA-Z_]\w*(?:\[\d+\])?', original_expression)
        inputs = list(dict.fromkeys(variables))
        
        # If no variables found, try simpler pattern
        if not inputs:
            variables = re.findall(r'[a-zA-Z_]\w*(?:\[\d+\])?', original_expression)
            inputs = list(dict.fromkeys(variables))
        
        return inputs, gate_type
    
    def _parse_gate_connections(self, connections: str,
                               gate_type: str = '') -> Tuple[List[str], List[str], Dict[str, str]]:
        """
        Parse gate input/output connections from connection string.

        Handles named connections (.port(net)) and positional connections.
        For positional connections the split between inputs and outputs depends
        on the gate_type:
          - Standard primitives (and, or, not, ...): first argument is the output.
          - Multi-output components (fa, ha, fs, hs): last N are outputs.
          - MUX: last argument is the output.
        
        Args:
            connections: Connection string from gate instantiation
            gate_type: The type of gate (e.g. 'and', 'fa', 'ha') used for
                       positional connection splitting.
            
        Returns:
            Tuple of (input_nets_list, output_nets_list, port_map)
        """
        inputs = []
        outputs = []
        port_map = {}
        
        conns = [conn.strip() for conn in connections.split(',')]
        
        for conn in conns:
            if '.' in conn:
                match = re.match(r'\.(\w+)\s*\((.*?)\)', conn)
                if match:
                    port_name = match.group(1)
                    net_name = match.group(2).strip()
                    
                    port_map[port_name] = net_name
                    
                    output_port_names = [
                        'y', 'out', 'z', 'q', 'sum', 'cout', 'diff', 'bout',
                        's', 'co', 'bo', 'con', 'sn', 'result', 'carry',
                        'output', 'dout', 'do', 'f', 'p', 'product',
                    ]
                    if port_name.lower() in output_port_names:
                        outputs.append(net_name)
                    else:
                        inputs.append(net_name)
            else:
                inputs.append(conn)
        
        # For positional connections (no named ports), split based on gate type.
        if not port_map and inputs:
            gt = gate_type.lower()
            # Multi-output gates: inputs come first, last N are outputs
            #   FA/FS: 3 inputs, 2 outputs (carry/borrow, sum/diff)
            #   HA/HS: 2 inputs, 2 outputs (carry/borrow, sum/diff)
            #   MUX2:  3 inputs, 1 output
            #   MUX4:  6 inputs, 1 output
            if gt in ('fa', 'fs') and len(inputs) >= 5:
                outputs = inputs[3:]
                inputs = inputs[:3]
            elif gt in ('ha', 'hs') and len(inputs) >= 4:
                outputs = inputs[2:]
                inputs = inputs[:2]
            elif gt in ('mux', 'mux2') and len(inputs) >= 4:
                outputs = [inputs[-1]]
                inputs = inputs[:-1]
            elif gt == 'mux4' and len(inputs) >= 7:
                outputs = [inputs[-1]]
                inputs = inputs[:-1]
            else:
                # Standard Verilog primitives: first argument is the output
                outputs = [inputs[0]]
                inputs = inputs[1:]
        
        # For multi-output gates with named connections, ensure the output order
        # matches what the simulator returns:
        #   FA/HA → [carry, sum]    FS/HS → [borrow, diff]
        # The carry/borrow port must be outputs[0] and sum/diff must be outputs[1].
        gt = gate_type.lower()
        if port_map and len(outputs) == 2 and gt in ('fa', 'ha', 'fs', 'hs'):
            carry_ports = {'cout', 'carry', 'co', 'con', 'bout', 'borrow', 'bo'}
            sum_ports = {'sum', 's', 'sn', 'diff', 'd'}
            # Find which port name maps to each output net
            port_for_net = {}
            for pname, nname in port_map.items():
                if nname in outputs:
                    port_for_net[nname] = pname.lower()
            # Reorder: carry/borrow first, sum/diff second
            if len(port_for_net) == 2:
                net0, net1 = outputs[0], outputs[1]
                p0 = port_for_net.get(net0, '')
                p1 = port_for_net.get(net1, '')
                if p0 in sum_ports and p1 in carry_ports:
                    outputs = [net1, net0]

        return inputs, outputs, port_map
    
    def _parse_net_declarations(self, module_body: str) -> Dict[str, Net]:
        """
        Parse wire declarations from module body
        
        This method extracts wire/net declarations like:
        - wire w1, w2, w3;
        - wire [3:0] sum;
        - wire carry_out;
        
        It creates Net objects for each declared wire, which are used during
        simulation to track signal values.
        
        Args:
            module_body: The module body text to parse
            
        Returns:
            Dictionary mapping wire names to Net objects
        """
        nets = {}
        
        # Pattern for wire declarations:
        # wire wire_name1, wire_name2, ...;
        # wire [msb:lsb] wire_name;
        # Examples:
        # - wire w1, w2, w3;
        # - wire [3:0] sum;
        # - wire carry_out;
        wire_pattern = r'wire\s+(\w+(?:\[\d+:\d+\])?)\s*(?:,(\w+(?:\[\d+:\d+\])?))*\s*;'
        matches = re.findall(wire_pattern, module_body)
        
        # Process each wire declaration
        for match in matches:
            # First wire in the declaration
            wire_name = match[0]
            nets[wire_name] = Net(name=wire_name)
            
            # Additional wires declared in the same statement (comma-separated)
            additional_wires = match[1].split(',') if match[1] else []
            for wire in additional_wires:
                wire = wire.strip()  # Remove whitespace
                if wire:  # Only add non-empty wire names
                    nets[wire] = Net(name=wire)
        
        return nets


class LogicSimulator:
    """
    Simulates logic behavior of the circuit
    
    This class performs digital logic simulation on the parsed circuit modules.
    It propagates logic values through the circuit based on gate functions,
    handling unknown values (X) and performing multiple simulation passes
    to ensure all values propagate correctly.
    """
    
    def __init__(self, modules: List[Module]):
        """
        Initialize the simulator with circuit modules
        
        Args:
            modules: List of Module objects representing the circuit
        """
        self.modules = modules                           # Circuit modules to simulate
        self.input_values: Dict[str, LogicValue] = {}   # Primary input values
    
    def set_inputs(self, inputs: Dict[str, LogicValue]):
        """
        Set primary input values for simulation
        
        Args:
            inputs: Dictionary mapping input net names to their logic values
        """
        self.input_values = inputs.copy()  # Make a copy to avoid modifying original
    
    def calculate_gate_depths(self) -> Dict[str, int]:
        """
        Calculate the depth (level) of each gate in the circuit
        
        Depth is defined as the maximum distance from any primary input:
        - Primary inputs have depth 0
        - Gates driven by primary inputs have depth 1
        - Gates driven by depth-1 gates have depth 2, etc.
        
        Returns:
            Dictionary mapping gate names to their depth levels
        """
        gate_depths = {}
        net_depths = {}
        
        # Get all primary inputs from modules
        primary_inputs = set()
        for module in self.modules:
            for port, direction in module.ports.items():
                if direction == 'input':
                    primary_inputs.add(port)
                    net_depths[port] = 0
        
        # Iteratively calculate depths until all gates are assigned
        max_iterations = 100
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            progress_made = False
            
            for module in self.modules:
                for gate in module.gates:
                    # Skip if we already calculated this gate's depth
                    if gate.name in gate_depths:
                        continue
                    
                    # Check if all inputs have known depths
                    input_depths = []
                    all_inputs_known = True
                    
                    for input_net in gate.inputs:
                        if input_net in net_depths:
                            input_depths.append(net_depths[input_net])
                        else:
                            all_inputs_known = False
                            break
                    
                    # If all input depths are known, calculate gate depth
                    if all_inputs_known and input_depths:
                        gate_depth = max(input_depths) + 1
                        gate_depths[gate.name] = gate_depth
                        
                        # Set output net depths
                        for output_net in gate.outputs:
                            net_depths[output_net] = gate_depth
                        
                        progress_made = True
            
            if not progress_made:
                break
        
        return gate_depths
    
    def simulate_by_level(self, max_level: int) -> Dict[str, LogicValue]:
        """
        Simulate the circuit up to a specific depth level
        
        Args:
            max_level: Maximum depth level to simulate (0 = inputs only, 1 = first level gates, etc.)
            
        Returns:
            Dictionary mapping net names to their logic values (only up to max_level)
        """
        # Initialize all nets to unknown (X) state
        all_nets = {}
        
        # Add all explicitly declared nets from modules
        for module in self.modules:
            all_nets.update(module.nets)
        
        # Create nets for all gate inputs and outputs that aren't explicitly declared
        for module in self.modules:
            for gate in module.gates:
                for input_net in gate.inputs:
                    if input_net not in all_nets:
                        all_nets[input_net] = Net(name=input_net, value=LogicValue.X)
                for output_net in gate.outputs:
                    if output_net not in all_nets:
                        all_nets[output_net] = Net(name=output_net, value=LogicValue.X)
        
        # Set primary input values from user input
        for net_name, value in self.input_values.items():
            if net_name in all_nets:
                all_nets[net_name].value = value
        
        # Calculate gate depths
        gate_depths = self.calculate_gate_depths()
        
        # Simulate gates up to max_level with iterative propagation
        # Multiple passes ensure all values propagate correctly
        max_iterations = 20  # Increased to ensure all values propagate
        for iteration in range(max_iterations):
            progress_made = False
            
            for module in self.modules:
                for gate in module.gates:
                    # Only simulate gates at or below the max level
                    gate_depth = gate_depths.get(gate.name, float('inf'))
                    if gate_depth <= max_level:
                        # Simulate this gate
                        output_values = self._simulate_gate(gate, all_nets)
                        
                        # Update output nets
                        for i, output_net in enumerate(gate.outputs):
                            if output_net in all_nets and i < len(output_values):
                                old_value = all_nets[output_net].value
                                new_value = output_values[i]
                                
                                # Update if we have a definite value or old was X
                                if new_value != LogicValue.X:
                                    all_nets[output_net].value = new_value
                                    if old_value != new_value:
                                        progress_made = True
                                elif old_value == LogicValue.X:
                                    all_nets[output_net].value = new_value
            
            # If no progress was made, simulation is stable
            if not progress_made:
                break
        
        # Return final net values as a simple dictionary
        return {name: net.value for name, net in all_nets.items()}
    
    def simulate(self) -> Dict[str, LogicValue]:
        """
        Simulate the circuit and return all net values
        
        This method performs the complete circuit simulation:
        1. Creates a comprehensive net dictionary including all nets in the circuit
        2. Sets primary input values
        3. Runs simulation passes until all values propagate
        4. Returns final net values
        
        Returns:
            Dictionary mapping net names to their final logic values
        """
        # Initialize all nets to unknown (X) state
        all_nets = {}
        
        # Add all explicitly declared nets from modules
        for module in self.modules:
            all_nets.update(module.nets)
        
        # Create nets for all gate inputs and outputs that aren't explicitly declared
        # This handles nets that are used but not declared with 'wire'
        for module in self.modules:
            for gate in module.gates:
                # Add nets for gate inputs
                for input_net in gate.inputs:
                    if input_net not in all_nets:
                        all_nets[input_net] = Net(name=input_net, value=LogicValue.X)
                # Add nets for gate outputs
                for output_net in gate.outputs:
                    if output_net not in all_nets:
                        all_nets[output_net] = Net(name=output_net, value=LogicValue.X)
        
        # Set primary input values from user input
        for net_name, value in self.input_values.items():
            if net_name in all_nets:
                all_nets[net_name].value = value
        
        # Simulate each module to propagate values through the circuit
        # Run simulation multiple times to ensure all modules converge
        for _ in range(5):  # Multiple passes for hierarchical designs
            for module in self.modules:
                self._simulate_module(module, all_nets)
        
        # Report any nets that could not be resolved
        unresolved = [name for name, net in all_nets.items() if net.value == LogicValue.X]
        if unresolved:
            print(f"Note: {len(unresolved)} net(s) remain unresolved (X): {', '.join(sorted(unresolved)[:10])}"
                  + (f" ... and {len(unresolved)-10} more" if len(unresolved) > 10 else ""))
        
        # Return final net values as a simple dictionary
        return {name: net.value for name, net in all_nets.items()}
    
    def _simulate_module(self, module: Module, all_nets: Dict[str, Net]):
        """
        Simulate a single module with iterative value propagation
        
        This method performs iterative simulation to handle combinational circuits
        where outputs depend on inputs that may not be available in the first pass.
        It continues until no more values can be determined or a maximum number
        of iterations is reached.
        
        Args:
            module: The module to simulate
            all_nets: Dictionary of all nets in the circuit with their current values
        """
        # Multiple simulation passes to ensure all values propagate through combinational logic
        max_iterations = 20  # Increased to ensure all values propagate (prevent infinite loops)
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            progress_made = False  # Track if any values changed in this iteration
            
            # Simulate each gate in the module
            for gate in module.gates:
                # Get current input values for this gate
                input_values = []
                for input_net in gate.inputs:
                    if input_net in all_nets:
                        input_values.append(all_nets[input_net].value)
                    else:
                        # Treat unknown nets as 0 to avoid X propagation in diagrams
                        input_values.append(LogicValue.ZERO)
                
                # Simulate the gate to get output values
                output_values = self._simulate_gate(gate, all_nets)
                
                # Update output nets with the gate's output values
                for i, output_net in enumerate(gate.outputs):
                    if output_net in all_nets and i < len(output_values):
                        old_value = all_nets[output_net].value
                        new_value = output_values[i]
                        
                        # Update the net value if:
                        # 1. We have a definite value (not X), OR
                        # 2. The old value was also X (no information lost)
                        if new_value != LogicValue.X:
                            # Only update if we have a definite value
                            all_nets[output_net].value = new_value
                            # Track progress if value actually changed
                            if old_value != new_value:
                                progress_made = True
                        elif old_value == LogicValue.X:
                            # Only update X if the old value was also X
                            all_nets[output_net].value = new_value
            
            # If no progress was made in this iteration, simulation is complete
            if not progress_made:
                break

    @staticmethod
    def _resolve_net_name(net_name: str, all_nets: Dict[str, Net]) -> str:
        """Resolve dynamic array indices like X[PR2[0]] at simulation time.

        If the name contains a nested bracket (e.g. X[PR2[0]]), it is a dynamic
        index that must be resolved to X[<value of PR2[0]>].
        """
        # Detect dynamic index: BASE[INNER_BASE[INNER_IDX]]
        m = re.match(r'^(\w+)\[(\w+\[\d+\])\]$', net_name)
        if m:
            base, inner_net = m.group(1), m.group(2)
            if inner_net in all_nets:
                idx_val = all_nets[inner_net].value
                if idx_val != LogicValue.X:
                    resolved = f"{base}[{idx_val.value}]"
                    if resolved in all_nets:
                        return resolved
        return net_name

    def _evaluate_expression(self, expr: str, all_nets: Dict[str, Net]) -> LogicValue:
        """Evaluate a Verilog assign expression using current net values.

        Supports: &, |, ^, !, ~, parentheses, ternary (sel ? b : a),
        and variable references with optional array indices.
        """
        def _lookup(var_name: str) -> int:
            """Return 0 or 1 for a net; -1 for X."""
            resolved = self._resolve_net_name(var_name.strip(), all_nets)
            if resolved in all_nets:
                v = all_nets[resolved].value
                if v == LogicValue.ONE:
                    return 1
                elif v == LogicValue.ZERO:
                    return 0
            return -1  # X

        expr = expr.strip()

        # Handle ternary: sel ? b : a
        ternary = re.match(r'^(.+?)\s*\?\s*(.+?)\s*:\s*(.+)$', expr)
        if ternary:
            sel_val = self._evaluate_expression(ternary.group(1), all_nets)
            if sel_val == LogicValue.ONE:
                return self._evaluate_expression(ternary.group(2), all_nets)
            elif sel_val == LogicValue.ZERO:
                return self._evaluate_expression(ternary.group(3), all_nets)
            return LogicValue.X

        # Convert Verilog expression to Python-evaluable form
        py_expr = expr
        # Replace Verilog operators with Python operators
        py_expr = py_expr.replace('~', ' not_bit ')
        py_expr = py_expr.replace('!', ' not_bit ')

        # Find all variable references (with optional array index)
        var_pattern = r'[a-zA-Z_]\w*(?:\[\w+(?:\[\d+\])?\])?'
        variables = re.findall(var_pattern, py_expr)
        variables = list(dict.fromkeys(variables))

        # Substitute variable values
        val_map: Dict[str, int] = {}
        has_x = False
        for var in variables:
            if var == 'not_bit':
                continue
            v = _lookup(var)
            if v == -1:
                has_x = True
            val_map[var] = v

        if has_x:
            return LogicValue.X

        # Build safe evaluation by replacing variables with their integer values
        # Process longest variable names first to avoid partial replacements
        safe_expr = py_expr
        for var in sorted(val_map.keys(), key=len, reverse=True):
            escaped = re.escape(var)
            safe_expr = re.sub(r'\b' + escaped + r'\b', str(val_map[var]), safe_expr)
            # Also handle array notation without word boundary issues
            safe_expr = safe_expr.replace(var, str(val_map[var]))

        # Replace Verilog/intermediate operators with Python bitwise operators
        safe_expr = safe_expr.replace('not_bit', '~')
        safe_expr = safe_expr.replace('&', ' & ')
        safe_expr = safe_expr.replace('|', ' | ')
        safe_expr = safe_expr.replace('^', ' ^ ')

        try:
            result = eval(safe_expr) & 1  # Mask to single bit
            return LogicValue.ONE if result else LogicValue.ZERO
        except Exception:
            return LogicValue.X

    def _simulate_gate(self, gate: Gate, all_nets: Dict[str, Net]) -> List[LogicValue]:
        """
        Simulate a single gate and return output values
        
        This method determines the output values of a gate based on its type
        and input values. It handles all supported gate types including basic
        gates and complex components like adders and multiplexers.
        
        Args:
            gate: The gate to simulate
            all_nets: Dictionary of all nets with their current values
            
        Returns:
            List of LogicValue objects representing the gate's outputs
        """
        # Get input values for this gate, resolving dynamic array indices
        input_values = []
        for input_net in gate.inputs:
            resolved = self._resolve_net_name(input_net, all_nets)
            if resolved in all_nets:
                input_values.append(all_nets[resolved].value)
            else:
                input_values.append(LogicValue.X)

        # For assign gates with a stored expression, evaluate it directly
        if gate.expression:
            return [self._evaluate_expression(gate.expression, all_nets)]
        
        # Route to appropriate gate simulation method based on gate type
        if gate.gate_type == 'buf':
            return [input_values[0]] if input_values else [LogicValue.X]
        elif gate.gate_type == 'and':
            return self._simulate_and(input_values)
        elif gate.gate_type == 'or':
            return self._simulate_or(input_values)
        elif gate.gate_type == 'not':
            return self._simulate_not(input_values)
        elif gate.gate_type == 'nand':
            return self._simulate_nand(input_values)
        elif gate.gate_type == 'nor':
            return self._simulate_nor(input_values)
        elif gate.gate_type == 'xor':
            return self._simulate_xor(input_values)
        elif gate.gate_type == 'xnor':
            return self._simulate_xnor(input_values)
        elif gate.gate_type == 'fa':
            return self._simulate_full_adder(input_values)
        elif gate.gate_type == 'ha':
            return self._simulate_half_adder(input_values)
        elif gate.gate_type == 'fs':
            return self._simulate_full_subtractor(input_values)
        elif gate.gate_type == 'hs':
            return self._simulate_half_subtractor(input_values)
        elif gate.gate_type in ['mux', 'mux2']:
            return self._simulate_mux2(input_values)
        elif gate.gate_type == 'mux4':
            return self._simulate_mux4(input_values)
        else:
            # Unknown gate type -- attempt recursive sub-module simulation
            sub_module = self._find_module_definition(gate.gate_type)
            if sub_module and gate.port_map:
                return self._simulate_submodule(gate, sub_module, all_nets)
            # Fallback: propagate X so downstream gates know value is unresolved
            print(f"Warning: Unknown gate type '{gate.gate_type}' for gate '{gate.name}', outputs set to X")
            return [LogicValue.X] * max(len(gate.outputs), 1)
    
    def _find_module_definition(self, gate_type: str) -> Optional[Module]:
        """Return the Module whose name matches *gate_type* (case-insensitive)."""
        for module in self.modules:
            if module.name.lower() == gate_type.lower():
                return module
        return None

    def _simulate_submodule(self, gate: Gate, sub_module: Module,
                            parent_nets: Dict[str, Net]) -> List[LogicValue]:
        """Recursively simulate a sub-module instance and return its output values."""
        sub_sim = LogicSimulator([sub_module])
        sub_inputs: Dict[str, LogicValue] = {}

        for port_name, parent_net in gate.port_map.items():
            if port_name in sub_module.ports and sub_module.ports[port_name] == 'input':
                if parent_net in parent_nets:
                    sub_inputs[port_name] = parent_nets[parent_net].value
                else:
                    sub_inputs[port_name] = LogicValue.X

        sub_sim.set_inputs(sub_inputs)
        sub_net_values = sub_sim.simulate()

        results: List[LogicValue] = []
        for output_net in gate.outputs:
            # Find which sub-module port maps to this parent net
            matched = False
            for port_name, parent_net in gate.port_map.items():
                if parent_net == output_net:
                    val = sub_net_values.get(port_name, LogicValue.X)
                    results.append(val)
                    matched = True
                    break
            if not matched:
                results.append(LogicValue.X)
        return results

    def _simulate_and(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate AND gate logic
        
        AND gate output is 1 only if ALL inputs are 1.
        - If any input is 0, output is 0
        - If any input is X (unknown), output is X
        - Otherwise (all inputs are 1), output is 1
        
        Args:
            inputs: List of input logic values
            
        Returns:
            List with single output value
        """
        if LogicValue.ZERO in inputs:
            return [LogicValue.ZERO]  # Any 0 input makes output 0
        elif LogicValue.X in inputs:
            return [LogicValue.X]     # Any unknown input makes output unknown
        else:
            return [LogicValue.ONE]   # All inputs are 1, so output is 1
    
    def _simulate_or(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate OR gate logic
        
        OR gate output is 1 if ANY input is 1.
        - If any input is 1, output is 1
        - If any input is X (unknown), output is X
        - Otherwise (all inputs are 0), output is 0
        
        Args:
            inputs: List of input logic values
            
        Returns:
            List with single output value
        """
        if LogicValue.ONE in inputs:
            return [LogicValue.ONE]   # Any 1 input makes output 1
        elif LogicValue.X in inputs:
            return [LogicValue.X]     # Any unknown input makes output unknown
        else:
            return [LogicValue.ZERO]  # All inputs are 0, so output is 0
    
    def _simulate_not(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate NOT gate (inverter) logic
        
        NOT gate inverts the input value.
        - 0 input → 1 output
        - 1 input → 0 output
        - X input → X output
        
        Args:
            inputs: List with single input logic value
            
        Returns:
            List with single output value
        """
        if not inputs:
            return [LogicValue.X]  # No input, output is unknown
        
        input_val = inputs[0]
        if input_val == LogicValue.ZERO:
            return [LogicValue.ONE]   # Invert 0 to 1
        elif input_val == LogicValue.ONE:
            return [LogicValue.ZERO]  # Invert 1 to 0
        else:
            return [LogicValue.X]     # Unknown input, unknown output
    
    def _simulate_nand(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate NAND gate logic
        
        NAND is the complement of AND: NAND = NOT(AND)
        - Output is 0 only if ALL inputs are 1
        - Otherwise output is 1
        
        Args:
            inputs: List of input logic values
            
        Returns:
            List with single output value
        """
        and_result = self._simulate_and(inputs)[0]  # Get AND result first
        return self._simulate_not([and_result])     # Invert it for NAND
    
    def _simulate_nor(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate NOR gate logic
        
        NOR is the complement of OR: NOR = NOT(OR)
        - Output is 1 only if ALL inputs are 0
        - Otherwise output is 0
        
        Args:
            inputs: List of input logic values
            
        Returns:
            List with single output value
        """
        or_result = self._simulate_or(inputs)[0]   # Get OR result first
        return self._simulate_not([or_result])     # Invert it for NOR
    
    def _simulate_xor(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate XOR gate logic
        
        XOR (exclusive OR) outputs 1 when the number of 1 inputs is odd.
        - Even number of 1s → output 0
        - Odd number of 1s → output 1
        - Any unknown input → output unknown
        
        Args:
            inputs: List of input logic values
            
        Returns:
            List with single output value
        """
        if len(inputs) < 2:
            return [LogicValue.X]  # Need at least 2 inputs for XOR
        
        # If any input is unknown, output is unknown
        if LogicValue.X in inputs:
            return [LogicValue.X]
        
        # Count the number of 1s in the inputs
        ones_count = sum(1 for val in inputs if val == LogicValue.ONE)
        
        # XOR output is 1 if odd number of 1s, 0 if even number of 1s
        if ones_count % 2 == 1:
            return [LogicValue.ONE]   # Odd number of 1s
        else:
            return [LogicValue.ZERO]  # Even number of 1s
    
    def _simulate_xnor(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate XNOR gate logic
        
        XNOR is the complement of XOR: XNOR = NOT(XOR)
        - Output is 0 when the number of 1 inputs is odd
        - Output is 1 when the number of 1 inputs is even
        
        Args:
            inputs: List of input logic values
            
        Returns:
            List with single output value
        """
        xor_result = self._simulate_xor(inputs)[0]  # Get XOR result first
        return self._simulate_not([xor_result])     # Invert it for XNOR
    
    def _simulate_full_adder(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate Full Adder (FA) gate logic
        
        A Full Adder adds three 1-bit numbers (A, B, and carry-in) and produces
        a 1-bit sum and a 1-bit carry-out.
        
        Truth table:
        A  B  CI | SUM  COUT
        ---------|----------
        0  0  0  |  0    0
        0  0  1  |  1    0
        0  1  0  |  1    0
        0  1  1  |  0    1
        1  0  0  |  1    0
        1  0  1  |  0    1
        1  1  0  |  0    1
        1  1  1  |  1    1
        
        Args:
            inputs: List of 3 input values [A, B, CI]
            
        Returns:
            List of 2 output values [COUT, SUM]
        """
        if len(inputs) < 3:
            return [LogicValue.X, LogicValue.X]  # Need 3 inputs for full adder
        
        # Extract inputs: A, B, CI (carry in)
        a, b, ci = inputs[0], inputs[1], inputs[2]
        
        # Sum = A XOR B XOR CI (odd parity function)
        sum_result = self._simulate_xor([a, b, ci])[0]
        
        # Carry out = (A AND B) OR (B AND CI) OR (A AND CI)
        # This represents: "at least two of the three inputs are 1"
        ab = self._simulate_and([a, b])[0]      # A AND B
        bci = self._simulate_and([b, ci])[0]    # B AND CI
        aci = self._simulate_and([a, ci])[0]    # A AND CI
        carry_out = self._simulate_or([ab, bci, aci])[0]  # OR of all AND terms
        
        return [carry_out, sum_result]  # Return [COUT, SUM]
    
    def _simulate_half_adder(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate Half Adder (HA) gate logic
        
        A Half Adder adds two 1-bit numbers (A and B) and produces
        a 1-bit sum and a 1-bit carry-out.
        
        Truth table:
        A  B | SUM  COUT
        -----|----------
        0  0 |  0    0
        0  1 |  1    0
        1  0 |  1    0
        1  1 |  0    1
        
        Args:
            inputs: List of 2 input values [A, B]
            
        Returns:
            List of 2 output values [COUT, SUM]
        """
        if len(inputs) < 2:
            return [LogicValue.X, LogicValue.X]  # Need 2 inputs for half adder
        
        # Extract inputs: A, B
        a, b = inputs[0], inputs[1]
        
        # Sum = A XOR B (exclusive OR)
        sum_result = self._simulate_xor([a, b])[0]
        
        # Carry out = A AND B (both inputs must be 1 to generate carry)
        carry_out = self._simulate_and([a, b])[0]
        
        return [carry_out, sum_result]  # Return [COUT, SUM]
    
    def _simulate_half_subtractor(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate Half Subtractor (HS) gate logic
        
        A Half Subtractor subtracts one 1-bit number (B) from another (A) and
        produces a 1-bit difference and a 1-bit borrow-out.
        
        Truth table:
        A  B | DIFF  BOUT
        -----|-----------
        0  0 |  0     0
        0  1 |  1     1
        1  0 |  1     0
        1  1 |  0     0
        
        Args:
            inputs: List of 2 input values [A, B] where A - B is computed
            
        Returns:
            List of 2 output values [BOUT, DIFF]
        """
        if len(inputs) < 2:
            return [LogicValue.X, LogicValue.X]  # Need 2 inputs for half subtractor
        
        # Extract inputs: A, B (A - B)
        a, b = inputs[0], inputs[1]
        
        # Difference = A XOR B (same as sum in half adder)
        diff_result = self._simulate_xor([a, b])[0]
        
        # Borrow out = (NOT A) AND B
        # This means: borrow only when A=0 and B=1
        not_a = self._simulate_not([a])[0]
        borrow_out = self._simulate_and([not_a, b])[0]
        
        return [borrow_out, diff_result]  # Return [BOUT, DIFF]
    
    def _simulate_full_subtractor(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate Full Subtractor (FS) gate logic
        
        A Full Subtractor subtracts three 1-bit numbers (A, B, and borrow-in) and
        produces a 1-bit difference and a 1-bit borrow-out.
        
        Truth table:
        A  B  BI | DIFF  BOUT
        ---------|-----------
        0  0  0  |  0    0
        0  0  1  |  1    1
        0  1  0  |  1    1
        0  1  1  |  0    1
        1  0  0  |  1    0
        1  0  1  |  0    0
        1  1  0  |  0    0
        1  1  1  |  1    1
        
        Args:
            inputs: List of 3 input values [A, B, BI] where A - B - BI is computed
            
        Returns:
            List of 2 output values [BOUT, DIFF]
        """
        if len(inputs) < 3:
            return [LogicValue.X, LogicValue.X]  # Need 3 inputs for full subtractor
        
        # Extract inputs: A, B, BI (borrow in)
        a, b, bi = inputs[0], inputs[1], inputs[2]
        
        # Difference = A XOR B XOR BI (odd parity function)
        diff_result = self._simulate_xor([a, b, bi])[0]
        
        # Borrow out = (NOT A AND B) OR (NOT A AND BI) OR (B AND BI)
        # This represents: "borrow needed when A=0 and (B=1 or BI=1), or when B=1 and BI=1"
        not_a = self._simulate_not([a])[0]
        not_a_and_b = self._simulate_and([not_a, b])[0]     # NOT A AND B
        not_a_and_bi = self._simulate_and([not_a, bi])[0]   # NOT A AND BI
        b_and_bi = self._simulate_and([b, bi])[0]           # B AND BI
        borrow_out = self._simulate_or([not_a_and_b, not_a_and_bi, b_and_bi])[0]
        
        return [borrow_out, diff_result]  # Return [BOUT, DIFF]
    
    def _simulate_mux2(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate 2-to-1 Multiplexer (MUX2) gate logic
        
        A 2-to-1 multiplexer selects one of two data inputs based on a select signal.
        
        Truth table:
        A  B  S | Y
        --------|--
        0  0  0 | 0 (A selected)
        0  0  1 | 0 (B selected)
        0  1  0 | 0 (A selected)
        0  1  1 | 1 (B selected)
        1  0  0 | 1 (A selected)
        1  0  1 | 0 (B selected)
        1  1  0 | 1 (A selected)
        1  1  1 | 1 (B selected)
        
        Args:
            inputs: List of 3 input values [A, B, S] where S is the select signal
            
        Returns:
            List with single output value [Y]
        """
        if len(inputs) < 3:
            return [LogicValue.X]  # Need 3 inputs for 2-to-1 MUX
        
        # Extract inputs: A, B, S (select)
        a, b, s = inputs[0], inputs[1], inputs[2]
        
        # Y = (NOT S AND A) OR (S AND B)
        # When S=0: Y = A (first input selected)
        # When S=1: Y = B (second input selected)
        not_s = self._simulate_not([s])[0]           # NOT S
        not_s_and_a = self._simulate_and([not_s, a])[0]  # NOT S AND A
        s_and_b = self._simulate_and([s, b])[0]          # S AND B
        output = self._simulate_or([not_s_and_a, s_and_b])[0]  # OR of both terms
        
        return [output]
    
    def _simulate_mux4(self, inputs: List[LogicValue]) -> List[LogicValue]:
        """
        Simulate 4-to-1 Multiplexer (MUX4) gate logic
        
        A 4-to-1 multiplexer selects one of four data inputs based on two select signals.
        
        Truth table:
        A  B  C  D  S1 S0 | Y
        ------------------|--
        0  0  0  0  0  0  | 0 (A selected)
        0  0  0  0  0  1  | 0 (B selected)
        0  0  0  0  1  0  | 0 (C selected)
        0  0  0  0  1  1  | 0 (D selected)
        1  0  0  0  0  0  | 1 (A selected)
        0  1  0  0  0  1  | 1 (B selected)
        0  0  1  0  1  0  | 1 (C selected)
        0  0  0  1  1  1  | 1 (D selected)
        
        Args:
            inputs: List of 6 input values [A, B, C, D, S1, S0] where S1,S0 are select signals
            
        Returns:
            List with single output value [Y]
        """
        if len(inputs) < 6:
            return [LogicValue.X]  # Need 6 inputs for 4-to-1 MUX
        
        # Extract inputs: A, B, C, D (data inputs), S1, S0 (select bits)
        a, b, c, d, s1, s0 = inputs[0], inputs[1], inputs[2], inputs[3], inputs[4], inputs[5]
        
        # Generate NOT signals for select bits
        not_s1 = self._simulate_not([s1])[0]  # NOT S1
        not_s0 = self._simulate_not([s0])[0]  # NOT S0
        
        # Y = (NOT S1 AND NOT S0 AND A) OR (NOT S1 AND S0 AND B) OR 
        #     (S1 AND NOT S0 AND C) OR (S1 AND S0 AND D)
        
        # Term 1: NOT S1 AND NOT S0 AND A (select A when S1=0, S0=0)
        term1 = self._simulate_and([not_s1, not_s0, a])[0]
        
        # Term 2: NOT S1 AND S0 AND B (select B when S1=0, S0=1)
        term2 = self._simulate_and([not_s1, s0, b])[0]
        
        # Term 3: S1 AND NOT S0 AND C (select C when S1=1, S0=0)
        term3 = self._simulate_and([s1, not_s0, c])[0]
        
        # Term 4: S1 AND S0 AND D (select D when S1=1, S0=1)
        term4 = self._simulate_and([s1, s0, d])[0]
        
        # Final output: OR of all terms (only one term will be active at a time)
        output = self._simulate_or([term1, term2, term3, term4])[0]
        
        return [output]


class DOTGenerator:
    """
    Generates Graphviz DOT files from circuit data
    
    This class creates DOT (Graph Description Language) files that can be rendered
    by Graphviz to produce circuit diagrams. It handles:
    - Node creation (inputs, gates, outputs)
    - Edge creation (connections between nodes)
    - Styling and layout configuration
    - Focus mode for highlighting specific gates
    """
    
    def __init__(self):
        """Initialize the DOT generator"""
        self.graph = None  # Will hold the Graphviz object
    
    def generate_dot(self, modules: List[Module], net_values: Dict[str, LogicValue], 
                    focus_gate: Optional[str] = None) -> str:
        """
        Generate DOT representation of the circuit
        
        This method creates a complete DOT file string that represents the circuit
        as a directed graph. It includes styling, layout, and all circuit elements.
        
        Args:
            modules: List of Module objects to visualize
            net_values: Dictionary of net names to their current logic values
            focus_gate: Optional gate name to focus on (highlight only this gate)
            
        Returns:
            DOT file content as a string
        """
        
        # Create directed graph with improved styling for circuit visualization
        dot = graphviz.Digraph(comment='Verilog Circuit')
        
        # Set graph layout properties
        dot.attr(rankdir='LR')  # Left to right layout (inputs → gates → outputs)
        dot.attr('graph', size='8.5,11!', ratio='auto', nodesep='0.3', ranksep='0.4')
        dot.attr('node', fontsize='8', width='0.6', height='0.4', margin='0.05,0.02')
        dot.attr('edge', fontsize='8', arrowsize='0.6')
        
        # Add all modules to the DOT graph
        for module in modules:
            self._add_module_to_dot(dot, module, net_values, focus_gate)
        
        return dot.source  # Return the DOT file content as a string

    def generate_high_level_dot(self, modules: List[Module]) -> str:
        """
        Generate a high-level DOT representation of the top-level module
        
        This method creates a simplified DOT graph that shows the top-level
        module as a single block with only its primary inputs and outputs.
        
        Args:
            modules: List of Module objects; the first is treated as top-level
        
        Returns:
            DOT file content as a string
        """

        # Safeguard: handle empty module list
        if not modules:
            dot = graphviz.Digraph(comment='High-level Verilog Module')
            dot.attr(rankdir='LR')
            dot.attr('graph', size='8.5,11!', ratio='auto', nodesep='0.3', ranksep='0.4')
            dot.attr('node', fontsize='8', width='0.6', height='0.4', margin='0.05,0.02')
            dot.attr('edge', fontsize='8', arrowsize='0.6')
            dot.node('empty', 'No modules to visualize', shape='box', fillcolor='lightgray', style='filled')
            return dot.source

        top_module = modules[0]

        # Create directed graph with similar styling to the detailed view
        dot = graphviz.Digraph(comment='High-level Verilog Module')
        dot.attr(rankdir='LR')  # Left to right layout (inputs → module → outputs)
        dot.attr('graph', size='8.5,11!', ratio='auto', nodesep='0.3', ranksep='0.4')
        dot.attr('node', fontsize='8', width='0.6', height='0.4', margin='0.05,0.02')
        dot.attr('edge', fontsize='8', arrowsize='0.6')

        # Create a single node representing the top-level module
        module_node_id = f"module_{top_module.name}"
        module_label = f"{top_module.name}\\n(high-level)"
        dot.node(module_node_id, module_label, shape='box', fillcolor='lightblue', style='filled,bold')

        # Collect unique base names for inputs and outputs (handle array ports)
        input_ports: Set[str] = set()
        output_ports: Set[str] = set()

        for port, direction in top_module.ports.items():
            base_name = port.split('[')[0] if '[' in port else port
            if direction == 'input':
                input_ports.add(base_name)
            elif direction == 'output':
                output_ports.add(base_name)

        # Add input nodes and edges into the module block
        for base_name in sorted(input_ports):
            input_node_id = f"input_{base_name}"
            dot.node(input_node_id, base_name, shape='circle', fillcolor='lightgreen', style='filled')
            dot.edge(input_node_id, module_node_id)

        # Add output nodes and edges out of the module block
        for base_name in sorted(output_ports):
            output_node_id = f"output_{base_name}"
            dot.node(output_node_id, base_name, shape='circle', fillcolor='orange', style='filled')
            dot.edge(module_node_id, output_node_id)

        return dot.source

    def generate_high_level_simulation_dot(self, modules: List[Module],
                                           net_values: Dict[str, LogicValue]) -> str:
        """
        Generate a higher-level simulation view.

        For hierarchical designs (top module contains sub-module instances) this
        renders each sub-module instance as a single box with simulation values
        on its port edges, hiding the internal gate-level detail.

        For flat / mapped designs (top module contains only primitive gates) this
        renders the top module as a single block with simulation values on the
        primary I/O ports.

        Args:
            modules: List of Module objects; the first is the top-level module
            net_values: Simulation results mapping net names to LogicValue

        Returns:
            DOT file content as a string
        """
        if not modules:
            dot = graphviz.Digraph(comment='High-level Simulation')
            dot.node('empty', 'No modules to visualize', shape='box',
                     fillcolor='lightgray', style='filled')
            return dot.source

        top_module = modules[0]
        primitive_types = {'and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor'}

        # Decide whether the design is hierarchical (has sub-module instances)
        has_submodule_instances = any(
            g.gate_type not in primitive_types
            for g in top_module.gates
            if not g.name.startswith('assign_')
        )

        dot = graphviz.Digraph(comment='High-level Simulation')
        dot.attr(rankdir='LR')
        dot.attr('graph', size='11,8.5!', ratio='auto', nodesep='0.5', ranksep='0.7')
        dot.attr('node', fontsize='9', width='0.7', height='0.5', margin='0.08,0.04')
        dot.attr('edge', fontsize='8', arrowsize='0.6')

        # --- Collect array-aware input / output labels with values ---
        def _port_label(base_name: str, direction: str) -> str:
            """Build a label like 'X[4:0]=10110' or 'a=1' with simulation values."""
            bits = []
            for port, d in top_module.ports.items():
                if d != direction:
                    continue
                pbase = port.split('[')[0] if '[' in port else port
                if pbase != base_name:
                    continue
                if '[' in port:
                    idx_str = port.split('[')[1].split(']')[0]
                    if idx_str.isdigit():
                        bits.append((int(idx_str), port))
                else:
                    val = net_values.get(port, LogicValue.X).value
                    return f"{base_name}={val}"
            if bits:
                bits.sort(key=lambda x: x[0], reverse=True)
                msb, lsb = bits[0][0], bits[-1][0]
                val_str = ''.join(net_values.get(p, LogicValue.X).value for _, p in bits)
                return f"{base_name}[{msb}:{lsb}]={val_str}"
            return base_name

        input_bases: Set[str] = set()
        output_bases: Set[str] = set()
        for port, direction in top_module.ports.items():
            base = port.split('[')[0] if '[' in port else port
            if direction == 'input':
                input_bases.add(base)
            elif direction == 'output':
                output_bases.add(base)

        # -- Add primary input nodes --
        for base in sorted(input_bases):
            label = _port_label(base, 'input')
            dot.node(f"input_{base}", label, shape='circle',
                     fillcolor='lightgreen', style='filled')

        # -- Add primary output nodes --
        for base in sorted(output_bases):
            label = _port_label(base, 'output')
            color = 'lightcoral'
            dot.node(f"output_{base}", label, shape='circle',
                     fillcolor=color, style='filled')

        if has_submodule_instances:
            # ---- Hierarchical view: one box per sub-module instance ----
            added_connections: Set[tuple] = set()
            assign_gates = [g for g in top_module.gates if g.name.startswith('assign_')]
            instance_gates = [g for g in top_module.gates if not g.name.startswith('assign_')]

            for gate in instance_gates:
                gate_label = f"{gate.name}\\n({gate.gate_type.upper()})"
                color = self._get_gate_color(gate.gate_type)
                dot.node(gate.name, gate_label, shape='box',
                         fillcolor=color, style='filled,bold')

            for gate in assign_gates:
                gate_label = f"{gate.name}\\n({gate.gate_type.upper()})"
                dot.node(gate.name, gate_label, shape='box',
                         fillcolor='khaki', style='filled')

            all_gates = instance_gates + assign_gates

            # Build output-net -> gate lookup for fast edge creation
            output_to_gate: Dict[str, str] = {}
            for gate in all_gates:
                for out_net in gate.outputs:
                    output_to_gate[out_net] = gate.name

            for gate in all_gates:
                for input_net in gate.inputs:
                    input_base = input_net.split('[')[0] if '[' in input_net else input_net
                    if input_base in input_bases:
                        conn = (f"input_{input_base}", gate.name)
                        if conn not in added_connections:
                            val = net_values.get(input_net, LogicValue.X).value
                            dot.edge(conn[0], conn[1], label=val)
                            added_connections.add(conn)
                    elif input_net in output_to_gate:
                        src = output_to_gate[input_net]
                        conn = (src, gate.name, input_net)
                        if conn not in added_connections:
                            val = net_values.get(input_net, LogicValue.X).value
                            short = input_net if len(input_net) <= 8 else ''
                            lbl = f"{short}={val}" if short else val
                            dot.edge(src, gate.name, label=lbl)
                            added_connections.add(conn)

                for output_net in gate.outputs:
                    output_base = output_net.split('[')[0] if '[' in output_net else output_net
                    if output_base in output_bases:
                        conn = (gate.name, f"output_{output_base}")
                        if conn not in added_connections:
                            val = net_values.get(output_net, LogicValue.X).value
                            dot.edge(conn[0], conn[1], label=val)
                            added_connections.add(conn)
        else:
            # ---- Flat / mapped view: single module block with I/O values ----
            module_id = f"module_{top_module.name}"
            module_label = f"{top_module.name}\\n({len(top_module.gates)} gates)"
            dot.node(module_id, module_label, shape='box',
                     fillcolor='lightblue', style='filled,bold')

            for base in sorted(input_bases):
                dot.edge(f"input_{base}", module_id)

            for base in sorted(output_bases):
                dot.edge(module_id, f"output_{base}")

        return dot.source

    def _add_module_to_dot(self, dot: graphviz.Digraph, module: Module, 
                          net_values: Dict[str, LogicValue], focus_gate: Optional[str]):
        """
        Add a module to the DOT graph with improved styling
        
        This method adds all elements of a module to the DOT graph:
        1. Primary input nodes (green circles)
        2. Gate nodes (colored boxes)
        3. Connections between nodes (edges)
        4. Primary output nodes (orange/red circles)
        
        Args:
            dot: Graphviz Digraph object to add nodes to
            module: Module object to visualize
            net_values: Dictionary of net names to their current logic values
            focus_gate: Optional gate name to focus on (only show this gate)
        """
        
        # Add primary input nodes (green circles)
        # These represent the module's input ports
        for port, direction in module.ports.items():
            if direction == 'input':
                # Check if this is an array input (has indexed versions in ports)
                is_array = any(
                    p.startswith(port + '[') and p.endswith(']') and module.ports.get(p) == 'input'
                    for p in module.ports.keys()
                )
                
                if is_array:
                    # Collect all bit values for this array input
                    array_indices = []
                    
                    # Find all array bits for this port
                    for p, d in module.ports.items():
                        if d == 'input' and p.startswith(port + '[') and p.endswith(']'):
                            idx_str = p[len(port)+1:-1]  # Extract index from "X[4]"
                            if idx_str.isdigit():
                                idx = int(idx_str)
                                array_indices.append((idx, p))
                    
                    # Sort by index and collect values (MSB first for display)
                    array_indices.sort(key=lambda x: x[0], reverse=True)
                    value_strs = []
                    for idx, bit_port in array_indices:
                        bit_value = net_values.get(bit_port, LogicValue.ZERO)
                        value_strs.append(bit_value.value)
                    
                    # Create label showing array name and bit values (MSB to LSB)
                    if array_indices:
                        msb = array_indices[0][0]  # First in reversed sort
                        lsb = array_indices[-1][0]  # Last in reversed sort
                        array_value_str = ''.join(value_strs)  # Already MSB first
                        label = f"{port}[{msb}:{lsb}]={array_value_str}"
                    else:
                        label = f"{port}=???"
                else:
                    # Single-bit input
                    value_str = net_values.get(port, LogicValue.ZERO).value
                    label = f"{port}={value_str}"
                
                # Add node with green circle styling
                dot.node(f"input_{port}", label, shape='circle', fillcolor='lightgreen', style='filled')
        
        # Add gates (colored boxes for basic gates, gray boxes for module instances)
        for gate in module.gates:
            # Skip gates not in focus mode if focus_gate is specified
            if focus_gate and gate.name != focus_gate and focus_gate not in gate.name:
                continue
            
            # Determine gate styling based on type
            if gate.gate_type in ['and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor', 'buf']:
                # Basic gates - use colored boxes with distinct colors for each type
                gate_label = f"{gate.name}\\n({gate.gate_type.upper()})"
                color = self._get_gate_color(gate.gate_type)
                dot.node(gate.name, gate_label, shape='box', fillcolor=color, style='filled')
            else:
                # Module instances and complex gates - use gray boxes
                gate_label = f"{gate.name}\\n({gate.gate_type})"
                dot.node(gate.name, gate_label, shape='box', fillcolor='lightgray', style='filled')
        
        # Add connections between nodes (edges)
        self._add_connections(dot, module, net_values, focus_gate)
        
        # Add primary output nodes (orange/red circles)
        # These represent the module's output ports
        for port, direction in module.ports.items():
            if direction == 'output':
                # Check if this is an array output (has indexed versions in ports)
                is_array = any(
                    p.startswith(port + '[') and p.endswith(']') and module.ports.get(p) == 'output'
                    for p in module.ports.keys()
                )
                
                if is_array:
                    # Collect all bit values for this array output
                    array_bits = []
                    array_indices = []
                    
                    # Find all array bits for this port
                    for p, d in module.ports.items():
                        if d == 'output' and p.startswith(port + '[') and p.endswith(']'):
                            idx_str = p[len(port)+1:-1]  # Extract index from "Q[2]"
                            if idx_str.isdigit():
                                idx = int(idx_str)
                                array_indices.append((idx, p))
                    
                    # Sort by index and collect values
                    array_indices.sort(key=lambda x: x[0])
                    value_strs = []
                    for idx, bit_port in array_indices:
                        bit_value = net_values.get(bit_port, LogicValue.ZERO)
                        value_strs.append(bit_value.value)
                        array_bits.append(bit_value.value)
                    
                    # Create label showing array name and bit values (MSB to LSB)
                    if array_indices:
                        msb = array_indices[-1][0]
                        lsb = array_indices[0][0]
                        array_value_str = ''.join(reversed(value_strs))  # MSB first
                        label = f"{port}[{msb}:{lsb}]={array_value_str}"
                    else:
                        label = f"{port}=???"
                    
                else:
                    # Single-bit output
                    value_str = net_values.get(port, LogicValue.ZERO).value
                    label = f"{port}={value_str}"
                
                # Use red for final outputs, orange for intermediate outputs
                color = 'lightcoral' if self._is_final_output(module, port) else 'orange'
                dot.node(f"output_{port}", label, shape='circle', fillcolor=color, style='filled')
    
    def _get_gate_color(self, gate_type: str) -> str:
        """
        Get color for basic gate types
        
        This method returns a distinct color for each gate type to make
        the circuit diagram easier to read and understand.
        
        Args:
            gate_type: String identifying the gate type
            
        Returns:
            Color name string for Graphviz styling
        """
        colors = {
            # Basic logic gates
            'and': 'lightblue',           # Blue for AND gates
            'or': 'lightcyan',            # Cyan for OR gates
            'not': 'lightyellow',         # Yellow for NOT gates (inverters)
            'nand': 'lightsteelblue',     # Steel blue for NAND gates
            'nor': 'lightpink',           # Pink for NOR gates
            'xor': 'lightgoldenrodyellow', # Gold for XOR gates
            'xnor': 'lightgray',          # Gray for XNOR gates
            
            # Arithmetic gates
            'fa': 'lightcoral',           # Coral for Full Adders
            'ha': 'lightpink',            # Pink for Half Adders
            'fs': 'lightgreen',           # Green for Full Subtractors
            'hs': 'lightgreen',           # Green for Half Subtractors
            
            # Multiplexers
            'mux': 'lightblue',           # Blue for general multiplexers
            'mux2': 'lightblue',          # Blue for 2-to-1 MUX
            'mux4': 'lightblue',          # Blue for 4-to-1 MUX
            'buf': 'lightyellow',          # Yellow for buffers / wire assignments
        }
        return colors.get(gate_type, 'lightgray')  # Default gray for unknown types
    
    def _add_connections(self, dot: graphviz.Digraph, module: Module, 
                        net_values: Dict[str, LogicValue], focus_gate: Optional[str]):
        """
        Add connections between nodes with improved labeling
        
        This method creates edges (connections) between nodes in the DOT graph:
        1. Primary inputs to gates
        2. Gates to other gates (internal nets)
        3. Gates to primary outputs
        
        It handles focus mode and avoids duplicate connections.
        
        Args:
            dot: Graphviz Digraph object to add edges to
            module: Module object containing the circuit
            net_values: Dictionary of net names to their current logic values
            focus_gate: Optional gate name to focus on (only show connections to this gate)
        """
        
        # Track connections to avoid duplicates
        added_connections = set()
        
        # Connect primary inputs to gates
        for gate in module.gates:
            # Skip gates not in focus mode if focus_gate is specified
            if focus_gate and gate.name != focus_gate and focus_gate not in gate.name:
                continue
                
            # Connect each input of this gate
            for input_net in gate.inputs:
                # Check if this is a primary input (module port)
                if input_net in module.ports and module.ports[input_net] == 'input':
                    # Connect from primary input node to gate
                    connection = (f"input_{input_net}", gate.name)
                    if connection not in added_connections:
                        dot.edge(f"input_{input_net}", gate.name)
                        added_connections.add(connection)
                else:
                    # Connect from previous gate with wire value label
                    for prev_gate in module.gates:
                        if input_net in prev_gate.outputs:
                            # Create edge label based on whether we have simulation values
                            if net_values and input_net in net_values:
                                # Show values during simulation
                                value_str = net_values[input_net].value
                                # Use short labels for short wire names, just value for long names
                                if len(input_net) <= 3:  # Short wire names like "w1", "c1"
                                    edge_label = f"{input_net}={value_str}"
                                else:
                                    edge_label = value_str  # Just show the value for long names
                            else:
                                # Structure-only mode - no label
                                edge_label = ""
                            
                            # Include net name in connection key to allow multiple edges between same gates
                            connection = (prev_gate.name, gate.name, input_net)
                            if connection not in added_connections:
                                if edge_label:
                                    dot.edge(prev_gate.name, gate.name, label=edge_label)
                                else:
                                    dot.edge(prev_gate.name, gate.name)
                                added_connections.add(connection)
                                break  # Found the source gate for this input, move to next input
        
        # Connect gates to primary outputs
        for gate in module.gates:
            # Skip gates not in focus mode if focus_gate is specified
            if focus_gate and gate.name != focus_gate and focus_gate not in gate.name:
                continue
                
            # Connect each output of this gate
            for output_net in gate.outputs:
                # Check if this is a primary output (module port)
                if output_net in module.ports and module.ports[output_net] == 'output':
                    # Connect from gate to primary output node
                    connection = (gate.name, f"output_{output_net}")
                    if connection not in added_connections:
                        dot.edge(gate.name, f"output_{output_net}")
                        added_connections.add(connection)
                else:
                    # Connect to next gate (handled in the input connection loop above)
                    pass
    
    def _is_final_output(self, module: Module, net_name: str) -> bool:
        """
        Check if a net is a final output of the module
        
        This method determines if a net is a final output by checking:
        1. If it's declared as an output port
        2. If no other gates use it as an input (fanout = 0)
        
        Args:
            module: Module object to check
            net_name: Name of the net to check
            
        Returns:
            True if the net is a final output, False otherwise
        """
        # Check if it's declared as a module output port
        if net_name in module.ports and module.ports[net_name] == 'output':
            return True
        
        # Check if any other gates use this net as an input
        # If no gates use it as input, it's a final output
        for gate in module.gates:
            if net_name in gate.inputs:
                return False  # Net is used as input by another gate, not final
        
        return True  # Net is not used as input by any gate, it's final


class VerilogVisualizer:
    """
    Main class that coordinates the visualization process
    
    This class orchestrates the entire visualization workflow:
    1. Parsing Verilog files
    2. Getting user input for simulation
    3. Running logic simulation
    4. Generating circuit diagrams
    5. Creating output files (DOT and PDF)
    """
    
    def __init__(self):
        """Initialize the visualizer with required components"""
        self.parser = VerilogParser()        # Parser for Verilog files
        self.simulator = None                # Will be initialized with modules
        self.dot_generator = DOTGenerator()  # Generator for DOT files
    
    def visualize(self, verilog_files: List[str], full_mode: bool = False, step_mode: bool = False) -> bool:
        """
        Main visualization function with new workflow:
        1. Generate structure visualization (no simulation values)
        2. Prompt for inputs
        3. Run simulation based on mode (-f full or -s step-by-step)
        
        Args:
            verilog_files: List of Verilog file paths to visualize
            full_mode: If True, run full simulation showing all values
            step_mode: If True, run step-by-step simulation level by level
            
        Returns:
            True if visualization was successful, False otherwise
        """
        
        print("=== Verilog Circuit Visualizer ===")
        print(f"Parsing Verilog file(s): {', '.join(verilog_files)}")
        
        # Parse all Verilog files to extract circuit modules
        all_modules = []
        for verilog_file in verilog_files:
            modules = self.parser.parse_file(verilog_file)
            all_modules.extend(modules)
        
        # Check if any modules were found
        if not all_modules:
            print("Error: No modules found in Verilog files")
            return False
        
        print(f"Found {len(all_modules)} module(s): {', '.join([m.name for m in all_modules])}")
        
        # For hierarchical designs, identify top-level module vs library modules
        # Library modules are typically defined after the main module and only contain gate definitions
        top_module = all_modules[0]  # First module is always the top-level one
        print(f"Top-level module: {top_module.name}")
        if len(all_modules) > 1:
            print(f"Library modules (ignored for visualization): {', '.join([m.name for m in all_modules[1:]])}")
        
        # STEP 1: Generate structure visualization (no simulation values)
        print("\n=== Step 1: Generating Circuit Structure ===")
        base_filename = os.path.splitext(os.path.basename(verilog_files[0]))[0]
        structure_name = f"{base_filename}_structure"
        
        # Generate DOT with no values - only visualize top-level module
        structure_dot = self.dot_generator.generate_dot([top_module], {}, None)
        
        # Write structure DOT file
        structure_dot_file = f"{structure_name}.dot"
        with open(structure_dot_file, 'w') as f:
            f.write(structure_dot)
        
        # Generate structure PDF
        try:
            dot = graphviz.Source(structure_dot)
            dot.render(structure_name, format='pdf', cleanup=True)
            print(f"[SUCCESS] Generated structure visualization: {structure_name}.pdf")
            print(f"          (Circuit diagram without simulation values)")
        except Exception as e:
            print(f"Error generating structure PDF: {e}")
            return False

        # Generate highest-level (single-block) visualization of the top-level module
        try:
            highest_level_name = f"{base_filename}_highest_level"
            high_level_dot = self.dot_generator.generate_high_level_dot([top_module])

            # Write highest-level DOT file
            highest_level_dot_file = f"{highest_level_name}.dot"
            with open(highest_level_dot_file, 'w') as f:
                f.write(high_level_dot)

            # Generate highest-level PDF
            high_level_graph = graphviz.Source(high_level_dot)
            high_level_graph.render(highest_level_name, format='pdf', cleanup=True)
            print(f"[SUCCESS] Generated highest-level visualization: {highest_level_name}.pdf")
            print(f"          (Single-block view of the top-level module)")
        except Exception as e:
            print(f"Warning: Error generating highest-level PDF: {e}")
        
        # STEP 2: Detect and prompt for inputs
        print("\n=== Step 2: Input Configuration ===")
        
        # Count primary inputs from TOP-LEVEL module only (first module in the list)
        # For hierarchical designs, only the first module is the actual circuit
        top_module = all_modules[0]  # First module is the top-level one
        
        # Identify array ports and single-bit ports
        # Array ports have indexed versions (e.g., X[0], X[1], etc. exist if X is an array)
        array_ports = {}  # Maps base_name -> list of bit indices (e.g., 'X' -> ['0','1','2','3','4'])
        single_bit_inputs = set()
        
        # First pass: collect all array elements
        for port, direction in top_module.ports.items():
            if direction == 'input' and '[' in port and ']' in port:
                # This is an array element (e.g., X[4])
                base_name = port.split('[')[0]
                bit_index = port.split('[')[1].split(']')[0]
                
                if base_name not in array_ports:
                    array_ports[base_name] = []
                if bit_index not in array_ports[base_name]:
                    array_ports[base_name].append(bit_index)
        
        # Second pass: identify single-bit inputs (exclude base names that have arrays)
        for port, direction in top_module.ports.items():
            if direction == 'input':
                # Skip array elements (already processed)
                if '[' in port and ']' in port:
                    continue
                
                # Skip base names that have array elements
                if port not in array_ports:
                    # This is a true single-bit input
                    single_bit_inputs.add(port)
        
        # Count inputs: arrays count as 1, single bits count as 1 each
        primary_input_count = len(array_ports) + len(single_bit_inputs)
        
        # Build display string showing array sizes
        input_names = []
        for base_name in sorted(array_ports.keys()):
            indices = sorted(array_ports[base_name], key=lambda x: int(x) if x.isdigit() else 999)
            array_size = len(indices)
            input_names.append(f"{base_name}[{array_size-1}:0] ({array_size} bits)")
        for name in sorted(single_bit_inputs):
            input_names.append(name)
        
        print(f"This circuit requires {primary_input_count} input(s): {', '.join(input_names)}")
        print(f"(Top-level module: {top_module.name})")
        
        # Calculate total bits needed (for input file validation)
        total_bits_needed = sum(len(indices) for indices in array_ports.values()) + len(single_bit_inputs)
        
        # Prompt for input file
        input_file = self._prompt_for_input_file_path()
        
        # Load input values with array information
        input_values = self._load_input_values_from_file_hierarchical(
            input_file, array_ports, single_bit_inputs, total_bits_needed
        )
        if not input_values:
            print("Error: Failed to load input values")
            return False
        
        # STEP 3: Run simulation based on mode
        print("\n=== Step 3: Running Simulation ===")
        
        # Initialize simulator
        self.simulator = LogicSimulator(all_modules)
        self.simulator.set_inputs(input_values)
        
        simulation_name = f"{base_filename}_simulation"
        
        net_values = None
        if full_mode:
            # Full simulation mode - show all values at once
            print("Mode: Full simulation (showing all values)")
            net_values = self._run_full_simulation(all_modules, simulation_name)
        
        elif step_mode:
            # Step-by-step simulation mode - level by level
            print("Mode: Step-by-step simulation (level by level)")
            net_values = self._run_step_simulation(all_modules, simulation_name)
        
        # STEP 4: Generate higher-level simulation view
        if net_values:
            print("\n=== Step 4: Generating Higher-Level Simulation View ===")
            high_sim_name = f"{base_filename}_high_level_simulation"
            try:
                high_sim_dot = self.dot_generator.generate_high_level_simulation_dot(
                    [top_module], net_values
                )
                with open(f"{high_sim_name}.dot", 'w') as f:
                    f.write(high_sim_dot)
                high_sim_graph = graphviz.Source(high_sim_dot)
                high_sim_graph.render(high_sim_name, format='pdf', cleanup=True)
                print(f"[SUCCESS] Generated higher-level simulation: {high_sim_name}.pdf")
                print(f"          (Sub-modules shown as blocks with simulation values)")
            except Exception as e:
                print(f"Warning: Error generating higher-level simulation PDF: {e}")

        # After main simulation, offer local gate simulation
        if net_values:
            self._prompt_for_local_gate_simulation(all_modules, net_values)
            
        return True

    def _prompt_for_local_gate_simulation(self, modules: List[Module], net_values: Dict[str, LogicValue]):
        """
        Interactive loop for simulating individual gates locally
        
        Args:
            modules: List of modules containing gates
            net_values: Dictionary of net values from the main simulation
        """
        while True:
            print("\n=== Local Gate Simulation ===")
            print("You can simulate a specific gate in isolation using inputs from the main simulation.")
            response = input("Do you want to simulate a specific gate? (y/n): ").strip().lower()
            
            if response != 'y':
                break
            
            # Collect all gates from all modules
            all_gates = []
            for module in modules:
                all_gates.extend(module.gates)
            
            # Prompt for gate name
            gate_name = input("Enter gate name (e.g., XOR1, FA0): ").strip()
            
            # Find the gate
            target_gate = None
            for gate in all_gates:
                if gate.name == gate_name:
                    target_gate = gate
                    break
            
            if not target_gate:
                print(f"Error: Gate '{gate_name}' not found.")
                continue
            
            # Check if gate type is supported
            supported_types = ['fa', 'ha', 'fs', 'hs', 'mux2', 'mux4', 
                               'and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor']
            
            if target_gate.gate_type not in supported_types and not target_gate.gate_type.startswith('mux'):
                 print(f"Warning: Gate type '{target_gate.gate_type}' might not be fully supported for visualization.")
            
            # Check if this gate corresponds to a known module definition
            # We need to find the original module name (before mapping to 'fa', 'ha', etc.)
            # But we don't store the original type in Gate, so we check both current type and guess
            
            target_module_def = None
            
            # Try to find a matching module definition
            # 1. Check if gate_type matches a module name directly (e.g. 'full_adder')
            # 2. Check if any module maps to this gate type (e.g. 'full_adder' -> 'fa')
            
            for module in modules:
                # Check exact name match (if we stored original type, which we don't, but let's try common names)
                if module.name == target_gate.gate_type:
                    target_module_def = module
                    break
                
                # Check common mappings
                if target_gate.gate_type == 'fa' and module.name in ['full_adder', 'FullAdder']:
                    target_module_def = module
                    break
                if target_gate.gate_type == 'ha' and module.name in ['half_adder', 'HalfAdder']:
                    target_module_def = module
                    break
                if target_gate.gate_type == 'fs' and module.name in ['full_subtractor', 'FullSubtractor']:
                    target_module_def = module
                    break
                if target_gate.gate_type == 'hs' and module.name in ['half_subtractor', 'HalfSubtractor']:
                    target_module_def = module
                    break
            
            local_output_name = f"local_simulation_{target_gate.name}"
            
            if target_module_def and target_gate.port_map:
                print(f"Found module definition '{target_module_def.name}' for gate '{target_gate.name}'. Visualizing internals.")
                
                # Create a new simulator for the submodule
                sub_simulator = LogicSimulator([target_module_def])
                
                # Map parent nets to submodule inputs
                # target_gate.port_map maps port_name -> parent_net_name
                # We need to set input_values for the submodule based on parent_net values
                
                sub_input_values = {}
                for port_name, parent_net_name in target_gate.port_map.items():
                    # Check if this port is an input in the submodule definition
                    # Handle array ports (e.g. a[0])
                    is_input = False
                    clean_port_name = port_name.split('[')[0]
                    
                    if port_name in target_module_def.ports and target_module_def.ports[port_name] == 'input':
                        is_input = True
                    elif clean_port_name in target_module_def.ports and target_module_def.ports[clean_port_name] == 'input':
                        is_input = True
                        
                    if is_input:
                        # Get value from parent simulation
                        if parent_net_name in net_values:
                            val = net_values[parent_net_name]
                            sub_input_values[port_name] = val
                        else:
                            # Default to 0 if not found (shouldn't happen if map is correct)
                            sub_input_values[port_name] = LogicValue.ZERO
                
                # Set inputs for the submodule simulator
                sub_simulator.set_inputs(sub_input_values)
                
                # Run simulation for the submodule
                sub_net_values = sub_simulator.simulate()
                
                # Generate DOT/PDF for the submodule
                dot_content = self.dot_generator.generate_dot([target_module_def], sub_net_values, None)
                
            else:
                # Fallback to black-box visualization (primitive gate or no module def found)
                if not target_module_def:
                    print(f"No module definition found for '{target_gate.gate_type}'. Visualizing as primitive.")
                
                # Create a temporary module for this gate to allow visualization
                # We map gate inputs/outputs to module ports so they get rendered as input/output nodes
                temp_ports = {}
                for input_net in target_gate.inputs:
                    temp_ports[input_net] = 'input'
                for output_net in target_gate.outputs:
                    temp_ports[output_net] = 'output'
                    
                temp_module = Module(
                    name=f"{target_gate.name}_local",
                    ports=temp_ports,
                    gates=[target_gate],
                    nets={} # Nets are handled by net_values
                )
                
                # Use the existing net_values which contain the state of all wires
                dot_content = self.dot_generator.generate_dot([temp_module], net_values, None)
            
            # Write DOT file
            with open(f"{local_output_name}.dot", 'w') as f:
                f.write(dot_content)
                
            # Generate PDF
            try:
                dot = graphviz.Source(dot_content)
                dot.render(local_output_name, format='pdf', cleanup=True)
                print(f"[SUCCESS] Generated local simulation: {local_output_name}.pdf")
            except Exception as e:
                print(f"Error generating PDF: {e}")
            
            # Ask to continue
            print("-" * 30)
    
    def _prompt_for_input_file_path(self) -> str:
        """
        Prompt user for input file path
        
        Returns:
            File path string
        """
        while True:
            response = input("\nEnter input file path: ").strip()
            
            # Check if the provided file exists
            if os.path.exists(response):
                print(f"[OK] Input file found: {response}")
                return response
            else:
                print(f"[ERROR] File '{response}' not found. Please try again.")
    
    def _load_input_values_from_file(self, input_file: str, primary_inputs: Set[str]) -> Dict[str, LogicValue]:
        """
        Load input values from a file containing a single line of 0s and 1s
        
        Args:
            input_file: Path to the input file
            primary_inputs: Set of primary input names
            
        Returns:
            Dictionary mapping input names to logic values
        """
        input_values = {}
        
        try:
            with open(input_file, 'r') as f:
                content = f.read().strip()
            
            # Remove any whitespace
            content = content.replace(' ', '').replace('\n', '').replace('\r', '')
            
            # Check if we have enough bits
            sorted_inputs = sorted(primary_inputs)
            if len(content) != len(sorted_inputs):
                print(f"Error: Input file has {len(content)} bits but circuit needs {len(sorted_inputs)} inputs")
                return {}
            
            # Map each bit to each input in sorted order
            print("\nMapping inputs:")
            for i, input_name in enumerate(sorted_inputs):
                bit = content[i]
                if bit == '0':
                    input_values[input_name] = LogicValue.ZERO
                    print(f"  {input_name} = 0")
                elif bit == '1':
                    input_values[input_name] = LogicValue.ONE
                    print(f"  {input_name} = 1")
                else:
                    print(f"Error: Invalid bit '{bit}' at position {i}")
                    return {}
            
            return input_values
            
        except Exception as e:
            print(f"Error reading input file: {e}")
            return {}
    
    def _load_input_values_from_file_hierarchical(
        self, input_file: str, array_ports: Dict[str, List[str]], 
        single_bit_inputs: Set[str], total_bits_needed: int
    ) -> Dict[str, LogicValue]:
        """
        Load input values from a file for hierarchical designs with array ports
        
        This method handles array inputs by reading bits sequentially and assigning
        them to the correct array indices. For example, X[4:0] would read 5 bits
        and assign them to X[0], X[1], ..., X[4].
        
        Args:
            input_file: Path to the input file
            array_ports: Dictionary mapping base array names to their bit indices
                         e.g., {'X': ['0','1','2','3','4'], 'D': ['0','1','2']}
            single_bit_inputs: Set of single-bit input port names
            total_bits_needed: Total number of bits needed (for validation)
            
        Returns:
            Dictionary mapping input names (including array indices) to logic values
        """
        input_values = {}
        
        try:
            with open(input_file, 'r') as f:
                content = f.read().strip()
            
            # Remove any whitespace
            content = content.replace(' ', '').replace('\n', '').replace('\r', '')
            
            # Validate total bits
            if len(content) != total_bits_needed:
                print(f"Error: Input file has {len(content)} bits but circuit needs {total_bits_needed} bits")
                print(f"  Arrays: {sum(len(indices) for indices in array_ports.values())} bits")
                print(f"  Single bits: {len(single_bit_inputs)} bits")
                return {}
            
            bit_position = 0
            print("\nMapping inputs:")
            
            # Process array ports first (in sorted order)
            for base_name in sorted(array_ports.keys()):
                indices = sorted(array_ports[base_name], key=lambda x: int(x) if x.isdigit() else 999)
                
                # Determine MSB and LSB
                msb_idx = max(int(i) for i in indices if i.isdigit()) if indices and indices[0].isdigit() else 0
                lsb_idx = min(int(i) for i in indices if i.isdigit()) if indices and indices[0].isdigit() else 0
                
                # Read bits for this array (MSB to LSB - standard Verilog convention)
                # File format: leftmost bit = MSB, rightmost bit = LSB
                # So we need to read in descending index order (MSB first)
                array_bits = []
                array_bits_map = {}  # Store bits by index for proper ordering
                
                # Sort indices in descending order for MSB-first reading
                indices_desc = sorted(indices, key=lambda x: int(x) if x.isdigit() else 999, reverse=True)
                
                # Read bits from file (MSB first)
                for idx_str in indices_desc:
                    if bit_position >= len(content):
                        print(f"Error: Not enough bits in input file")
                        return {}
                    
                    bit = content[bit_position]
                    idx = int(idx_str) if idx_str.isdigit() else 0
                    
                    if bit == '0':
                        input_values[f"{base_name}[{idx}]"] = LogicValue.ZERO
                        array_bits_map[idx] = '0'
                        array_bits.append('0')  # For display
                    elif bit == '1':
                        input_values[f"{base_name}[{idx}]"] = LogicValue.ONE
                        array_bits_map[idx] = '1'
                        array_bits.append('1')  # For display
                    else:
                        print(f"Error: Invalid bit '{bit}' at position {bit_position}")
                        return {}
                    bit_position += 1
                
                # Display array input (show as MSB:LSB format)
                # array_bits is already in MSB-first order from file reading
                array_bits_str = ''.join(array_bits)
                print(f"  {base_name}[{msb_idx}:{lsb_idx}] = {array_bits_str} ({len(indices)} bits)")
            
            # Process single-bit inputs
            for input_name in sorted(single_bit_inputs):
                if bit_position >= len(content):
                    print(f"Error: Not enough bits in input file")
                    return {}
                
                bit = content[bit_position]
                if bit == '0':
                    input_values[input_name] = LogicValue.ZERO
                    print(f"  {input_name} = 0")
                elif bit == '1':
                    input_values[input_name] = LogicValue.ONE
                    print(f"  {input_name} = 1")
                else:
                    print(f"Error: Invalid bit '{bit}' at position {bit_position}")
                    return {}
                bit_position += 1
            
            return input_values
            
        except Exception as e:
            print(f"Error reading input file: {e}")
            return {}
    
    def _run_full_simulation(self, modules: List[Module], output_name: str) -> Optional[Dict[str, LogicValue]]:
        """
        Run full simulation and generate visualization with all values
        
        Args:
            modules: List of modules to simulate
            output_name: Base name for output files
            
        Returns:
            Dictionary of net values if successful, None otherwise
        """
        # Run complete simulation (uses all modules for hierarchical support)
        print("Running full circuit simulation...")
        net_values = self.simulator.simulate()
        
        # Generate DOT file with all values - only visualize top-level module
        top_module = modules[0] if modules else None
        dot_content = self.dot_generator.generate_dot([top_module] if top_module else modules, net_values, None)
        
        # Write DOT file
        dot_filename = f"{output_name}.dot"
        with open(dot_filename, 'w') as f:
            f.write(dot_content)
        
        # Generate PDF
        try:
            dot = graphviz.Source(dot_content)
            dot.render(output_name, format='pdf', cleanup=True)
            print(f"\n[SUCCESS] Generated simulation: {output_name}.pdf")
            print(f"          (Shows all values throughout the circuit)")
            return net_values
        except Exception as e:
            print(f"Error generating simulation PDF: {e}")
            return None
    
    def _run_step_simulation(self, modules: List[Module], output_name: str) -> Optional[Dict[str, LogicValue]]:
        """
        Run step-by-step simulation, showing one level at a time
        
        Args:
            modules: List of modules to simulate
            output_name: Base name for output files
            
        Returns:
            Dictionary of final net values if successful, None otherwise
        """
        # Calculate maximum depth
        gate_depths = self.simulator.calculate_gate_depths()
        max_depth = max(gate_depths.values()) if gate_depths else 0
        
        print(f"Circuit has {max_depth} level(s) of gates")
        print("Press Enter to show each level...")
        
        final_net_values = {}
        
        # Step through each level
        for level in range(max_depth + 1):
            input(f"\nPress Enter to show level {level}...")
            
            # Simulate up to this level (uses all modules for hierarchical support)
            net_values = self.simulator.simulate_by_level(level)
            final_net_values = net_values
            
            # Generate DOT file with values up to this level - only visualize top-level module
            top_module = modules[0] if modules else None
            dot_content = self.dot_generator.generate_dot([top_module] if top_module else modules, net_values, None)
            
            # Write DOT file (overwrite previous)
            dot_filename = f"{output_name}.dot"
            with open(dot_filename, 'w') as f:
                f.write(dot_content)
            
            # Generate PDF (overwrite previous)
            try:
                dot = graphviz.Source(dot_content)
                dot.render(output_name, format='pdf', cleanup=True)
                print(f"[OK] Updated {output_name}.pdf (level {level}/{max_depth})")
            except Exception as e:
                print(f"Error generating PDF: {e}")
                return None
        
        print(f"\n[SUCCESS] Simulation complete! Final result in {output_name}.pdf")
        return final_net_values
    
    def _load_input_values(self, input_file: Optional[str], 
                          modules: List[Module]) -> Dict[str, LogicValue]:
        """
        Load input values from file or prompt user for manual entry
        
        This method determines all primary inputs in the circuit and loads their
        values either from a file or through interactive user prompts.
        
        Args:
            input_file: Optional path to input file with values
            modules: List of Module objects to analyze for inputs
            
        Returns:
            Dictionary mapping input net names to their logic values
        """
        input_values = {}
        
        # Get all primary inputs from the circuit
        # Primary inputs include both declared ports and gate inputs that aren't driven by other gates
        all_inputs = set()
        
        for module in modules:
            # Add declared input ports
            for port, direction in module.ports.items():
                if direction == 'input':
                    all_inputs.add(port)
            
            # For mapped/flat designs, only use declared ports as primary inputs
            # Skip the gate connection analysis to avoid false primary inputs
            # This prevents internal nets from being treated as primary inputs
        
        # Load values from file if provided
        if input_file and os.path.exists(input_file):
            print(f"Loading input values from: {input_file}")
            with open(input_file, 'r') as f:
                content = f.read().strip()
                # Parse input assignments in format: "A=1, B=0, Cin=1"
                assignments = content.split(',')
                for assignment in assignments:
                    assignment = assignment.strip()
                    if '=' in assignment:
                        port, value = assignment.split('=')
                        port = port.strip()
                        value = value.strip()
                        
                        # Convert string values to LogicValue enum
                        if value == '1':
                            input_values[port] = LogicValue.ONE
                        elif value == '0':
                            input_values[port] = LogicValue.ZERO
                        else:
                            input_values[port] = LogicValue.X  # Unknown/invalid value
        else:
            # Manual input entry through interactive prompts
            print(f"\n--- Manual Input Entry ---")
            print(f"Circuit analysis detected {len(all_inputs)} primary input(s): {', '.join(sorted(all_inputs))}")
            print("Enter logic values for each input:")
            print("  • 0 = Logic LOW")
            print("  • 1 = Logic HIGH") 
            print("  • x = Unknown/undefined")
            print("  • Press Enter for unknown (default)\n")
            
            # Prompt user for each input
            for i, port in enumerate(sorted(all_inputs), 1):
                while True:
                    value = input(f"[{i}/{len(all_inputs)}] Enter value for input '{port}': ").strip().lower()
                    
                    # Handle different input formats
                    if value == '':
                        input_values[port] = LogicValue.X
                        print(f"  [OK] {port} = X (unknown)")
                        break
                    elif value == '0':
                        input_values[port] = LogicValue.ZERO
                        print(f"  [OK] {port} = 0 (LOW)")
                        break
                    elif value == '1':
                        input_values[port] = LogicValue.ONE
                        print(f"  [OK] {port} = 1 (HIGH)")
                        break
                    elif value == 'x':
                        input_values[port] = LogicValue.X
                        print(f"  [OK] {port} = X (unknown)")
                        break
                    else:
                        print("  [ERROR] Invalid input. Please enter: 0, 1, x, or press Enter for unknown")
            
            print(f"\nInput configuration complete! Set {len(input_values)} input(s).")
        
        return input_values
    
    def _prompt_for_input_file(self) -> Optional[str]:
        """
        Prompt user for input file path
        
        This method asks the user to provide a file path containing input values,
        or allows them to skip and enter values manually.
        
        Returns:
            File path string if provided, None if user chooses manual entry
        """
        while True:
            response = input("Enter input file path (or type 'n' for no input file): ").strip()
            
            # Handle user choice to skip file input
            if response.lower() == 'n' or response.lower() == 'no':
                print("No input file specified. You'll be prompted for input values.")
                return None
            
            # Check if the provided file exists
            elif os.path.exists(response):
                print(f"Input file found: {response}")
                return response
            
            # File not found - ask user to try again
            else:
                print(f"File '{response}' not found. Please try again or type 'n' for no input file.")
    
    def _prompt_for_focus_gate(self, modules: List[Module]) -> Optional[str]:
        """
        Prompt user for focus gate selection
        
        This method allows the user to select a specific gate to focus on,
        which will highlight only that gate and its connections in the diagram.
        
        Args:
            modules: List of Module objects to extract gate names from
            
        Returns:
            Gate name string if selected, None if user chooses full diagram mode
        """
        # Collect all available gates from all modules
        all_gates = []
        for module in modules:
            for gate in module.gates:
                all_gates.append(gate.name)
        
        # Check if any gates were found
        if not all_gates:
            print("No gates found in the circuit.")
            return None
        
        print("Available gates:", ", ".join(all_gates))
        
        # Prompt user for gate selection
        while True:
            response = input("Enter gate name to focus on (or type 'n' for full diagram): ").strip()
            
            # Handle user choice for full diagram mode
            if response.lower() == 'n' or response.lower() == 'no':
                print("Full diagram mode selected.")
                return None
            
            # Check if the provided gate name exists
            elif response in all_gates:
                print(f"Focus mode selected: {response}")
                return response
            
            # Gate not found - show available gates and ask again
            else:
                print(f"Gate '{response}' not found. Available gates: {', '.join(all_gates)}")
                print("Please try again or type 'n' for full diagram.")


def main():
    """
    Main function with interactive interface
    
    This function handles command-line argument parsing and orchestrates
    the complete visualization process. It provides a user-friendly interface
    for running the Verilog circuit visualizer.
    """
    # Set up command-line argument parser with helpful descriptions and examples
    parser = argparse.ArgumentParser(
        description='Visualize and simulate Verilog circuits interactively',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verilog_visualizer.py circuit.v -f
  python verilog_visualizer.py circuit.v -s
  python verilog_visualizer.py *.v -f
  python verilog_visualizer.py 4-bit-add-hier.v 4_mapped.v -s
        """
    )
    
    # Define command-line argument for Verilog files
    parser.add_argument('verilog_files', nargs='+', 
                       help='Verilog file(s) to visualize')
    
    # Add simulation mode arguments
    sim_group = parser.add_mutually_exclusive_group()
    sim_group.add_argument('-f', '--full', action='store_true',
                          help='Run full simulation (show all values at once)')
    sim_group.add_argument('-s', '--step', action='store_true',
                          help='Run step-by-step simulation (level by level)')
    
    # Parse command-line arguments
    args = parser.parse_args()
    
    # Validate that all specified Verilog files exist
    for verilog_file in args.verilog_files:
        if not os.path.exists(verilog_file):
            print(f"Error: Verilog file '{verilog_file}' not found")
            sys.exit(1)  # Exit with error code 1 if file not found
    
    # Check if simulation mode is specified
    if not args.full and not args.step:
        print("Error: You must specify a simulation mode:")
        print("  -f or --full : Run full simulation (show all values at once)")
        print("  -s or --step : Run step-by-step simulation (level by level)")
        sys.exit(1)
    
    # Create visualizer instance and run the visualization process
    visualizer = VerilogVisualizer()
    success = visualizer.visualize(verilog_files=args.verilog_files, 
                                   full_mode=args.full, 
                                   step_mode=args.step)
    
    # Check if visualization was successful
    if not success:
        print("Visualization failed!")
        sys.exit(1)  # Exit with error code 1 if visualization failed


if __name__ == '__main__':
    # Only run main() when script is executed directly (not imported)
    main()
