# Bonn Shutter Control

Control and integration software for the **Bonn shutter mechanism** using **Python, C, and C++**.

This repository provides a multi-language control stack for operating a hardware shutter system, supporting integration into larger instrument or data acquisition workflows. The project is designed to combine:

- **Python** for high-level simple testing and controls 
- **C/C++** for low-level hardware communication and performance-critical control  

## Features

- Hardware shutter command and control interface  
- Python tools for communication and simple integration  
- C/C++ backend components for device-level operation  
- Modular design intended for instrument control environments  

## Repository Structure

Typical components in this repository include:

- `bonn_shutter.py` — Main Python shutter control module  
- `python/` — Additional Python interfaces and utilities  
- `src/` or `cpp/` — Core C/C++ shutter control implementation  
- `include/` — Header files for driver and interface code  
- `examples/` — Example usage and test programs  
- `docs/` — Additional documentation (if available)  

(Directory names may vary depending on development stage.)

## Requirements

- Python 3.8+  
- C/C++ compiler
- Additional dependencies may be required depending on the target hardware interface  

### Python Base Class Dependency

The Python shutter controller is built using a shared hardware abstraction base class:

```python
from hardware_device_base import HardwareMotionBase
