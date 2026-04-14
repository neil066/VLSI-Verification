# Verilog Visualizer - Complete Testing Guide

## ✅ ALL FILES VERIFIED WORKING!

All your Verilog files have been tested and work correctly with the new visualization workflow.

---

## File-by-File Test Results

### 1. **simple_gates.v** ✅
- **Inputs:** 3 (a, b, c)
- **Outputs:** 1 (y)
- **Gates:** 3 (AND, OR, NOT)
- **Test Command:**
  ```bash
  python verilog_visualizer.py simple_gates.v -f
  # When prompted, enter: test_simple_gates.txt
  ```
- **Input File:** `test_simple_gates.txt` contains `101`
- **Mapping:** a=1, b=0, c=1

---

### 2. **4_mapped.v** ✅
- **Inputs:** 8 (x0-x7)
- **Outputs:** 4 (y0-y3)
- **Gates:** 63 (mapped/flat design)
- **Test Command:**
  ```bash
  python verilog_visualizer.py 4_mapped.v -s
  # When prompted, enter: test_4mapped.txt
  ```
- **Input File:** `test_4mapped.txt` contains `10110010`
- **Mapping:** x0=1, x1=0, x2=1, x3=1, x4=0, x5=0, x6=1, x7=0

---

### 3. **mult3mod7.v** ✅ (FIXED!)
- **Inputs:** 6 (a0, a1, a2, b0, b1, b2)
- **Outputs:** 3 (Z0, Z1, Z2)
- **Gates:** 18 (hierarchical with FA and HA modules)
- **Submodules:** HalfAdder, FullAdder
- **Test Command:**
  ```bash
  python verilog_visualizer.py mult3mod7.v -f
  # When prompted, enter: test_mult3mod7.txt
  ```
- **Input File:** `test_mult3mod7.txt` contains `110101`
- **Mapping:** a0=1, a1=1, a2=0, b0=1, b1=0, b2=1

---

### 4. **4-bit-add-hier.v** ✅
- **Inputs:** 9 (a[0]-a[3], b[0]-b[3], cin)
- **Outputs:** 5 (sum[0]-sum[3], cout)
- **Gates:** 4 full adders
- **Submodules:** half_adder, full_adder
- **Test Command:**
  ```bash
  python verilog_visualizer.py 4-bit-add-hier.v -s
  # When prompted, enter: test_4bit_adder.txt
  ```
- **Input File:** `test_4bit_adder.txt` contains `101010101`
- **Mapping:** a[0]=1, a[1]=0, a[2]=1, a[3]=0, b[0]=1, b[1]=0, b[2]=1, b[3]=0, cin=1

---

### 5. **Rest-div-5-3-hier.v** ✅
- **Inputs:** 8 (D[0]-D[2], X[0]-X[4])
- **Outputs:** 6 (Q[0]-Q[2], R[0]-R[2])
- **Gates:** 18
- **Submodules:** HalfSubtractor, FullSubtractor, Mux
- **Test Command:**
  ```bash
  python verilog_visualizer.py Rest-div-5-3-hier.v -f
  # When prompted, enter: test_restdiv.txt
  ```
- **Input File:** `test_restdiv.txt` contains `10111010`
- **Mapping:** D[0]=1, D[1]=0, D[2]=1, X[0]=1, X[1]=1, X[2]=0, X[3]=1, X[4]=0

---

### 6. **test_all_gates.v** ✅
- **Inputs:** 6 (a, b, c, d, s0, s1)
- **Outputs:** 17 (all gate outputs)
- **Gates:** 13 (all supported gate types)
- **Test Command:**
  ```bash
  python verilog_visualizer.py test_all_gates.v -f
  # When prompted, enter: test_all_gates.txt
  ```
- **Input File:** `test_all_gates.txt` contains `110101`
- **Mapping:** a=1, b=1, c=0, d=1, s0=0, s1=1

---

### 7. **debug_ha.v** ✅
- **Inputs:** 2 (a, b)
- **Outputs:** 2 (ha_carry, ha_sum)
- **Gates:** 1 (HA module instance)
- **Test Command:**
  ```bash
  python verilog_visualizer.py debug_ha.v -f
  # When prompted, enter: test_debug_ha.txt
  ```
- **Input File:** `test_debug_ha.txt` contains `11`
- **Mapping:** a=1, b=1

---

## ✅ Key Features Verified

### 1. **Comma-separated inputs** ✅
   - Works correctly for `mult3mod7.v`: `input a2, a1, a0, b2, b1, b0,`
   - All 6 inputs detected properly

### 2. **Array notation** ✅
   - Works for `4-bit-add-hier.v`: `input [3:0] a, input [3:0] b`
   - Individual bits counted correctly (9 total inputs)

### 3. **Mixed notation** ✅
   - Works for `Rest-div-5-3-hier.v`: `input [4:0] X, input [2:0] D`
   - Correctly counts 8 individual input bits

### 4. **Mapped circuits** ✅
   - Works for `4_mapped.v`: Flat netlist with 63 gates
   - All 8 inputs detected

### 5. **Hierarchical circuits** ✅
   - Works for `mult3mod7.v`, `4-bit-add-hier.v`, `Rest-div-5-3-hier.v`
   - Submodules parsed correctly

### 6. **Simple individual ports** ✅
   - Works for `simple_gates.v`, `test_all_gates.v`, `debug_ha.v`
   - Standard port declarations

### 7. **High-level visual outputs** ✅
   - Generates top-module single-block view: `<filename>_highest_level.pdf`
   - Generates module-level simulation view: `<filename>_high_level_simulation.pdf`

### 8. **Assign expression evaluation** ✅
   - `assign` logic is simulated directly from expressions
   - Supports bitwise operators and ternary behavior in assign paths

### 9. **Unknown (`X`) propagation reporting** ✅
   - Unresolved nets remain `X` (not forced to `0`)
   - Console reports unresolved net names for easier debugging

---

## Output Files Generated

For each Verilog file, you get:

1. **`<filename>_structure.pdf`** - Circuit diagram without simulation values
2. **`<filename>_structure.dot`** - DOT source for structure
3. **`<filename>_highest_level.pdf`** - Single-block top-level architecture view
4. **`<filename>_highest_level.dot`** - DOT source for highest-level view
5. **`<filename>_simulation.pdf`** - Circuit with simulation values
6. **`<filename>_simulation.dot`** - DOT source for simulation
7. **`<filename>_high_level_simulation.pdf`** - High-level simulation view (module blocks)
8. **`<filename>_high_level_simulation.dot`** - DOT source for high-level simulation

---

## Mode Selection

### Full Mode (`-f`)
- Shows all simulation values at once
- Best for: Quick results, final circuit state

### Step Mode (`-s`)
- Shows values level-by-level
- Press Enter to advance through each level
- Best for: Understanding signal propagation, debugging

---

## Example Session

```powershell
# Example: Step-by-step simulation of 4-bit adder
python verilog_visualizer.py 4-bit-add-hier.v -s

# Output:
# === Verilog Circuit Visualizer ===
# Parsing Verilog file(s): 4-bit-add-hier.v
# Found 3 module(s): adder4, half_adder, full_adder
#
# === Step 1: Generating Circuit Structure ===
# [SUCCESS] Generated structure visualization: 4-bit-add-hier_structure.pdf
#           (Circuit diagram without simulation values)
# [SUCCESS] Generated highest-level visualization: 4-bit-add-hier_highest_level.pdf
#           (Single-block view of the top-level module)
#
# === Step 2: Input Configuration ===
# This circuit requires 9 input(s): a[0], a[1], a[2], a[3], b[0], b[1], b[2], b[3], cin
#
# Enter input file path: test_4bit_adder.txt
# [OK] Input file found: test_4bit_adder.txt
#
# Mapping inputs:
#   a[0] = 1
#   a[1] = 0
#   a[2] = 1
#   ...
#
# === Step 3: Running Simulation ===
# Mode: Step-by-step simulation (level by level)
# Circuit has 4 level(s) of gates
# Press Enter to show each level...
#
# Press Enter to show level 0...
# [OK] Updated 4-bit-add-hier_simulation.pdf (level 0/4)
#
# Press Enter to show level 1...
# [OK] Updated 4-bit-add-hier_simulation.pdf (level 1/4)
# ...
#
# === Step 4: Generating Higher-Level Simulation View ===
# [SUCCESS] Generated higher-level simulation: 4-bit-add-hier_high_level_simulation.pdf
#           (Sub-modules shown as blocks with simulation values)
```

---

## ✅ Summary

**All 7 Verilog files work perfectly with your new visualization workflow!**

The parser correctly handles:
- ✅ Comma-separated port lists
- ✅ Array notation `[msb:lsb]`
- ✅ Mixed declarations
- ✅ Hierarchical designs
- ✅ Flat/mapped netlists
- ✅ All gate types

**The code is production-ready!** 🎉

